"""
CXASClient — thin wrapper around dfcx_scrapi (cxas-scrapi) classes.
Uses lazy imports per resource type so optional deps don't hard-fail at import.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from cxas_claw.profile import Profile


class CXASClient:
    """
    Provides access to every cxas-scrapi resource class.
    Pass a Profile or supply project_id/location/creds directly.
    """

    def __init__(
        self,
        profile: Optional[Profile] = None,
        project_id: Optional[str] = None,
        location: Optional[str] = None,
        credentials_file: Optional[str] = None,
        oauth_token: Optional[str] = None,
    ):
        # Resolve from profile first, then explicit kwargs, then env
        if profile:
            profile.apply_env()
            self.project_id = project_id or profile.project_id
            self.location = location or profile.location
            self.credentials_file = credentials_file or profile.credentials_file
            self.oauth_token = oauth_token or profile.oauth_token
            self.default_app = profile.default_app
        else:
            self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT", "")
            self.location = location or "global"
            self.credentials_file = credentials_file or os.environ.get(
                "GOOGLE_APPLICATION_CREDENTIALS"
            )
            self.oauth_token = oauth_token or os.environ.get("CXAS_OAUTH_TOKEN")
            self.default_app = None

        if self.credentials_file:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.credentials_file
        if self.oauth_token:
            os.environ["CXAS_OAUTH_TOKEN"] = self.oauth_token

        self._creds = self.credentials_file  # may be None → ADC

    # ------------------------------------------------------------------ #
    # Lazy resource accessors
    # ------------------------------------------------------------------ #

    def _creds_arg(self) -> Optional[str]:
        return self._creds

    @property
    def apps(self):
        from dfcx_scrapi.core.apps import Apps  # type: ignore
        return Apps(creds_path=self._creds_arg())

    @property
    def agents(self):
        from dfcx_scrapi.core.agents import Agents  # type: ignore
        return Agents(creds_path=self._creds_arg())

    @property
    def sessions(self):
        from dfcx_scrapi.core.sessions import Sessions  # type: ignore
        return Sessions(creds_path=self._creds_arg())

    @property
    def tools(self):
        from dfcx_scrapi.core.tools import Tools  # type: ignore
        return Tools(creds_path=self._creds_arg())

    @property
    def guardrails(self):
        from dfcx_scrapi.core.guardrails import Guardrails  # type: ignore
        return Guardrails(creds_path=self._creds_arg())

    @property
    def deployments(self):
        from dfcx_scrapi.core.deployments import Deployments  # type: ignore
        return Deployments(creds_path=self._creds_arg())

    @property
    def evaluations(self):
        from dfcx_scrapi.core.evaluations import Evaluations  # type: ignore
        return Evaluations(creds_path=self._creds_arg())

    @property
    def variables(self):
        from dfcx_scrapi.core.variables import Variables  # type: ignore
        return Variables(creds_path=self._creds_arg())

    @property
    def versions(self):
        from dfcx_scrapi.core.versions import Versions  # type: ignore
        return Versions(creds_path=self._creds_arg())

    @property
    def changelogs(self):
        from dfcx_scrapi.core.changelogs import Changelogs  # type: ignore
        return Changelogs(creds_path=self._creds_arg())

    @property
    def callbacks(self):
        from dfcx_scrapi.core.callbacks import Callbacks  # type: ignore
        return Callbacks(creds_path=self._creds_arg())

    @property
    def conversation_history(self):
        from dfcx_scrapi.core.conversation_history import ConversationHistory  # type: ignore
        return ConversationHistory(creds_path=self._creds_arg())

    @property
    def insights(self):
        from dfcx_scrapi.core.insights import Insights  # type: ignore
        return Insights(creds_path=self._creds_arg())

    # Eval runners
    @property
    def tool_evals(self):
        from dfcx_scrapi.evals.tool_evals import ToolEvals  # type: ignore
        return ToolEvals(creds_path=self._creds_arg())

    @property
    def simulation_evals(self):
        from dfcx_scrapi.evals.simulation_evals import SimulationEvals  # type: ignore
        return SimulationEvals(creds_path=self._creds_arg())

    @property
    def callback_evals(self):
        from dfcx_scrapi.evals.callback_evals import CallbackEvals  # type: ignore
        return CallbackEvals(creds_path=self._creds_arg())

    @property
    def guardrail_evals(self):
        from dfcx_scrapi.evals.guardrail_evals import GuardrailEvals  # type: ignore
        return GuardrailEvals(creds_path=self._creds_arg())

    # Utils
    @property
    def linter(self):
        from dfcx_scrapi.utils.linter import Linter  # type: ignore
        return Linter(creds_path=self._creds_arg())

    @property
    def eval_utils(self):
        from dfcx_scrapi.utils.eval_utils import EvalUtils  # type: ignore
        return EvalUtils(creds_path=self._creds_arg())

    # ------------------------------------------------------------------ #
    # Convenience helpers
    # ------------------------------------------------------------------ #

    def parent(self) -> str:
        """Returns projects/{project}/locations/{location}"""
        return f"projects/{self.project_id}/locations/{self.location}"

    def resolve_app(self, app: str) -> str:
        """Return full resource name — passthrough if already full, else look up by display name."""
        if app.startswith("projects/"):
            return app
        results = self.apps.list_apps(parent=self.parent())
        for a in results:
            if a.display_name == app:
                return a.name
        raise ValueError(
            f"App '{app}' not found in {self.parent()}. "
            "Use full resource name or pass --project-id/--location."
        )
