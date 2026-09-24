from __future__ import annotations

import json
from pathlib import Path

from llama_project_team_ui.config import ConfigStore, LauncherProfile, default_llama_server_path


def test_launcher_profile_defaults_to_cuda13_wrapper() -> None:
    profile = LauncherProfile(name="test")
    assert profile.llama_server_path == "~/.local/bin/llama-server-cuda13"


def test_config_store_preserves_existing_profile_launcher_path(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "profiles": [
                    {
                        "name": "TM",
                        "llama_server_path": "/opt/custom/llama-server",
                        "model_path": "/models/tm.gguf",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    config = ConfigStore(path=config_path).load()

    assert config.profiles[0].llama_server_path == "/opt/custom/llama-server"
