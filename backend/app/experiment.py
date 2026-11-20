"""Experiment runner for comparing coordination strategies in the Warehouse Lab.

Provides reusable functions to execute warehouse scenarios under different
coordination strategies and collect comparable metrics.

Supported strategies (from app.simulation.multi_agent_executor):
  FULL  - conflicts + reservation table + deadlock detection (default)
  PRIORITY - conflicts + priorities, no deadlock check
  RESERVATION - only reservation table checks
  DEADLOCK - conflicts + deadlock detection only
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from app.algorithms.reservation_table import ReservationTable
from app.simulation.engine import SimulationEngine
from app.simulation.session import SimulationSession
from app.metrics.metrics import SimulationMetrics
from app.simulation.multi_agent_executor import CoordinationStrategy
from app.simulation.state import SimulationState
from app.models.agent import Agent
from app.models.position import Position
from app.models.action import Action, ActionType
from app.algorithms.astar import a_star, PathResult
from app.models.obstacle import Obstacle
from app.environments.warehouse_grid import WarehouseGridEnvironment
from app.environments.scenario_loader import load_scenario as _load_scenario_func


# ---------------------------------------------------------------------------
# Scenario loading
# ---------------------------------------------------------------------------

_SCENARIO_CONFIG_PATH = "configs/warehouse_scenarios.yaml"


def _load_scenario_config(name: str) -> dict:
    """Load a warehouse scenario configuration by name from the YAML file."""
    import yaml
    from pathlib import Path

    # Resolve config path: 3 levels up from app/experiment.py -> project root
    config_path = Path(__file__).resolve().parent.parent.parent / _SCENARIO_CONFIG_PATH
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    except FileNotFoundError:
        raise HTTPException(
            status_code=500, detail=f"Scenario config not found at {config_path}"
        )

    if name not in config:
        available = list(config.keys()) if config else []
        raise HTTPException(
            status_code=404, detail=f"Scenario '{name}' not found. Available: {available}"
        )
    return config[name]


# ---------------------------------------------------------------------------
# Core: convert WarehouseGridEnvironment -> SimulationState
# ---------------------------------------------------------------------------

def _env_to_simulation_state(env: WarehouseGridEnvironment) -> SimulationState:
    """Convert a WarehouseGridEnvironment into a SimulationState.

    Agents, obstacles and goals are transferred; agent goals are stored
    as the agent's ``goal`` field (the simulation engine uses agent
    ``goal`` for deadlock‑related checks).
    """
    grid_width = env.grid_width
    grid_height = env.grid_height

    # Build obstacles as Obstacle objects
    obstacles: list[Obstacle] = []
    for o in env.obstacles:
        obstacles.append(
            Obstacle(
                id=o.id,
                position=o.position,
                is_dynamic=getattr(o, "is_dynamic", False),
            )
        )

    # Build agents with their goals
    agents: list[Agent] = []
    for a in env.agents:
        # Find the assigned goal by assigned_agent_id
        goal = next((g for g in env.goals if g.assigned_agent_id == a.id), None)
        if goal is None:
            # Fallback: use the first goal if available
            goal = env.goals[0] if env.goals else Position(x=0, y=0)

        agents.append(
            Agent(
                id=a.id,
                position=a.position,
                goal=goal.position,
                priority=getattr(a, "priority", 1),
                speed=getattr(a, "speed", 1.0),
            )
        )

    state = SimulationState(
        grid_width=grid_width,
        grid_height=grid_height,
        agents=agents,
        obstacles=obstacles,
    )

    return state


# ---------------------------------------------------------------------------
# Core: generate next action from A* path
# ---------------------------------------------------------------------------

def _next_action_from_path(
    agent: Agent,
    path: tuple,
) -> Action:
    """Determine the next ``Action`` for *agent* based on its A* path.

    If the agent is already at its goal, return ``Action``\ ``wait``.
    If a next-step position exists on the path, move towards it.
    Otherwise wait.
    """
    current = agent.position
    goal = agent.goal

    # Already at goal -> wait (the caller may mark the agent completed later)
    if current == goal:
        return Action(agent_id=agent.id, action_type=ActionType.WAIT)

    # No path or empty path -> wait
    if not path or len(path) < 2:
        return Action(agent_id=agent.id, action_type=ActionType.WAIT)

    # Find the next position on the path that is different from current
    next_pos = None
    for p in path:
        if p != current:
            next_pos = p
            break

    if next_pos is None:
        return Action(agent_id=agent.id, action_type=ActionType.WAIT)

    # Determine the action type from the direction to next_pos
    dx = next_pos.x - current.x
    dy = next_pos.y - current.y

    if dx > 0:
        action_type = ActionType.MOVE_RIGHT
    elif dx < 0:
        action_type = ActionType.MOVE_LEFT
    elif dy > 0:
        action_type = ActionType.MOVE_DOWN
    elif dy < 0:
        action_type = ActionType.MOVE_UP
    else:
        action_type = ActionType.WAIT

    return Action(agent_id=agent.id, action_type=action_type)


# ---------------------------------------------------------------------------
# Single-run execution
# ---------------------------------------------------------------------------

def run_experiment(
    scenario_name: str,
    strategy: CoordinationStrategy = CoordinationStrategy.FULL,
    max_steps: int = 100,
    run_id: Optional[str] = None,
) -> dict:
    """Execute one warehouse simulation experiment.

    Args:
        scenario_name: Name of the scenario to load (e.g. ``"simple_warehouse"``).
        strategy: Coordination strategy to use during simulation.
        max_steps: Maximum timesteps to run the simulation.
        run_id: Optional unique experiment identifier; if ``None`` one is
            generated automatically.

    Returns:
        A dictionary containing the experiment result record with all recorded
        metrics and metadata.
    """
    rid = run_id or str(uuid.uuid4())
    session = SimulationSession()
    session.load(scenario_name, strategy=strategy, max_steps=max_steps)
    session.run()

    state = session.state
    metrics = session.metrics
    final_completed = sum(agent.position == agent.goal for agent in state.agents)
    completion_rate = round(
        final_completed / len(state.agents) * 100, 2
    ) if state.agents else 0.0
    termination_reason = metrics.simulation_termination_reason or "finished early"

    result: dict[str, Any] = {
        "run_id": rid,
        "scenario": scenario_name,
        "strategy": strategy.value,
        "grid_width": state.grid_width,
        "grid_height": state.grid_height,
        "max_steps": max_steps,
        "termination_reason": termination_reason,
        "current_step": state.current_step,
        "total_agents": len(state.agents),
        "completed_agents": final_completed,
        "completion_rate": completion_rate,
        "total_path_length": round(metrics.total_path_length, 2),
        "waiting_steps": metrics.waiting_steps,
        "blocked_steps": metrics.blocked_events,
        "deadlocks_detected": metrics.deadlocks_detected,
        "deadlock_recovery_attempts": metrics.deadlock_recovery_attempts,
        "successful_recoveries": metrics.successful_recoveries,
        "collisions_prevented": metrics.collisions_prevented,
        "finished": metrics.simulation_complete and final_completed == len(state.agents),
    }

    # Store result in the in-memory store
    from app.experiment import _experiment_store  # local import to avoid circularity
    _experiment_store[rid] = result

    return result


# ---------------------------------------------------------------------------
# Comparison runner
# ---------------------------------------------------------------------------

def run_comparative_experiment(
    scenario_name: str,
    max_steps: int = 100,
    run_id_prefix: Optional[str] = None,
) -> Dict[str, dict]:
    """Run the same warehouse scenario under all four coordination strategies.

    Args:
        scenario_name: Name of the scenario to load.
        max_steps: Maximum simulation steps per run.
        run_id_prefix: Optional prefix for generated run IDs (e.g. "compare_").

    Returns:
        A dictionary mapping strategy name to its experiment result.
    """
    rid_prefix = run_id_prefix or "compare_"
    results: Dict[str, dict] = {}

    for strategy in CoordinationStrategy:
        run_id = f"{rid_prefix}{strategy.value}"
        result = run_experiment(
            scenario_name=scenario_name,
            strategy=strategy,
            max_steps=max_steps,
            run_id=run_id,
        )
        results[strategy.value] = result

    return results


# ---------------------------------------------------------------------------
# In-memory result store (can be replaced with DB later)
# ---------------------------------------------------------------------------

_experiment_store: Dict[str, dict] = {}


def store_result(result: dict) -> None:
    """Store an experiment result in the in-memory store."""
    run_id = result.get("run_id")
    if run_id is not None:
        _experiment_store[run_id] = result


def get_result(run_id: str) -> Optional[dict]:
    """Retrieve a stored experiment result by run ID."""
    return _experiment_store.get(run_id)


def list_results() -> List[dict]:
    """List all stored experiment results."""
    return list(_experiment_store.values())


# ---------------------------------------------------------------------------
# FastAPI integration helpers
# ---------------------------------------------------------------------------

def add_experiment_routes(app: Any) -> None:
    """Add experiment-related routes to a FastAPI application."""

    from fastapi import Body

    @app.post("/api/experiment/run", tags=["experiment"])
    def run_single_experiment(
        scenario_name: str = Body(..., embed=True),
        strategy: str = Body(..., embed=True),
        max_steps: int = Body(100, embed=True),
    ) -> dict:
        """Start a single warehouse experiment.

        - **scenario_name**: Name of the warehouse scenario (e.g. ``"simple_warehouse"``).
        - **strategy**: Coordination strategy name (`"full"`, `"priority"`, `"reservation"`, `"deadlock"`).
        - **max_steps**: Maximum simulation steps.

        Returns the experiment result record including ``run_id``.
        """
        try:
            strategy_enum = CoordinationStrategy(strategy.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid strategy '{strategy}'. Must be one of: {[s.value for s in CoordinationStrategy]}",
            )

        result = run_experiment(
            scenario_name=scenario_name,
            strategy=strategy_enum,
            max_steps=max_steps,
        )
        store_result(result)
        return result

    @app.post("/api/experiment/compare", tags=["experiment"])
    def run_comparative_experiment_endpoint(
        scenario_name: str = Body(..., embed=True),
        max_steps: int = Body(100, embed=True),
        run_id_prefix: str = Body("compare_", embed=True),
    ) -> dict:
        """Run a comparative experiment across all four strategies.

        - **scenario_name**: Name of the warehouse scenario.
        - **max_steps**: Maximum simulation steps per strategy.
        - **run_id_prefix**: Prefix for generated run IDs.

        Returns a dict mapping each strategy name to its experiment result.
        """
        results = run_comparative_experiment(
            scenario_name=scenario_name,
            max_steps=max_steps,
            run_id_prefix=run_id_prefix,
        )
        for r in results.values():
            store_result(r)
        return results

    @app.get("/api/experiment/result/{run_id}", tags=["experiment"])
    def get_experiment_result(run_id: str) -> dict:
        """Retrieve an experiment result by its run ID.

        - **run_id**: The experiment identifier returned by a run endpoint.
        """
        result = get_result(run_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Experiment result '{run_id}' not found")
        return result

    @app.get("/api/experiment/results", tags=["experiment"])
    def list_experiment_results() -> dict:
        """List all stored experiment results."""
        return {"results": list_results()}
