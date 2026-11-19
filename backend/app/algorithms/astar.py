from __future__ import annotations

from typing import Sequence, TypeVar

from app.models.obstacle import Obstacle
from app.models.position import Position

T = TypeVar("T", bound=Position)


class PathResult:
    """Result of a pathfinding operation."""

    def __init__(
        self,
        success: bool,
        path: Sequence[Position] | None = None,
        message: str | None = None,
    ):
        self.success = success
        self.path = path if path is not None else []
        self.message = message

    def __repr__(self) -> str:
        if self.success:
            return f"PathResult(success=True, path={self.path})"
        return f"PathResult(success=False, message={self.message!r})"


def manhattan_distance(a: Position, b: Position) -> int:
    """Compute Manhattan distance between two positions."""
    return abs(a.x - b.x) + abs(a.y - b.y)


def _pos_key(position: Position) -> tuple[int, int]:
    """Convert a Position to a hashable tuple key."""
    return (position.x, position.y)


def is_valid_cell(
    position: Position,
    grid_width: int,
    grid_height: int,
    obstacles: Sequence[Obstacle],
) -> bool:
    """Check whether a cell is within bounds and not an obstacle."""
    if not (0 <= position.x < grid_width and 0 <= position.y < grid_height):
        return False
    if any(obs.position == position for obs in obstacles):
        return False
    return True


def a_star(
    start: Position,
    goal: Position,
    grid_width: int,
    grid_height: int,
    obstacles: Sequence[Obstacle] = (),
) -> PathResult:
    """Run A* pathfinding with 4-directional movement and Manhattan heuristic.

    Returns a PathResult containing the path found, or an indication of
    failure (unreachable, invalid input, etc.).
    """

    # Handle invalid start/goal positions.
    if not is_valid_cell(start, grid_width, grid_height, obstacles):
        return PathResult(
            success=False,
            message=f"Start position {start} is invalid or blocked",
        )
    if not is_valid_cell(goal, grid_width, grid_height, obstacles):
        return PathResult(
            success=False,
            message=f"Goal position {goal} is invalid or blocked",
        )

    # Start equals goal.
    if start == goal:
        return PathResult(success=True, path=[start])

    # A* setup using tuple keys for hashability.
    start_key = _pos_key(start)
    goal_key = _pos_key(goal)

    open_set: list[Position] = [start]
    open_set_keys: set[tuple[int, int]] = {start_key}
    came_from: dict[tuple[int, int], Position | None] = {start_key: None}
    g_score: dict[tuple[int, int], int] = {start_key: 0}
    closed_set: set[tuple[int, int]] = set()

    # Four-directional movement: up, down, left, right.
    directions: list[tuple[int, int]] = [
        (0, -1),  # Up
        (0, 1),   # Down
        (-1, 0),  # Left
        (1, 0),   # Right
    ]

    while open_set:
        # Pick the node in open_set with the lowest f_score.
        # For determinism and simplicity, sort by (f, x, y).
        current = min(
            open_set,
            key=lambda n: (g_score.get(_pos_key(n), 999999) + manhattan_distance(n, goal), n.x, n.y),
        )

        current_key = _pos_key(current)

        if current == goal:
            # Reconstruct path.
            path: list[Position] = []
            while current is not None:
                path.append(current)
                current = came_from[current_key]
                current_key = _pos_key(current) if current is not None else None
            path.reverse()
            return PathResult(success=True, path=tuple(path))

        open_set.remove(current)
        open_set_keys.discard(current_key)
        closed_set.add(current_key)

        for dxx, dyy in directions:
            # Compute neighbor coordinates and validate before creating Position.
            nx = current.x + dxx
            ny = current.y + dyy
            if not (0 <= nx < grid_width and 0 <= ny < grid_height):
                continue
            neighbor_pos = Position(x=nx, y=ny)
            if not is_valid_cell(neighbor_pos, grid_width, grid_height, obstacles):
                continue

            tentative_g = g_score[current_key] + 1
            nkey = _pos_key(neighbor_pos)

            if nkey in closed_set:
                continue

            if nkey in open_set_keys:
                # Already discovered; check if we found a better path.
                if tentative_g < g_score[nkey]:
                    # Better path found, update.
                    came_from[nkey] = current
                    g_score[nkey] = tentative_g
                else:
                    continue
            else:
                # First time discovering this node.
                open_set.append(neighbor_pos)
                open_set_keys.add(nkey)
                came_from[nkey] = current
                g_score[nkey] = tentative_g

    # Goal was never reached.
    return PathResult(
        success=False,
        message=f"Goal {goal} is unreachable from start {start}",
    )