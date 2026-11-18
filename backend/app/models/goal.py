from pydantic import BaseModel, Field

from app.models.position import Position


class Goal(BaseModel):
    """Represents a target location assigned to an agent."""

    id: str = Field(min_length=1)
    position: Position
    assigned_agent_id: str | None = None
    is_completed: bool = False