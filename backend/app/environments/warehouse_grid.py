from typing import Optional

from app.models.obstacle import Obstacle
from app.models.position import Position
from app.models.goal import Goal


class WarehouseGridEnvironment:
    """A reusable grid-based warehouse environment.

    Manages grid boundaries, static and dynamic obstacles, agent starting
    positions, and goal positions. Validates all placements and supports
    reset and obstacle management.
    """

    def __init__(
        self,
        grid_width: int,
        grid_height: int,
        obstacles: Optional[list[Obstacle]] = None,
        agents: Optional[list] = None,
        goals: Optional[list[Goal]] = None,
    ):
        if grid_width < 1 or grid_height < 1:
            raise ValueError("Grid dimensions must be at least 1")

        self.grid_width = grid_width
        self.grid_height = grid_height

        self.obstacles: list[Obstacle] = obstacles if obstacles is not None else []
        self.agents = agents if agents is not None else []
        self.goals: list[Goal] = goals if goals is not None else []

        self._validate_no_overlaps()

    # ------------------------------------------------------------------
    # Position validation
    # ------------------------------------------------------------------

    def is_within_bounds(self, position: Position) -> bool:
        """Check whether a position lies inside the grid boundaries."""
        return (
            0 <= position.x < self.grid_width
            and 0 <= position.y < self.grid_height
        )

    def is_obstacle_position(self, position: Position) -> bool:
        """Check whether a position coincides with any obstacle."""
        return any(
            obs.position == position for obs in self.obstacles
        )

    def is_goal_position(self, position: Position) -> bool:
        """Check whether a position coincides with any goal."""
        return any(
            g.position == position for g in self.goals
        )

    def is_position_occupied(self, position: Position) -> bool:
        """Check whether a position is occupied by any agent."""
        return any(
            a.position == position for a in self.agents
        )

    # ------------------------------------------------------------------
    # Obstacle management
    # ------------------------------------------------------------------

    def add_obstacle(self, obstacle: Obstacle) -> None:
        """Add an obstacle to the environment after validation."""
        if not self.is_within_bounds(obstacle.position):
            raise ValueError(
                f"Obstacle position {obstacle.position} is outside grid bounds"
            )
        if self.is_obstacle_position(obstacle.position):
            raise ValueError(
                f"Obstacle position {obstacle.position} already contains an obstacle"
            )
        if self.is_position_occupied(obstacle.position):
            raise ValueError(
                f"Obstacle position {obstacle.position} is already occupied by an agent"
            )
        self.obstacles.append(obstacle)

    def remove_obstacle(self, obstacle_id: str) -> None:
        """Remove an obstacle by ID."""
        self.obstacles = [o for o in self.obstacles if o.id != obstacle_id]

    def update_obstacle_position(self, obstacle_id: str, new_position: Position) -> None:
        """Update an obstacle's position after validation."""
        obstacle = next((o for o in self.obstacles if o.id == obstacle_id), None)
        if obstacle is None:
            raise ValueError(f"Obstacle '{obstacle_id}' not found")
        if not self.is_within_bounds(new_position):
            raise ValueError("New obstacle position is outside grid bounds")
        if self.is_obstacle_position(new_position):
            raise ValueError("New obstacle position already contains an obstacle")
        if self.is_position_occupied(new_position):
            raise ValueError("New obstacle position is already occupied by an agent")
        obstacle.position = new_position

    # ------------------------------------------------------------------
    # Agent and goal validation / placement
    # ------------------------------------------------------------------

    def validate_agent_placement(
        self,
        agent,
    ) -> list[str]:
        """Validate that an agent's position and goal are valid.

        Returns a list of error messages; empty list means valid.
        """
        errors: list[str] = []

        if not self.is_within_bounds(agent.position):
            errors.append("Agent position is outside grid bounds")

        if not self.is_within_bounds(agent.goal):
            errors.append("Agent goal is outside grid bounds")

        if self.is_obstacle_position(agent.position):
            errors.append("Agent position is inside an obstacle")

        if self.is_obstacle_position(agent.goal):
            errors.append("Agent goal is inside an obstacle")

        if agent.position == agent.goal:
            errors.append("Agent position and goal must differ")

        if self.is_position_occupied(agent.position):
            errors.append("Agent position overlaps with another agent")

        return errors

    def validate_goal_placement(self, goal: Goal) -> list[str]:
        """Validate that a goal's position is valid.

        Returns a list of error messages; empty list means valid.
        """
        errors: list[str] = []

        if not self.is_within_bounds(goal.position):
            errors.append("Goal position is outside grid bounds")

        if self.is_obstacle_position(goal.position):
            errors.append("Goal position is inside an obstacle")

        if self.is_position_occupied(goal.position):
            errors.append("Goal position overlaps with an agent position")

        return errors

    def place_agent(self, agent) -> None:
        """Validate and place an agent in the environment.

        Raises ValueError if the agent cannot be placed.
        """
        errors = self.validate_agent_placement(agent)
        if errors:
            raise ValueError("; ".join(errors))
        if self.is_position_occupied(agent.position):
            raise ValueError("Agent position overlaps with another agent or goal")
        agent_ids = [a.id for a in self.agents]
        if agent.id in agent_ids:
            raise ValueError(f"Agent '{agent.id}' already exists in the environment")
        self.agents.append(agent)

    def remove_agent(self, agent_id: str) -> None:
        """Remove an agent by ID."""
        self.agents = [a for a in self.agents if a.id != agent_id]

    def place_goal(self, goal: Goal) -> None:
        """Validate and place a goal in the environment.

        Raises ValueError if the goal cannot be placed.
        """
        errors = self.validate_goal_placement(goal)
        if errors:
            raise ValueError("; ".join(errors))
        for existing in self.goals:
            if existing.position == goal.position and existing.id != goal.id:
                raise ValueError("Goal position already occupied by another goal")
        goal_ids = [g.id for g in self.goals]
        if goal.id in goal_ids:
            raise ValueError(f"Goal '{goal.id}' already exists in the environment")
        self.goals.append(goal)

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset the environment to its initial state."""
        # Positions and goals are retained; only step-relevant state is cleared.
        # Environments typically don't have internal step counters, but this
        # method ensures the object can be reused cleanly.
        pass

    # ------------------------------------------------------------------
    # Internal validation
    # ------------------------------------------------------------------

    def _validate_no_overlaps(self) -> None:
        """Validate that no agents/obstacles/goal overlap at init."""
        all_positions: dict[Position, int] = {}

        for obs in self.obstacles:
            p = obs.position
            all_positions[p] = all_positions.get(p, 0) + 1

        for i, agent in enumerate(self.agents):
            p = agent.position
            if p in all_positions:
                raise ValueError(
                    f"Agent '{agent.id}' position {p} overlaps with obstacle"
                )
            if self.is_goal_position(p):
                raise ValueError(
                    f"Agent '{agent.id}' position {p} overlaps with a goal"
                )
            all_positions[p] = all_positions.get(p, 0) + 1

        # Check agent starting position overlaps
        for i in range(len(self.agents)):
            for j in range(i + 1, len(self.agents)):
                if self.agents[i].position == self.agents[j].position:
                    raise ValueError(
                        f"Agents '{self.agents[i].id}' and '{self.agents[j].id}' "
                        f"share the same starting position"
                    )

        # Validate goals
        for goal in self.goals:
            if self.is_obstacle_position(goal.position):
                raise ValueError(
                    f"Goal '{goal.id}' position is inside an obstacle"
                )
            if self.is_position_occupied(goal.position):
                raise ValueError(
                    f"Goal '{goal.id}' position overlaps with an agent position"
                )

        # Check goal overlaps
        goal_positions: dict[Position, int] = {}
        for goal in self.goals:
            p = goal.position
            goal_positions[p] = goal_positions.get(p, 0) + 1
        if any(
            count > 1 for count in goal_positions.values()
        ):
            raise ValueError(
                "Multiple goals share the same position"
            )