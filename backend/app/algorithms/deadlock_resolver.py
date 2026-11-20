
from app.models.agent import Agent, AgentStatus
from app.models.position import Position
from app.simulation.state import SimulationState


class DeadlockResolver:
    """Selects agents and safe positions during deadlock recovery."""

    MOVEMENTS = [
        (0, -1),  # Up
        (0, 1),   # Down
        (-1, 0),  # Left
        (1, 0),   # Right
    ]

    @staticmethod
    def select_yield_agent(
        state: SimulationState,
        deadlocked_agents: set[str],
    ) -> Agent | None:

        candidates = [
            agent
            for agent in state.agents
            if agent.id in deadlocked_agents
        ]

        if not candidates:
            return None

        return min(
            candidates,
            key=lambda agent: (agent.priority, agent.id),
        )

    @staticmethod
    def find_safe_positions(
        state: SimulationState,
        agent: Agent,
        grid_width: int,
        grid_height: int,
        forbidden_positions: set[tuple[int, int]] | None = None,
    ) -> list[Position]:

        safe_positions = []

        occupied_positions = {
            (other.position.x, other.position.y)
            for other in state.agents
            if other.id != agent.id
        }

        obstacle_positions = {
            (obstacle.position.x, obstacle.position.y)
            for obstacle in state.obstacles
        }

        for dx, dy in DeadlockResolver.MOVEMENTS:
            x = agent.position.x + dx
            y = agent.position.y + dy

            if not (0 <= x < grid_width and 0 <= y < grid_height):
                continue

            if (x, y) in occupied_positions:
                continue

            if (x, y) in obstacle_positions:
                continue

            if forbidden_positions and (x, y) in forbidden_positions:
                continue

            safe_positions.append(Position(x=x, y=y))

        return safe_positions


    @staticmethod
    def select_yield_position(
        safe_positions: list[Position],
        agent: Agent,
        prefer_lateral: bool = False,
    ) -> Position | None:

        if not safe_positions:
            return None

        return min(
            safe_positions,
            key=lambda position: (
                # Prefer a lateral bay during active recovery.  The default
                # retains the original deterministic nearest-goal tie-break.
                int(prefer_lateral and position.x == agent.position.x),
                abs(position.x - agent.goal.x)
                + abs(position.y - agent.goal.y)
            ),
        )


    @staticmethod
    def move_yielding_agent(
        state: SimulationState,
        agent: Agent,
        destination: Position,
        grid_width: int,
        grid_height: int,
    ) -> bool:
        """Move a yielding agent to a validated safe position."""

        if not (0 <= destination.x < grid_width):
            return False

        if not (0 <= destination.y < grid_height):
            return False

        for other in state.agents:
            if other.id != agent.id and other.position == destination:
                return False

        for obstacle in state.obstacles:
            if obstacle.position == destination:
                return False

        agent.position = destination
        agent.status = AgentStatus.WAITING

        return True


    @staticmethod
    def recover_deadlock(
        state: SimulationState,
        deadlocked_agents: set[str],
        grid_width: int,
        grid_height: int,
        forbidden_positions: set[tuple[int, int]] | None = None,
    ) -> bool:
        """Perform one rule-based deadlock recovery operation."""

        # Step 1: Select the agent that should yield.
        yielding_agent = DeadlockResolver.select_yield_agent(
            state, deadlocked_agents
        )

        if yielding_agent is None:
            return False

        # Step 2: Find available neighbouring positions.
        safe_positions = DeadlockResolver.find_safe_positions(
            state,
            yielding_agent,
            grid_width,
            grid_height,
            forbidden_positions,
        )

        if not safe_positions:
            return False

        # Step 3: Select the best yielding position.
        destination = DeadlockResolver.select_yield_position(
            safe_positions,
            yielding_agent,
            prefer_lateral=True,
        )

        if destination is None:
            return False

        # Step 4: Move the selected agent.
        return DeadlockResolver.move_yielding_agent(
            state,
            yielding_agent,
            destination,
            grid_width,
            grid_height,
        )
