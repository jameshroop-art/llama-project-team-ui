from __future__ import annotations

from llama_project_team_ui.isolation import IsolationDiscoverer, IsolationOptions, ProjectDiscovery


def test_recommend_prefers_existing_container() -> None:
    discoverer = IsolationDiscoverer()
    project = ProjectDiscovery(path="/tmp/project", language_hints=["python"], has_venv=False)
    options = IsolationOptions(
        podman_available=True,
        distrobox_available=True,
        podman_containers=["x"],
        distrobox_containers=["devbox running"],
    )

    rec = discoverer.recommend(project, options)
    assert rec.strategy == "existing_container"
    assert rec.proposed_argv[:2] == ["distrobox", "enter"]


def test_recommend_uses_configured_venv_name() -> None:
    discoverer = IsolationDiscoverer()
    project = ProjectDiscovery(path="/tmp/project", language_hints=["python"], has_venv=True)
    options = IsolationOptions(
        podman_available=False,
        distrobox_available=False,
        podman_containers=[],
        distrobox_containers=[],
    )
    rec = discoverer.recommend(project, options, venv_name=".envpy")
    assert rec.strategy == "project_venv"
    assert "/tmp/project/.envpy/bin/python" in rec.proposed_argv[0]
