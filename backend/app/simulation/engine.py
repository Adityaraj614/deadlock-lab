from app.simulation.state import SimulationState
from app.simulation.multi_agent_executor import MultiAgentExecutor, CoordinationStrategy
from app.metrics.metrics import SimulationMetrics
from typing import Optional

class SimulationEngine:
    """Controls the lifecycle of a multi-agent simulation."""

    def __init__(
        self,
        initial_state: SimulationState,
        metrics: Optional[SimulationMetrics] = None,
    ):
        self.initial_state = initial_state
        self.state = initial_state.model_copy(deep=True)
        self.metrics = metrics
        self._grid_width: int | None = None
        self._grid_height: int | None = None

    def reset(self) -> SimulationState:
        """Restore the simulation to its initial state."""
        self.state = self.initial_state.model_copy(deep=True)
        self.state.current_step = 0
        self.state.is_running = False
        self.state.is_finished = False

        if self.metrics is not None:
            self.metrics.total_steps = 0
            self.metrics.completed_agents = 0
            self.metrics.waiting_agents = 0
            self.metrics.blocked_agents = 0
            self.metrics.collisions_prevented = 0
            self.metrics.deadlocks_detected = 0
            self.metrics.deadlock_recovery_attempts = 0
            self.metrics.successful_recoveries = 0
            self.metrics.total_path_length = 0.0
            self.metrics.average_steps_per_completed = 0.0
            self.metrics.simulation_complete = False
            self.metrics.simulation_termination_reason = None

        return self.state

    def step(
        self,
        actions: list | None = None,
        grid_width: int | None = None,
        grid_height: int | None = None,
        reservation_table: object | None = None,
        strategy: CoordinationStrategy = CoordinationStrategy.FULL,
    ) -> SimulationState:
        """Advance the simulation by one timestep.

        ``actions`` should be a list of ``Action`` objects, one per agent.
        If ``actions`` is empty or ``None``, all agents wait.
        ``grid_width`` and ``grid_height`` are the simulation grid dimensions.
        If not provided, defaults of 10x10 are used.
        ``strategy`` controls the coordination strategy to use during the step.
        The default ``CoordinationStrategy.FULL`` preserves the existing behavior.
        """

        if self.state.is_finished:
            return self.state

        # Use provided dimensions or defaults.
        if grid_width is not None:
            self._grid_width = grid_width
        if grid_height is not None:
            self._grid_height = grid_height

        w = self._grid_width or 10
        h = self._grid_height or 10

        # Execute one multi-agent timestep.
        if actions is None:
            actions = []

        self.state = MultiAgentExecutor.execute(
            self.state,
            actions,
            w,
            h,
            time=self.state.current_step,
            reservation_table=reservation_table,
            metrics=self.metrics,
            strategy=strategy,
        )

        self.state.current_step += 1
        self.state.is_running = True

        return self.state

    def stop(self) -> SimulationState:
        """Stop the simulation manually."""
        self.state.is_running = False
        self.state.is_finished = True
        return self.state

    def run(
        self,
        max_steps: int = 100,
        actions_provider: object | None = None,
    ) -> SimulationState:
        """Run the simulation until the step limit is reached.

        ``actions_provider`` should provide a list of ``Action`` objects
        for each timestep.
        """

        if max_steps < 1:
            raise ValueError("max_steps must be at least 1")

        while (
            self.state.current_step < max_steps
            and not self.state.is_finished
        ):
            # Get actions for this step if a provider is given.
            actions: list | None = None
            if actions_provider is not None:
                actions = actions_provider.get_actions(
                    self.state, self.state.current_step
                )

            self.state = self.step(
                actions,
                self._grid_width,
                self._grid_height,
            )

        if self.state.current_step >= max_steps:
            self.state.is_running = False
            self.state.is_finished = True
            if self.metrics is not None:
                self.metrics.mark_complete("max_steps reached")

        return self.state