
from enum import Enum

from pydantic import BaseModel, Field

from app.models.position import Position


class AgentStatus(str, Enum):
    IDLE = "idle"
    MOVING = "moving"
    WAITING = "waiting"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class Agent(BaseModel):
    """Represents an autonomous agent in a simulation."""

    id: str = Field(min_length=1)
    position: Position
    goal: Position
    status: AgentStatus = AgentStatus.IDLE
    priority: int = Field(default=1, ge=1)
    speed: float = Field(default=1.0, gt=0)
