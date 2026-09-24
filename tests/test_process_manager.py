from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

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


def test_build_server_argv_expands_user_in_server_path(tmp_path: Path) -> None:
    logger = AuditLogger(path=tmp_path / "audit.jsonl")
    manager = ProcessManager(logger)
    profile = LauncherProfile(
        name="test",
        llama_server_path="~/.local/bin/llama-server-cuda13",
        model_path="/tmp/model.gguf",
    )

    argv = manager.build_server_argv(profile)

    assert argv[0] == str(Path.home() / ".local/bin/llama-server-cuda13")


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


def test_health_status_stopped_and_running(tmp_path: Path) -> None:
    logger = AuditLogger(path=tmp_path / "audit.jsonl")
    manager = ProcessManager(logger)
    profile = LauncherProfile(name="test")
    assert manager.health(profile.id) == "stopped"

    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(1)"])
    manager.running[profile.id] = type("RP", (), {"profile": profile, "process": proc, "log_queue": None})()  # type: ignore[assignment]
    try:
        assert manager.health(profile.id) == "running"
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_duplicate_start_is_rejected(tmp_path: Path) -> None:
    logger = AuditLogger(path=tmp_path / "audit.jsonl")
    manager = ProcessManager(logger)
    profile = LauncherProfile(
        name="test",
        llama_server_path="/usr/bin/llama-server",
        model_path="/tmp/model.gguf",
        host="127.0.0.1",
        port=8080,
    )

    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(1)"])
    manager.running[profile.id] = type("RP", (), {"profile": profile, "process": proc, "log_queue": None})()  # type: ignore[assignment]
    try:
        with pytest.raises(ValueError, match="already running"):
            manager.start(profile, approved=True)
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_log_pump_collects_output(tmp_path: Path) -> None:
    logger = AuditLogger(path=tmp_path / "audit.jsonl")
    manager = ProcessManager(logger)

    fake_server = tmp_path / "fake_server.py"
    fake_server.write_text(
        "#!/usr/bin/env python3\nimport time\nprint('fake-server-started', flush=True)\ntime.sleep(2)\n",
        encoding="utf-8",
    )
    fake_server.chmod(0o755)
    model = tmp_path / "model.gguf"
    model.write_text("x", encoding="utf-8")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    profile = LauncherProfile(
        name="fake",
        llama_server_path=str(fake_server),
        model_path=str(model),
        host="127.0.0.1",
        port=port,
    )
    manager.start(profile, approved=True)
    try:
        time.sleep(0.2)
        logs = manager.collect_logs(profile.id)
        assert any("fake-server-started" in line for line in logs)
    finally:
        manager.stop(profile.id, approved=True)
