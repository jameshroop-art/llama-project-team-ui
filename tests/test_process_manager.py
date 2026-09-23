from __future__ import annotations

from pathlib import Path

from llama_project_team_ui.audit import AuditLogger
from llama_project_team_ui.config import LauncherProfile
from llama_project_team_ui.process_manager import ProcessManager


def test_build_server_argv_includes_expected_flags(tmp_path: Path) -> None:
    logger = AuditLogger(path=tmp_path / "audit.jsonl")
    manager = ProcessManager(logger)
    profile = LauncherProfile(
        name="test",
        llama_server_path="/usr/bin/llama-server",
        model_path="/tmp/model.gguf",
        projector_path="/tmp/mmproj.gguf",
        host="127.0.0.1",
        port=8080,
        ctx_size=4096,
        gpu_layers=10,
        extra_args=["--temp", "0.2"],
    )

    argv = manager.build_server_argv(profile)
    assert argv[0] == "/usr/bin/llama-server"
    assert "--mmproj" in argv
    assert "--temp" in argv


def test_start_rejected_is_audited_without_launch(tmp_path: Path) -> None:
    logger = AuditLogger(path=tmp_path / "audit.jsonl")
    manager = ProcessManager(logger)
    profile = LauncherProfile(
        name="test",
        llama_server_path="/usr/bin/llama-server",
        model_path="/tmp/model.gguf",
        host="127.0.0.1",
        port=8080,
    )

    manager.start(profile, approved=False)
    assert profile.id not in manager.running
    text = (tmp_path / "audit.jsonl").read_text(encoding="utf-8")
    assert '"approval": "rejected"' in text
