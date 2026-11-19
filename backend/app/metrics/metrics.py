from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from app.models.agent import Agent, AgentStatus
from app.simulation.state import SimulationState


@dataclass
class SimulationMetrics:
    """Metrics collected during a multi-agent simulation run.

    Provides programmatic access to simulation performance and
    coordination statistics, suitable for frontend charting.
    """

    total_steps: int = 0
    completed_agents: int = 0
    waiting_agents: int = 0
    blocked_agents: int = 0
    collisions_prevented: int = 0
    deadlocks_detected: int = 0
    deadlock_recovery_attempts: int = 0
    successful_recoveries: int = 0
    total_path_length: float = 0.0
    average_steps_per_completed: float = 0.0
    simulation_complete: bool = False
    simulation_termination_reason: str | None = None

    # ------------------------------------------------------------------
    # Step-by-step collection
    # ------------------------------------------------------------------

    def record_step(self, state: SimulationState) -> None:
        """Record metrics from a single simulation step."""

        self.total_steps += 1

        # Count agent statuses.
        self.waiting_agents = sum(
            1 for a in state.agents if a.status == AgentStatus.WAITING
        )
        self.blocked_agents = sum(
            1 for a in state.agents if a.status == AgentStatus.BLOCKED
        )

        # Completed agents have reached their goal.
        self.completed_agents = sum(
            1 for a in state.agents if a.status == AgentStatus.COMPLETED
        )

    # ------------------------------------------------------------------
    # Collision tracking
    # ------------------------------------------------------------------

    def record_collision_prevented(self) -> None:
        """Record that a collision was prevented during movement coordination."""
        self.collisions_prevented += 1

    # ------------------------------------------------------------------
    # Deadlock tracking
    # ------------------------------------------------------------------

    def record_deadlock_detected(self) -> None:
        """Record that a deadlock was detected."""
        self.deadlocks_detected += 1

    def record_deadlock_recovery_attempt(self) -> None:
        """Record a deadlock recovery attempt."""
        self.deadlock_recovery_attempts += 1

    def record_successful_recovery(self) -> None:
        """Record that a deadlock recovery was successful."""
        self.successful_recoveries += 1

    # ------------------------------------------------------------------
    # Path length tracking
    # ------------------------------------------------------------------

    def add_path_length(self, length: float) -> None:
        """Add the path length of a completed agent."""
        self.total_path_length += length
        n_completed = max(self.completed_agents, 1)
        self.average_steps_per_completed = (
            self.total_path_length / n_completed
        )

    # ------------------------------------------------------------------
    # Simulation completion
    # ------------------------------------------------------------------

    def mark_complete(self, reason: str | None = None) -> None:
        """Mark the simulation as complete."""
        self.simulation_complete = True
        self.simulation_termination_reason = reason

    def mark_incomplete(self) -> None:
        """Mark the simulation as incomplete (e.g., step limit reached)."""
        self.simulation_complete = False
        self.simulation_termination_reason = None

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Convert metrics to a dictionary suitable for JSON serialization."""
        return {
            "total_steps": self.total_steps,
            "completed_agents": self.completed_agents,
            "waiting_agents": self.waiting_agents,
            "blocked_agents": self.blocked_agents,
            "collisions_prevented": self.collisions_prevented,
            "deadlocks_detected": self.deadlocks_detected,
            "deadlock_recovery_attempts": self.deadlock_recovery_attempts,
            "successful_recoveries": self.successful_recoveries,
            "total_path_length": self.total_path_length,
            "average_steps_per_completed": self.average_steps_per_completed,
            "simulation_complete": self.simulation_complete,
            "simulation_termination_reason": self.simulation_termination_reason,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SimulationMetrics:
        """Create a SimulationMetrics instance from a dictionary."""
        instance = cls()
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        return instance

    def __repr__(self) -> str:
        return (
            f"SimulationSteps={self.total_steps}, "
            f"Completed={self.completed_agents}, "
            f"Waiting={self.waiting_agents}, "
            f"Blocked={self.blocked_agents}, "
            f"CollisionsPrevented={self.collisions_prevented}, "
            f"Deadlocks={self.deadlocks_detected}, "
            f"Recoveries={self.successful_recoveries}/{self.deadlock_recovery_attempts}"
        )