# Deadlock Lab — Phase 2 Architecture Document

## Warehouse Robotics Lab Architecture

### Overview

This document describes the architecture of Phase 2: Warehouse Robotics Lab, a multi-agent coordination and deadlock resolution simulation platform. The platform is designed to be modular, testable, and extensible for future phases (e.g., Drone Studio).

### Grid Environment

The `WarehouseGridEnvironment` class manages a 2D grid representing the warehouse floor.

**Grid Boundaries**
- Configurable width and height (validated to be at least 1).
- Positions are validated against boundaries using `is_within_bounds()`.
- Coordinates range from (0, 0) at the top-left to (w-1, h-1) at the bottom-right.

**Obstacles**
- Static and dynamic obstacles are represented by `Obstacle` models.
- Obstacles can be added, removed, and updated after environment creation.
- Position validation prevents spawning agents/obstacles/goals inside existing obstacles.
- Overlapping positions are rejected at both initialization and runtime.

**Agents**
- Each `Agent` has an `id`, `position`, `goal`, `status`, `priority`, and `speed`.
- Status values: `idle`, `moving`, `waiting`, `completed`, `blocked`.
- Agents can be placed via `place_agent()`, which validates that:
  - The position is within grid boundaries.
  - The position is not inside an obstacle.
  - The position does not overlap with another agent or goal.
  - The agent ID is unique.
- Agents move toward their goal position through coordinated movement.

**Goals**
- Each `Goal` has an `id`, `position`, and `assigned_agent_id`.
- Goal positions are validated against obstacles and agent positions.
- Multiple goals cannot share the same position.

### A* Pathfinding

The A* algorithm finds shortest paths on the grid with 4-directional movement (up, down, left, right) and Manhattan distance heuristic.

**Heuristic**: Manhattan distance `h(n) = |x_n - x_goal| + |y_n - y_goal|`.

**Movement**: Four-directional — up (0, -1), down (0, 1), left (-1, 0), right (1, 0).

**Key properties**:
- Respects grid boundaries.
- Avoids obstacles.
- Handles start == goal (returns `[start]`).
- Handles unreachable goals (returns failed `PathResult`).
- Handles invalid start/goal positions (out-of-bounds or blocked).
- Returns a `PathResult` containing success flag and path (tuple of `Position` objects).

**Data structure**: The algorithm uses tuple keys `(x, y)` for hashability in the open/closed sets, while returning `Position` objects in the path.

### Reservation Table

The `ReservationTable` provides a time-based reservation system for collision-free multi-agent movement.

**Vertex Reservations**: A cell `(x, y)` is reserved for a specific agent at time step `t`.
- `reserve_vertex(position, time, agent_id)` — reserve a cell.
- `can_reserve_vertex(position, time)` — check availability.
- `release_vertex(position, time)` — release a reservation.

**Edge Reservations**: A transition from cell `A` to cell `B` between time step `t` and `t+1` is reserved.
- `reserve_edge(from_pos, to_pos, time, agent_id)` — reserve a transition.
- `can_reserve_edge(from_pos, to_pos, time)` — check availability.
- `release_edge(from_pos, to_pos, time)` — release a reservation.

**Conflict Detection**
- **Vertex conflict**: Two agents reserving the same cell at the same time step.
- **Edge conflict**: Two agents reserving the same transition at the same time step.
- **Swap conflict**: Two agents performing a head-on edge swap (A moves X→Y and B moves Y→X).

**Swap Detection**: Checks if both the forward and reverse transitions are reserved by different agents at the same time step.

### Multi-Agent Coordination

The `MultiAgentExecutor` coordinates simultaneous actions for multiple agents using the following policy:

**Movement Policy**: Simultaneous movement where all agents compute their proposed destination based on their action, then conflicts are detected and resolved.

**Conflict Detection**:
1. **Vertex conflicts**: Agents proposing the same destination.
2. **Edge conflicts (head-on swaps)**: Agents swapping positions (A→B and B→A).
3. **Occupied destination conflicts**: Agents moving into a cell occupied by a stationary agent.

**Resolution**: Conflict agents have their status set to `waiting` and their positions are not updated. Conflict-free agents move to their proposed destinations.

**Reservation Table Integration**: Before applying proposals, the executor checks the reservation table for additional vertex and edge conflicts. Successful proposals are added to the reservation table; conflicting agents are skipped.

**Priority Handling**: Agents have a `priority` field (positive integer). Lower values indicate higher priority. Used in deadlock resolution to select which agent should yield.

### Wait-For Graph and Deadlock Detection

The `DeadlockDetector` uses a wait-for graph to identify deadlocked agent groups.

**Wait-For Graph Construction**: Based on proposed destinations, an agent A is said to "wait for" agent B if A's proposed destination is B's current position. This creates a dependency edge A → B.

**Cycle Detection**: Using DFS, cycles in the wait-for graph indicate deadlocks. If agent A waits for B, B waits for C, and C waits for A, all three are deadlocked.

**Key improvements to avoid false positives**:
- Only create dependencies when the blocking agent is also moving (not stationary).
- If an agent's proposal equals its current position, no dependency is created (it's waiting, not blocked).
- Empty graphs and graphs without cycles return no deadlocked agents.

**Deadlock Identification**: Returns the set of all agents involved in detected cycles. If no cycles exist, returns an empty set.

### Deadlock Resolution

The `DeadlockResolver` integrates with `MultiAgentExecutor` to recover from detected deadlocks.

**Recovery Process**:
1. **Select yielding agent**: The lowest-priority agent within the deadlocked group is selected to yield. Ties are broken by agent ID (deterministic).
2. **Find safe position**: Identify neighboring cells (up, down, left, right) that are:
   - Within grid boundaries.
   - Not occupied by other agents.
   - Not inside obstacles.
3. **Select best position**: Choose the safe position that minimizes Manhattan distance to the agent's goal.
4. **Move yielding agent**: Move the selected agent to the safe position. If the move does not create new collisions, the deadlock is partially resolved.
5. **Replan**: After recovery, paths may need to be replanned for remaining agents.

**Important**: A single movement to an adjacent empty cell is NOT automatically considered a fully resolved deadlock. The system verifies whether the deadlock has actually been removed (i.e., no cycle exists in the updated wait-for graph) before reporting successful recovery. Infinite recovery loops are avoided by limiting recovery attempts and verifying actual deadlock removal.

### Simulation Metrics

The `SimulationMetrics` class tracks the following during simulation runs:

**Core Metrics**:
- `total_steps`: Number of simulation timesteps elapsed.
- `completed_agents`: Agents that have reached their goal.
- `waiting_agents`: Agents currently waiting (status = `waiting`).
- `blocked_agents`: Agents currently blocked (status = `blocked`).
- `simulation_complete`: Whether the simulation has finished.
- `simulation_termination_reason`: Why the simulation ended.

**Coordination Metrics**:
- `collisions_prevented`: Number of collisions that were detected and prevented during movement coordination.
- `deadlocks_detected`: Number of deadlocks detected across the simulation.
- `deadlock_recovery_attempts`: Number of deadlock recovery operations attempted.
- `successful_recoveries`: Number of recovery operations that actually removed the deadlock.
- `total_path_length`: Sum of path lengths for all completed agents.
- `average_steps_per_completed`: Average path length per completed agent.

**Metrics Collection**: The `SimulationEngine` records metrics at each step via the `MultiAgentExecutor.execute()` method. Metrics are accessible programmatically via `SimulationMetrics.to_dict()` and suitable for frontend charting.

### API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/api/scenarios` | GET | List available warehouse scenarios |
| `/api/scenarios/{name}` | GET | Get scenario configuration |
| `/api/simulate/step` | POST | Execute one simulation step |
| `/api/simulate/run` | POST | Run simulation for specified steps |
| `/api/simulate/reset` | POST | Reset simulation to initial state |
| `/api/scenario/load/{name}` | POST | Load a warehouse scenario and initialize state |
| `/api/metrics` | GET | Retrieve simulation metrics |

### Current Limitations

- Phase 2 is limited to 2D grid warehouse environments; 3D or drone operations are not supported.
- Real robot or hardware deployment is not claimed or implied.
- Machine learning / reinforcement learning training is not included in this phase.
- The reservation table operates on a fixed time step; continuous time is not supported.
- Deadlock resolution is based on single-step movement; multi-step replanning is a future enhancement.
- API is designed for simulation control and metrics; full frontend integration is a future goal.