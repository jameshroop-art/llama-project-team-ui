from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from .safety import run_read_only_command


@dataclass
class ProjectDiscovery:
    path: str
    language_hints: list[str]
    has_venv: bool


@dataclass
class IsolationOptions:
    podman_available: bool
    distrobox_available: bool
    podman_containers: list[str]
    distrobox_containers: list[str]


@dataclass
class IsolationRecommendation:
    strategy: str
    reason: str
    proposed_argv: list[str]


class IsolationDiscoverer:
    def discover_projects(self, roots: list[str], venv_name: str = ".venv") -> list[ProjectDiscovery]:
        discoveries: list[ProjectDiscovery] = []
        for root in roots:
            root_path = Path(root).expanduser()
            if not root_path.exists() or not root_path.is_dir():
                continue
            for candidate in [root_path] + [p for p in root_path.iterdir() if p.is_dir()]:
                hints: list[str] = []
                if (candidate / "pyproject.toml").exists() or (candidate / "requirements.txt").exists():
                    hints.append("python")
                if (candidate / "package.json").exists():
                    hints.append("node")
                if (candidate / "Cargo.toml").exists():
                    hints.append("rust")
                if not hints:
                    continue
                discoveries.append(
                    ProjectDiscovery(
                        path=str(candidate),
                        language_hints=hints,
                        has_venv=(candidate / venv_name).exists(),
                    )
                )
        return discoveries

    def detect_isolation_options(self) -> IsolationOptions:
        podman_available = shutil.which("podman") is not None
        distrobox_available = shutil.which("distrobox") is not None
        podman_containers: list[str] = []
        distrobox_containers: list[str] = []

        if podman_available:
            result = run_read_only_command(["podman", "ps", "-a", "--format", "{{.Names}}"])
            if result.returncode == 0:
                podman_containers = [line.strip() for line in result.stdout.splitlines() if line.strip()]

        if distrobox_available:
            result = run_read_only_command(["distrobox", "list", "--no-color"])
            if result.returncode == 0:
                distrobox_containers = [line.strip() for line in result.stdout.splitlines()[1:] if line.strip()]

        return IsolationOptions(
            podman_available=podman_available,
            distrobox_available=distrobox_available,
            podman_containers=podman_containers,
            distrobox_containers=distrobox_containers,
        )

    def recommend(self, project: ProjectDiscovery, options: IsolationOptions) -> IsolationRecommendation:
        if options.distrobox_containers:
            name = options.distrobox_containers[0].split()[0]
            return IsolationRecommendation(
                strategy="existing_container",
                reason="An existing distrobox container provides strongest isolation with minimal setup.",
                proposed_argv=["distrobox", "enter", name, "--", "bash", "-lc", "pwd"],
            )
        if project.has_venv:
            return IsolationRecommendation(
                strategy="project_venv",
                reason="Project already has a local venv; use it before creating new isolation layers.",
                proposed_argv=[str(Path(project.path) / ".venv/bin/python"), "-V"],
            )
        if options.podman_available and options.distrobox_available:
            box_name = Path(project.path).name + "-dev"
            return IsolationRecommendation(
                strategy="create_distrobox",
                reason=(
                    "Project appears to need stronger isolation or native dependencies; "
                    "propose creating a distrobox backed by podman."
                ),
                proposed_argv=[
                    "distrobox",
                    "create",
                    "--name",
                    box_name,
                    "--image",
                    "docker.io/library/fedora:latest",
                ],
            )
        return IsolationRecommendation(
            strategy="project_venv",
            reason="No container runtime detected; project-local .venv is the safest available path.",
            proposed_argv=["python", "-m", "venv", str(Path(project.path) / ".venv")],
        )
