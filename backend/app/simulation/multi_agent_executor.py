from typing import Optional

from app.algorithms.deadlock_detector import DeadlockDetector
from app.algorithms.reservation_table import ReservationTable, VertexKey, EdgeKey
from app.models.action import Action, ActionType
from app.models.agent import Agent, AgentStatus
from app.models.position import Position
from app.simulation.state import SimulationState
from app.algorithms.deadlock_resolver import DeadlockResolver


from enum import Enum


class CoordinationStrategy(Enum):
    """Supported coordination strategies for multi-agent simulation."""

    FULL = "full"  # Priority arbitration + reservations + deadlock recovery.
    PRIORITY = "priority"  # Priority arbitration + collision prevention.
    RESERVATION = "reservation"  # Time-based reservations + collision prevention.
    DEADLOCK = "deadlock"  # Collision prevention + deadlock recovery.


class MultiAgentExecutor:
    """Coordinates simultaneous actions for multiple agents.

    Uses a reservation table to prevent vertex and edge conflicts during
    simultaneous multi-agent movement. Supports priorities, waiting, and
    deadlock recovery.

    Optional metrics collection is available through the ``metrics``
    parameter of ``execute()``.

    The ``coordination_strategy`` parameter controls which coordination
    checks are performed during each simulation step. The default strategy
    ``CoordinationStrategy.FULL`` preserves the existing behavior.
    """

    MOVEMENTS = {
        ActionType.MOVE_UP: (0, -1),
        ActionType.MOVE_DOWN: (0, 1),
        ActionType.MOVE_LEFT: (-1, 0),
        ActionType.MOVE_RIGHT: (1, 0),
        ActionType.WAIT: (0, 0),
    }

    def __init__(self, reservation_table: Optional[ReservationTable] = None) -> None:
        self._reservation_table = reservation_table

    # ------------------------------------------------------------------
    # Proposal calculation
    # ------------------------------------------------------------------

    @staticmethod
    def calculate_proposals(
        state: SimulationState,
        actions: list[Action],
        grid_width: int,
        grid_height: int,
    ) -> dict[str, Position]:
        """Calculate proposed destinations without modifying agent positions.

        Returns a dict mapping agent_id -> proposed Position.
        If an agent has no action or an invalid action, it proposes staying
        in its current position.
        """

        if grid_width < 1 or grid_height < 1:
            raise ValueError("Grid dimensions must be at least 1")

        proposals: dict[str, Position] = {}
        agent_map: dict[str, object] = {
            a.id: a for a in state.agents
        }

        obstacle_positions = {
            (obstacle.position.x, obstacle.position.y)
            for obstacle in state.obstacles
        }

        # Build action map; last action wins if duplicates.
        actions_by_agent: dict[str, Action] = {}
        for action in actions:
            if action.agent_id in actions_by_agent:
                raise ValueError(
                    f"Duplicate action for agent '{action.agent_id}'"
                )
            actions_by_agent[action.agent_id] = action

        # For agents not in the actions list, they wait (stay put).
        for agent in state.agents:
            if agent.id not in actions_by_agent:
                proposals[agent.id] = agent.position
                continue

        for action in actions:
            if action.agent_id not in {a.id for a in state.agents}:
                raise ValueError(
                    f"Agent '{action.agent_id}' not found in simulation state"
                )

            agent = next(
                item for item in state.agents if item.id == action.agent_id
            )

            dx, dy = MultiAgentExecutor.MOVEMENTS[action.action_type]

            new_x = agent.position.x + dx
            new_y = agent.position.y + dy

            if not (0 <= new_x < grid_width and 0 <= new_y < grid_height):
                proposals[action.agent_id] = agent.position
                continue

            if (new_x, new_y) in obstacle_positions:
                proposals[action.agent_id] = agent.position
                continue

            proposals[action.agent_id] = Position(x=new_x, y=new_y)

        return proposals

    # ------------------------------------------------------------------
    # Conflict detection
    # ------------------------------------------------------------------

    @staticmethod
    def detect_vertex_conflicts(
        proposals: dict[str, Position],
    ) -> set[str]:
        """Find agents proposing to occupy the same destination."""

        destination_agents: dict[tuple[int, int], list[str]] = {}

        for agent_id, position in proposals.items():
            destination = (position.x, position.y)
            destination_agents.setdefault(destination, []).append(agent_id)

        conflicts: set[str] = set()
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
            agent.id: agent.position for agent in state.agents
        }

        conflicts: set[str] = set()
        agent_ids = list(proposals.keys())

        for i in range(len(agent_ids)):
            for j in range(i + 1, len(agent_ids)):
                agent_a = agent_ids[i]
                agent_b = agent_ids[j]

                a_start = original_positions.get(agent_a)
                b_start = original_positions.get(agent_b)

                a_end = proposals.get(agent_a)
                b_end = proposals.get(agent_b)

                if a_start is None or b_start is None:
                    continue
                if a_end is None or b_end is None:
                    continue

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
        """Detect agents moving into cells occupied by stationary agents.

        A stationary agent is one whose proposed destination equals its
        current position (i.e., it is waiting or not moving).
        """

        original_positions = {
            agent.id: agent.position for agent in state.agents
        }

        conflicts: set[str] = set()

        for agent_id, destination in proposals.items():
            # Ignore agents that are not moving.
            start_pos = original_positions.get(agent_id, Position(x=0, y=0))
            if destination == start_pos:
                continue

            for other_id, other_position in original_positions.items():
                if other_id == agent_id:
                    continue

                other_proposal = proposals.get(other_id, other_position)
                # If the other agent is also moving, skip the occupied
                # check — vertex/edge conflicts cover that case.
                if other_proposal != other_position:
                    continue

                if destination == other_position:
                    conflicts.add(agent_id)

        return conflicts

    @staticmethod
    def resolve_conflicts(
        state: SimulationState,
        proposals: dict[str, Position],
        strategy: CoordinationStrategy = CoordinationStrategy.FULL,
    ) -> set[str]:
        """Identify all agents involved in movement conflicts.

        Conflicts include vertex (destination), edge (head-on swap), and
        occupied-destination collisions. Priorities can be provided to
        break ties.

        Args:
            state: The simulation state.
            proposals: The proposed destinations for each agent.
            strategy: The coordination strategy to use.

        Returns:
            A set of agent IDs involved in conflicts.
        """

        vertex_conflicts = MultiAgentExecutor.detect_vertex_conflicts(proposals)

        # FULL and PRIORITY arbitrate a shared empty destination instead of
        # blocking every contender.  A stationary occupant remains an
        # invariant violation: the movers must wait rather than displace it.
        if strategy in {
            CoordinationStrategy.FULL,
            CoordinationStrategy.PRIORITY,
            CoordinationStrategy.RESERVATION,
        }:
            original_positions = {agent.id: agent.position for agent in state.agents}
            agent_by_id = {agent.id: agent for agent in state.agents}
            destinations: dict[tuple[int, int], list[str]] = {}
            for agent_id, destination in proposals.items():
                destinations.setdefault((destination.x, destination.y), []).append(agent_id)

            vertex_conflicts = set()
            for agent_ids in destinations.values():
                if len(agent_ids) < 2:
                    continue
                movers = [
                    agent_id
                    for agent_id in agent_ids
                    if proposals[agent_id] != original_positions[agent_id]
                ]
                if len(movers) != len(agent_ids):
                    vertex_conflicts.update(movers)
                    continue
                preferred_movers = [
                    agent_id
                    for agent_id in movers
                    if agent_by_id[agent_id].status != AgentStatus.BLOCKED
                ] or movers
                priorities = {
                    agent_by_id[agent_id].priority for agent_id in preferred_movers
                }
                if strategy in {
                    CoordinationStrategy.FULL,
                    CoordinationStrategy.PRIORITY,
                } and (
                    len(priorities) > 1
                    or len(preferred_movers) < len(movers)
                    or strategy == CoordinationStrategy.PRIORITY
                ):
                    winner = min(
                        preferred_movers,
                        key=lambda agent_id: (
                            agent_by_id[agent_id].priority,
                            agent_id,
                        ),
                    )
                    vertex_conflicts.update(
                        agent_id for agent_id in movers if agent_id != winner
                    )
                elif strategy == CoordinationStrategy.RESERVATION:
                    # Simultaneous contenders are committed in deterministic
                    # agent order; this is the same arbitration a reservation
                    # table provides when it accepts the first proposal.
                    winner = min(movers)
                    vertex_conflicts.update(
                        agent_id for agent_id in movers if agent_id != winner
                    )
                else:
                    vertex_conflicts.update(movers)

        # Vertex and edge safety are invariants for every strategy.  The
        # strategy controls additional coordination behaviour, never whether
        # an unsafe head-on swap is allowed.
        edge_conflicts = MultiAgentExecutor.detect_edge_conflicts(
            state, proposals
        )

        occupied_conflicts = MultiAgentExecutor.detect_occupied_destination_conflicts(
            state, proposals
        )

        all_conflicts = vertex_conflicts | edge_conflicts | occupied_conflicts

        return all_conflicts

    # ------------------------------------------------------------------
    # Proposal application
    # ------------------------------------------------------------------

    @staticmethod
    def apply_proposals(
        state: SimulationState,
        proposals: dict[str, Position],
        conflicts: set[str],
    ) -> SimulationState:
        """Apply conflict-free movement proposals to the simulation.

        Agents in ``conflicts`` are NOT moved; their status is set to
        ``waiting``. Conflict-free agents move and their status is set
        to ``moving`` or kept ``idle`` if the proposal equals their current
        position.

        The returned state is a copy; the original state is not mutated.
        """

        new_state = state.model_copy(deep=True)

        for agent in new_state.agents:
            if agent.id not in proposals:
                continue

            if agent.status == "completed":
                continue

            if agent.id in conflicts:
                agent.status = AgentStatus.WAITING
                continue

            new_position = proposals[agent.id]

            if new_position == agent.position:
                agent.status = AgentStatus.IDLE
            else:
                agent.position = new_position
                agent.status = AgentStatus.MOVING

        return new_state

    # ------------------------------------------------------------------
    # Reservation table conflict checking (stand-alone, no instance state)
    # ------------------------------------------------------------------

    @staticmethod
    def check_vertex_reservation_conflict(
        position: Position,
        time: int,
        agent_id: str,
        reservation_table: ReservationTable,
    ) -> set[str]:
        """Check if reserving a vertex conflicts with existing reservations.

        Returns a set of agent IDs that already hold this cell at this time.
        """
        key = VertexKey(x=position.x, y=position.y, time=time)
        conflicting: set[str] = set()
        existing_agent = reservation_table._vertex_reservations.get(key)
        if existing_agent and existing_agent != agent_id:
            # The proposer is the robot that must wait; the existing owner
            # already has the reservation it is entitled to use.
            conflicting.add(agent_id)
        return conflicting

    @staticmethod
    def check_edge_reservation_conflict(
        from_position: Position,
        to_position: Position,
        time: int,
        agent_id: str,
        reservation_table: ReservationTable,
    ) -> set[str]:
        """Check if reserving an edge conflicts with existing reservations.

        Returns a set of agent IDs that already hold this transition at this time.
        """
        key = EdgeKey(
            from_x=from_position.x,
            from_y=from_position.y,
            to_x=to_position.x,
            to_y=to_position.y,
            time=time,
        )
        conflicting: set[str] = set()
        existing_agent = reservation_table._edge_reservations.get(key)
        reverse_key = EdgeKey(
            from_x=to_position.x,
            from_y=to_position.y,
            to_x=from_position.x,
            to_y=from_position.y,
            time=time,
        )
        reverse_agent = reservation_table._edge_reservations.get(reverse_key)
        if existing_agent and existing_agent != agent_id:
            conflicting.add(agent_id)
        if reverse_agent and reverse_agent != agent_id:
            conflicting.add(agent_id)
        return conflicting

    # ------------------------------------------------------------------
    # Execute one complete multi-agent simulation timestep
    # ------------------------------------------------------------------

    @staticmethod
    def execute(
        state: SimulationState,
        actions: list[Action],
        grid_width: int,
        grid_height: int,
        time: int = 0,
        reservation_table: Optional[ReservationTable] = None,
        metrics: Optional[object] = None,
        strategy: CoordinationStrategy = CoordinationStrategy.FULL,
    ) -> SimulationState:
        """Execute one complete multi-agent simulation timestep.

        Steps:
        1. Calculate movement proposals.
        2. Detect movement conflicts (vertex, edge, occupied destination).
        3. Check reservation table for additional conflicts.
        4. Detect deadlocked agents.
        5. Combine all blocked agents.
        6. Update reservation table with safe proposals.
        7. Apply safe movements.

        The returned state is a new copy; the original state is not mutated.

        If ``metrics`` is provided, its recording methods are called to
        track simulation progress.

        The ``strategy`` parameter controls which coordination checks are
        performed. The default ``CoordinationStrategy.FULL`` preserves the
        existing behavior.
        """

        # Step 1: Calculate movement proposals.
        proposals = MultiAgentExecutor.calculate_proposals(
            state, actions, grid_width, grid_height
        )

        # Step 2: Detect movement conflicts.
        conflicts = MultiAgentExecutor.resolve_conflicts(
            state, proposals, strategy
        )
        edge_conflicts = MultiAgentExecutor.detect_edge_conflicts(
            state, proposals
        )

        # Step 3: Check reservation table for additional conflicts.
        if reservation_table is not None and strategy in {
            CoordinationStrategy.FULL,
            CoordinationStrategy.RESERVATION,
        }:
            res_conflicts: set[str] = set()
            for agent_id, destination in proposals.items():
                agent = next(
                    (a for a in state.agents if a.id == agent_id),
                    None,
                )
                if agent is None:
                    continue

                # Check vertex reservation conflict.
                v_conf = MultiAgentExecutor.check_vertex_reservation_conflict(
                    destination, time, agent_id, reservation_table
                )
                res_conflicts |= v_conf

                # Check edge reservation conflict.
                start = agent.position
                e_conf = MultiAgentExecutor.check_edge_reservation_conflict(
                    start, destination, time, agent_id, reservation_table
                )
                res_conflicts |= e_conf

            conflicts |= res_conflicts
            if res_conflicts:
                original_positions = {agent.id: agent.position for agent in state.agents}
                for agent_id, destination in proposals.items():
                    if agent_id in res_conflicts:
                        conflicts.update(
                            other_id
                            for other_id, other_destination in proposals.items()
                            if other_destination == destination
                            and other_destination != original_positions[other_id]
                        )

        # Step 4: DEADLOCK and FULL explicitly enable cycle detection and
        # recovery.  PRIORITY and RESERVATION retain collision prevention but
        # do not silently acquire the deadlock strategy's behavior.
        deadlock_enabled = strategy in {
            CoordinationStrategy.FULL,
            CoordinationStrategy.DEADLOCK,
        }
        deadlocked_agents = (
            DeadlockDetector.detect_deadlocks(
                state,
                proposals,
                include_shared_destinations=True,
            )
            if deadlock_enabled
            else set()
        )

        # Step 5: Combine movement conflicts and deadlocks.
        all_blocked_agents = conflicts | deadlocked_agents

        # Step 6: Update reservation table with non-conflicting proposals.
        if reservation_table is not None and strategy in {
            CoordinationStrategy.FULL,
            CoordinationStrategy.RESERVATION,
        }:
            # Reserve vertices and edges for agents not in the blocked set.
            for agent_id, destination in proposals.items():
                if agent_id in all_blocked_agents:
                    continue

                agent = next(
                    (a for a in state.agents if a.id == agent_id),
                    None,
                )
                if agent is None:
                    continue

                # Reserve the destination vertex at this time step.
                reservation_table.reserve_vertex(
                    destination, time, agent_id
                )

                # Reserve the edge (transition) from current position to
                # destination at this time step.
                start = agent.position
                if start != destination:
                    reservation_table.reserve_edge(
                        start, destination, time, agent_id
                    )

        # Step 7: Apply safe movements.
        new_state = MultiAgentExecutor.apply_proposals(
            state, proposals, all_blocked_agents
        )

        # PRIORITY and RESERVATION still need a deterministic way to clear a
        # safe head-on blockage, but they do not run the deadlock detector or
        # record deadlock metrics.  This is collision recovery, not their
        # defining coordination mechanism.
        if not deadlock_enabled and edge_conflicts:
            positions_before_yield = {
                agent.id: agent.position for agent in new_state.agents
            }
            recovered = DeadlockResolver.recover_deadlock(
                new_state,
                edge_conflicts,
                grid_width,
                grid_height,
                {
                    (destination.x, destination.y)
                    for destination in proposals.values()
                },
            )
            if recovered:
                for agent in new_state.agents:
                    if agent.position != positions_before_yield[agent.id]:
                        agent.status = AgentStatus.BLOCKED

        # Recover only a newly observed deadlock. A persistent cycle is kept
        # active in the metrics object and is not counted repeatedly.
        if deadlock_enabled and deadlocked_agents and metrics is not None:
            is_new_incident = True
            if metrics is not None and hasattr(metrics, "record_deadlock_incident"):
                is_new_incident = metrics.record_deadlock_incident(deadlocked_agents)
            if is_new_incident:
                positions_before_recovery = {
                    agent.id: agent.position for agent in new_state.agents
                }
                recovered = DeadlockResolver.recover_deadlock(
                    new_state,
                    deadlocked_agents,
                    grid_width,
                    grid_height,
                    {
                        (destination.x, destination.y)
                        for agent_id, destination in proposals.items()
                    },
                )
                if metrics is not None and hasattr(metrics, "record_deadlock_recovery_attempt"):
                    metrics.record_deadlock_recovery_attempt()
                if recovered:
                    for agent in new_state.agents:
                        if agent.position != positions_before_recovery[agent.id]:
                            agent.status = AgentStatus.BLOCKED
                    # Re-check the original movement intent after the yield
                    # move.  Passing current positions here would always
                    # produce an empty graph and falsely report success.
                    post_recovery_proposals = dict(proposals)
                    for agent in new_state.agents:
                        if agent.position != positions_before_recovery[agent.id]:
                            post_recovery_proposals[agent.id] = agent.position
                    remaining = DeadlockDetector.detect_deadlocks(
                        new_state,
                        post_recovery_proposals,
                        include_shared_destinations=True,
                    )
                    if not remaining and metrics is not None and hasattr(metrics, "record_successful_recovery"):
                        metrics.record_successful_recovery()
                    # The yield move changes the incident state.  Close this
                    # incident so a later, genuinely re-formed cycle can be
                    # distinguished from repeated detection of the same
                    # unchanged frame.
                    if metrics is not None and hasattr(metrics, "clear_deadlock_incident"):
                        metrics.clear_deadlock_incident()
        elif metrics is not None and hasattr(metrics, "clear_deadlock_incident"):
            metrics.clear_deadlock_incident()

        # Step 8: Record metrics if available.
        if metrics is not None:
            if hasattr(metrics, "record_step"):
                metrics.record_step(new_state)
            if hasattr(metrics, "record_collision_prevented"):
                # Count prevented collisions as the number of agents that
                # were blocked from moving due to conflicts.
                for _ in conflicts:
                    metrics.record_collision_prevented()
            if hasattr(metrics, "record_blocked_events"):
                metrics.record_blocked_events(len(all_blocked_agents))

            if hasattr(metrics, "record_deadlock_detected"):
                if deadlocked_agents and not hasattr(metrics, "record_deadlock_incident"):
                    metrics.record_deadlock_detected()

            if hasattr(metrics, "record_deadlock_recovery_attempt"):
                # Recovery attempts are recorded at the resolver call above.
                pass

            if hasattr(metrics, "record_successful_recovery"):
                pass  # recovery success tracked separately

            if hasattr(metrics, "add_path_length"):
                # Path length would be tracked per-agent; simplified here.
                pass

        return new_state
