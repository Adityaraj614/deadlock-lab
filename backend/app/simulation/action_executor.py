from app.models.action import Action, ActionType
from app.models.position import Position
from app.simulation.state import SimulationState


class ActionExecutor:
    """Executes actions selected by simulation agents."""

    @staticmethod
    def execute(
        state: SimulationState,
        action: Action,
        grid_width: int,
        grid_height: int,
    ) -> Position:
        """Execute an action and return the agent's resulting position."""

        if grid_width < 1 or grid_height < 1:
            raise ValueError("Grid dimensions must be at least 1")

        agent = next(
            (item for item in state.agents if item.id == action.agent_id),
            None,
        )

        if agent is None:
            raise ValueError(f"Agent '{action.agent_id}' not found")

        current = agent.position

        movement = {
            ActionType.MOVE_UP: (0, -1),
            ActionType.MOVE_DOWN: (0, 1),
            ActionType.MOVE_LEFT: (-1, 0),
            ActionType.MOVE_RIGHT: (1, 0),
        }

        if action.action_type == ActionType.WAIT:
            agent.status = "idle"
            return current

        dx, dy = movement[action.action_type]

        new_x = current.x + dx
        new_y = current.y + dy

        # Check grid boundaries.
        if not (0 <= new_x < grid_width and 0 <= new_y < grid_height):
            agent.status = "blocked"
            return current

        # Check static and dynamic obstacles.
        obstacle_positions = {
            (obstacle.position.x, obstacle.position.y)
            for obstacle in state.obstacles
        }

        if (new_x, new_y) in obstacle_positions:
            agent.status = "blocked"
            return current

        # Execute movement.
        new_position = Position(x=new_x, y=new_y)
        agent.position = new_position
        agent.status = "moving"

        return new_position