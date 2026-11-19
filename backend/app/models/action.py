from enum import Enum

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    MOVE_UP = "move_up"
    MOVE_DOWN = "move_down"
    MOVE_LEFT = "move_left"
    MOVE_RIGHT = "move_right"
    WAIT = "wait"


class Action(BaseModel):
    """Represents an action selected by an agent."""

    agent_id: str = Field(min_length=1)
    action_type: ActionType