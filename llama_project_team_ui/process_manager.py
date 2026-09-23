from __future__ import annotations

import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from queue import Queue

from .audit import AuditLogger
from .config import LauncherProfile
from .safety import is_port_in_use, validate_port, validate_safe_argv


@dataclass
class RunningProcess:
    profile: LauncherProfile
    process: subprocess.Popen[str]
    log_queue: Queue[str]


class ProcessManager:
    def __init__(self, audit_logger: AuditLogger):
        self.audit_logger = audit_logger
        self.running: dict[str, RunningProcess] = {}

    def build_server_argv(self, profile: LauncherProfile) -> list[str]:
        argv = [
            str(Path(profile.llama_server_path).expanduser()),
            "-m",
            profile.model_path,
            "--host",
            profile.host,
            "--port",
            str(profile.port),
            "--ctx-size",
            str(profile.ctx_size),
            "--gpu-layers",
            str(profile.gpu_layers),
        ]
        if profile.projector_path:
            argv.extend(["--mmproj", profile.projector_path])
        argv.extend(profile.extra_args)
        safe = validate_safe_argv(argv)
        if not safe.ok:
            raise ValueError(safe.reason)
        return argv

    def validate_profile_start(self, profile: LauncherProfile) -> None:
        port_ok = validate_port(profile.port)
        if not port_ok.ok:
            raise ValueError(port_ok.reason)
        model_file = Path(profile.model_path).expanduser()
        if not model_file.is_file() or not model_file.exists():
            raise ValueError("model path is not readable")
        if is_port_in_use(profile.host, profile.port):
            raise ValueError(f"port {profile.port} is already in use")

    def start(self, profile: LauncherProfile, approved: bool) -> None:
        argv = self.build_server_argv(profile)
        if not approved:
            self.audit_logger.log("start_server", argv, "rejected", None)
            return
        self.validate_profile_start(profile)
        process = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        queue: Queue[str] = Queue()
        self.running[profile.id] = RunningProcess(profile=profile, process=process, log_queue=queue)

        def pump() -> None:
            if process.stdout is None:
                return
            for line in process.stdout:
                queue.put(line.rstrip("\n"))

        threading.Thread(target=pump, daemon=True).start()
        self.audit_logger.log("start_server", argv, "approved", None)

    def stop(self, profile_id: str, approved: bool) -> None:
        running = self.running.get(profile_id)
        if not running:
            return
        if not approved:
            self.audit_logger.log("stop_server", [running.profile.name], "rejected", None)
            return
        running.process.terminate()
        exit_status = running.process.wait(timeout=10)
        self.audit_logger.log("stop_server", [running.profile.name], "approved", exit_status)
        self.running.pop(profile_id, None)

    def restart(self, profile: LauncherProfile, approved: bool) -> None:
        self.stop(profile.id, approved)
        if approved:
            self.start(profile, approved)

    def status(self, profile_id: str) -> str:
        running = self.running.get(profile_id)
        if not running:
            return "stopped"
        code = running.process.poll()
        return "running" if code is None else f"exited({code})"

    def health(self, profile_id: str) -> str:
        return self.status(profile_id)

    def collect_logs(self, profile_id: str) -> list[str]:
        running = self.running.get(profile_id)
        if not running:
            return []
        lines: list[str] = []
        while not running.log_queue.empty():
            lines.append(running.log_queue.get_nowait())
        return lines
