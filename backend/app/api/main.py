from fastapi import FastAPI, HTTPException, Body
from typing import Any, Optional
from pathlib import Path
import yaml
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Deadlock Lab API")

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

@app.post("/api/simulate/step", tags=["simulation"])
def simulate_step(options: dict) -> dict:
    return {"message": "Step endpoint placeholder"}

@app.post("/api/simulate/run", tags=["simulation"])
def simulate_run(options: dict) -> dict:
    return {"message": "Run endpoint placeholder"}

@app.post("/api/simulate/reset", tags=["simulation"])
def simulate_reset() -> dict:
    return {"message": "Reset endpoint placeholder"}

@app.post("/api/scenario/load/{name}", tags=["warehouse"])
def simulate_load_scenario(name: str) -> dict:
    return {"message": "Load endpoint placeholder", "name": name}

# --- Metrics Endpoint ---

@app.get("/api/metrics", tags=["metrics"])
def get_metrics() -> dict:
    return {"total_steps": 0, "completed_agents": 0, "waiting_agents": 0, "blocked_agents": 0}


# --- Experiment Endpoints ---

from app.experiment import add_experiment_routes

add_experiment_routes(app)