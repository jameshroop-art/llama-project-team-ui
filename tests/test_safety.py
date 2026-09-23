from __future__ import annotations

import socket
from pathlib import Path

from llama_project_team_ui.safety import (
    in_virtualenv,
    is_port_in_use,
    validate_loopback_host,
    validate_port,
    validate_safe_argv,
    validate_workspace_boundary,
)


def test_validate_port_bounds() -> None:
    assert validate_port(1).ok
    assert validate_port(65535).ok
    assert not validate_port(0).ok
    assert not validate_port(65536).ok


def test_validate_loopback() -> None:
    assert validate_loopback_host("127.0.0.1").ok
    assert validate_loopback_host("::1").ok
    assert validate_loopback_host("localhost").ok
    assert not validate_loopback_host("0.0.0.0").ok


def test_validate_safe_argv_blocks_forbidden_patterns() -> None:
    assert not validate_safe_argv(["sudo", "dnf", "install"]).ok
    assert not validate_safe_argv(["python", "-m", "pip", "install", "--user", "x"]).ok
    assert not validate_safe_argv(["echo", "a;rm", "-rf", "/"]).ok
    assert validate_safe_argv(["/bin/echo", "hello"]).ok


def test_workspace_boundary() -> None:
    approved = [Path("/tmp/work")]
    assert validate_workspace_boundary(Path("/tmp/work/project"), approved).ok
    assert not validate_workspace_boundary(Path("/tmp/other"), approved).ok


def test_port_collision_detection() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        host, port = sock.getsockname()
        assert is_port_in_use(host, port)


def test_in_virtualenv_detection(monkeypatch) -> None:
    import sys

    monkeypatch.setattr(sys, "prefix", "/tmp/a")
    monkeypatch.setattr(sys, "base_prefix", "/tmp/b")
    assert in_virtualenv()
