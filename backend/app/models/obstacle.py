
from pydantic import BaseModel, Field

from app.models.position import Position


class Obstacle(BaseModel):
    """Represents a blocked area in a simulation environment."""

    id: str = Field(min_length=1)
    position: Position
    is_dynamic: bool = False

