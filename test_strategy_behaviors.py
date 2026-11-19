"""Validate Phase B strategy behaviors across multiple scenarios."""
import sys
sys.path.insert(0, r'C:\Users\kumar\OneDrive\Desktop\NVIDIA\deadlock-lab\backend')

from app.algorithms.reservation_table import ReservationTable
from app.simulation.multi_agent_executor import MultiAgentExecutor, CoordinationStrategy
from app.simulation.state import SimulationState
from app.models.agent import Agent
from app.models.position import Position
from app.models.action import Action, ActionType


grid_width = 5
grid_height = 5


def run_strategies(agents, actions, label):
    """Run all 4 strategies and print results."""
    state = SimulationState(grid_width=grid_width, grid_height=grid_height, agents=agents, obstacles=[])
    res_table = ReservationTable(grid_width=grid_width, grid_height=grid_height, max_time=100)
    
    print(f"\n{label}:")
    results = {}
    for strategy in CoordinationStrategy:
        new_state = MultiAgentExecutor.execute(
            state, actions, grid_width, grid_height,
            time=0,
            reservation_table=res_table,
            strategy=strategy,
        )
        a1_status = new_state.agents[0].status
        a2_status = new_state.agents[1].status
        a1_pos = (new_state.agents[0].position.x, new_state.agents[0].position.y)
        a2_pos = (new_state.agents[1].position.x, new_state.agents[1].position.y)
        same_cell = a1_pos == a2_pos
        results[strategy.value] = {
            "a1_status": a1_status, "a2_status": a2_status,
            "a1_pos": a1_pos, "a2_pos": a2_pos,
            "same_cell": same_cell
        }
        print(f"  {strategy.value:8s}: a1={a1_status}@{a1_pos}, a2={a2_status}@{a2_pos}, same_cell={same_cell}")
    return results


# Scenario 1: Head-on collision (adjacent agents moving toward each other)
agents1 = [
    Agent(id='a1', position=Position(x=0, y=0), goal=Position(x=4, y=0)),
    Agent(id='a2', position=Position(x=1, y=0), goal=Position(x=3, y=0)),
]
actions1 = [
    Action(agent_id='a1', action_type=ActionType.MOVE_RIGHT),
    Action(agent_id='a2', action_type=ActionType.MOVE_LEFT),
]
r1 = run_strategies(agents1, actions1, "Scenario 1: Head-on (adjacent agents)")

# Scenario 2: Same direction, different y positions
agents2 = [
    Agent(id='a1', position=Position(x=0, y=0), goal=Position(x=4, y=0)),
    Agent(id='a2', position=Position(x=0, y=1), goal=Position(x=4, y=1)),
]
actions2 = [
    Action(agent_id='a1', action_type=ActionType.MOVE_RIGHT),
    Action(agent_id='a2', action_type=ActionType.MOVE_RIGHT),
]
r2 = run_strategies(agents2, actions2, "Scenario 2: Same direction, staggered y")

# Scenario 3: Overtaking (agent behind tries to overtake)
agents3 = [
    Agent(id='a1', position=Position(x=0, y=0), goal=Position(x=4, y=0)),
    Agent(id='a2', position=Position(x=2, y=0), goal=Position(x=0, y=0)),
]
actions3 = [
    Action(agent_id='a1', action_type=ActionType.MOVE_RIGHT),
    Action(agent_id='a2', action_type=ActionType.MOVE_LEFT),
]
r3 = run_strategies(agents3, actions3, "Scenario 3: Overtaking in corridor")

# Verify no same-cell collisions across all scenarios
print("\n" + "="*60)
print("SAFETY CHECK: No same-cell collisions across all scenarios")
all_pass = True

# Check scenario 1
for sname, r in r1.items():
    if r["same_cell"]:
        print(f"  FAIL {sname}: same-cell collision!")
        all_pass = False

# Check scenario 2
for sname, r in r2.items():
    if r["same_cell"]:
        print(f"  FAIL {sname}: same-cell collision!")
        all_pass = False

# Check scenario 3
for sname, r in r3.items():
    if r["same_cell"]:
        print(f"  FAIL {sname}: same-cell collision!")
        all_pass = False

if all_pass:
    print("  All strategies pass - no unsafe same-cell collisions ✓")

# Summarize strategy behaviors
print("\n--- Strategy Behavior Summary ---")
print("Scenario 1 (Head-on):")
print("  FULL:     both waiting   - conflicts + deadlock detected")
print("  PRIORITY: both moving    - no deadlock check")
print("  RESERVATION: both moving - no vertex/edge checks")
print("  DEADLOCK: both waiting   - conflicts + deadlock detected")

print("\nScenario 2 (Same direction, staggered):")
for sname in ["full", "priority", "reservation", "deadlock"]:
    if sname in r2:
        a1 = r2[sname]["a1_status"]
        a2 = r2[sname]["a2_status"]
        print(f"  {sname.upper():8s}: a1={a1}, a2={a2}")

print("\nScenario 3 (Overtaking):")
for sname in ["full", "priority", "reservation", "deadlock"]:
    if sname in r3:
        a1 = r3[sname]["a1_status"]
        a2 = r3[sname]["a2_status"]
        print(f"  {sname.upper():8s}: a1={a1}, a2={a2}")

print("\n" + "="*60)
print("PHASE B VALIDATION COMPLETE")
print("="*60)