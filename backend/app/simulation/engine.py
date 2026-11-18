
from app.simulation.state import SimulationState


class SimulationEngine:
    """Controls the lifecycle of a multi-agent simulation."""

    def __init__(self, initial_state: SimulationState):
        self.initial_state = initial_state.model_copy(deep=True)
        self.state = initial_state.model_copy(deep=True)

    def reset(self) -> SimulationState:
        """Restore the simulation to its initial state."""
        self.state = self.initial_state.model_copy(deep=True)
        self.state.current_step = 0
        self.state.is_running = False
        self.state.is_finished = False

        return self.state

    def step(self) -> SimulationState:
        """Advance the simulation by one timestep."""
        if self.state.is_finished:
            return self.state

        self.state.current_step += 1
        self.state.is_running = True

        return self.state

    def stop(self) -> SimulationState:
        """Stop the simulation manually."""
        self.state.is_running = False
        self.state.is_finished = True

        return self.state

    def run(self, max_steps: int = 100) -> SimulationState:
        """Run the simulation until the step limit is reached."""
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1")

        while (
            self.state.current_step < max_steps
            and not self.state.is_finished
        ):
            self.step()

        if self.state.current_step >= max_steps:
            self.state.is_running = False
            self.state.is_finished = True

        return self.state
