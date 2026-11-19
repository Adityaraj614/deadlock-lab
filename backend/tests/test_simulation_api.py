import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, r"C:\Users\kumar\OneDrive\Desktop\NVIDIA\deadlock-lab\backend")

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_load_serializes_real_scenario(client):
    response = client.post("/api/scenario/load/simple_warehouse")
    assert response.status_code == 200
    data = response.json()
    assert (data["grid_width"], data["grid_height"]) == (10, 10)
    assert len(data["agents"]) == 2
    assert len(data["obstacles"]) == 2
    assert data["current_step"] == 0
    assert data["status"] == "ready"


def test_invalid_scenario_returns_404(client):
    response = client.post("/api/scenario/load/not_a_scenario")
    assert response.status_code == 404


def test_invalid_action_returns_400(client):
    client.post("/api/scenario/load/simple_warehouse")
    response = client.post("/api/simulate/step", json={"actions": [{"agent_id": "robot_1", "action_type": "teleport"}]})
    assert response.status_code == 400


def test_step_moves_robots_and_tracks_path_length(client):
    client.post("/api/scenario/load/simple_warehouse")
    response = client.post("/api/simulate/step")
    data = response.json()
    assert response.status_code == 200
    assert data["current_step"] == 1
    assert data["metrics"]["total_path_length"] == 2
    assert data["agents"][0]["position"] != {"x": 1, "y": 1}


def test_run_reaches_goals_and_finishes(client):
    client.post("/api/scenario/load/simple_warehouse", json={"max_steps": 100})
    data = client.post("/api/simulate/run").json()
    assert data["status"] == "completed"
    assert data["metrics"]["completed_agents"] == 2
    assert data["metrics"]["simulation_termination_reason"] == "all_agents_completed"
    assert all(agent["status"] == "completed" for agent in data["agents"])
    assert data["metrics"]["total_path_length"] > 0


def test_pause_resume_preserves_and_continues_state(client):
    client.post("/api/scenario/load/simple_warehouse")
    stepped = client.post("/api/simulate/step").json()
    paused = client.post("/api/simulate/pause").json()
    assert paused["status"] == "paused"
    assert paused["current_step"] == stepped["current_step"]
    still_paused = client.post("/api/simulate/run", json={"steps": 2}).json()
    assert still_paused["current_step"] == stepped["current_step"]
    resumed = client.post("/api/simulate/resume").json()
    assert resumed["status"] == "running"
    continued = client.post("/api/simulate/step").json()
    assert continued["current_step"] == stepped["current_step"] + 1


def test_reset_restores_initial_state(client):
    client.post("/api/scenario/load/simple_warehouse")
    client.post("/api/simulate/step")
    data = client.post("/api/simulate/reset").json()
    assert data["current_step"] == 0
    assert data["status"] == "ready"
    assert data["metrics"]["total_steps"] == 0


def test_max_step_termination_is_explicit(client):
    client.post("/api/scenario/load/simple_warehouse", json={"max_steps": 1})
    data = client.post("/api/simulate/run").json()
    assert data["status"] == "completed"
    assert data["current_step"] == 1
    assert data["metrics"]["simulation_termination_reason"] == "max_steps_reached"
    assert data["metrics"]["completed_agents"] < 2


def test_replay_contains_initial_and_step_snapshots(client):
    client.post("/api/scenario/load/simple_warehouse")
    client.post("/api/simulate/step")
    snapshots = client.get("/api/simulate/replay").json()["snapshots"]
    assert len(snapshots) == 2
    assert snapshots[0]["current_step"] == 0
    assert snapshots[1]["current_step"] == 1


def test_deadlock_recovery_is_real_and_not_recounted_every_frame(client):
    client.post("/api/scenario/load/simple_warehouse")
    data = client.post("/api/simulate/run", json={"steps": 20}).json()
    metrics = data["metrics"]
    assert metrics["deadlock_recovery_attempts"] == metrics["deadlock_incidents"]
    assert metrics["successful_recoveries"] <= metrics["deadlock_recovery_attempts"]
