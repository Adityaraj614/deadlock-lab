"""In-memory live simulation session for the Warehouse Lab API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.algorithms.astar import a_star
from app.algorithms.reservation_table import ReservationTable
from app.environments.scenario_loader import load_scenario
from app.metrics.metrics import SimulationMetrics
from app.models.action import Action, ActionType
from app.models.agent import Agent, AgentStatus
from app.models.goal import Goal
from app.models.obstacle import Obstacle
from app.models.position import Position
from app.simulation.engine import SimulationEngine
from app.simulation.multi_agent_executor import CoordinationStrategy
from app.simulation.state import SimulationState


def _build_state(scenario_name: str) -> SimulationState:
    environment = load_scenario(scenario_name)
    return SimulationState(
        grid_width=environment.grid_width,
        grid_height=environment.grid_height,
        agents=[agent.model_copy(deep=True) for agent in environment.agents],
        obstacles=[obstacle.model_copy(deep=True) for obstacle in environment.obstacles],
        goals=[goal.model_copy(deep=True) for goal in environment.goals],
    )


@dataclass
class SimulationSession:
    scenario_name: str | None = None
    initial_state: SimulationState | None = None
    engine: SimulationEngine | None = None
    metrics: SimulationMetrics = field(default_factory=SimulationMetrics)
    strategy: CoordinationStrategy = CoordinationStrategy.FULL
    max_steps: int = 100
    reservation_table: ReservationTable | None = None
    replay: list[dict[str, Any]] = field(default_factory=list)
    paused: bool = False

    def load(
        self,
        scenario_name: str,
        strategy: CoordinationStrategy = CoordinationStrategy.FULL,
        max_steps: int = 100,
    ) -> SimulationState:
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1")
        state = _build_state(scenario_name)
        self.scenario_name = scenario_name
        self.initial_state = state.model_copy(deep=True)
        self.metrics = SimulationMetrics()
        self.strategy = strategy
        self.max_steps = max_steps
        self.reservation_table = ReservationTable(
            grid_width=state.grid_width,
            grid_height=state.grid_height,
            max_time=max_steps + 1,
        )
        self.engine = SimulationEngine(state, self.metrics)
        self.engine._grid_width = state.grid_width
        self.engine._grid_height = state.grid_height
        self.paused = False
        self.replay = []
        self._snapshot()
        return self.state

    @property
    def state(self) -> SimulationState:
        if self.engine is None:
            raise RuntimeError("No scenario is loaded")
        return self.engine.state

    @property
    def loaded(self) -> bool:
        return self.engine is not None

    def _snapshot(self) -> None:
        self.replay.append(self.serialize_state())

    def serialize_state(self) -> dict[str, Any]:
        state = self.state
        data = state.model_dump(mode="json")
        data["scenario"] = self.scenario_name
        data["strategy"] = self.strategy.value
        data["max_steps"] = self.max_steps
        data["paused"] = self.paused
        data["status"] = self.status
        data["metrics"] = self.metrics.to_dict()
        return data

    @property
    def status(self) -> str:
        if not self.loaded:
            return "idle"
        if self.state.is_finished:
            return "completed"
        if self.paused:
            return "paused"
        if self.state.is_running:
            return "running"
        return "ready"

    def _actions(self) -> list[Action]:
        actions: list[Action] = []
        for agent in self.state.agents:
            if agent.status == AgentStatus.COMPLETED or agent.position == agent.goal:
                continue
            result = a_star(
                start=agent.position,
                goal=agent.goal,
                grid_width=self.state.grid_width,
                grid_height=self.state.grid_height,
                obstacles=self.state.obstacles,
            )
            action_type = ActionType.WAIT
            if result.success and len(result.path) > 1:
                next_position = result.path[1]
                dx = next_position.x - agent.position.x
                dy = next_position.y - agent.position.y
                action_type = (
                    ActionType.MOVE_RIGHT if dx == 1 else
                    ActionType.MOVE_LEFT if dx == -1 else
                    ActionType.MOVE_DOWN if dy == 1 else
                    ActionType.MOVE_UP if dy == -1 else
                    ActionType.WAIT
                )
            actions.append(Action(agent_id=agent.id, action_type=action_type))
        return actions

    def _mark_completed(self) -> None:
        for agent in self.state.agents:
            if agent.position == agent.goal:
                agent.status = AgentStatus.COMPLETED

        self.metrics.completed_agents = sum(
            agent.status == AgentStatus.COMPLETED for agent in self.state.agents
        )
        self.metrics.average_steps_per_completed = (
            self.metrics.total_path_length / self.metrics.completed_agents
            if self.metrics.completed_agents else 0.0
        )

    def step(self, actions: list[Action] | None = None) -> SimulationState:
        if not self.loaded:
            raise RuntimeError("No scenario is loaded")
        if self.paused:
            return self.state
        if self.state.is_finished:
            return self.state

        self._mark_completed()
        if self.metrics.completed_agents == len(self.state.agents):
            self.state.is_finished = True
            self.metrics.mark_complete("all_agents_completed")
            self._snapshot()
            return self.state

        before = {agent.id: agent.position for agent in self.state.agents}
        self.engine.step(
            actions=self._actions() if actions is None else actions,
            grid_width=self.state.grid_width,
            grid_height=self.state.grid_height,
            reservation_table=self.reservation_table,
            strategy=self.strategy,
        )
        moved = sum(
            abs(agent.position.x - before[agent.id].x)
            + abs(agent.position.y - before[agent.id].y)
            for agent in self.state.agents
        )
        self.metrics.add_path_length(moved)
        self._mark_completed()

        if self.metrics.completed_agents == len(self.state.agents):
            self.state.is_finished = True
            self.state.is_running = False
            self.metrics.mark_complete("all_agents_completed")
        elif self.state.current_step >= self.max_steps:
            self.state.is_finished = True
            self.state.is_running = False
            self.metrics.mark_complete("max_steps_reached")
        self._snapshot()
        return self.state

    def run(self, steps: int | None = None) -> SimulationState:
        count = steps if steps is not None else self.max_steps - self.state.current_step
        if count < 1:
            return self.state
        for _ in range(count):
            if self.state.is_finished or self.paused:
                break
            self.step()
        return self.state

    def pause(self) -> SimulationState:
        if not self.loaded:
            raise RuntimeError("No scenario is loaded")
        self.paused = True
        self.state.is_running = False
        return self.state

    def resume(self) -> SimulationState:
        if not self.loaded:
            raise RuntimeError("No scenario is loaded")
        if not self.state.is_finished:
            self.paused = False
            self.state.is_running = True
        return self.state

    def reset(self) -> SimulationState:
        if not self.loaded or self.initial_state is None:
            raise RuntimeError("No scenario is loaded")
        self.engine = SimulationEngine(self.initial_state.model_copy(deep=True), self.metrics)
        self.engine._grid_width = self.initial_state.grid_width
        self.engine._grid_height = self.initial_state.grid_height
        self.metrics = SimulationMetrics()
        self.engine.metrics = self.metrics
        self.reservation_table = ReservationTable(
            grid_width=self.initial_state.grid_width,
            grid_height=self.initial_state.grid_height,
            max_time=self.max_steps + 1,
        )
        self.paused = False
        self.replay = []
        self._snapshot()
        return self.state
