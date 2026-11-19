from fastapi import FastAPI, HTTPException
from typing import Any, Optional
from pathlib import Path
import yaml

from app.simulation.state import SimulationState
from app.simulation.multi_agent_executor import MultiAgentExecutor
from app.metrics.metrics import SimulationMetrics
from app.models.action import Action
from app.models.agent import Agent
from app.models.goal import Goal
from app.models.obstacle import Obstacle
from app.models.position import Position
from app.environments.warehouse_grid import WarehouseGridEnvironment

app = FastAPI(title="Deadlock Lab API")


@app.get("/health", tags=["general"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}

# --- Warehouse Scenario Configuration ---

# Resolve config path relative to this file's location.
# api/main.py is at backend/app/api/main.py; project root is 3 levels up.
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_CONFIG_PATH = _PROJECT_ROOT / "configs" / "warehouse_scenarios.yaml"

try:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as _f:
        _SCENARIOS: dict[str, dict] = yaml.safe_load(_f) or {}
except Exception:  # pragma: no cover - filesystem guard
    _SCENARIOS = {}


def _list_scenario_names() -> list[str]:
    return list(_SCENARIOS.keys())


def _load_scenario(name: str) -> dict[str, Any]:
    scenario = _SCENARIOS.get(name)
    if scenario is None:
        raise HTTPException(status_code=404, detail=f"Scenario '{name}' not found")
    return scenario


@app.get("/api/scenarios", tags=["warehouse"])
def list_scenarios() -> dict[str, list[str]]:
    return {"scenarios": _list_scenario_names()}


@app.get("/api/scenarios/{name}", tags=["warehouse"])
def get_scenario(name: str) -> dict[str, Any]:
    return _load_scenario(name)


# --- Simulation State Management ---

# Track the currently loaded simulation state across requests
_loaded_state: SimulationState | None = None
_loaded_grid_size: tuple[int, int] | None = None


def _initialize_simulation_state_from_scenario(scenario: dict[str, Any]) -> tuple[SimulationState, tuple[int, int]]:
    """Parse a warehouse scenario and create a fully initialized SimulationState.

    Extracts grid dimensions, obstacles, agents with goals, and goals from the
    YAML scenario configuration and constructs the appropriate Pydantic model
    instances.
    """
    grid_width = scenario["grid_width"]
    grid_height = scenario["grid_height"]

    environment = WarehouseGridEnvironment(grid_width=grid_width, grid_height=grid_height)

    # Add obstacles.
    for obs_data in scenario.get("obstacles", []):
        position = Position(x=obs_data["position"]["x"], y=obs_data["position"]["y"])
        obstacle = Obstacle(id=obs_data["id"], position=position, is_dynamic=obs_data.get("is_dynamic", False))
        environment.add_obstacle(obstacle)

    # Add agents with goals.
    for agent_data in scenario.get("agents", []):
        position = Position(x=agent_data["position"]["x"], y=agent_data["position"]["y"])
        goal_position = Position(x=agent_data["goal"]["x"], y=agent_data["goal"]["y"])
        goal = Goal(id=f"goal_{agent_data['id']}", position=goal_position, assigned_agent_id=agent_data["id"])
        agent = Agent(
            id=agent_data["id"],
            position=position,
            goal=goal_position,
            priority=agent_data.get("priority", 1),
            speed=agent_data.get("speed", 1.0),
        )
        environment.place_agent(agent)
        environment.place_goal(goal)

    # Convert WarehouseGridEnvironment to SimulationState
    state = SimulationState(
        current_step=0,
        is_running=False,
        is_finished=False,
        agents=environment.agents,
        obstacles=environment.obstacles,
        goals=environment.goals,
    )
    return state, (grid_width, grid_height)


# --- Simulation Lifecycle Endpoints ---

@app.post("/api/simulate/step", tags=["simulation"])
def simulate_step(actions: list[Action]) -> SimulationState:
    """Advance the simulation by one timestep.

    ``actions`` should be a list of ``Action`` objects, one per agent.
    If ``actions`` is empty or ``None``, all agents wait.
    """
    global _loaded_state, _loaded_grid_size

    if _loaded_state is None:
        return SimulationState(current_step=0, is_running=False, is_finished=False, agents=[], obstacles=[], goals=[])

    # Execute one timestep using the multi-agent executor
    executed_state = MultiAgentExecutor.execute(
        _loaded_state,
        actions,
        _loaded_grid_size[0],
        _loaded_grid_size[1],
        time=_loaded_state.current_step,
        metrics=None,
    )

    # Update the global state
    _loaded_state = executed_state
    _loaded_state.current_step += 1
    _loaded_state.is_running = True

    return _loaded_state


@app.post("/api/simulate/run", tags=["simulation"])
def simulate_run(max_steps: int = 100) -> dict[str, Any]:
    """Run the simulation until the step limit is reached.

    ``max_steps`` controls the maximum number of timesteps to run.
    """
    global _loaded_state, _loaded_grid_size

    if _loaded_state is None:
        return {"message": "No scenario loaded. Use POST /api/scenario/load/{name} first.", "status": "error"}

    from app.simulation.engine import SimulationEngine

    engine = SimulationEngine(initial_state=_loaded_state, metrics=SimulationMetrics())
    result = engine.run(max_steps=max_steps)

    # Update global state
    _loaded_state = result

    return {"message": f"Simulation ran for {result.current_step} steps", "status": "completed", "final_step": result.current_step}


@app.post("/api/simulate/reset", tags=["simulation"])
def simulate_reset() -> SimulationState:
    """Reset the simulation to its initial state.

    Restores the originally loaded scenario state.
    """
    global _loaded_state, _loaded_grid_size

    if _loaded_state is None:
        return SimulationState(current_step=0, is_running=False, is_finished=False, agents=[], obstacles=[], goals=[])

    # Restore to initial state
    _loaded_state = _loaded_state.model_copy(deep=True)
    _loaded_state.current_step = 0
    _loaded_state.is_running = False
    _loaded_state.is_finished = False

    return _loaded_state


@app.post("/api/scenario/load/{name}", tags=["warehouse"])
def simulate_load_scenario(name: str) -> SimulationState:
    """Load a warehouse scenario and initialize the simulation.

    The scenario name corresponds to a key in the YAML configuration file.
    Returns a fully initialized SimulationState with agents, obstacles,
    goals, and grid dimensions set.
    """
    global _loaded_state, _loaded_grid_size

    scenario = _load_scenario(name)
    state, grid_size = _initialize_simulation_state_from_scenario(scenario)
    _loaded_state = state
    _loaded_grid_size = grid_size

    return state


@app.get("/api/metrics", tags=["metrics"])
def get_metrics() -> SimulationMetrics:
    """Get current simulation metrics.

    Metrics are updated from actual simulation execution, not merely from API calls.
    """
    global _loaded_state

    if _loaded_state is None:
        return SimulationMetrics()

    # Return current metrics based on the loaded state
    metrics = SimulationMetrics()

    # Populate basic metrics from the state
    if _loaded_state.agents:
        metrics.total_steps = _loaded_state.current_step
        # Handle both AgentStatus enum and string status values
        for a in _loaded_state.agents:
            status = a.status
            if isinstance(status, str):
                s = status
            else:
                s = status.name
            if s == "COMPLETED":
                metrics.completed_agents += 1
            elif s == "WAITING":
                metrics.waiting_agents += 1
            elif s == "BLOCKED":
                metrics.blocked_agents += 1

    return metrics