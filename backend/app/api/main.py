from fastapi import FastAPI, HTTPException, Body
from typing import Any, Optional
from pathlib import Path
import yaml
from fastapi.middleware.cors import CORSMiddleware
from app.simulation.multi_agent_executor import CoordinationStrategy
from app.simulation.session import SimulationSession
from app.models.action import Action

app = FastAPI(title="Deadlock Lab API")
_SESSION = SimulationSession()

# Add CORS middleware for development origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8080", "http://localhost:8080"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.options("/health")
def health_options() -> dict[str, str]:
    return {"status": "ok"}

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


# --- Simulation Lifecycle Endpoints ---

def _require_session() -> SimulationSession:
    if not _SESSION.loaded:
        raise HTTPException(status_code=409, detail="Load a scenario first")
    return _SESSION


def _parse_strategy(value: str | None) -> CoordinationStrategy:
    if value is None:
        return _SESSION.strategy
    try:
        return CoordinationStrategy(value.lower())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid strategy '{value}'") from exc


def _parse_actions(options: dict | None) -> list[Action] | None:
    if not options or "actions" not in options:
        return None
    raw_actions = options["actions"]
    if not isinstance(raw_actions, list):
        raise HTTPException(status_code=400, detail="actions must be a list")
    if not raw_actions:
        return None
    try:
        return [Action.model_validate(item) for item in raw_actions]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid action: {exc}") from exc


@app.post("/api/simulate/step", tags=["simulation"])
def simulate_step(options: dict | None = Body(default=None)) -> dict:
    session = _require_session()
    if options and "strategy" in options:
        session.strategy = _parse_strategy(options["strategy"])
    try:
        session.step(_parse_actions(options))
        return session.serialize_state()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.post("/api/simulate/run", tags=["simulation"])
def simulate_run(options: dict | None = Body(default=None)) -> dict:
    session = _require_session()
    options = options or {}
    if "strategy" in options:
        session.strategy = _parse_strategy(options["strategy"])
    if "actions" in options:
        raise HTTPException(status_code=400, detail="actions are supported by the step endpoint only")
    steps = options.get("steps", options.get("max_steps"))
    if steps is not None and (not isinstance(steps, int) or steps < 1):
        raise HTTPException(status_code=400, detail="steps must be a positive integer")
    session.run(steps)
    return session.serialize_state()

@app.post("/api/simulate/reset", tags=["simulation"])
def simulate_reset() -> dict:
    try:
        _SESSION.reset()
        return _SESSION.serialize_state()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

@app.post("/api/scenario/load/{name}", tags=["warehouse"])
def simulate_load_scenario(name: str, options: dict | None = Body(default=None)) -> dict:
    options = options or {}
    strategy = _parse_strategy(options.get("strategy")) if options.get("strategy") else CoordinationStrategy.FULL
    max_steps = options.get("max_steps", 100)
    if not isinstance(max_steps, int):
        raise HTTPException(status_code=400, detail="max_steps must be an integer")
    try:
        _SESSION.load(name, strategy=strategy, max_steps=max_steps)
    except ValueError as exc:
        raise HTTPException(status_code=404 if "not found" in str(exc).lower() else 400, detail=str(exc)) from exc
    return _SESSION.serialize_state()

# --- Metrics Endpoint ---

@app.get("/api/metrics", tags=["metrics"])
def get_metrics() -> dict:
    if not _SESSION.loaded:
        return SimulationSession().metrics.to_dict()
    return _SESSION.metrics.to_dict()


@app.post("/api/simulate/pause", tags=["simulation"])
def simulate_pause() -> dict:
    try:
        _SESSION.pause()
        return _SESSION.serialize_state()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/simulate/resume", tags=["simulation"])
def simulate_resume() -> dict:
    try:
        _SESSION.resume()
        return _SESSION.serialize_state()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/api/simulate/replay", tags=["simulation"])
def get_replay() -> dict:
    return {"snapshots": _SESSION.replay}


# --- Experiment Endpoints ---

from app.experiment import add_experiment_routes

add_experiment_routes(app)
