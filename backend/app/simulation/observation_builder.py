from app.models.observation import Observation
from app.simulation.state import SimulationState


class ObservationBuilder:
    """Builds observations for individual agents."""

    @staticmethod
    def build(
        state: SimulationState,
        agent_id: str,
    ) -> Observation:
        """Generate an observation for the requested agent."""

        agent = next(
            (item for item in state.agents if item.id == agent_id),
            None,
        )

        if agent is None:
            raise ValueError(f"Agent '{agent_id}' not found")

        nearby_agents = [
            other.position
            for other in state.agents
            if other.id != agent_id
        ]

        nearby_obstacles = [
            obstacle.position
            for obstacle in state.obstacles
        ]

        return Observation(
            agent_id=agent.id,
            current_position=agent.position,
            goal_position=agent.goal,
            nearby_agents=nearby_agents,
            nearby_obstacles=nearby_obstacles,
            current_step=state.current_step,
        )