with open(r'C:\Users\kumar\OneDrive\Desktop\NVIDIA\deadlock-lab\backend\app\experiment.py', 'r') as f:
    content = f.read()

# Fix 1: Modify the goal completion section
old1 = """        # Check for goal completion: if agent position equals goal position
        for agent in new_state.agents:
            goal = next((a for a in state.agents if a.id == agent.id), None)
            if goal is not None:
                # Simple distance check - if agent is at its goal position
                if (agent.position.x == goal.position.x and
                    agent.position.y == goal.position.y):
                    # Agent has reached its goal
                    if agent.status != "completed":
                        completed_agents += 1
                        agent.status = "completed"

        state = new_state"""

new1 = """        # Check for goal completion: if agent position equals goal position
        all_agents_completed = True
        for agent in new_state.agents:
            goal = next((a for a in state.agents if a.id == agent.id), None)
            if goal is not None:
                # Simple distance check - if agent is at its goal position
                if (agent.position.x == goal.position.x and
                    agent.position.y == goal.position.y):
                    # Agent has reached its goal
                    if agent.status != "completed":
                        completed_agents += 1
                        agent.status = "completed"
                else:
                    all_agents_completed = False

        # If all agents are completed, finish the simulation
        if all_agents_completed and completed_agents == len(state.agents) - 1:
            engine.state.is_finished = True

        state = new_state"""

content = content.replace(old1, new1)
print('Fixed goal completion section')

# Fix 2: Fix the final_completed calculation and termination reason
old2 = """    # Count agents that are completed or idle at the end
    final_completed = sum(
        1 for a in state.agents if a.status in ("completed", "idle")
    )

    # Count waiting/blocked at end
    final_waiting = sum(1 for a in state.agents if a.status == "waiting")
    final_blocked = sum(1 for a in state.agents if a.status in ("waiting", "blocked"))

    # Determine termination reason
    if engine.state.is_finished:
        termination_reason = "max_steps reached"
    elif engine.state.current_step >= max_steps:
        termination_reason = "max_steps reached"
    else:
        termination_reason = "finished early""""

new2 = """    # Count agents that are completed at the end (only those with status "completed")
    final_completed = sum(1 for a in state.agents if a.status == "completed")

    # Count waiting/blocked at end
    final_waiting = sum(1 for a in state.agents if a.status == "waiting")
    final_blocked = sum(1 for a in state.agents if a.status in ("waiting", "blocked"))

    # Determine termination reason
    if engine.state.is_finished:
        termination_reason = "all_agents_completed"
    elif engine.state.current_step >= max_steps:
        termination_reason = "max_steps_reached"
    else:
        termination_reason = "finished early""""

content = content.replace(old2, new2)
print('Fixed final metrics and termination reason')

# Fix 3: Fix the finished field in the result result
old3 = '"finished": engine.state.is_finished,'
new3 = '"finished": engine.state.is_finished and completed_agents >= len(state.agents) - 1,'
content = content.replace(old3, new3)
print('Fixed finished field')

with open(r'C:\Users\kumar\OneDrive\Desktop\NVIDIA\deadlock-lab\backend\app\experiment.py', 'w') as f:
    f.write(content)
print('All fixes applied')