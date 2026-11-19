import pytest
from pydantic import ValidationError

from app.models.action import Action, ActionType


def test_valid_move_action():
    action = Action(
        agent_id="robot_1",
        action_type=ActionType.MOVE_RIGHT,
    )

    assert action.agent_id == "robot_1"
    assert action.action_type == ActionType.MOVE_RIGHT


def test_wait_action():
    action = Action(
        agent_id="robot_1",
        action_type=ActionType.WAIT,
    )

    assert action.action_type == ActionType.WAIT


def test_all_action_types():
    assert len(ActionType) == 5


def test_empty_agent_id_rejected():
    with pytest.raises(ValidationError):
        Action(
            agent_id="",
            action_type=ActionType.MOVE_UP,
        )


def test_invalid_action_type_rejected():
    with pytest.raises(ValidationError):
        Action(
            agent_id="robot_1",
            action_type="fly",
        )