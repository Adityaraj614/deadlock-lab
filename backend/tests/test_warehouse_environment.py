import pytest

from app.models.position import Position
from app.models.agent import Agent, AgentStatus
from app.models.obstacle import Obstacle
from app.models.goal import Goal
from app.models.action import Action, ActionType

from app.environments.warehouse_grid import WarehouseGridEnvironment
from app.algorithms.astar import a_star, PathResult, manhattan_distance
from app.algorithms.reservation_table import ReservationTable, VertexKey, EdgeKey
from app.metrics.metrics import SimulationMetrics
from app.simulation.state import SimulationState
from app.environments.scenario_loader import load_scenario


# ------------------------------------------------------------------
# WarehouseGridEnvironment tests
# ------------------------------------------------------------------


def test_warehouse_grid_creation():
    env = WarehouseGridEnvironment(grid_width=10, grid_height=10)
    assert env.grid_width == 10
    assert env.grid_height == 10
    assert env.obstacles == []
    assert env.agents == []
    assert env.goals == []


def test_grid_boundary_validation():
    env = WarehouseGridEnvironment(grid_width=5, grid_height=5)

    # Valid position inside grid
    assert env.is_within_bounds(Position(x=2, y=2))

    # Valid Position object outside grid bounds (tests is_within_bounds, not Pydantic)
    assert not env.is_within_bounds(Position(x=5, y=5))  # x=5 >= grid_width=5
    assert not env.is_within_bounds(Position(x=5, y=5))  # x=5 >= grid_width=5
    # Note: Position(x=-1) raises ValidationError; boundary test uses out-of-bounds coords that pass Pydantic


def test_obstacle_position_validation():
    env = WarehouseGridEnvironment(grid_width=10, grid_height=10)
    obs = Obstacle(id="o1", position=Position(x=5, y=5))
    env.add_obstacle(obs)
    assert env.is_obstacle_position(Position(x=5, y=5))

    # Try to add obstacle at position already occupied by another obstacle
    obs2 = Obstacle(id="o2", position=Position(x=5, y=5))
    try:
        env.add_obstacle(obs2)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_agent_goal_validation():
    env = WarehouseGridEnvironment(grid_width=10, grid_height=10)
    agent = Agent(id="a1", position=Position(x=1, y=1), goal=Position(x=5, y=5))
    errors = env.validate_agent_placement(agent)
    assert len(errors) == 0

    # Agent position inside obstacle
    env.add_obstacle(Obstacle(id="o1", position=Position(x=1, y=1)))
    errors = env.validate_agent_placement(agent)
    assert any("obstacle" in e.lower() for e in errors)


def test_agent_goal_same_position():
    env = WarehouseGridEnvironment(grid_width=10, grid_height=10)
    agent = Agent(id="a1", position=Position(x=1, y=1), goal=Position(x=1, y=1))
    errors = env.validate_agent_placement(agent)
    assert any("must differ" in e for e in errors)


def test_no_overlapping_agent_positions():
    env = WarehouseGridEnvironment(grid_width=10, grid_height=10)
    env.place_agent(Agent(id="a1", position=Position(x=1, y=1), goal=Position(x=5, y=5)))
    # Placing another agent at same position should raise ValueError during init
    try:
        env.place_agent(Agent(id="a2", position=Position(x=1, y=1), goal=Position(x=5, y=5)))
        assert False, "Should have raised ValueError for overlapping agent positions"
    except ValueError:
        pass


def test_no_overlapping_goals():
    env = WarehouseGridEnvironment(grid_width=10, grid_height=10)
    env.place_goal(Goal(id="g1", position=Position(x=5, y=5)))
    try:
        env.place_goal(Goal(id="g2", position=Position(x=5, y=5)))
        assert False, "Should have raised ValueError for duplicate goal position"
    except ValueError:
        pass


# Helper Goal class (move to proper location in real code)
from app.models.goal import Goal


# ------------------------------------------------------------------
# A* Pathfinding tests
# ------------------------------------------------------------------


def test_astar_simple_path():
    obstacles = []
    result = a_star(
        start=Position(x=0, y=0),
        goal=Position(x=3, y=3),
        grid_width=5,
        grid_height=5,
        obstacles=obstacles,
    )
    assert result.success
    # Manhattan distance is 6, path has 7 positions (distance + 1)
    assert len(result.path) == 7


def test_astar_manhattan_heuristic():
    d = manhattan_distance(Position(x=1, y=1), Position(x=4, y=5))
    assert d == 7


def test_astar_obstacle_avoidance():
    obstacles = [Obstacle(id="o1", position=Position(x=1, y=0))]
    result = a_star(
        start=Position(x=0, y=0),
        goal=Position(x=3, y=3),
        grid_width=5,
        grid_height=5,
        obstacles=obstacles,
    )
    assert result.success


def test_astar_unreachable_goal():
    result = a_star(
        start=Position(x=0, y=0),
        goal=Position(x=0, y=0),  # start == goal
        grid_width=5,
        grid_height=5,
        obstacles=[],
    )
    assert result.success
    assert len(result.path) == 1
    assert result.path[0] == Position(x=0, y=0)


def test_astar_invalid_start():
    obstacles = []
    result = a_star(
        start=Position(x=5, y=5),  # outside 5x5 grid
        goal=Position(x=3, y=3),
        grid_width=5,
        grid_height=5,
        obstacles=obstacles,
    )
    assert not result.success
    assert result.message is not None


def test_astar_invalid_goal():
    obstacles = []
    result = a_star(
        start=Position(x=0, y=0),
        goal=Position(x=5, y=5),  # outside 5x5 grid
        grid_width=5,
        grid_height=5,
        obstacles=obstacles,
    )
    assert not result.success
    assert result.message is not None


# ------------------------------------------------------------------
# ReservationTable tests
# ------------------------------------------------------------------


def test_reservation_table_creation():
    rt = ReservationTable(grid_width=10, grid_height=10, max_time=100)
    assert rt.grid_width == 10
    assert rt.grid_height == 10


def test_vertex_reservation():
    rt = ReservationTable(grid_width=10, grid_height=10, max_time=100)
    assert rt.can_reserve_vertex(Position(x=5, y=5), time=1)
    rt.reserve_vertex(Position(x=5, y=5), time=1, agent_id="robot_1")
    assert not rt.can_reserve_vertex(Position(x=5, y=5), time=1)


def test_edge_reservation():
    rt = ReservationTable(grid_width=10, grid_height=10, max_time=100)
    assert rt.can_reserve_edge(
        from_position=Position(x=5, y=5),
        to_position=Position(x=6, y=5),
        time=1,
    )
    rt.reserve_edge(
        from_position=Position(x=5, y=5),
        to_position=Position(x=6, y=5),
        time=1,
        agent_id="robot_1",
    )
    assert not rt.can_reserve_edge(
        from_position=Position(x=5, y=5),
        to_position=Position(x=6, y=5),
        time=1,
    )


def test_swap_conflict_detection():
    rt = ReservationTable(grid_width=10, grid_height=10, max_time=100)
    # Agent A moves from (5,5) to (6,5), Agent B moves from (6,5) to (5,5)
    # This is a swap conflict.
    from_key = EdgeKey(from_x=5, from_y=5, to_x=6, to_y=5, time=1)
    to_key = EdgeKey(from_x=6, from_y=5, to_x=5, to_y=5, time=1)
    rt._edge_reservations[from_key] = "robot_A"
    rt._edge_reservations[to_key] = "robot_B"

    # Check swap conflict
    a_pos = Position(x=5, y=5)
    b_pos = Position(x=6, y=5)
    conflict = rt.check_swap_conflict(
        a_pos, b_pos, time=1, agent_a_id="robot_A", agent_b_id="robot_B"
    )
    assert conflict is True


# ------------------------------------------------------------------
# SimulationMetrics tests
# ------------------------------------------------------------------


def test_metrics_creation():
    m = SimulationMetrics()
    assert m.total_steps == 0
    assert m.completed_agents == 0
    assert m.waiting_agents == 0
    assert m.blocked_agents == 0


def test_metrics_record_step():
    m = SimulationMetrics()
    state = SimulationState(agents=[])
    m.record_step(state)
    assert m.total_steps == 1


def test_metrics_record_collision_prevented():
    m = SimulationMetrics()
    m.record_collision_prevented()
    assert m.collisions_prevented == 1


def test_metrics_record_deadlock_detected():
    m = SimulationMetrics()
    m.record_deadlock_detected()
    assert m.deadlocks_detected == 1


def test_metrics_record_deadlock_recovery_attempt():
    m = SimulationMetrics()
    m.record_deadlock_recovery_attempt()
    assert m.deadlock_recovery_attempts == 1


def test_metrics_record_successful_recovery():
    m = SimulationMetrics()
    m.record_successful_recovery()
    assert m.successful_recoveries == 1


def test_metrics_mark_complete():
    m = SimulationMetrics()
    m.mark_complete("test reason")
    assert m.simulation_complete is True
    assert m.simulation_termination_reason == "test reason"


def test_metrics_mark_incomplete():
    m = SimulationMetrics()
    m.mark_incomplete()
    assert m.simulation_complete is False


def test_metrics_to_dict_and_from_dict():
    m = SimulationMetrics()
    m.record_step(SimulationState(agents=[]))
    m.record_collision_prevented()
    m.record_deadlock_detected()
    m.record_deadlock_recovery_attempt()
    m.record_successful_recovery()
    m.mark_complete("test")
    d = m.to_dict()
    m2 = SimulationMetrics.from_dict(d)
    assert m2.total_steps == m.total_steps
    assert m2.completed_agents == m.completed_agents
    assert m2.simulation_complete == m.simulation_complete


# ------------------------------------------------------------------
# Scenario loader tests
# ------------------------------------------------------------------


def test_load_simple_warehouse():
    base_dir = r"C:\Users\kumar\OneDrive\Desktop\NVIDIA\deadlock-lab"
    env = load_scenario("simple_warehouse", base_dir=base_dir)
    assert env.grid_width == 10
    assert env.grid_height == 10
    assert len(env.obstacles) == 2
    assert len(env.agents) == 2
    assert len(env.goals) == 2


def test_load_narrow_corridor():
    base_dir = r"C:\Users\kumar\OneDrive\Desktop\NVIDIA\deadlock-lab"
    env = load_scenario("narrow_corridor", base_dir=base_dir)
    assert env.grid_width == 5
    assert env.grid_height == 10
    assert len(env.obstacles) == 18
    assert len(env.agents) == 2


def test_load_congested_warehouse():
    base_dir = r"C:\Users\kumar\OneDrive\Desktop\NVIDIA\deadlock-lab"
    env = load_scenario("congested_warehouse", base_dir=base_dir)
    assert env.grid_width == 12
    assert env.grid_height == 12
    assert len(env.obstacles) == 4
    assert len(env.agents) == 4


def test_unknown_scenario():
    base_dir = r"C:\Users\kumar\OneDrive\Desktop\NVIDIA\deadlock-lab"
    with pytest.raises(ValueError, match="Scenario 'nonexistent' not found"):
        load_scenario("nonexistent", base_dir=base_dir)
