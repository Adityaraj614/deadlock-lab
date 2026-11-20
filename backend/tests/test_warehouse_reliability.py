"""Regression tests for the presentation scenarios and live session path."""

import pytest

from app.simulation.multi_agent_executor import CoordinationStrategy
from app.simulation.session import SimulationSession


SCENARIOS = ("simple_warehouse", "narrow_corridor", "congested_warehouse")


def _assert_safe_replay(session: SimulationSession) -> None:
    obstacle_cells = {
        (obstacle.position.x, obstacle.position.y)
        for obstacle in session.state.obstacles
    }
    previous = None
    for frame in session.replay:
        positions = {
            agent["id"]: (agent["position"]["x"], agent["position"]["y"])
            for agent in frame["agents"]
        }
        assert len(positions) == len(set(positions.values()))
        assert not obstacle_cells.intersection(positions.values())
        if previous is not None:
            for agent_id, current in positions.items():
                assert 0 <= current[0] < session.state.grid_width
                assert 0 <= current[1] < session.state.grid_height
                for other_id, other in previous.items():
                    if agent_id != other_id and current == other:
                        assert positions.get(other_id) != previous[agent_id]
        previous = positions


@pytest.mark.parametrize("scenario", SCENARIOS)
@pytest.mark.parametrize("strategy", tuple(CoordinationStrategy))
def test_scenario_strategy_is_deterministic_and_safe(scenario, strategy):
    results = []
    for _ in range(2):
        session = SimulationSession(max_steps=100)
        session.load(scenario, strategy)
        session.run()
        metrics = session.metrics.to_dict()
        assert metrics["completed_agents"] == len(session.state.agents)
        assert metrics["simulation_termination_reason"] == "all_agents_completed"
        assert metrics["total_path_length"] > 0
        _assert_safe_replay(session)
        results.append(metrics)

    assert results[0] == results[1]


def test_congested_scenario_records_real_recovery():
    session = SimulationSession(max_steps=100)
    session.load("congested_warehouse", CoordinationStrategy.DEADLOCK)
    session.run()

    assert session.metrics.deadlocks_detected >= 1
    assert session.metrics.deadlock_recovery_attempts >= 1
    assert session.metrics.successful_recoveries >= 1
    assert session.metrics.simulation_termination_reason == "all_agents_completed"
