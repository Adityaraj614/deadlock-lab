from app.models.position import Position
from app.simulation.state import SimulationState

class DeadlockDetector:
    """Detects deadlocks using a wait-for graph."""

    @staticmethod
    def build_wait_for_graph(
        waiting_dependencies: dict[str, set[str]],
    ) -> dict[str, set[str]]:
        """Build a wait-for graph from agent dependencies."""

        graph = {}

        for agent_id, waiting_for in waiting_dependencies.items():
            graph[agent_id] = set(waiting_for)

            for other_id in waiting_for:
                graph.setdefault(other_id, set())

        return graph


    @staticmethod
    def detect_cycles(
        graph: dict[str, set[str]],
    ) -> list[list[str]]:
        """Detect cycles in a wait-for graph using DFS."""

        visited = set()
        recursion_stack = set()
        cycles = []

        def dfs(node, path):
            visited.add(node)
            recursion_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, set()):
                if neighbor not in visited:
                    dfs(neighbor, path)
                elif neighbor in recursion_stack:
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:].copy()

                    if cycle not in cycles:
                        cycles.append(cycle)

            path.pop()
            recursion_stack.remove(node)

        for node in graph:
            if node not in visited:
                dfs(node, [])

        return cycles


    @staticmethod
    def get_deadlocked_agents(
        graph: dict[str, set[str]],
    ) -> set[str]:
        """Return all agents involved in detected deadlock cycles."""

        cycles = DeadlockDetector.detect_cycles(graph)

        deadlocked_agents = set()

        for cycle in cycles:
            deadlocked_agents.update(cycle)

        return deadlocked_agents


    @staticmethod
    def build_waiting_dependencies(
        state: SimulationState,
        proposals: dict[str, Position],
    ) -> dict[str, set[str]]:
        """Build dependencies between agents based on occupied destinations."""

        original_positions = {
            agent.id: agent.position
            for agent in state.agents
        }

        dependencies = {}

        for agent_id, destination in proposals.items():
            if destination == original_positions[agent_id]:
                continue

            for other_id, other_position in original_positions.items():
                if other_id == agent_id:
                    continue

                if destination == other_position:
                    dependencies.setdefault(agent_id, set()).add(other_id)

        return dependencies


    @staticmethod
    def detect_deadlocks(
        state: SimulationState,
        proposals: dict[str, Position],
    ) -> set[str]:
        """Detect deadlocked agents from simulation state and proposals."""

        dependencies = DeadlockDetector.build_waiting_dependencies(
            state, proposals
        )

        graph = DeadlockDetector.build_wait_for_graph(dependencies)

        return DeadlockDetector.get_deadlocked_agents(graph)
