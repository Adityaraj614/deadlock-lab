from app.algorithms.deadlock_detector import DeadlockDetector
from app.models.action import Action, ActionType
from app.models.position import Position
from app.simulation.state import SimulationState
from app.algorithms.deadlock_resolver import DeadlockResolver

class MultiAgentExecutor:
    """Coordinates simultaneous actions for multiple agents."""

    MOVEMENTS = {
        ActionType.MOVE_UP: (0, -1),
        ActionType.MOVE_DOWN: (0, 1),
        ActionType.MOVE_LEFT: (-1, 0),
        ActionType.MOVE_RIGHT: (1, 0),
        ActionType.WAIT: (0, 0),
    }

    @staticmethod
    def calculate_proposals(
        state: SimulationState,
        actions: list[Action],
        grid_width: int,
        grid_height: int,
    ) -> dict[str, Position]:
        """Calculate proposed destinations without modifying agent positions."""

        if grid_width < 1 or grid_height < 1:
            raise ValueError("Grid dimensions must be at least 1")

        proposals = {}
        agent_ids = {agent.id for agent in state.agents}

        obstacle_positions = {
            (obstacle.position.x, obstacle.position.y)
            for obstacle in state.obstacles
        }

        for action in actions:
            if action.agent_id not in agent_ids:
                raise ValueError(f"Agent '{action.agent_id}' not found")

            if action.agent_id in proposals:
                raise ValueError(
                    f"Duplicate action for agent '{action.agent_id}'"
                )

            agent = next(
                item for item in state.agents
                if item.id == action.agent_id
            )

            dx, dy = MultiAgentExecutor.MOVEMENTS[action.action_type]

            new_x = agent.position.x + dx
            new_y = agent.position.y + dy

            if not (
                0 <= new_x < grid_width
                and 0 <= new_y < grid_height
            ):
                proposals[action.agent_id] = agent.position
                continue

            if (new_x, new_y) in obstacle_positions:
                proposals[action.agent_id] = agent.position
                continue

            proposals[action.agent_id] = Position(x=new_x, y=new_y)

        return proposals

    @staticmethod
    def detect_vertex_conflicts(
        proposals: dict[str, Position],
    ) -> set[str]:
        """Find agents proposing to occupy the same destination."""

        destination_agents = {}

        for agent_id, position in proposals.items():
            destination = (position.x, position.y)

            destination_agents.setdefault(destination, []).append(agent_id)

        conflicts = set()

        for agent_ids in destination_agents.values():
            if len(agent_ids) > 1:
                conflicts.update(agent_ids)

        return conflicts

    @staticmethod
    def detect_edge_conflicts(
        state: SimulationState,
        proposals: dict[str, Position],
    ) -> set[str]:
        """Detect agents swapping positions in the same timestep."""

        original_positions = {
            agent.id: agent.position
            for agent in state.agents
        }

        conflicts = set()
        agent_ids = list(proposals.keys())

        for i in range(len(agent_ids)):
            for j in range(i + 1, len(agent_ids)):
                agent_a = agent_ids[i]
                agent_b = agent_ids[j]

                a_start = original_positions[agent_a]
                b_start = original_positions[agent_b]

                a_end = proposals[agent_a]
                b_end = proposals[agent_b]

                if (
                    a_start == b_end
                    and b_start == a_end
                    and a_start != a_end
                ):
                    conflicts.add(agent_a)
                    conflicts.add(agent_b)

        return conflicts

    @staticmethod
    def detect_occupied_destination_conflicts(
        state: SimulationState,
        proposals: dict[str, Position],
    ) -> set[str]:
        """Detect agents moving into cells occupied by stationary agents."""

        original_positions = {
            agent.id: agent.position
            for agent in state.agents
        }

        conflicts = set()

        for agent_id, destination in proposals.items():

            # Ignore agents that are not moving.
            if destination == original_positions[agent_id]:
                continue

            for other_id, other_position in original_positions.items():
                if other_id == agent_id:
                    continue

                if (
                    destination == other_position
                    and proposals.get(other_id, other_position)
                    == other_position
                ):
                    conflicts.add(agent_id)

        return conflicts

    @staticmethod
    def resolve_conflicts(
        state: SimulationState,
        proposals: dict[str, Position],
    ) -> set[str]:
        """Identify all agents involved in movement conflicts."""

        vertex_conflicts = MultiAgentExecutor.detect_vertex_conflicts(
            proposals
        )

        edge_conflicts = MultiAgentExecutor.detect_edge_conflicts(
            state, proposals
        )

        occupied_conflicts = (
            MultiAgentExecutor.detect_occupied_destination_conflicts(
                state, proposals
            )
        )

        return vertex_conflicts | edge_conflicts | occupied_conflicts


    @staticmethod
    def apply_proposals(
        state: SimulationState,
        proposals: dict[str, Position],
        conflicts: set[str],
    ) -> SimulationState:
        """Apply conflict-free movement proposals to the simulation."""

        for agent in state.agents:
            if agent.id not in proposals:
                continue

            if agent.id in conflicts:
                agent.status = "waiting"
                continue

            new_position = proposals[agent.id]

            if new_position == agent.position:
                agent.status = "idle"
            else:
                agent.position = new_position
                agent.status = "moving"

        return state


    @staticmethod
    def execute(
        state: SimulationState,
        actions: list[Action],
        grid_width: int,
        grid_height: int,
    ) -> SimulationState:
        """Execute one complete multi-agent simulation timestep."""

        # Step 1: Calculate movement proposals.
        proposals = MultiAgentExecutor.calculate_proposals(
            state,
            actions,
            grid_width,
            grid_height,
        )

        # Step 2: Detect movement conflicts.
        conflicts = MultiAgentExecutor.resolve_conflicts(
            state,
            proposals,
        )

        # Step 3: Detect deadlocked agents.
        deadlocked_agents = DeadlockDetector.detect_deadlocks(
            state,
            proposals,
        )

        # Step 4: Combine movement conflicts and deadlocks.
        all_blocked_agents = conflicts | deadlocked_agents

        # Step 5: Apply safe movements.
        return MultiAgentExecutor.apply_proposals(
            state,
            proposals,
            all_blocked_agents,
        )
