from app.algorithms.reservation_table import ReservationTable
from app.metrics.metrics import SimulationMetrics
from app.models.action import Action, ActionType
from app.models.agent import Agent, AgentStatus
from app.models.position import Position
from app.simulation.multi_agent_executor import (
    CoordinationStrategy,
    MultiAgentExecutor,
)
from app.simulation.state import SimulationState


def make_state(*agents: Agent) -> SimulationState:
    return SimulationState(
        grid_width=6,
        grid_height=6,
        agents=list(agents),
        obstacles=[],
    )


def test_priority_prefers_higher_priority_robot_for_shared_destination():
    state = make_state(
        Agent(
            id="high",
            position=Position(x=0, y=1),
            goal=Position(x=5, y=1),
            priority=1,
        ),
        Agent(
            id="low",
            position=Position(x=2, y=1),
            goal=Position(x=0, y=1),
            priority=3,
        ),
    )
    actions = [
        Action(agent_id="high", action_type=ActionType.MOVE_RIGHT),
        Action(agent_id="low", action_type=ActionType.MOVE_LEFT),
    ]

    result = MultiAgentExecutor.execute(
        state,
        actions,
        6,
        6,
        strategy=CoordinationStrategy.PRIORITY,
    )

    assert result.agents[0].position == Position(x=1, y=1)
    assert result.agents[0].status == AgentStatus.MOVING
    assert result.agents[1].position == Position(x=2, y=1)
    assert result.agents[1].status == AgentStatus.WAITING


def test_reservation_blocks_reserved_vertex_and_edge_at_current_timestep():
    state = make_state(
        Agent(
            id="robot",
            position=Position(x=0, y=0),
            goal=Position(x=5, y=0),
        )
    )
    actions = [Action(agent_id="robot", action_type=ActionType.MOVE_RIGHT)]
    table = ReservationTable(grid_width=6, grid_height=6, max_time=10)
    table.reserve_vertex(Position(x=1, y=0), time=2, agent_id="other")
    table.reserve_edge(
        Position(x=0, y=0), Position(x=1, y=0), time=2, agent_id="other"
    )

    result = MultiAgentExecutor.execute(
        state,
        actions,
        6,
        6,
        time=2,
        reservation_table=table,
        strategy=CoordinationStrategy.RESERVATION,
    )

    assert result.agents[0].position == Position(x=0, y=0)
    assert result.agents[0].status == AgentStatus.WAITING


def test_deadlock_strategy_detects_and_recovers_cycle():
    state = make_state(
        Agent(
            id="a",
            position=Position(x=1, y=1),
            goal=Position(x=5, y=5),
            priority=2,
        ),
        Agent(
            id="b",
            position=Position(x=2, y=1),
            goal=Position(x=5, y=5),
            priority=1,
        ),
        Agent(
            id="c",
            position=Position(x=2, y=2),
            goal=Position(x=5, y=5),
            priority=3,
        ),
        Agent(
            id="d",
            position=Position(x=1, y=2),
            goal=Position(x=5, y=5),
            priority=4,
        ),
    )
    actions = [
        Action(agent_id="a", action_type=ActionType.MOVE_RIGHT),
        Action(agent_id="b", action_type=ActionType.MOVE_DOWN),
        Action(agent_id="c", action_type=ActionType.MOVE_LEFT),
        Action(agent_id="d", action_type=ActionType.MOVE_UP),
    ]
    metrics = SimulationMetrics()

    result = MultiAgentExecutor.execute(
        state,
        actions,
        6,
        6,
        metrics=metrics,
        strategy=CoordinationStrategy.DEADLOCK,
    )

    assert metrics.deadlocks_detected == 1
    assert metrics.deadlock_recovery_attempts == 1
    assert metrics.successful_recoveries == 1
    assert any(agent.position != original for agent, original in zip(
        result.agents,
        [
            Position(x=1, y=1),
            Position(x=2, y=1),
            Position(x=2, y=2),
            Position(x=1, y=2),
        ],
    ))


def test_full_combines_priority_reservation_and_deadlock_recovery():
    state = make_state(
        Agent(
            id="high",
            position=Position(x=0, y=1),
            goal=Position(x=5, y=1),
            priority=1,
        ),
        Agent(
            id="low",
            position=Position(x=2, y=1),
            goal=Position(x=0, y=1),
            priority=3,
        ),
    )
    table = ReservationTable(grid_width=6, grid_height=6, max_time=10)
    table.reserve_vertex(Position(x=1, y=1), time=0, agent_id="reserved")
    metrics = SimulationMetrics()

    result = MultiAgentExecutor.execute(
        state,
        [
            Action(agent_id="high", action_type=ActionType.MOVE_RIGHT),
            Action(agent_id="low", action_type=ActionType.MOVE_LEFT),
        ],
        6,
        6,
        time=0,
        reservation_table=table,
        metrics=metrics,
        strategy=CoordinationStrategy.FULL,
    )

    assert all(
        agent.position != Position(x=1, y=1) for agent in result.agents
    )
    assert metrics.deadlocks_detected >= 1
    assert metrics.deadlock_recovery_attempts >= 1


def test_all_strategies_prevent_vertex_and_edge_collisions():
    for strategy in CoordinationStrategy:
        vertex_state = make_state(
            Agent(id="a", position=Position(x=0, y=0), goal=Position(x=5, y=0)),
            Agent(id="b", position=Position(x=2, y=0), goal=Position(x=0, y=0)),
        )
        vertex_result = MultiAgentExecutor.execute(
            vertex_state,
            [
                Action(agent_id="a", action_type=ActionType.MOVE_RIGHT),
                Action(agent_id="b", action_type=ActionType.MOVE_LEFT),
            ],
            6,
            6,
            strategy=strategy,
        )
        assert len({(agent.position.x, agent.position.y) for agent in vertex_result.agents}) == 2

        edge_state = make_state(
            Agent(id="a", position=Position(x=0, y=0), goal=Position(x=5, y=0)),
            Agent(id="b", position=Position(x=1, y=0), goal=Position(x=0, y=0)),
        )
        edge_result = MultiAgentExecutor.execute(
            edge_state,
            [
                Action(agent_id="a", action_type=ActionType.MOVE_RIGHT),
                Action(agent_id="b", action_type=ActionType.MOVE_LEFT),
            ],
            6,
            6,
            strategy=strategy,
        )
        assert len({
            (agent.position.x, agent.position.y)
            for agent in edge_result.agents
        }) == 2
        assert [
            (edge_state.agents[index].position.x, edge_state.agents[index].position.y)
            for index in range(2)
        ] != [
            (edge_result.agents[1].position.x, edge_result.agents[1].position.y),
            (edge_result.agents[0].position.x, edge_result.agents[0].position.y),
        ]


def test_completed_robots_remain_at_their_goals():
    completed = Agent(
        id="done",
        position=Position(x=2, y=2),
        goal=Position(x=2, y=2),
        status=AgentStatus.COMPLETED,
    )
    moving = Agent(
        id="moving",
        position=Position(x=0, y=0),
        goal=Position(x=5, y=0),
    )

    result = MultiAgentExecutor.execute(
        make_state(completed, moving),
        [
            Action(agent_id="done", action_type=ActionType.MOVE_RIGHT),
            Action(agent_id="moving", action_type=ActionType.MOVE_RIGHT),
        ],
        6,
        6,
        strategy=CoordinationStrategy.FULL,
    )

    assert result.agents[0].position == Position(x=2, y=2)
    assert result.agents[0].status == AgentStatus.COMPLETED
