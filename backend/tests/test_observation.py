import pytest
from pydantic import ValidationError

from app.models.observation import Observation
from app.models.position import Position


def test_observation_creation():
    observation = Observation(
        agent_id="robot_1",
        current_position=Position(x=2, y=3),
        goal_position=Position(x=8, y=9),
        current_step=5,
    )

    assert observation.agent_id == "robot_1"
    assert observation.current_position == Position(x=2, y=3)
    assert observation.goal_position == Position(x=8, y=9)
    assert observation.current_step == 5


def test_observation_default_lists():
    observation = Observation(
        agent_id="robot_1",
        current_position=Position(x=2, y=3),
        goal_position=Position(x=8, y=9),
    )

    assert observation.nearby_agents == []
    assert observation.nearby_obstacles == []


def test_observation_with_nearby_entities():
    observation = Observation(
        agent_id="robot_1",
        current_position=Position(x=2, y=3),
        goal_position=Position(x=8, y=9),
        nearby_agents=[Position(x=3, y=3)],
        nearby_obstacles=[Position(x=4, y=3)],
    )

    assert len(observation.nearby_agents) == 1
    assert len(observation.nearby_obstacles) == 1


def test_empty_agent_id_rejected():
    with pytest.raises(ValidationError):
        Observation(
            agent_id="",
            current_position=Position(x=2, y=3),
            goal_position=Position(x=8, y=9),
        )


def test_negative_timestep_rejected():
    with pytest.raises(ValidationError):
        Observation(
            agent_id="robot_1",
            current_position=Position(x=2, y=3),
            goal_position=Position(x=8, y=9),
            current_step=-1,
        )