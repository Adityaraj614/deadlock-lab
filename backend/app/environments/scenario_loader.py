from __future__ import annotations
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.models.agent import Agent
from app.models.goal import Goal
from app.models.obstacle import Obstacle
from app.models.position import Position
from app.environments.warehouse_grid import WarehouseGridEnvironment


def load_yaml_config(filepath: str) -> dict:
    """Load a YAML configuration file and return the parsed dictionary."""
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_scenario(name: str, base_dir: str | None = None) -> WarehouseGridEnvironment:
    """Load a warehouse scenario by name and return a WarehouseGridEnvironment.

    The scenario name corresponds to a key in a YAML configuration file
    located at ``<base_dir>/configs/warehouse_scenarios.yaml`` (or the
    default path).
    """

    project_root = Path(base_dir) if base_dir else Path(__file__).resolve().parents[3]
    config_path = project_root / "configs" / "warehouse_scenarios.yaml"
    config = load_yaml_config(config_path)

    scenario: Optional[dict[str, Any]] = config.get(name) if config else None
    if scenario is None:
        available = list(config.keys()) if config else []
        raise ValueError(
            f"Scenario '{name}' not found. Available: {available}"
        )

    grid_width = scenario["grid_width"]
    grid_height = scenario["grid_height"]

    environment = WarehouseGridEnvironment(grid_width=grid_width, grid_height=grid_height)

    # Add obstacles.
    for obs in scenario.get("obstacles", []):
        position = Position(x=obs["position"]["x"], y=obs["position"]["y"])
        obstacle = Obstacle(id=obs["id"], position=position, is_dynamic=obs.get("is_dynamic", False))
        environment.add_obstacle(obstacle)

    # Add agents with goals.
    for agent_data in scenario.get("agents", []):
        position = Position(x=agent_data["position"]["x"], y=agent_data["position"]["y"])
        goal_position = Position(x=agent_data["goal"]["x"], y=agent_data["goal"]["y"])
        goal = Goal(
            id=f"goal_{agent_data['id']}",
            position=goal_position,
            assigned_agent_id=agent_data["id"],
        )
        agent = Agent(
            id=agent_data["id"],
            position=position,
            goal=goal_position,
            priority=agent_data.get("priority", 1),
            speed=agent_data.get("speed", 1.0),
        )
        environment.place_agent(agent)
        environment.place_goal(goal)

    return environment
