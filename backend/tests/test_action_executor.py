import pytest

from app.models.action import Action, ActionType
from app.models.agent import Agent, AgentStatus
from app.models.obstacle import Obstacle
from app.models.position import Position
from app.simulation.state import SimulationState
from app.simulation.action_executor import ActionExecutor


@pytest.fixture
def simulation_state():
    robot = Agent(
        id="robot_1",
        position=Position(x=2, y=2),
        goal=Position(x=8, y=8),
    )

    return SimulationState(agents=[robot])


def test_move_right(simulation_state):
    action = Action(
        agent_id="robot_1",
        action_type=ActionType.MOVE_RIGHT,
    )

    result = ActionExecutor.execute(simulation_state, action, 10, 10)

    assert result == Position(x=3, y=2)
    assert simulation_state.agents[0].position == result
    assert simulation_state.agents[0].status == AgentStatus.MOVING


def test_move_up(simulation_state):
    action = Action(
        agent_id="robot_1",
        action_type=ActionType.MOVE_UP,
    )

    result = ActionExecutor.execute(simulation_state, action, 10, 10)

    assert result == Position(x=2, y=1)


def test_wait_action(simulation_state):
    action = Action(
        agent_id="robot_1",
        action_type=ActionType.WAIT,
    )

    result = ActionExecutor.execute(simulation_state, action, 10, 10)

    assert result == Position(x=2, y=2)
    assert simulation_state.agents[0].status == AgentStatus.IDLE


def test_obstacle_blocks_movement(simulation_state):
    simulation_state.obstacles.append(
        Obstacle(
            id="obstacle_1",
            position=Position(x=3, y=2),
        )
    )

    action = Action(
        agent_id="robot_1",
        action_type=ActionType.MOVE_RIGHT,
    )

    result = ActionExecutor.execute(simulation_state, action, 10, 10)

    assert result == Position(x=2, y=2)
    assert simulation_state.agents[0].status == AgentStatus.BLOCKED


def test_grid_boundary_blocks_movement(simulation_state):
    simulation_state.agents[0].position = Position(x=0, y=2)

    action = Action(
        agent_id="robot_1",
        action_type=ActionType.MOVE_LEFT,
    )

    result = ActionExecutor.execute(simulation_state, action, 10, 10)

    assert result == Position(x=0, y=2)
    assert simulation_state.agents[0].status == AgentStatus.BLOCKED


def test_unknown_agent_rejected(simulation_state):
    action = Action(
        agent_id="robot_99",
        action_type=ActionType.MOVE_RIGHT,
    )

    with pytest.raises(ValueError, match="Agent 'robot_99' not found"):
        ActionExecutor.execute(simulation_state, action, 10, 10)


def test_invalid_grid_dimensions_rejected(simulation_state):
    action = Action(
        agent_id="robot_1",
        action_type=ActionType.MOVE_RIGHT,
    )

    with pytest.raises(ValueError, match="Grid dimensions must be at least 1"):
        ActionExecutor.execute(simulation_state, action, 0, 10)