"""
cxclaw — CX Agent Studio CLI Agent & Workspace
Entry-point: cxclaw

All cxas-scrapi CLI commands are available as subcommands here.
Extra cxclaw commands: profile, chat, repl, scratchpad, mcp.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from cxas_claw import __version__
from cxas_claw.renderer import (
    console,
    error,
    info,
    print_banner,
    render,
    success,
    warn,
)

# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _load_profile(ctx: click.Context) -> Optional["Profile"]:  # noqa: F821
    from cxas_claw.profile import Profile
    name = ctx.obj.get("profile") if ctx.obj else None
    if name:
        return Profile.load(name)
    return Profile.get_active()


def _client(ctx: click.Context, project_id=None, location=None):
    from cxas_claw.client import CXASClient
    from cxas_claw.profile import Profile
    profile = _load_profile(ctx)
    return CXASClient(
        profile=profile,
        project_id=project_id,
        location=location,
    )


def _run_cxas(*args, **kwargs) -> int:
    """
    Delegate to the real `cxas` CLI subprocess.
    Returns the exit code.
    Extra env vars (CXAS_OAUTH_TOKEN, GOOGLE_APPLICATION_CREDENTIALS) are
    inherited from the current process.
    """
    cmd = ["cxas", *[str(a) for a in args if a is not None]]
    # strip None values coming from optional params
    cmd = [c for c in cmd if c != "None"]
    result = subprocess.run(cmd, env=os.environ.copy())
    return result.returncode


def _exit_on_fail(code: int) -> None:
    if code != 0:
        sys.exit(code)


# ------------------------------------------------------------------ #
# Root group
# ------------------------------------------------------------------ #

@click.group(
    context_settings={"help_option_names": ["-h", "--help"], "max_content_width": 120},
    invoke_without_command=True,
)
@click.version_option(__version__, "-V", "--version", prog_name="cxclaw")
@click.option(
    "--profile",
    "-p",
    default=None,
    help="Named cxclaw profile to use (overrides active profile).",
    envvar="CXCLAW_PROFILE",
)
@click.option(
    "--oauth-token",
    default=None,
    help="OAuth bearer token. Sets CXAS_OAUTH_TOKEN for this invocation.",
    envvar="CXAS_OAUTH_TOKEN",
)
@click.pass_context
def main(ctx: click.Context, profile: Optional[str], oauth_token: Optional[str]) -> None:
    """
    cxclaw — CX Agent Studio CLI Agent & Workspace

    \b
    Combines the full cxas CLI (pull, push, lint, ci-test, …) with
    interactive chat, REPL, profile management, and MCP support.

    \b
    Quickstart:
      cxclaw profile create dev --project-id my-proj --location us-central1
      cxclaw apps list
      cxclaw pull "My Support Agent" --target-dir ./agent
      cxclaw lint --app-dir ./agent
    """
    ctx.ensure_object(dict)
    ctx.obj["profile"] = profile
    if oauth_token:
        os.environ["CXAS_OAUTH_TOKEN"] = oauth_token

    # When user runs `cxclaw` with no subcommand — show banner + help
    if ctx.invoked_subcommand is None:
        print_banner(__version__)
        console.print(ctx.get_help())


# ------------------------------------------------------------------ #
# banner
# ------------------------------------------------------------------ #

@main.command()
def banner() -> None:
    """Print the cxclaw banner."""
    print_banner(__version__)


# ================================================================== #
#  PROFILE management (cxclaw-native, not delegated to cxas)
# ================================================================== #

@main.group("profile")
def profile_group() -> None:
    """Manage named GCP credential profiles."""


@profile_group.command("create")
@click.argument("name")
@click.option("--project-id", required=True, help="GCP project ID.")
@click.option("--location", default="global", show_default=True, help="GCP location.")
@click.option("--credentials-file", default=None, help="Path to service account JSON key.")
@click.option("--oauth-token", default=None, help="OAuth bearer token.")
@click.option("--default-app", default=None, help="Default app resource name.")
@click.option("--activate", is_flag=True, default=False, help="Set as active profile immediately.")
def profile_create(name, project_id, location, credentials_file, oauth_token, default_app, activate):
    """Create a new named profile."""
    from cxas_claw.profile import Profile
    p = Profile(
        name=name,
        project_id=project_id,
        location=location,
        credentials_file=credentials_file,
        oauth_token=oauth_token,
        default_app=default_app,
    )
    p.save()
    success(f"Profile '{name}' created.")
    if activate:
        Profile.set_active(name)
        success(f"Profile '{name}' is now active.")


@profile_group.command("list")
def profile_list():
    """List all profiles."""
    from cxas_claw.profile import Profile, ACTIVE_FILE
    profiles = Profile.list_profiles()
    if not profiles:
        info("No profiles found. Run: cxclaw profile create <name>")
        return
    active = ACTIVE_FILE.read_text().strip() if ACTIVE_FILE.exists() else None
    rows = [{"name": p, "active": "✔" if p == active else ""} for p in profiles]
    render(rows, title="Profiles")


@profile_group.command("show")
@click.argument("name")
def profile_show(name):
    """Show details of a profile."""
    from cxas_claw.profile import Profile
    p = Profile.load(name)
    render(
        [
            {"field": k, "value": v}
            for k, v in vars(p).items()
            if k != "extra"
        ],
        title=f"Profile: {name}",
    )


@profile_group.command("activate")
@click.argument("name")
def profile_activate(name):
    """Set a profile as the active default."""
    from cxas_claw.profile import Profile
    Profile.set_active(name)
    success(f"Profile '{name}' is now active.")


@profile_group.command("delete")
@click.argument("name")
@click.confirmation_option(prompt="Delete profile? This cannot be undone.")
def profile_delete(name):
    """Delete a named profile."""
    from cxas_claw.profile import Profile
    Profile.load(name).delete()
    success(f"Profile '{name}' deleted.")


# ================================================================== #
#  apps — list / get
# ================================================================== #

@main.group("apps")
def apps_group() -> None:
    """List and inspect CXAS apps. (delegates to cxas apps)"""


@apps_group.command("list")
@click.option("--project-id", default=None, help="GCP project ID.")
@click.option("--location", default=None, help="GCP location.")
@click.option("--output", "-o", default="table", type=click.Choice(["table", "json", "csv"]))
@click.pass_context
def apps_list(ctx, project_id, location, output):
    """List all apps in the project."""
    profile = _load_profile(ctx)
    pid = project_id or (profile.project_id if profile else None)
    loc = location or (profile.location if profile else None)
    if not pid or not loc:
        error("--project-id and --location are required (or set an active profile).")
        sys.exit(1)
    _exit_on_fail(_run_cxas("apps", "list", "--project-id", pid, "--location", loc))


@apps_group.command("get")
@click.argument("app")
@click.option("--project-id", default=None)
@click.option("--location", default=None)
@click.pass_context
def apps_get(ctx, app, project_id, location):
    """Get details of a specific app."""
    profile = _load_profile(ctx)
    pid = project_id or (profile.project_id if profile else None)
    loc = location or (profile.location if profile else None)
    args = ["apps", "get", app]
    if pid:
        args += ["--project-id", pid]
    if loc:
        args += ["--location", loc]
    _exit_on_fail(_run_cxas(*args))


# ================================================================== #
#  pull
# ================================================================== #

@main.command("pull")
@click.argument("app")
@click.option("--target-dir", default=".", show_default=True, help="Local dir to extract into.")
@click.option("--project-id", default=None)
@click.option("--location", default=None)
@click.pass_context
def pull(ctx, app, target_dir, project_id, location):
    """
    Export a CXAS app to a local directory.

    APP  Full resource name or display name of the app.
    """
    profile = _load_profile(ctx)
    pid = project_id or (profile.project_id if profile else None)
    loc = location or (profile.location if profile else None)
    args = ["pull", app, "--target-dir", target_dir]
    if pid:
        args += ["--project-id", pid]
    if loc:
        args += ["--location", loc]
    _exit_on_fail(_run_cxas(*args))


# ================================================================== #
#  push
# ================================================================== #

@main.command("push")
@click.option("--app-dir", default=".", show_default=True, help="Local agent directory.")
@click.option("--to", default=None, help="Target app (resource name or display name).")
@click.option("--env-file", default=None, help="Path to environment.json override.")
@click.option("--app-name", default=None, help="Explicit app resource name (v1beta).")
@click.option("--display-name", default=None, help="Display name for a new app.")
@click.option("--project-id", required=True, help="GCP project ID.")
@click.option("--location", required=True, help="GCP location.")
@click.pass_context
def push(ctx, app_dir, to, env_file, app_name, display_name, project_id, location):
    """Upload a local agent directory to CXAS."""
    args = ["push", "--app-dir", app_dir, "--project-id", project_id, "--location", location]
    if to:
        args += ["--to", to]
    if env_file:
        args += ["--env-file", env_file]
    if app_name:
        args += ["--app-name", app_name]
    if display_name:
        args += ["--display-name", display_name]
    _exit_on_fail(_run_cxas(*args))


# ================================================================== #
#  create
# ================================================================== #

@main.command("create")
@click.argument("name")
@click.option("--description", default=None, help="Short description of the app.")
@click.option("--app-name", default=None, help="Optional custom resource ID.")
@click.option("--project-id", required=True, help="GCP project ID.")
@click.option("--location", required=True, help="GCP location.")
def create(name, description, app_name, project_id, location):
    """Create a new empty CXAS app.

    NAME  Display name for the new app.
    """
    args = ["create", name, "--project-id", project_id, "--location", location]
    if description:
        args += ["--description", description]
    if app_name:
        args += ["--app-name", app_name]
    _exit_on_fail(_run_cxas(*args))


# ================================================================== #
#  delete
# ================================================================== #

@main.command("delete")
@click.option("--app-name", default=None, help="Full resource name of the app.")
@click.option("--display-name", default=None, help="Display name of the app.")
@click.option("--project-id", default=None)
@click.option("--location", default=None)
@click.option("--force", is_flag=True, default=False, help="Force delete even if resources exist.")
@click.pass_context
def delete(ctx, app_name, display_name, project_id, location, force):
    """Permanently delete a CXAS app. WARNING: irreversible."""
    if not app_name and not display_name:
        error("Provide --app-name or --display-name.")
        sys.exit(1)
    args = ["delete"]
    if app_name:
        args += ["--app-name", app_name]
    if display_name:
        args += ["--display-name", display_name]
    if project_id:
        args += ["--project-id", project_id]
    if location:
        args += ["--location", location]
    if force:
        args.append("--force")
    _exit_on_fail(_run_cxas(*args))


# ================================================================== #
#  branch
# ================================================================== #

@main.command("branch")
@click.argument("source")
@click.option("--new-name", required=True, help="Display name for the new (branched) app.")
@click.option("--project-id", required=True)
@click.option("--location", required=True)
def branch(source, new_name, project_id, location):
    """Clone a CXAS app into a new one (pull → create → push in cloud).

    SOURCE  Full resource name or display name of the app to clone.
    """
    _exit_on_fail(_run_cxas(
        "branch", source,
        "--new-name", new_name,
        "--project-id", project_id,
        "--location", location,
    ))


# ================================================================== #
#  export
# ================================================================== #

@main.command("export")
@click.option("--app-name", required=True, help="Full resource name of the app.")
@click.option("--evaluation-id", required=True, help="Full resource name of the evaluation.")
@click.option("--format", "fmt", default="yaml", type=click.Choice(["yaml", "json"]))
@click.option("--output", default=None, help="Output file path (stdout if omitted).")
def export(app_name, evaluation_id, fmt, output):
    """Export an evaluation definition to a YAML or JSON file."""
    args = ["export", "--app-name", app_name, "--evaluation-id", evaluation_id, "--format", fmt]
    if output:
        args += ["--output", output]
    _exit_on_fail(_run_cxas(*args))


# ================================================================== #
#  push-eval
# ================================================================== #

@main.command("push-eval")
@click.option("--app-name", required=True, help="Full resource name of the target app.")
@click.option("--file", "file_path", required=True, help="YAML file with evaluation definitions.")
def push_eval(app_name, file_path):
    """Upload evaluation definitions from a YAML file to a CXAS app."""
    _exit_on_fail(_run_cxas("push-eval", "--app-name", app_name, "--file", file_path))


# ================================================================== #
#  run (evaluations)
# ================================================================== #

@main.command("run")
@click.option("--app-name", required=True, help="Full resource name of the app.")
@click.option("--evaluation-id", default=None, help="Full resource name of a specific evaluation.")
@click.option("--display-name-prefix", default=None, help="Run evals whose names start with this.")
@click.option("--tags", multiple=True, help="Tags to filter evaluations (repeatable).")
@click.option("--wait", is_flag=True, default=False, help="Block until evaluations complete.")
@click.option("--filter-auto-metrics", is_flag=True, default=False, help="Ignore LLM auto-metrics.")
@click.option("--modality", default="text", type=click.Choice(["text", "audio"]))
def run(app_name, evaluation_id, display_name_prefix, tags, wait, filter_auto_metrics, modality):
    """Trigger evaluations and optionally wait for results."""
    args = ["run", "--app-name", app_name]
    if evaluation_id:
        args += ["--evaluation-id", evaluation_id]
    if display_name_prefix:
        args += ["--display-name-prefix", display_name_prefix]
    for tag in tags:
        args += ["--tags", tag]
    if wait:
        args.append("--wait")
    if filter_auto_metrics:
        args.append("--filter-auto-metrics")
    args += ["--modality", modality]
    _exit_on_fail(_run_cxas(*args))


# ================================================================== #
#  test-tools
# ================================================================== #

@main.command("test-tools")
@click.option("--app-name", required=True, help="Full resource name of the deployed app.")
@click.option("--test-file", required=True, help="YAML/JSON tool test file.")
@click.option("--debug", is_flag=True, default=False, help="Enable verbose debug logging.")
def test_tools(app_name, test_file, debug):
    """Run unit tests against your agent's tools."""
    args = ["test-tools", "--app-name", app_name, "--test-file", test_file]
    if debug:
        args.append("--debug")
    _exit_on_fail(_run_cxas(*args))


# ================================================================== #
#  test-callbacks
# ================================================================== #

@main.command("test-callbacks")
@click.option("--app-dir", required=True, help="Path to the app directory.")
@click.option("--agent-name", default=None, help="Narrow to a specific agent.")
@click.option("--callback-type", default=None, help="Only run callbacks of this type.")
@click.option("--callback-name", default=None, help="Run a single callback by name.")
@click.option("--log-file", default=None, help="File to write pytest output to.")
@click.option("--pytest-args", default=None, help="Comma-separated extra args for pytest.")
def test_callbacks(app_dir, agent_name, callback_type, callback_name, log_file, pytest_args):
    """Run pytest-based callback unit tests for an app directory."""
    args = ["test-callbacks", "--app-dir", app_dir]
    if agent_name:
        args += ["--agent-name", agent_name]
    if callback_type:
        args += ["--callback-type", callback_type]
    if callback_name:
        args += ["--callback-name", callback_name]
    if log_file:
        args += ["--log-file", log_file]
    if pytest_args:
        args += ["--pytest-args", pytest_args]
    _exit_on_fail(_run_cxas(*args))


# ================================================================== #
#  test-single-callback
# ================================================================== #

@main.command("test-single-callback")
@click.option("--app-name", required=True, help="Full resource name of the app.")
@click.option("--agent-name", required=True, help="Name of the agent.")
@click.option("--callback-type", required=True, help="Type of callback (before_call, etc.).")
@click.option("--test-file-path", required=True, help="Path to the pytest test file.")
@click.option("--log-file", default=None, help="File to write pytest output to.")
@click.option("--pytest-args", default=None, help="Comma-separated extra args for pytest.")
def test_single_callback(app_name, agent_name, callback_type, test_file_path, log_file, pytest_args):
    """Run tests for a single, specific callback."""
    args = [
        "test-single-callback",
        "--app-name", app_name,
        "--agent-name", agent_name,
        "--callback-type", callback_type,
        "--test-file-path", test_file_path,
    ]
    if log_file:
        args += ["--log-file", log_file]
    if pytest_args:
        args += ["--pytest-args", pytest_args]
    _exit_on_fail(_run_cxas(*args))


# ================================================================== #
#  ci-test
# ================================================================== #

@main.command("ci-test")
@click.option("--app-dir", default=".", show_default=True, help="Agent directory.")
@click.option("--project-id", required=True, help="GCP project ID.")
@click.option("--location", required=True, help="GCP location.")
@click.option("--display-name", default=None, help="Display name for the temp CI app.")
@click.option("--env-file", default=None, help="Path to environment.json override.")
def ci_test(app_dir, project_id, location, display_name, env_file):
    """Run the full CI test lifecycle (push → tool tests → evaluations)."""
    args = [
        "ci-test",
        "--app-dir", app_dir,
        "--project-id", project_id,
        "--location", location,
    ]
    if display_name:
        args += ["--display-name", display_name]
    if env_file:
        args += ["--env-file", env_file]
    _exit_on_fail(_run_cxas(*args))


# ================================================================== #
#  local-test
# ================================================================== #

@main.command("local-test")
@click.option("--app-dir", default=".", show_default=True, help="Agent directory (needs Dockerfile).")
@click.option("--project-id", required=True, help="GCP project ID.")
@click.option("--location", required=True, help="GCP location.")
@click.option("--env-file", default=None, help="Path to environment.json override.")
def local_test(app_dir, project_id, location, env_file):
    """Run the CI lifecycle inside a local Docker container."""
    args = [
        "local-test",
        "--app-dir", app_dir,
        "--project-id", project_id,
        "--location", location,
    ]
    if env_file:
        args += ["--env-file", env_file]
    _exit_on_fail(_run_cxas(*args))


# ================================================================== #
#  init-github-action
# ================================================================== #

@main.command("init-github-action")
@click.option("--app-dir", default=None, help="Path to the agent directory.")
@click.option("--app-name", default=None, help="Full resource name of the CXAS app.")
@click.option("--workload-identity-provider", default=None, help="GCP WIF provider resource name.")
@click.option("--service-account", default=None, help="GCP service account email for WIF.")
@click.option("--branch", default="main", show_default=True, help="Branch that triggers deploy.")
@click.option("--no-cleanup", is_flag=True, default=False, help="Skip cleanup workflow generation.")
@click.option("--install-hook", is_flag=True, default=False, help="Install git pre-push hook.")
@click.option("--auto-create-wif", is_flag=True, default=False, help="Auto-create WIF resources.")
@click.option("--wif-pool-name", default=None, help="WIF pool name.")
@click.option("--github-repo", default=None, help="OWNER/REPO override for WIF binding.")
@click.option("--output", default=None, help="Override output path for generated workflow.")
@click.option("--project-id", default=None)
@click.option("--location", default=None)
def init_github_action(
    app_dir, app_name, workload_identity_provider, service_account, branch,
    no_cleanup, install_hook, auto_create_wif, wif_pool_name, github_repo,
    output, project_id, location,
):
    """Generate a GitHub Actions workflow file for your agent."""
    args = ["init-github-action"]
    if app_dir:
        args += ["--app-dir", app_dir]
    if app_name:
        args += ["--app-name", app_name]
    if workload_identity_provider:
        args += ["--workload-identity-provider", workload_identity_provider]
    if service_account:
        args += ["--service-account", service_account]
    args += ["--branch", branch]
    if no_cleanup:
        args.append("--no-cleanup")
    if install_hook:
        args.append("--install-hook")
    if auto_create_wif:
        args.append("--auto-create-wif")
    if wif_pool_name:
        args += ["--wif-pool-name", wif_pool_name]
    if github_repo:
        args += ["--github-repo", github_repo]
    if output:
        args += ["--output", output]
    if project_id:
        args += ["--project-id", project_id]
    if location:
        args += ["--location", location]
    _exit_on_fail(_run_cxas(*args))


# ================================================================== #
#  lint
# ================================================================== #

@main.command("lint")
@click.option("--app-dir", default=".", show_default=True, help="Root of the app directory.")
@click.option("--fix", is_flag=True, default=False, help="Show fix suggestions.")
@click.option("--only", default=None, help="Limit to one category (instructions/tools/evals/…).")
@click.option("--rule", default=None, help="Comma-separated rule IDs (e.g. I003,C005).")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output results as JSON.")
@click.option("--list-rules", is_flag=True, default=False, help="Print all rules and exit.")
@click.option("--validate-only", is_flag=True, default=False, help="Schema/config checks only.")
@click.option("--agent", default=None, help="Validate a single agent directory.")
@click.option("--tool", default=None, help="Validate a single tool directory.")
@click.option("--toolset", default=None, help="Validate a single toolset directory.")
@click.option("--guardrail", default=None, help="Validate a single guardrail directory.")
@click.option("--evaluation", default=None, help="Validate a single evaluation directory.")
@click.option("--evaluation-expectations", default=None, help="Validate eval expectations dir.")
def lint(
    app_dir, fix, only, rule, as_json, list_rules, validate_only,
    agent, tool, toolset, guardrail, evaluation, evaluation_expectations,
):
    """Lint your app directory for best-practice violations (60+ rules)."""
    args = ["lint", "--app-dir", app_dir]
    if fix:
        args.append("--fix")
    if only:
        args += ["--only", only]
    if rule:
        args += ["--rule", rule]
    if as_json:
        args.append("--json")
    if list_rules:
        args.append("--list-rules")
    if validate_only:
        args.append("--validate-only")
    if agent:
        args += ["--agent", agent]
    if tool:
        args += ["--tool", tool]
    if toolset:
        args += ["--toolset", toolset]
    if guardrail:
        args += ["--guardrail", guardrail]
    if evaluation:
        args += ["--evaluation", evaluation]
    if evaluation_expectations:
        args += ["--evaluation-expectations", evaluation_expectations]
    _exit_on_fail(_run_cxas(*args))


# ================================================================== #
#  init
# ================================================================== #

@main.command("init")
@click.option("--target-dir", default=".", show_default=True, help="Directory to install skills.")
@click.option("--force", is_flag=True, default=False, help="Overwrite existing files.")
def init(target_dir, force):
    """Bootstrap a project with AI agent development skills and config files."""
    args = ["init", "--target-dir", target_dir]
    if force:
        args.append("--force")
    _exit_on_fail(_run_cxas(*args))


# ================================================================== #
#  insights
# ================================================================== #

@main.group("insights")
def insights_group() -> None:
    """Manage QA scorecards via the Insights API. (delegates to cxas insights)"""


@insights_group.command("list-scorecards")
@click.option("--parent", required=True, help="projects/{project}/locations/{location}")
def insights_list_scorecards(parent):
    """List all QA scorecards."""
    _exit_on_fail(_run_cxas("insights", "list-scorecards", "--parent", parent))


@insights_group.command("export-scorecard")
@click.option("--scorecard-name", required=True, help="Full resource name of the scorecard.")
@click.option("--template", required=True, help="Output file path (.json or .yaml).")
def insights_export_scorecard(scorecard_name, template):
    """Export a scorecard to a local template file."""
    _exit_on_fail(_run_cxas(
        "insights", "export-scorecard-from-insights",
        "--scorecard-name", scorecard_name,
        "--template", template,
    ))


@insights_group.command("import-scorecard")
@click.option("--template", required=True, help="Path to the scorecard template file.")
@click.option("--scorecard-name", default=None, help="Existing scorecard to update.")
@click.option("--parent", default=None, help="Parent resource name (to create new scorecard).")
def insights_import_scorecard(template, scorecard_name, parent):
    """Import a scorecard template into Insights."""
    if not scorecard_name and not parent:
        error("Provide --scorecard-name (update) or --parent (create new).")
        sys.exit(1)
    args = ["insights", "import-scorecard-to-insights", "--template", template]
    if scorecard_name:
        args += ["--scorecard-name", scorecard_name]
    if parent:
        args += ["--parent", parent]
    _exit_on_fail(_run_cxas(*args))


@insights_group.command("copy-scorecard")
@click.option("--scorecard-name", required=True, help="Source scorecard resource name.")
@click.option("--dst-scorecard-name", default=None, help="Destination scorecard resource name.")
@click.option("--parent", default=None, help="Parent resource name (create new destination).")
def insights_copy_scorecard(scorecard_name, dst_scorecard_name, parent):
    """Copy a scorecard's questions into another scorecard."""
    if not dst_scorecard_name and not parent:
        error("Provide --dst-scorecard-name or --parent.")
        sys.exit(1)
    args = ["insights", "copy-scorecard", "--scorecard-name", scorecard_name]
    if dst_scorecard_name:
        args += ["--dst-scorecard-name", dst_scorecard_name]
    if parent:
        args += ["--parent", parent]
    _exit_on_fail(_run_cxas(*args))


# ================================================================== #
#  migrate
# ================================================================== #

@main.group("migrate")
def migrate_group() -> None:
    """Migrate legacy agents to CX Agent Studio. (delegates to cxas migrate)"""


@migrate_group.command("dfcx")
@click.option("--default-agent-name", default="migrated-agent", show_default=True,
              help="Default name for the target agent.")
def migrate_dfcx(default_agent_name):
    """Launch the interactive DFCX → CXAS migration dashboard."""
    _exit_on_fail(_run_cxas("migrate", "dfcx", "--default-agent-name", default_agent_name))


# ================================================================== #
#  trace
# ================================================================== #

@main.command("trace")
@click.argument("subcmd", nargs=-1)
def trace(subcmd):
    """
    Inspect, analyze, and report on individual conversations.

    All arguments are forwarded verbatim to `cxas trace`.

    \b
    Examples:
      cxclaw trace list --app-name projects/my-proj/locations/us/apps/abc
      cxclaw trace fetch-report --conversation-id abc123 --app-name ...
    """
    if not subcmd:
        _exit_on_fail(_run_cxas("trace", "--help"))
    else:
        _exit_on_fail(_run_cxas("trace", *subcmd))


# ================================================================== #
#  chat  (cxclaw-native interactive REPL)
# ================================================================== #

@main.command("chat")
@click.option("--app", required=True, help="Full resource name or display name of the app.")
@click.option("--project-id", default=None)
@click.option("--location", default=None)
@click.option("--session-id", default=None, help="Resume an existing session by ID.")
@click.pass_context
def chat(ctx, app, project_id, location, session_id):
    """
    Start an interactive multi-turn chat session with a CXAS app.
    (cxclaw-native — does not require live GCP creds if using mock)
    """
    profile = _load_profile(ctx)
    pid = project_id or (profile.project_id if profile else None)
    loc = location or (profile.location if profile else None)
    if not pid or not loc:
        error("--project-id and --location are required (or set an active profile).")
        sys.exit(1)

    from cxas_claw.client import CXASClient
    client = CXASClient(profile=profile, project_id=pid, location=loc)
    app_name = client.resolve_app(app) if not app.startswith("projects/") else app

    from cxas_claw.scratchpad import ScratchpadSession
    from cxas_claw.repl import CXASRepl
    session = ScratchpadSession(
        app_name=app_name,
        project_id=pid,
        location=loc,
        credentials_file=profile.credentials_file if profile else None,
        session_id=session_id,
    )
    repl = CXASRepl(session, agent_name=app_name.split("/")[-1])
    repl.run()


# ================================================================== #
#  scratchpad  (single-turn quick test)
# ================================================================== #

@main.command("scratchpad")
@click.option("--app", required=True, help="Full resource name or display name of the app.")
@click.option("--text", required=True, help="Text to send to the agent.")
@click.option("--project-id", default=None)
@click.option("--location", default=None)
@click.option("--session-id", default=None, help="Reuse a specific session ID.")
@click.pass_context
def scratchpad(ctx, app, text, project_id, location, session_id):
    """Send a single text turn to a CXAS app and print the response."""
    profile = _load_profile(ctx)
    pid = project_id or (profile.project_id if profile else None)
    loc = location or (profile.location if profile else None)
    if not pid or not loc:
        error("--project-id and --location are required.")
        sys.exit(1)

    from cxas_claw.client import CXASClient
    client = CXASClient(profile=profile, project_id=pid, location=loc)
    app_name = client.resolve_app(app) if not app.startswith("projects/") else app

    from cxas_claw.scratchpad import ScratchpadSession
    session = ScratchpadSession(
        app_name=app_name,
        project_id=pid,
        location=loc,
        credentials_file=profile.credentials_file if profile else None,
        session_id=session_id,
    )
    response = session.send(text)
    console.print(f"[bold cyan]agent[/bold cyan]: {response}")


# ================================================================== #
#  mcp  (MCP server interaction)
# ================================================================== #

@main.group("mcp")
def mcp_group() -> None:
    """Interact with the CX Agent Studio MCP server."""


@mcp_group.command("health")
@click.option("--server-url", default=None, envvar="CXAS_MCP_SERVER_URL")
def mcp_health(server_url):
    """Check MCP server health."""
    from cxas_claw.mcp import MCPClient
    client = MCPClient(server_url=server_url)
    result = client.health()
    console.print_json(json.dumps(result, default=str, indent=2))
    client.close()


@mcp_group.command("list-tools")
@click.option("--server-url", default=None, envvar="CXAS_MCP_SERVER_URL")
@click.option("--output", "-o", default="table", type=click.Choice(["table", "json", "csv"]))
def mcp_list_tools(server_url, output):
    """List tools exposed by the MCP server."""
    from cxas_claw.mcp import MCPClient
    client = MCPClient(server_url=server_url)
    tools = client.list_tools()
    client.close()
    if not isinstance(tools, list):
        console.print_json(json.dumps(tools, default=str))
        return
    rows = [t if isinstance(t, dict) else {"tool": str(t)} for t in tools]
    render(rows, output=output, title="MCP Tools")


@mcp_group.command("invoke")
@click.option("--tool", "tool_name", required=True, help="Tool name to invoke.")
@click.option("--params", default="{}", help="JSON string of parameters.")
@click.option("--server-url", default=None, envvar="CXAS_MCP_SERVER_URL")
def mcp_invoke(tool_name, params, server_url):
    """Invoke an MCP tool with JSON parameters."""
    from cxas_claw.mcp import MCPClient
    client = MCPClient(server_url=server_url)
    try:
        parameters = json.loads(params)
    except json.JSONDecodeError as exc:
        error(f"Invalid JSON for --params: {exc}")
        sys.exit(1)
    result = client.invoke_tool(tool_name, parameters)
    console.print_json(json.dumps(result, default=str, indent=2))
    client.close()
