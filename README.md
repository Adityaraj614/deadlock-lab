# deadlock-lab
A Multi-Agent Coordination and Deadlock Resolution Simulation Platform

## Phase 2: Warehouse Robotics Lab

This project implements a comprehensive multi-agent coordination and deadlock resolution simulation platform, with Phase 2 focusing on the Warehouse Robotics Lab.

### Features

- **Warehouse Grid Environment**: Configurable grid-based warehouse with obstacles, agents, and goals
- **A* Pathfinding**: 4-directional movement with Manhattan distance heuristic
- **Multi-Agent Coordination**: Simultaneous movement with collision and deadlock prevention
- **Reservation Table**: Time-based cell and transition reservations for conflict-free planning
- **Deadlock Detection**: Wait-for graph with cycle detection
- **Deadlock Resolution**: Priority-based yielding agent selection and safe position recovery
- **Warehouse Scenarios**: Preconfigured layouts (Simple, Narrow Corridor, Congested)
- **Simulation Metrics**: Step counting, agent status tracking, collision/deadlock statistics
- **Backend API**: FastAPI endpoints for simulation control and metrics retrieval

### Architecture

The platform is organized into modular components:

- **Models**: Position, Agent, Goal, Obstacle, Action
- **Environments**: WarehouseGridEnvironment (grid management)
- **Algorithms**: A* pathfinding, ReservationTable (time-based reservations)
- **Simulation**: MultiAgentExecutor (coordination), SimulationEngine (lifecycle)
- **Algorithms/Deadlock**: DeadlockDetector (wait-for graph), DeadlockResolver (recovery)
- **Metrics**: SimulationMetrics (step counting, agent status, collision/deadlock stats)
- **API**: FastAPI-based backend with endpoints for scenario management and simulation control

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run the backend
cd backend
uvicorn app.main:app --reload
```

### Running Tests

```bash
pytest -v
```

### API Endpoints

- `GET /health`: Health check
- `GET /api/scenarios`: List available warehouse scenarios
- `GET /api/scenarios/{name}`: Get scenario configuration
- `POST /api/simulate/step`: Execute one simulation step
- `POST /api/simulate/run`: Run simulation for specified steps
- `POST /api/simulate/reset`: Reset simulation to initial state
- `POST /api/scenario/load/{name}`: Load a warehouse scenario
- `GET /api/metrics`: Retrieve simulation metrics

### Warehouse Scenarios

Configured under `configs/warehouse_scenarios.yaml`:

- **Simple Warehouse**: Small grid (10x10), 2 agents, 2 obstacles, simple routes
- **Narrow Corridor**: Narrow passage (5x10), 4 obstacles, 3 agents sharing the corridor
- **Congested Warehouse**: More agents (4), multiple obstacles (4), larger grid (12x12), priority differences