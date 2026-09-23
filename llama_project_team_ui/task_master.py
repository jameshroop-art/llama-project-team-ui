from __future__ import annotations

from dataclasses import dataclass

from .config import AppConfig
from .isolation import IsolationDiscoverer, IsolationRecommendation
from .model_inventory import GGUFInventory, detect_available_ram_gb


@dataclass
class PlanningResult:
    discoveries: list[dict]
    isolation_options: dict
    recommendations: list[dict]
    model_inventory: list[dict]
    role_suggestions: dict


class TaskMasterPlanner:
    def __init__(self, discoverer: IsolationDiscoverer | None = None, inventory: GGUFInventory | None = None):
        self.discoverer = discoverer or IsolationDiscoverer()
        self.inventory = inventory or GGUFInventory()

    def plan_read_only(self, config: AppConfig) -> PlanningResult:
        projects = self.discoverer.discover_projects(config.workspace_roots, config.default_project_venv_name)
        options = self.discoverer.detect_isolation_options()

        recommendations: list[IsolationRecommendation] = [self.discoverer.recommend(project, options) for project in projects]
        inventory = self.inventory.discover(config.model_roots)
        role_suggestions = self.inventory.recommend_roles(inventory, available_ram_gb=detect_available_ram_gb())

        return PlanningResult(
            discoveries=[
                {
                    "path": project.path,
                    "language_hints": project.language_hints,
                    "has_venv": project.has_venv,
                }
                for project in projects
            ],
            isolation_options={
                "podman_available": options.podman_available,
                "distrobox_available": options.distrobox_available,
                "podman_containers": options.podman_containers,
                "distrobox_containers": options.distrobox_containers,
            },
            recommendations=[
                {
                    "strategy": rec.strategy,
                    "reason": rec.reason,
                    "proposed_argv": rec.proposed_argv,
                }
                for rec in recommendations
            ],
            model_inventory=[item.__dict__ for item in inventory],
            role_suggestions={
                role: [suggestion.__dict__ for suggestion in entries[:3]]
                for role, entries in role_suggestions.items()
            },
        )
