"""
ScratchpadSession — multi-turn interactive tester using dfcx_scrapi Sessions.
"""

from __future__ import annotations

import uuid
from typing import Optional


class ScratchpadSession:
    """
    Wraps dfcx_scrapi Sessions for a multi-turn conversation test loop.
    Keeps track of session_id, turn history, and parameters.
    """

    def __init__(
        self,
        app_name: str,
        project_id: str,
        location: str,
        credentials_file: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        self.app_name = app_name
        self.project_id = project_id
        self.location = location
        self.credentials_file = credentials_file
        self.session_id = session_id or str(uuid.uuid4())
        self.history: list[dict] = []
        self._sessions = None

    def _get_sessions(self):
        if self._sessions is None:
            from dfcx_scrapi.core.sessions import Sessions  # type: ignore
            self._sessions = Sessions(creds_path=self.credentials_file)
        return self._sessions

    def send(self, text: str) -> str:
        """Send a text turn and return the agent response text."""
        sessions = self._get_sessions()
        response = sessions.detect_intent(
            agent_id=self.app_name,
            session_id=self.session_id,
            text=text,
        )
        # dfcx_scrapi returns a QueryResult — extract text
        reply = self._extract_text(response)
        self.history.append({"user": text, "agent": reply})
        return reply

    def reset(self) -> None:
        """Start a brand-new session."""
        self.session_id = str(uuid.uuid4())
        self.history.clear()

    def dump_history(self) -> list[dict]:
        return list(self.history)

    @staticmethod
    def _extract_text(response) -> str:
        try:
            # google.cloud.dialogflowcx_v3 QueryResult
            parts = []
            for msg in response.query_result.response_messages:
                if hasattr(msg, "text") and msg.text.text:
                    parts.extend(msg.text.text)
            return " ".join(parts) if parts else str(response)
        except Exception:
            return str(response)
