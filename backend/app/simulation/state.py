
from pydantic import BaseModel, Field, model_validator

from app.models.agent import Agent
from app.models.obstacle import Obstacle
from app.models.goal import Goal


class SimulationState(BaseModel):
    """Stores the complete state of a multi-agent simulation."""

    agents: list[Agent] = Field(default_factory=list)
    obstacles: list[Obstacle] = Field(default_factory=list)
    goals: list[Goal] = Field(default_factory=list)

    current_step: int = Field(default=0, ge=0)
    is_running: bool = False
    is_finished: bool = False

    @model_validator(mode="after")
    def validate_unique_ids(self):
        """Ensure all entities have unique IDs within their category."""

        agent_ids = [agent.id for agent in self.agents]
        obstacle_ids = [obstacle.id for obstacle in self.obstacles]
        goal_ids = [goal.id for goal in self.goals]

        if len(agent_ids) != len(set(agent_ids)):
            raise ValueError("Duplicate agent IDs are not allowed")

        if len(obstacle_ids) != len(set(obstacle_ids)):
            raise ValueError("Duplicate obstacle IDs are not allowed")

        if len(goal_ids) != len(set(goal_ids)):
            raise ValueError("Duplicate goal IDs are not allowed")

        return self
