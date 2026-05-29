"""
Tests for cxas_claw v0.2.0
Entry point: cxclaw
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cxas_claw import __version__
from cxas_claw.cli import main
from cxas_claw.profile import Profile, PROFILES_DIR, ACTIVE_FILE
from cxas_claw.renderer import render
from cxas_claw.scratchpad import ScratchpadSession


# ================================================================== #
#  Version
# ================================================================== #

def test_version():
    assert __version__ == "0.2.0"


# ================================================================== #
#  CLI entrypoint
# ================================================================== #

def test_main_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "cxclaw" in result.output.lower() or "CX Agent Studio" in result.output


def test_banner_cmd():
    runner = CliRunner()
    result = runner.invoke(main, ["banner"])
    assert result.exit_code == 0


def test_version_flag():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.2.0" in result.output


# ================================================================== #
#  Profile management
# ================================================================== #

class TestProfile:
    def test_save_load_delete(self, tmp_path, monkeypatch):
        monkeypatch.setattr("cxas_claw.profile.PROFILES_DIR", tmp_path / "profiles")
        monkeypatch.setattr("cxas_claw.profile.ACTIVE_FILE", tmp_path / "active_profile")
        from cxas_claw import profile as pm
        pm.PROFILES_DIR = tmp_path / "profiles"
        pm.ACTIVE_FILE = tmp_path / "active_profile"

        p = Profile(name="test", project_id="my-proj", location="us-central1")
        p.save()
        loaded = Profile.load("test")
        assert loaded.project_id == "my-proj"
        loaded.delete()
        with pytest.raises(FileNotFoundError):
            Profile.load("test")

    def test_list_profiles(self, tmp_path, monkeypatch):
        import cxas_claw.profile as pm
        pm.PROFILES_DIR = tmp_path / "profiles"
        pm.ACTIVE_FILE = tmp_path / "active_profile"
        pm.PROFILES_DIR.mkdir(parents=True)
        (pm.PROFILES_DIR / "a.json").write_text(
            json.dumps({"name": "a", "project_id": "p", "location": "l",
                        "credentials_file": None, "oauth_token": None,
                        "default_app": None, "extra": {}})
        )
        assert "a" in Profile.list_profiles()

    def test_set_active(self, tmp_path, monkeypatch):
        import cxas_claw.profile as pm
        pm.PROFILES_DIR = tmp_path / "profiles"
        pm.ACTIVE_FILE = tmp_path / "active_profile"
        pm.PROFILES_DIR.mkdir(parents=True)
        p = Profile(name="dev", project_id="p", location="l")
        p.save()
        Profile.set_active("dev")
        assert pm.ACTIVE_FILE.read_text() == "dev"


# ================================================================== #
#  CXASClient
# ================================================================== #

class TestCXASClient:
    def test_init_from_kwargs(self):
        from cxas_claw.client import CXASClient
        c = CXASClient(project_id="test-project", location="us-central1")
        assert c.project_id == "test-project"
        assert c.location == "us-central1"

    def test_parent(self):
        from cxas_claw.client import CXASClient
        c = CXASClient(project_id="my-proj", location="global")
        assert c.parent() == "projects/my-proj/locations/global"

    def test_resolve_app_passthrough(self):
        from cxas_claw.client import CXASClient
        c = CXASClient(project_id="my-proj", location="global")
        full = "projects/my-proj/locations/global/apps/abc123"
        assert c.resolve_app(full) == full


# ================================================================== #
#  Renderer
# ================================================================== #

class TestRenderer:
    def test_render_table(self, capsys):
        data = [{"name": "agent-1", "status": "active"}]
        render(data, output="table")

    def test_render_json(self, capsys):
        data = [{"name": "agent-1"}]
        render(data, output="json")

    def test_render_csv(self):
        data = [{"a": "1", "b": "2"}]
        render(data, output="csv")

    def test_render_empty(self):
        render([], output="table")


# ================================================================== #
#  Scratchpad
# ================================================================== #

class TestScratchpad:
    def test_reset_changes_session_id(self):
        s = ScratchpadSession("app", "proj", "us")
        old = s.session_id
        s.reset()
        assert s.session_id != old

    def test_history_tracking(self):
        s = ScratchpadSession("app", "proj", "us")
        # Patch _get_sessions to mock the response
        mock_sessions = MagicMock()
        mock_response = MagicMock()
        mock_response.query_result.response_messages = []
        mock_sessions.detect_intent.return_value = mock_response
        s._sessions = mock_sessions
        s.send("hello")
        assert len(s.history) == 1
        assert s.history[0]["user"] == "hello"


# ================================================================== #
#  CLI delegation stubs (no real GCP calls)
# ================================================================== #

@patch("cxas_claw.cli._run_cxas", return_value=0)
def test_lint_command(mock_run):
    runner = CliRunner()
    result = runner.invoke(main, ["lint", "--app-dir", "."])
    assert result.exit_code == 0
    mock_run.assert_called_once()
    args = mock_run.call_args[0]
    assert "lint" in args


@patch("cxas_claw.cli._run_cxas", return_value=0)
def test_pull_command(mock_run):
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["pull", "projects/p/locations/l/apps/a", "--target-dir", "/tmp/agent"],
    )
    assert result.exit_code == 0
    args = mock_run.call_args[0]
    assert "pull" in args


@patch("cxas_claw.cli._run_cxas", return_value=0)
def test_run_command(mock_run):
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["run", "--app-name", "projects/p/locations/l/apps/a",
         "--evaluation-id", "projects/p/locations/l/apps/a/evaluations/e1",
         "--wait"],
    )
    assert result.exit_code == 0
    args = mock_run.call_args[0]
    assert "run" in args
    assert "--wait" in args
