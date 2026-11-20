from app.models.position import Position
from app.simulation.state import SimulationState
from app.models.agent import Agent
from app.algorithms.deadlock_detector import DeadlockDetector


def test_build_wait_for_graph():
    dependencies = {
        "robot_A": {"robot_B"},
        "robot_B": {"robot_C"},
        "robot_C": {"robot_A"},
    }

    graph = DeadlockDetector.build_wait_for_graph(dependencies)

    assert graph == {
        "robot_A": {"robot_B"},
        "robot_B": {"robot_C"},
        "robot_C": {"robot_A"},
    }


def test_build_wait_for_graph_with_no_dependencies():
    dependencies = {
        "robot_A": set(),
        "robot_B": set(),
    }

    graph = DeadlockDetector.build_wait_for_graph(dependencies)

    assert graph == {
        "robot_A": set(),
        "robot_B": set(),
    }


def test_build_wait_for_graph_adds_missing_nodes():
    dependencies = {
        "robot_A": {"robot_B"},
    }

    graph = DeadlockDetector.build_wait_for_graph(dependencies)

    assert graph == {
        "robot_A": {"robot_B"},
        "robot_B": set(),
    }


def test_detect_simple_cycle():
    graph = {
        "robot_A": {"robot_B"},
        "robot_B": {"robot_A"},
    }

    cycles = DeadlockDetector.detect_cycles(graph)

    assert len(cycles) == 1
    assert set(cycles[0]) == {"robot_A", "robot_B"}


def test_detect_three_agent_cycle():
    graph = {
        "robot_A": {"robot_B"},
        "robot_B": {"robot_C"},
        "robot_C": {"robot_A"},
    }

    cycles = DeadlockDetector.detect_cycles(graph)

    assert len(cycles) == 1
    assert set(cycles[0]) == {
        "robot_A",
        "robot_B",
        "robot_C",
    }


def test_detect_no_cycle():
    graph = {
        "robot_A": {"robot_B"},
        "robot_B": {"robot_C"},
        "robot_C": set(),
    }

    cycles = DeadlockDetector.detect_cycles(graph)

    assert cycles == []


def test_detect_multiple_independent_cycles():
    graph = {
        "robot_A": {"robot_B"},
        "robot_B": {"robot_A"},
        "robot_C": {"robot_D"},
        "robot_D": {"robot_C"},
    }

    cycles = DeadlockDetector.detect_cycles(graph)

    assert len(cycles) == 2


def test_get_deadlocked_agents():
    graph = {
        "robot_A": {"robot_B"},
        "robot_B": {"robot_C"},
        "robot_C": {"robot_A"},
    }

    deadlocked = DeadlockDetector.get_deadlocked_agents(graph)

    assert deadlocked == {
        "robot_A",
        "robot_B",
        "robot_C",
    }


def test_get_deadlocked_agents_with_no_cycle():
    graph = {
        "robot_A": {"robot_B"},
        "robot_B": {"robot_C"},
        "robot_C": set(),
    }

    deadlocked = DeadlockDetector.get_deadlocked_agents(graph)

    assert deadlocked == set()


def test_get_deadlocked_agents_with_multiple_cycles():
    graph = {
        "robot_A": {"robot_B"},
        "robot_B": {"robot_A"},
        "robot_C": {"robot_D"},
        "robot_D": {"robot_C"},
        "robot_E": set(),
    }

    deadlocked = DeadlockDetector.get_deadlocked_agents(graph)

    assert deadlocked == {
        "robot_A",
        "robot_B",
        "robot_C",
        "robot_D",
    }


def test_build_waiting_dependencies():
    state = SimulationState(
        agents=[
            Agent(
                id="robot_A",
                position=Position(x=1, y=1),
                goal=Position(x=5, y=5),
            ),
            Agent(
                id="robot_B",
                position=Position(x=2, y=1),
                goal=Position(x=5, y=5),
            ),
        ]
    )

    proposals = {
        "robot_A": Position(x=2, y=1),
    }

    dependencies = DeadlockDetector.build_waiting_dependencies(
        state, proposals
    )

    # A stationary occupant is a collision constraint, not a wait-for cycle.
    assert dependencies == {}


def test_build_three_agent_circular_dependencies():
    state = SimulationState(
        agents=[
            Agent(
                id="robot_A",
                position=Position(x=1, y=1),
                goal=Position(x=5, y=5),
            ),
            Agent(
                id="robot_B",
                position=Position(x=2, y=1),
                goal=Position(x=5, y=5),
            ),
            Agent(
                id="robot_C",
                position=Position(x=2, y=2),
                goal=Position(x=5, y=5),
            ),
        ]
    )

    proposals = {
        "robot_A": Position(x=2, y=1),
        "robot_B": Position(x=2, y=2),
        "robot_C": Position(x=1, y=1),
    }

    dependencies = DeadlockDetector.build_waiting_dependencies(
        state, proposals
    )

    assert dependencies == {
        "robot_A": {"robot_B"},
        "robot_B": {"robot_C"},
        "robot_C": {"robot_A"},
    }


def test_build_waiting_dependencies_ignores_stationary_agents():
    state = SimulationState(
        agents=[
            Agent(
                id="robot_A",
                position=Position(x=1, y=1),
                goal=Position(x=5, y=5),
            ),
            Agent(
                id="robot_B",
                position=Position(x=2, y=1),
                goal=Position(x=5, y=5),
            ),
        ]
    )

    proposals = {
        "robot_A": Position(x=1, y=1),
        "robot_B": Position(x=2, y=1),
    }

    dependencies = DeadlockDetector.build_waiting_dependencies(
        state, proposals
    )

    assert dependencies == {}


def test_detect_deadlocks_with_three_agent_cycle():
    state = SimulationState(
        agents=[
            Agent(
                id="robot_A",
                position=Position(x=1, y=1),
                goal=Position(x=5, y=5),
            ),
            Agent(
                id="robot_B",
                position=Position(x=2, y=1),
                goal=Position(x=5, y=5),
            ),
            Agent(
                id="robot_C",
                position=Position(x=2, y=2),
                goal=Position(x=5, y=5),
            ),
        ]
    )

    proposals = {
        "robot_A": Position(x=2, y=1),
        "robot_B": Position(x=2, y=2),
        "robot_C": Position(x=1, y=1),
    }

    deadlocked = DeadlockDetector.detect_deadlocks(state, proposals)

    assert deadlocked == {
        "robot_A",
        "robot_B",
        "robot_C",
    }


def test_detect_deadlocks_without_cycle():
    state = SimulationState(
        agents=[
            Agent(
                id="robot_A",
                position=Position(x=1, y=1),
                goal=Position(x=5, y=5),
            ),
            Agent(
                id="robot_B",
                position=Position(x=2, y=1),
                goal=Position(x=5, y=5),
            ),
        ]
    )

    proposals = {
        "robot_A": Position(x=3, y=1),
        "robot_B": Position(x=4, y=1),
    }

    deadlocked = DeadlockDetector.detect_deadlocks(state, proposals)

    assert deadlocked == set()


def test_detect_deadlocks_with_empty_proposals():
    state = SimulationState(
        agents=[
            Agent(
                id="robot_A",
                position=Position(x=1, y=1),
                goal=Position(x=5, y=5),
            ),
        ]
    )

    deadlocked = DeadlockDetector.detect_deadlocks(state, {})

    assert deadlocked == set()

