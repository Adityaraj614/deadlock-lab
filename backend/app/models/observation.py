from pydantic import BaseModel, Field

from app.models.position import Position


class Observation(BaseModel):
    """Represents the information available to an agent at a given timestep."""

    agent_id: str = Field(min_length=1)

    current_position: Position
    goal_position: Position

    nearby_agents: list[Position] = Field(default_factory=list)
    nearby_obstacles: list[Position] = Field(default_factory=list)

    current_step: int = Field(default=0, ge=0)