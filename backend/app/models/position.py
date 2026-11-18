from pydantic import BaseModel, Field


class Position(BaseModel):
    """Represents a 2D position in a simulation environment."""

    x: int = Field(ge=0, description="Horizontal grid coordinate")
    y: int = Field(ge=0, description="Vertical grid coordinate")