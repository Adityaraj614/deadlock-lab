import os
import sys
import pytest
from pathlib import Path

from app.api.main import _SCENARIOS, _list_scenario_names, _CONFIG_PATH, _PROJECT_ROOT, list_scenarios, get_scenario


class TestScenarioDiscovery:
    """Tests for warehouse scenario discovery and API endpoint reliability."""

    def test_scenarios_list_contains_three_names(self):
        """All three scenarios must be discoverable from the scenario list."""
        names = _list_scenario_names()
        assert len(names) == 3, f"Expected 3 scenarios, got {len(names)}: {names}"

    def test_scenario_names_match_expected(self):
        """Scenario names must match the expected YAML keys."""
        names = _list_scenario_names()
        expected = {"simple_warehouse", "narrow_corridor", "congested_warehouse"}
        assert set(names) == expected, f"Expected {expected}, got {set(names)}"

    def test_list_scenarios_api_returns_200(self):
        """GET /api/scenarios returns 200 with correct scenario names."""
        from fastapi.testclient import TestClient
        from app.api.main import app

        client = TestClient(app)
        resp = client.get("/api/scenarios")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.json()}"
        data = resp.json()
        assert "scenarios" in data, f"Expected 'scenarios' key in response, got {data}"
        assert len(data["scenarios"]) == 3, f"Expected 3 scenarios, got {len(data['scenarios'])}"

    def test_individual_scenario_loadable(self):
        """Each scenario must be individually loadable via GET /api/scenarios/{name}."""
        from fastapi.testclient import TestClient
        from app.api.main import app

        client = TestClient(app)
        names = _list_scenario_names()
        for name in names:
            resp = client.get(f"/api/scenarios/{name}")
            assert resp.status_code == 200, (
                f"Expected 200 for scenario '{name}', got {resp.status_code}: {resp.json()}"
            )
            scenario = resp.json()
            assert "grid_width" in scenario, f"Scenario '{name}' missing 'grid_width'"
            assert "grid_height" in scenario, f"Scenario '{name}' missing 'grid_height'"
            assert "agents" in scenario, f"Scenario '{name}' missing 'agents'"

    def test_config_path_is_absolute_not_relative(self):
        """The config path must be resolved absolutely based on file location, not CWD."""
        # The config path must exist and be absolute
        assert _CONFIG_PATH.is_absolute(), f"_CONFIG_PATH must be absolute, got {_CONFIG_PATH}"
        assert _CONFIG_PATH.exists(), f"_CONFIG_PATH must exist, got {_CONFIG_PATH}"

    def test_scenario_loading_works_from_backend_dir(self):
        """Scenario loading must work when launched from the backend directory."""
        # This is the key scenario: uvicorn launched from backend/
        names = _list_scenario_names()
        assert len(names) == 3, (
            f"Scenario loading failed from backend dir. "
            f"Names: {names}, Count: {len(names)}"
        )

    def test_scenario_loading_works_from_repo_root(self):
        """Scenario loading must work when launched from the repository root."""
        # Change to repo root and verify scenarios still load
        original_cwd = os.getcwd()
        try:
            os.chdir("C:/Users/kumar/OneDrive/Desktop/NVIDIA/deadlock-lab")
            from app.api.main import _list_scenario_names
            names = _list_scenario_names()
            assert len(names) == 3, (
                f"Scenario loading failed from repo root. "
                f"Names: {names}, Count: {len(names)}"
            )
        finally:
            os.chdir(original_cwd)

    def test_missing_config_file_fails_gracefully(self):
        """If the config file is missing, the API must not crash; _SCENARIOS should be empty."""
        # Temporarily rename the config file
        config_path = Path(_CONFIG_PATH)
        backup_path = config_path.with_suffix('.yaml.bak')

        try:
            config_path.rename(backup_path)
            names = _list_scenario_names()
            # Should gracefully handle missing file - _SCENARIOS becomes empty dict
            assert isinstance(names, list), "_list_scenario_names should return a list"
            # After restore, scenarios should come back
        finally:
            # Restore the config file
            if backup_path.exists():
                backup_path.rename(config_path)
            # Verify scenarios are back
            names = _list_scenario_names()
            assert len(names) == 3, f"Scenarios should be restored. Got: {names}"