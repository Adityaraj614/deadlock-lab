
from app.models.agent import Agent
from app.models.position import Position
from app.simulation.state import SimulationState
from app.algorithms.deadlock_resolver import DeadlockResolver


def test_selects_lowest_priority_agent():
    state = SimulationState(
        agents=[
            Agent(id="A", position=Position(x=1, y=1),
                  goal=Position(x=5, y=5), priority=3),
            Agent(id="B", position=Position(x=2, y=1),
                  goal=Position(x=5, y=5), priority=1),
            Agent(id="C", position=Position(x=3, y=1),
                  goal=Position(x=5, y=5), priority=2),
        ]
    )

    deadlocked_agents = {"A", "B", "C"}

    selected = DeadlockResolver.select_yield_agent(
        state, deadlocked_agents
    )

    assert selected is not None
    assert selected.id == "B"


def test_ignores_agents_outside_deadlock():
    state = SimulationState(
        agents=[
            Agent(id="A", position=Position(x=1, y=1),
                  goal=Position(x=5, y=5), priority=3),
            Agent(id="B", position=Position(x=2, y=1),
                  goal=Position(x=5, y=5), priority=1),
        ]
    )

    selected = DeadlockResolver.select_yield_agent(
        state, {"A"}
    )

    assert selected is not None
    assert selected.id == "A"


def test_returns_none_when_no_deadlocked_agents():
    state = SimulationState(
        agents=[
            Agent(id="A", position=Position(x=1, y=1),
                  goal=Position(x=5, y=5), priority=1),
        ]
    )

    selected = DeadlockResolver.select_yield_agent(
        state, set()
    )

    assert selected is None


def test_uses_agent_id_to_break_priority_ties():
    state = SimulationState(
        agents=[
            Agent(id="B", position=Position(x=1, y=1),
                  goal=Position(x=5, y=5), priority=1),
            Agent(id="A", position=Position(x=2, y=1),
                  goal=Position(x=5, y=5), priority=1),
        ]
    )

    selected = DeadlockResolver.select_yield_agent(
        state, {"A", "B"}
    )

    assert selected is not None
    assert selected.id == "A"

from app.models.obstacle import Obstacle


def test_finds_safe_neighbouring_positions():
    agent = Agent(
        id="A",
        position=Position(x=2, y=2),
        goal=Position(x=5, y=5),
    )

    state = SimulationState(agents=[agent])

    positions = DeadlockResolver.find_safe_positions(
        state, agent, grid_width=5, grid_height=5
    )

    actual = {(p.x, p.y) for p in positions}

    assert actual == {(2, 1), (2, 3), (1, 2), (3, 2)}


def test_excludes_obstacles_and_occupied_positions():
    agent = Agent(
        id="A",
        position=Position(x=2, y=2),
        goal=Position(x=5, y=5),
    )

    other_agent = Agent(
        id="B",
        position=Position(x=2, y=1),
        goal=Position(x=5, y=5),
    )

    obstacle = Obstacle(
        id="O1",
        position=Position(x=2, y=3),
    )

    state = SimulationState(
        agents=[agent, other_agent],
        obstacles=[obstacle],
    )

    positions = DeadlockResolver.find_safe_positions(
        state, agent, grid_width=5, grid_height=5
    )

    actual = {(p.x, p.y) for p in positions}

    assert actual == {(1, 2), (3, 2)}


def test_excludes_positions_outside_grid():
    agent = Agent(
        id="A",
        position=Position(x=0, y=0),
        goal=Position(x=5, y=5),
    )

    state = SimulationState(agents=[agent])

    positions = DeadlockResolver.find_safe_positions(
        state, agent, grid_width=3, grid_height=3
    )

    actual = {(p.x, p.y) for p in positions}

    assert actual == {(0, 1), (1, 0)}


def test_returns_empty_when_all_neighbours_blocked():
    agent = Agent(
        id="A",
        position=Position(x=2, y=2),
        goal=Position(x=5, y=5),
    )

    obstacles = [
        Obstacle(id="O1", position=Position(x=2, y=1)),
        Obstacle(id="O2", position=Position(x=2, y=3)),
        Obstacle(id="O3", position=Position(x=1, y=2)),
        Obstacle(id="O4", position=Position(x=3, y=2)),
    ]

    state = SimulationState(
        agents=[agent],
        obstacles=obstacles,
    )

    positions = DeadlockResolver.find_safe_positions(
        state, agent, grid_width=5, grid_height=5
    )

    assert positions == []


def test_selects_position_closest_to_goal():
    agent = Agent(
        id="A",
        position=Position(x=2, y=2),
        goal=Position(x=5, y=2),
    )

    safe_positions = [
        Position(x=2, y=1),
        Position(x=2, y=3),
        Position(x=3, y=2),
        Position(x=1, y=2),
    ]

    selected = DeadlockResolver.select_yield_position(
        safe_positions, agent
    )

    assert selected == Position(x=3, y=2)


def test_returns_none_when_no_safe_position_exists():
    agent = Agent(
        id="A",
        position=Position(x=2, y=2),
        goal=Position(x=5, y=5),
    )

    selected = DeadlockResolver.select_yield_position(
        [], agent
    )

    assert selected is None


def test_selects_first_position_when_distances_are_equal():
    agent = Agent(
        id="A",
        position=Position(x=2, y=2),
        goal=Position(x=3, y=1),
    )

    safe_positions = [
        Position(x=2, y=1),
        Position(x=3, y=2),
    ]

    # Both positions are equally distant from the goal.
    selected = DeadlockResolver.select_yield_position(
        safe_positions, agent
    )

    assert selected == Position(x=2, y=1)


def test_moves_yielding_agent_to_safe_position():
    agent = Agent(
        id="A",
        position=Position(x=2, y=2),
        goal=Position(x=5, y=5),
    )

    state = SimulationState(agents=[agent])

    result = DeadlockResolver.move_yielding_agent(
        state,
        agent,
        Position(x=3, y=2),
        grid_width=5,
        grid_height=5,
    )

    assert result is True
    assert agent.position == Position(x=3, y=2)


def test_rejects_occupied_destination():
    agent = Agent(
        id="A",
        position=Position(x=2, y=2),
        goal=Position(x=5, y=5),
    )

    other_agent = Agent(
        id="B",
        position=Position(x=3, y=2),
        goal=Position(x=5, y=5),
    )

    state = SimulationState(agents=[agent, other_agent])

    result = DeadlockResolver.move_yielding_agent(
        state, agent, Position(x=3, y=2), 5, 5
    )

    assert result is False
    assert agent.position == Position(x=2, y=2)


def test_rejects_obstacle_destination():
    agent = Agent(
        id="A",
        position=Position(x=2, y=2),
        goal=Position(x=5, y=5),
    )

    obstacle = Obstacle(
        id="O1",
        position=Position(x=3, y=2),
    )

    state = SimulationState(
        agents=[agent],
        obstacles=[obstacle],
    )

    result = DeadlockResolver.move_yielding_agent(
        state, agent, Position(x=3, y=2), 5, 5
    )

    assert result is False
    assert agent.position == Position(x=2, y=2)


def test_rejects_out_of_bounds_destination():
    agent = Agent(
        id="A",
        position=Position(x=2, y=2),
        goal=Position(x=5, y=5),
    )

    state = SimulationState(agents=[agent])

    result = DeadlockResolver.move_yielding_agent(
        state, agent, Position(x=5, y=2), 5, 5
    )

    assert result is False
    assert agent.position == Position(x=2, y=2)


def test_recovers_deadlock_by_moving_lowest_priority_agent():
    agent_a = Agent(
        id="A",
        position=Position(x=1, y=1),
        goal=Position(x=5, y=5),
        priority=3,
    )

    agent_b = Agent(
        id="B",
        position=Position(x=2, y=1),
        goal=Position(x=5, y=5),
        priority=1,
    )

    state = SimulationState(agents=[agent_a, agent_b])

    result = DeadlockResolver.recover_deadlock(
        state,
        {"A", "B"},
        grid_width=5,
        grid_height=5,
    )

    assert result is True
    assert agent_b.position != Position(x=2, y=1)
    assert agent_a.position == Position(x=1, y=1)


def test_recovery_fails_when_no_safe_position_exists():
    agent = Agent(
        id="A",
        position=Position(x=2, y=2),
        goal=Position(x=5, y=5),
    )

    obstacles = [
        Obstacle(id="O1", position=Position(x=2, y=1)),
        Obstacle(id="O2", position=Position(x=2, y=3)),
        Obstacle(id="O3", position=Position(x=1, y=2)),
        Obstacle(id="O4", position=Position(x=3, y=2)),
    ]

    state = SimulationState(
        agents=[agent],
        obstacles=obstacles,
    )

    result = DeadlockResolver.recover_deadlock(
        state, {"A"}, 5, 5
    )

    assert result is False
    assert agent.position == Position(x=2, y=2)


def test_recovery_fails_with_empty_deadlocked_group():
    agent = Agent(
        id="A",
        position=Position(x=2, y=2),
        goal=Position(x=5, y=5),
    )

    state = SimulationState(agents=[agent])

    result = DeadlockResolver.recover_deadlock(
        state, set(), 5, 5
    )

    assert result is False
    assert agent.position == Position(x=2, y=2)

