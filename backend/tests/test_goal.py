import pytest

from app.models.goal import Goal
from app.models.position import Position


def test_goal_creation():
    goal = Goal(
        id="goal_1",
        position=Position(x=5, y=5),
        assigned_agent_id="robot_1"
    )

    assert goal.id == "goal_1"
    assert goal.position == Position(x=5, y=5)
    assert goal.assigned_agent_id == "robot_1"
    assert goal.is_completed is False


def test_unassigned_goal():
    goal = Goal(
        id="goal_2",
        position=Position(x=3, y=4)
    )

    assert goal.assigned_agent_id is None


def test_completed_goal():
    goal = Goal(
        id="goal_3",
        position=Position(x=1, y=1),
        is_completed=True
    )

    assert goal.is_completed is True


def test_empty_goal_id_rejected():
    with pytest.raises(ValueError):
        Goal(
            id="",
            position=Position(x=1, y=1)
        )