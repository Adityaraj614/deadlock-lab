
import pytest

from app.models.agent import Agent, AgentStatus
from app.models.position import Position


def test_agent_creation():
    agent = Agent(
        id="robot_1",
        position=Position(x=0, y=0),
        goal=Position(x=5, y=5)
    )

    assert agent.id == "robot_1"
    assert agent.status == AgentStatus.IDLE
    assert agent.priority == 1
    assert agent.speed == 1.0


def test_agent_status_update():
    agent = Agent(
        id="robot_1",
        position=Position(x=0, y=0),
        goal=Position(x=5, y=5),
        status=AgentStatus.MOVING
    )

    assert agent.status == AgentStatus.MOVING


def test_invalid_speed_rejected():
    with pytest.raises(ValueError):
        Agent(
            id="robot_1",
            position=Position(x=0, y=0),
            goal=Position(x=5, y=5),
            speed=0
        )
