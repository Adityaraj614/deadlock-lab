from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.models.obstacle import Obstacle
from app.models.position import Position


@dataclass(frozen=True)
class VertexKey:
    """Key for a vertex reservation: position + time step."""

    x: int
    y: int
    time: int

    @property
    def position(self) -> Position:
        return Position(x=self.x, y=self.y)


@dataclass(frozen=True)
class EdgeKey:
    """Key for an edge reservation: transition + time step.

    Represents moving from `from_x, from_y` to `to_x, to_y` between
    time `time` and time `time + 1`.
    """

    from_x: int
    from_y: int
    to_x: int
    to_y: int
    time: int

    @property
    def from_position(self) -> Position:
        return Position(x=self.from_x, y=self.from_y)

    @property
    def to_position(self) -> Position:
        return Position(x=self.to_x, y=self.to_y)


class ReservationTable:
    """A time-based reservation system for multi-agent path planning.

    Supports vertex and edge reservations to prevent collisions during
    simultaneous multi-agent movement. Agents can wait (stay in place)
    when no safe movement is available.

    The table is deterministic and suitable for integration with A* path
    planning and multi-agent coordination.
    """

    def __init__(self, grid_width: int, grid_height: int, max_time: int):
        if grid_width < 1 or grid_height < 1:
            raise ValueError("Grid dimensions must be at least 1")
        if max_time < 1:
            raise ValueError("max_time must be at least 1")

        self.grid_width = grid_width
        self.grid_height = grid_height
        self.max_time = max_time

        # vertex_reservations: VertexKey -> agent_id
        self._vertex_reservations: dict[VertexKey, str] = {}
        # edge_reservations: EdgeKey -> agent_id
        self._edge_reservations: dict[EdgeKey, str] = {}

    # ------------------------------------------------------------------
    # Cell (vertex) reservation
    # ------------------------------------------------------------------

    def can_reserve_vertex(self, position: Position, time: int) -> bool:
        """Check whether a cell can be reserved at the given time step."""
        key = VertexKey(x=position.x, y=position.y, time=time)
        return key not in self._vertex_reservations

    def reserve_vertex(self, position: Position, time: int, agent_id: str) -> bool:
        """Reserve a cell for an agent at a given time step.

        Returns True if the reservation was successful (not already taken).
        """
        if not self.is_within_bounds(position):
            return False
        key = VertexKey(x=position.x, y=position.y, time=time)
        if key in self._vertex_reservations:
            return False
        self._vertex_reservations[key] = agent_id
        return True

    def release_vertex(self, position: Position, time: int) -> None:
        """Release a vertex reservation at the given time step."""
        key = VertexKey(x=position.x, y=position.y, time=time)
        self._vertex_reservations.pop(key, None)

    def is_within_bounds(self, position: Position) -> bool:
        """Check whether a position is within grid boundaries."""
        return (
            0 <= position.x < self.grid_width
            and 0 <= position.y < self.grid_height
        )

    # ------------------------------------------------------------------
    # Transition (edge) reservation
    # ------------------------------------------------------------------

    def can_reserve_edge(
        self,
        from_position: Position,
        to_position: Position,
        time: int,
    ) -> bool:
        """Check whether a transition can be reserved at the given time step."""
        if not self.is_within_bounds(from_position):
            return False
        if not self.is_within_bounds(to_position):
            return False
        key = EdgeKey(
            from_x=from_position.x,
            from_y=from_position.y,
            to_x=to_position.x,
            to_y=to_position.y,
            time=time,
        )
        return key not in self._edge_reservations

    def reserve_edge(
        self,
        from_position: Position,
        to_position: Position,
        time: int,
        agent_id: str,
    ) -> bool:
        """Reserve a transition for an agent at a given time step.

        Returns True if the reservation was successful (not already taken).
        """
        if not self.is_within_bounds(from_position):
            return False
        if not self.is_within_bounds(to_position):
            return False
        key = EdgeKey(
            from_x=from_position.x,
            from_y=from_position.y,
            to_x=to_position.x,
            to_y=to_position.y,
            time=time,
        )
        if key in self._edge_reservations:
            return False
        self._edge_reservations[key] = agent_id
        return True

    def release_edge(
        self,
        from_position: Position,
        to_position: Position,
        time: int,
    ) -> None:
        """Release an edge reservation at the given time step."""
        key = EdgeKey(
            from_x=from_position.x,
            from_y=from_position.y,
            to_x=to_position.x,
            to_y=to_position.y,
            time=time,
        )
        self._edge_reservations.pop(key, None)

    # ------------------------------------------------------------------
    # Conflict detection
    # ------------------------------------------------------------------

    def check_vertex_conflict(
        self,
        position: Position,
        time: int,
        agent_id: str,
    ) -> set[str]:
        """Check if reserving a vertex conflicts with existing reservations.

        Returns a set of agent IDs that already have this cell at this time.
        """
        key = VertexKey(x=position.x, y=position.y, time=time)
        conflicting: set[str] = set()
        existing_agent = self._vertex_reservations.get(key)
        if existing_agent and existing_agent != agent_id:
            conflicting.add(existing_agent)
        return conflicting

    def check_edge_conflict(
        self,
        from_position: Position,
        to_position: Position,
        time: int,
        agent_id: str,
    ) -> set[str]:
        """Check if reserving an edge conflicts with existing reservations.

        Returns a set of agent IDs that already have this transition at this time.
        """
        if not self.is_within_bounds(from_position):
            return set()
        if not self.is_within_bounds(to_position):
            return set()
        key = EdgeKey(
            from_x=from_position.x,
            from_y=from_position.y,
            to_x=to_position.x,
            to_y=to_position.y,
            time=time,
        )
        conflicting: set[str] = set()
        existing_agent = self._edge_reservations.get(key)
        if existing_agent and existing_agent != agent_id:
            conflicting.add(existing_agent)
        return conflicting

    # ------------------------------------------------------------------
    # Swap detection
    # ------------------------------------------------------------------

    def check_swap_conflict(
        self,
        agent_a_pos: Position,
        agent_b_pos: Position,
        time: int,
        agent_a_id: str,
        agent_b_id: str,
    ) -> bool:
        """Check whether two agents would perform a head-on edge swap.

        A swap occurs when agent A moves from X to Y and agent B moves
        from Y to X in the same time step.
        """
        from_key = EdgeKey(
            from_x=agent_a_pos.x,
            from_y=agent_a_pos.y,
            to_x=agent_b_pos.x,
            to_y=agent_b_pos.y,
            time=time,
        )
        to_key = EdgeKey(
            from_x=agent_b_pos.x,
            from_y=agent_b_pos.y,
            to_x=agent_a_pos.x,
            to_y=agent_a_pos.y,
            time=time,
        )

        a_has_b = from_key in self._edge_reservations
        b_has_a = to_key in self._edge_reservations
        return a_has_b and b_has_a

    # ------------------------------------------------------------------
    # Release all reservations for an agent at a given time (e.g., after
    # recovery or step completion)
    # ------------------------------------------------------------------

    def clear_time_step(self, time: int) -> None:
        """Release all reservations held at the given time step."""
        keys_to_remove = [
            key
            for key in self._vertex_reservations
            if key.time == time
        ]
        for key in keys_to_remove:
            self._vertex_reservations.pop(key, None)

        keys_to_remove = [
            key
            for key in self._edge_reservations
            if key.time == time
        ]
        for key in keys_to_remove:
            self._edge_reservations.pop(key, None)

    def clear_all(self) -> None:
        """Release all reservations."""
        self._vertex_reservations.clear()
        self._edge_reservations.clear()

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def get_reserved_vertices_at(self, time: int) -> dict[Position, str]:
        """Return a dict of position -> agent_id for all reservations at a time step."""
        result: dict[Position, str] = {}
        for key, agent_id in self._vertex_reservations.items():
            if key.time == time:
                result[key.position] = agent_id
        return result

    def get_reserved_edges_at(self, time: int) -> dict[tuple[Position, Position], str]:
        """Return a dict of (from, to) -> agent_id for all edge reservations at a time step."""
        result: dict[tuple[Position, Position], str] = {}
        for key, agent_id in self._edge_reservations.items():
            if key.time == time:
                result[(key.from_position, key.to_position)] = agent_id
        return result

    def __repr__(self) -> str:
        return (
            f"ReservationTable(w={self.grid_width}, h={self.grid_height}, "
            f"max_t={self.max_time}, vertices={len(self._vertex_reservations)}, "
            f"edges={len(self._edge_reservations)})"
        )