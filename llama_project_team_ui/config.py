from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal
from uuid import uuid4

ROLE_PRESETS = [
    "Task Master",
    "Architect",
    "Implementer",
    "Reviewer",
    "Test/Debug",
    "Vision Specialist",
    "Custom",
]


def default_llama_server_path() -> str:
    return "~/.local/bin/llama-server-cuda13"


def _xdg_path(env_name: str, fallback_suffix: str) -> Path:
    env_val = os.environ.get(env_name)
    if env_val:
        return Path(env_val).expanduser()
    return Path.home() / fallback_suffix


CONFIG_DIR = _xdg_path("XDG_CONFIG_HOME", ".config") / "llama-project-team-ui"
STATE_DIR = _xdg_path("XDG_STATE_HOME", ".local/state") / "llama-project-team-ui"
CACHE_DIR = _xdg_path("XDG_CACHE_HOME", ".cache") / "llama-project-team-ui"
LOG_DIR = STATE_DIR / "logs"
CONFIG_PATH = CONFIG_DIR / "config.json"


@dataclass
class LauncherProfile:
    name: str
    role: str = "Custom"
    llama_server_path: str = field(default_factory=default_llama_server_path)
    model_path: str = ""
    projector_path: str = ""
    host: str = "127.0.0.1"
    port: int = 8080
    ctx_size: int = 8192
    gpu_layers: int = 0
    extra_args: list[str] = field(default_factory=list)
    start_mode: Literal["always_on", "on_demand"] = "always_on"
    idle_shutdown_minutes: int | None = None
    enabled: bool = True
    id: str = field(default_factory=lambda: uuid4().hex)


@dataclass
class AppConfig:
    workspace_roots: list[str] = field(default_factory=list)
    approved_workspace_roots: list[str] = field(default_factory=list)
    model_roots: list[str] = field(default_factory=list)
    suggested_model_roots: list[str] = field(
        default_factory=lambda: [
            str(Path.home() / "models"),
            str(Path.home() / "Documents/models"),
            "/run/media",
            "/mnt",
        ]
    )
    profiles: list[LauncherProfile] = field(default_factory=list)
    task_master_enabled: bool = False
    default_project_venv_name: str = ".venv"


class ConfigStore:
    def __init__(self, path: Path = CONFIG_PATH):
        self.path = path

    def ensure_dirs(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for directory in (STATE_DIR, CACHE_DIR, LOG_DIR):
            directory.mkdir(parents=True, exist_ok=True)

    def load(self) -> AppConfig:
        self.ensure_dirs()
        if not self.path.exists():
            return AppConfig()
        data = json.loads(self.path.read_text(encoding="utf-8"))
        profiles = [LauncherProfile(**p) for p in data.get("profiles", [])]
        return AppConfig(
            workspace_roots=data.get("workspace_roots", []),
            approved_workspace_roots=data.get("approved_workspace_roots", []),
            model_roots=data.get("model_roots", []),
            suggested_model_roots=data.get("suggested_model_roots", AppConfig().suggested_model_roots),
            profiles=profiles,
            task_master_enabled=data.get("task_master_enabled", False),
            default_project_venv_name=data.get("default_project_venv_name", ".venv"),
        )

    def save(self, config: AppConfig) -> None:
        self.ensure_dirs()
        payload = asdict(config)
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
