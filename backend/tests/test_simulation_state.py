
import pytest

from app.simulation.state import SimulationState
from app.models.agent import Agent
from app.models.obstacle import Obstacle
from app.models.goal import Goal
from app.models.position import Position


def create_agent(agent_id):
    return Agent(
        id=agent_id,
        position=Position(x=0, y=0),
        goal=Position(x=5, y=5)
    )


def test_empty_simulation_state():
    state = SimulationState()

    assert state.agents == []
    assert state.obstacles == []
    assert state.goals == []
    assert state.current_step == 0
    assert state.is_running is False


def test_simulation_with_multiple_agents():
    state = SimulationState(
        agents=[
            create_agent("robot_1"),
            create_agent("robot_2")
        ]
    )

    assert len(state.agents) == 2


def test_duplicate_agent_ids_rejected():
    with pytest.raises(ValueError, match="Duplicate agent IDs"):
        SimulationState(
            agents=[
                create_agent("robot_1"),
                create_agent("robot_1")
            ]
        )


def test_duplicate_obstacle_ids_rejected():
    obstacle = Obstacle(
        id="wall_1",
        position=Position(x=2, y=2)
    )

    with pytest.raises(ValueError, match="Duplicate obstacle IDs"):
        SimulationState(
            obstacles=[obstacle, obstacle]
        )


def test_duplicate_goal_ids_rejected():
    goal = Goal(
        id="goal_1",
        position=Position(x=5, y=5)
    )

    with pytest.raises(ValueError, match="Duplicate goal IDs"):
        SimulationState(
            goals=[goal, goal]
        )


def test_independent_simulation_states():
    state_1 = SimulationState()
    state_2 = SimulationState()

    state_1.agents.append(create_agent("robot_1"))

    assert len(state_1.agents) == 1
    assert len(state_2.agents) == 0
