"""
Profile management for cxclaw.
Stores named GCP credential profiles at ~/.cxas-claw/profiles/<name>.json
Active profile pointer at ~/.cxas-claw/active_profile
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


PROFILES_DIR = Path.home() / ".cxas-claw" / "profiles"
ACTIVE_FILE = Path.home() / ".cxas-claw" / "active_profile"


@dataclass
class Profile:
    name: str
    project_id: str
    location: str
    credentials_file: Optional[str] = None   # path to SA JSON key, or None for ADC
    oauth_token: Optional[str] = None         # explicit OAuth bearer token
    default_app: Optional[str] = None         # full resource name of default app
    extra: dict = field(default_factory=dict)

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #

    def save(self) -> None:
        PROFILES_DIR.mkdir(parents=True, exist_ok=True)
        path = PROFILES_DIR / f"{self.name}.json"
        path.write_text(json.dumps(asdict(self), indent=2))

    def delete(self) -> None:
        path = PROFILES_DIR / f"{self.name}.json"
        if path.exists():
            path.unlink()

    # ------------------------------------------------------------------ #
    # Class helpers
    # ------------------------------------------------------------------ #

    @classmethod
    def load(cls, name: str) -> "Profile":
        path = PROFILES_DIR / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(f"Profile '{name}' not found. Run: cxclaw profile create {name}")
        data = json.loads(path.read_text())
        extra = data.pop("extra", {})
        return cls(**data, extra=extra)

    @classmethod
    def list_profiles(cls) -> list[str]:
        if not PROFILES_DIR.exists():
            return []
        return [p.stem for p in sorted(PROFILES_DIR.glob("*.json"))]

    @classmethod
    def get_active(cls) -> Optional["Profile"]:
        if ACTIVE_FILE.exists():
            name = ACTIVE_FILE.read_text().strip()
            try:
                return cls.load(name)
            except FileNotFoundError:
                return None
        return None

    @classmethod
    def set_active(cls, name: str) -> None:
        # validate it exists first
        cls.load(name)
        ACTIVE_FILE.parent.mkdir(parents=True, exist_ok=True)
        ACTIVE_FILE.write_text(name)

    # ------------------------------------------------------------------ #
    # Env-var injection helpers (used by CXASClient)
    # ------------------------------------------------------------------ #

    def apply_env(self) -> None:
        """Inject profile credentials into environment variables."""
        if self.credentials_file:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.credentials_file
        if self.oauth_token:
            os.environ["CXAS_OAUTH_TOKEN"] = self.oauth_token
