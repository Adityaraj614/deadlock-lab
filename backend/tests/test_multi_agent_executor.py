import pytest
from app.algorithms.deadlock_detector import DeadlockDetector
from app.models.action import Action, ActionType
from app.models.agent import Agent
from app.models.obstacle import Obstacle
from app.models.position import Position
from app.simulation.state import SimulationState
from app.simulation.multi_agent_executor import MultiAgentExecutor


@pytest.fixture
def multi_agent_state():
    robot_1 = Agent(
        id="robot_1",
        position=Position(x=2, y=2),
        goal=Position(x=8, y=8),
    )

    robot_2 = Agent(
        id="robot_2",
        position=Position(x=5, y=2),
        goal=Position(x=0, y=0),
    )

    return SimulationState(agents=[robot_1, robot_2])


def test_calculate_multiple_proposals(multi_agent_state):
    actions = [
        Action(agent_id="robot_1", action_type=ActionType.MOVE_RIGHT),
        Action(agent_id="robot_2", action_type=ActionType.MOVE_LEFT),
    ]

    proposals = MultiAgentExecutor.calculate_proposals(
        multi_agent_state, actions, 10, 10
    )

    assert proposals["robot_1"] == Position(x=3, y=2)
    assert proposals["robot_2"] == Position(x=4, y=2)


def test_proposals_do_not_modify_agent_positions(multi_agent_state):
    original_positions = {
        agent.id: agent.position for agent in multi_agent_state.agents
    }

    actions = [
        Action(agent_id="robot_1", action_type=ActionType.MOVE_RIGHT),
    ]

    MultiAgentExecutor.calculate_proposals(
        multi_agent_state, actions, 10, 10
    )

    for agent in multi_agent_state.agents:
        assert agent.position == original_positions[agent.id]


def test_wait_proposal(multi_agent_state):
    actions = [
        Action(agent_id="robot_1", action_type=ActionType.WAIT),
    ]

    proposals = MultiAgentExecutor.calculate_proposals(
        multi_agent_state, actions, 10, 10
    )

    assert proposals["robot_1"] == Position(x=2, y=2)


def test_obstacle_blocks_proposal(multi_agent_state):
    multi_agent_state.obstacles.append(
        Obstacle(
            id="obstacle_1",
            position=Position(x=3, y=2),
        )
    )

    actions = [
        Action(agent_id="robot_1", action_type=ActionType.MOVE_RIGHT),
    ]

    proposals = MultiAgentExecutor.calculate_proposals(
        multi_agent_state, actions, 10, 10
    )

    assert proposals["robot_1"] == Position(x=2, y=2)


def test_boundary_blocks_proposal(multi_agent_state):
    multi_agent_state.agents[0].position = Position(x=0, y=2)

    actions = [
        Action(agent_id="robot_1", action_type=ActionType.MOVE_LEFT),
    ]

    proposals = MultiAgentExecutor.calculate_proposals(
        multi_agent_state, actions, 10, 10
    )

    assert proposals["robot_1"] == Position(x=0, y=2)


def test_unknown_agent_rejected(multi_agent_state):
    actions = [
        Action(agent_id="robot_99", action_type=ActionType.MOVE_RIGHT),
    ]

    with pytest.raises(ValueError, match="Agent 'robot_99' not found"):
        MultiAgentExecutor.calculate_proposals(
            multi_agent_state, actions, 10, 10
        )


def test_duplicate_actions_rejected(multi_agent_state):
    actions = [
        Action(agent_id="robot_1", action_type=ActionType.MOVE_RIGHT),
        Action(agent_id="robot_1", action_type=ActionType.MOVE_UP),
    ]

    with pytest.raises(ValueError, match="Duplicate action"):
        MultiAgentExecutor.calculate_proposals(
            multi_agent_state, actions, 10, 10
        )


def test_invalid_grid_dimensions_rejected(multi_agent_state):
    with pytest.raises(ValueError, match="Grid dimensions must be at least 1"):
        MultiAgentExecutor.calculate_proposals(
            multi_agent_state, [], 0, 10
        )

def test_vertex_conflict_detected():
    proposals = {
        "robot_1": Position(x=3, y=2),
        "robot_2": Position(x=3, y=2),
        "robot_3": Position(x=5, y=4),
    }

    conflicts = MultiAgentExecutor.detect_vertex_conflicts(proposals)

    assert conflicts == {"robot_1", "robot_2"}


def test_no_vertex_conflict():
    proposals = {
        "robot_1": Position(x=3, y=2),
        "robot_2": Position(x=5, y=4),
    }

    conflicts = MultiAgentExecutor.detect_vertex_conflicts(proposals)

    assert conflicts == set()


def test_multiple_vertex_conflicts():
    proposals = {
        "robot_1": Position(x=3, y=2),
        "robot_2": Position(x=3, y=2),
        "robot_3": Position(x=5, y=4),
        "robot_4": Position(x=5, y=4),
    }

    conflicts = MultiAgentExecutor.detect_vertex_conflicts(proposals)

    assert conflicts == {
        "robot_1", "robot_2", "robot_3", "robot_4"
    }

def test_edge_conflict_detected(multi_agent_state):
    # Robot 1 moves from (2, 2) to (3, 2).
    # Robot 2 moves from (5, 2) to (4, 2).
    # Set up adjacent positions to simulate a swap.
    multi_agent_state.agents[0].position = Position(x=2, y=2)
    multi_agent_state.agents[1].position = Position(x=3, y=2)

    proposals = {
        "robot_1": Position(x=3, y=2),
        "robot_2": Position(x=2, y=2),
    }

    conflicts = MultiAgentExecutor.detect_edge_conflicts(
        multi_agent_state, proposals
    )

    assert conflicts == {"robot_1", "robot_2"}


def test_no_edge_conflict(multi_agent_state):
    proposals = {
        "robot_1": Position(x=3, y=2),
        "robot_2": Position(x=5, y=3),
    }

    conflicts = MultiAgentExecutor.detect_edge_conflicts(
        multi_agent_state, proposals
    )

    assert conflicts == set()


def test_waiting_agents_do_not_create_edge_conflict(multi_agent_state):
    proposals = {
        "robot_1": Position(x=2, y=2),
        "robot_2": Position(x=5, y=2),
    }

    conflicts = MultiAgentExecutor.detect_edge_conflicts(
        multi_agent_state, proposals
    )

    assert conflicts == set()


def test_resolve_vertex_conflicts(multi_agent_state):
    proposals = {
        "robot_1": Position(x=3, y=2),
        "robot_2": Position(x=3, y=2),
    }

    conflicts = MultiAgentExecutor.resolve_conflicts(
        multi_agent_state, proposals
    )

    assert conflicts == {"robot_1", "robot_2"}


def test_resolve_edge_conflicts(multi_agent_state):
    multi_agent_state.agents[0].position = Position(x=2, y=2)
    multi_agent_state.agents[1].position = Position(x=3, y=2)

    proposals = {
        "robot_1": Position(x=3, y=2),
        "robot_2": Position(x=2, y=2),
    }

    conflicts = MultiAgentExecutor.resolve_conflicts(
        multi_agent_state, proposals
    )

    assert conflicts == {"robot_1", "robot_2"}


def test_resolve_no_conflicts(multi_agent_state):
    proposals = {
        "robot_1": Position(x=3, y=2),
        "robot_2": Position(x=5, y=3),
    }

    conflicts = MultiAgentExecutor.resolve_conflicts(
        multi_agent_state, proposals
    )

    assert conflicts == set()


def test_stationary_agent_blocks_incoming_agent(multi_agent_state):
    multi_agent_state.agents[0].position = Position(x=1, y=2)
    multi_agent_state.agents[1].position = Position(x=2, y=2)

    proposals = {
        "robot_1": Position(x=2, y=2),
        "robot_2": Position(x=2, y=2),
    }

    conflicts = MultiAgentExecutor.detect_occupied_destination_conflicts(
        multi_agent_state, proposals
    )

    assert conflicts == {"robot_1"}


def test_agent_can_move_into_cell_being_vacated(multi_agent_state):
    multi_agent_state.agents[0].position = Position(x=1, y=2)
    multi_agent_state.agents[1].position = Position(x=2, y=2)

    proposals = {
        "robot_1": Position(x=2, y=2),
        "robot_2": Position(x=3, y=2),
    }

    conflicts = MultiAgentExecutor.detect_occupied_destination_conflicts(
        multi_agent_state, proposals
    )

    assert conflicts == set()


def test_no_occupied_destination_conflict(multi_agent_state):
    proposals = {
        "robot_1": Position(x=3, y=2),
        "robot_2": Position(x=5, y=3),
    }

    conflicts = MultiAgentExecutor.detect_occupied_destination_conflicts(
        multi_agent_state, proposals
    )

    assert conflicts == set()

def test_apply_proposals_moves_conflict_free_agents(multi_agent_state):
    proposals = {
        "robot_1": Position(x=3, y=2),
        "robot_2": Position(x=5, y=3),
    }

    result = MultiAgentExecutor.apply_proposals(
        multi_agent_state, proposals, set()
    )

    assert result.agents[0].position == Position(x=3, y=2)
    assert result.agents[1].position == Position(x=5, y=3)


def test_apply_proposals_keeps_conflicted_agents_waiting(multi_agent_state):
    proposals = {
        "robot_1": Position(x=3, y=2),
        "robot_2": Position(x=3, y=2),
    }

    conflicts = {"robot_1", "robot_2"}

    result = MultiAgentExecutor.apply_proposals(
        multi_agent_state, proposals, conflicts
    )

    assert result.agents[0].status == "waiting"
    assert result.agents[1].status == "waiting"

    assert result.agents[0].position != Position(x=3, y=2)
    assert result.agents[1].position != Position(x=3, y=2)


def test_apply_proposals_keeps_idle_agent_in_place(multi_agent_state):
    original_position = multi_agent_state.agents[0].position

    proposals = {
        "robot_1": original_position,
    }

    result = MultiAgentExecutor.apply_proposals(
        multi_agent_state, proposals, set()
    )

    assert result.agents[0].position == original_position
    assert result.agents[0].status == "idle"



def test_execute_moves_multiple_agents(multi_agent_state):
    actions = [
        Action(
            agent_id="robot_1",
            action_type=ActionType.MOVE_RIGHT,
        ),
        Action(
            agent_id="robot_2",
            action_type=ActionType.MOVE_RIGHT,
        ),
    ]

    result = MultiAgentExecutor.execute(
        multi_agent_state,
        actions,
        grid_width=10,
        grid_height=10,
    )

    assert result.agents[0].position == Position(x=3, y=2)
    assert result.agents[1].position == Position(x=6, y=2)



def test_execute_blocks_conflicting_agents(multi_agent_state):
    multi_agent_state.agents[0].position = Position(x=2, y=2)
    multi_agent_state.agents[1].position = Position(x=4, y=2)

    actions = [
        Action(
            agent_id="robot_1",
            action_type=ActionType.MOVE_RIGHT,
        ),
        Action(
            agent_id="robot_2",
            action_type=ActionType.MOVE_LEFT,
        ),
    ]

    result = MultiAgentExecutor.execute(
        multi_agent_state,
        actions,
        grid_width=10,
        grid_height=10,
    )

    assert result.agents[0].position == Position(x=2, y=2)
    assert result.agents[1].position == Position(x=4, y=2)

    assert result.agents[0].status == "waiting"
    assert result.agents[1].status == "waiting"



def test_execute_blocks_four_agent_deadlock(multi_agent_state):
    multi_agent_state.agents = [
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
        Agent(
            id="robot_D",
            position=Position(x=1, y=2),
            goal=Position(x=5, y=5),
        ),
    ]

    actions = [
        Action(
            agent_id="robot_A",
            action_type=ActionType.MOVE_RIGHT,
        ),
        Action(
            agent_id="robot_B",
            action_type=ActionType.MOVE_DOWN,
        ),
        Action(
            agent_id="robot_C",
            action_type=ActionType.MOVE_LEFT,
        ),
        Action(
            agent_id="robot_D",
            action_type=ActionType.MOVE_UP,
        ),
    ]

    result = MultiAgentExecutor.execute(
        multi_agent_state,
        actions,
        grid_width=10,
        grid_height=10,
    )

    expected_positions = [
        Position(x=1, y=1),
        Position(x=2, y=1),
        Position(x=2, y=2),
        Position(x=1, y=2),
    ]

    for agent, expected in zip(result.agents, expected_positions):
        assert agent.position == expected
        assert agent.status == "waiting"
