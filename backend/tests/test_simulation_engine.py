import pytest


from app.simulation.engine import SimulationEngine
from app.simulation.state import SimulationState
from app.models.agent import Agent
from app.models.position import Position


def create_initial_state():
    return SimulationState(
        agents=[
            Agent(
                id="robot_1",
                position=Position(x=0, y=0),
                goal=Position(x=5, y=5)
            )
        ]
    )


def test_engine_initialization():
    engine = SimulationEngine(create_initial_state())

    assert engine.state.current_step == 0
    assert engine.state.is_running is False
    assert len(engine.state.agents) == 1


def test_step_advances_timestep():
    engine = SimulationEngine(create_initial_state())

    engine.step()

    assert engine.state.current_step == 1
    assert engine.state.is_running is True


def test_multiple_steps():
    engine = SimulationEngine(create_initial_state())

    engine.step()
    engine.step()
    engine.step()

    assert engine.state.current_step == 3


def test_reset_restores_initial_state():
    engine = SimulationEngine(create_initial_state())

    engine.step()
    engine.step()
    engine.reset()

    assert engine.state.current_step == 0
    assert engine.state.is_running is False
    assert len(engine.state.agents) == 1


def test_reset_restores_agent_position():
    engine = SimulationEngine(create_initial_state())

    engine.state.agents[0].position = Position(x=3, y=3)
    engine.reset()

    assert engine.state.agents[0].position == Position(x=0, y=0)


def test_run_until_max_steps():
    engine = SimulationEngine(create_initial_state())

    engine.run(max_steps=10)

    assert engine.state.current_step == 10
    assert engine.state.is_running is False
    assert engine.state.is_finished is True


def test_manual_stop():
    engine = SimulationEngine(create_initial_state())

    engine.step()
    engine.stop()

    assert engine.state.is_running is False
    assert engine.state.is_finished is True


def test_finished_simulation_cannot_advance():
    engine = SimulationEngine(create_initial_state())

    engine.stop()
    engine.step()

    assert engine.state.current_step == 0


def test_invalid_max_steps():
    engine = SimulationEngine(create_initial_state())

    with pytest.raises(ValueError):
        engine.run(max_steps=0)


def test_reset_clears_finished_status():
    engine = SimulationEngine(create_initial_state())

    engine.run(max_steps=5)
    engine.reset()

    assert engine.state.current_step == 0
    assert engine.state.is_running is False
    assert engine.state.is_finished is False
