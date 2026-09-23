from __future__ import annotations

from llama_project_team_ui.model_inventory import GGUFModelInfo, GGUFInventory


def test_role_scoring_handles_missing_metadata() -> None:
    inventory = GGUFInventory()
    model = GGUFModelInfo(
        path="/models/unknown.gguf",
        size_bytes=2 * 1024 * 1024 * 1024,
        metadata_source="heuristic",
        confidence="low",
    )
    suggestions = inventory.recommend_roles([model], available_ram_gb=16)
    assert "Task Master" in suggestions
    assert suggestions["Task Master"][0].confidence == "low"
    assert suggestions["Implementer"][0].model_path == "/models/unknown.gguf"
