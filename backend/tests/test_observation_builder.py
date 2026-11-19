import pytest

from app.models.agent import Agent
from app.models.obstacle import Obstacle
from app.models.position import Position
from app.simulation.state import SimulationState
from app.simulation.observation_builder import ObservationBuilder


def test_build_observation_for_agent():
    robot = Agent(
        id="robot_1",
        position=Position(x=2, y=3),
        goal=Position(x=8, y=9),
    )

    state = SimulationState(agents=[robot], current_step=5)

    observation = ObservationBuilder.build(state, "robot_1")

    assert observation.agent_id == "robot_1"
    assert observation.current_position == Position(x=2, y=3)
    assert observation.goal_position == Position(x=8, y=9)
    assert observation.current_step == 5


def test_observation_includes_other_agents():
    robot_1 = Agent(
        id="robot_1",
        position=Position(x=2, y=3),
        goal=Position(x=8, y=9),
    )

    robot_2 = Agent(
        id="robot_2",
        position=Position(x=4, y=3),
        goal=Position(x=0, y=0),
    )

    state = SimulationState(agents=[robot_1, robot_2])

    observation = ObservationBuilder.build(state, "robot_1")

    assert len(observation.nearby_agents) == 1
    assert observation.nearby_agents[0] == Position(x=4, y=3)


def test_observation_includes_obstacles():
    robot = Agent(
        id="robot_1",
        position=Position(x=2, y=3),
        goal=Position(x=8, y=9),
    )

    obstacle = Obstacle(
        id="obstacle_1",
        position=Position(x=3, y=3),
    )

    state = SimulationState(
        agents=[robot],
        obstacles=[obstacle],
    )

    observation = ObservationBuilder.build(state, "robot_1")

    assert len(observation.nearby_obstacles) == 1
    assert observation.nearby_obstacles[0] == Position(x=3, y=3)


def test_unknown_agent_id_rejected():
    state = SimulationState()

    with pytest.raises(ValueError, match="Agent 'robot_99' not found"):
        ObservationBuilder.build(state, "robot_99")


def test_agent_does_not_observe_itself():
    robot = Agent(
        id="robot_1",
        position=Position(x=2, y=3),
        goal=Position(x=8, y=9),
    )

    state = SimulationState(agents=[robot])

    observation = ObservationBuilder.build(state, "robot_1")

    assert observation.nearby_agents == []