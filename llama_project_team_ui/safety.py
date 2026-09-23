from __future__ import annotations

import ipaddress
import os
import socket
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

FORBIDDEN_ARG_PREFIXES = (
    "sudo",
    "rpm-ostree",
    "dnf",
    "apt",
)
FORBIDDEN_PIP_PATTERNS = ("pip install", "python -m pip install", "--user")


@dataclass
class ValidationResult:
    ok: bool
    reason: str = ""


def in_virtualenv() -> bool:
    return (
        getattr(sys, "real_prefix", None) is not None
        or sys.prefix != getattr(sys, "base_prefix", sys.prefix)
        or "VIRTUAL_ENV" in os.environ
    )


def remediation_instructions() -> str:
    return (
        "Run this app from a private venv, for example:\n"
        "python -m venv ~/.local/venvs/llama-project-team-ui\n"
        "~/.local/venvs/llama-project-team-ui/bin/python -m pip install -e .[dev]\n"
        "~/.local/venvs/llama-project-team-ui/bin/llama-project-team-ui"
    )


def validate_loopback_host(host: str) -> ValidationResult:
    try:
        return ValidationResult(ipaddress.ip_address(host).is_loopback, "non-loopback host")
    except ValueError:
        if host == "localhost":
            return ValidationResult(True)
        return ValidationResult(False, "invalid host")


def validate_port(port: int) -> ValidationResult:
    if not isinstance(port, int):
        return ValidationResult(False, "port must be integer")
    if port < 1 or port > 65535:
        return ValidationResult(False, "port out of range")
    return ValidationResult(True)


def is_port_in_use(host: str, port: int) -> bool:
    try:
        addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return False
    for family, socktype, proto, _, sockaddr in addresses:
        with socket.socket(family, socktype, proto) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex(sockaddr) == 0:
                return True
    return False


def validate_safe_argv(argv: list[str]) -> ValidationResult:
    joined = " ".join(argv).lower()
    if any(part.lower() in FORBIDDEN_ARG_PREFIXES for part in argv):
        return ValidationResult(False, "forbidden host-modifying command")
    if any(pattern in joined for pattern in FORBIDDEN_PIP_PATTERNS):
        return ValidationResult(False, "global or --user pip install is forbidden")
    if any(any(ch in arg for ch in [";", "&&", "||", "`", "$("]) for arg in argv):
        return ValidationResult(False, "shell interpolation markers are forbidden")
    return ValidationResult(True)


def validate_workspace_boundary(target: Path, approved_roots: list[Path]) -> ValidationResult:
    resolved_target = target.expanduser().resolve()
    for root in approved_roots:
        resolved_root = root.expanduser().resolve()
        if resolved_target == resolved_root or resolved_root in resolved_target.parents:
            return ValidationResult(True)
    return ValidationResult(False, "path is outside approved workspace roots")


def run_read_only_command(argv: list[str], timeout: int = 5) -> subprocess.CompletedProcess[str]:
    safe = validate_safe_argv(argv)
    if not safe.ok:
        raise ValueError(safe.reason)
    return subprocess.run(argv, check=False, capture_output=True, text=True, timeout=timeout)
