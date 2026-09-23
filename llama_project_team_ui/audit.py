from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from .config import LOG_DIR


@dataclass
class AuditEvent:
    timestamp: str
    action: str
    argv: list[str]
    approval: str
    exit_status: int | None
    workspace: str | None
    container: str | None


class AuditLogger:
    def __init__(self, path: Path | None = None):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.path = path or (LOG_DIR / "actions.jsonl")

    def log(
        self,
        action: str,
        argv: list[str],
        approval: str,
        exit_status: int | None,
        workspace: str | None = None,
        container: str | None = None,
    ) -> None:
        event = AuditEvent(
            timestamp=datetime.now(UTC).isoformat(),
            action=action,
            argv=argv,
            approval=approval,
            exit_status=exit_status,
            workspace=workspace,
            container=container,
        )
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(event)) + "\n")
