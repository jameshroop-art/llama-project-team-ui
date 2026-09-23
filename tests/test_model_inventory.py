from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

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


def test_read_metadata_keeps_missing_fields(monkeypatch, tmp_path: Path) -> None:
    class Field:
        def __init__(self, value):
            self.parts = [value]

    class FakeReader:
        def __init__(self, _path: str):
            self.fields = {
                "general.architecture": Field("qwen2"),
                "qwen2.context_length": Field(32768),
                "tokenizer.ggml.model": Field("qwen"),
            }

    monkeypatch.setitem(sys.modules, "gguf", SimpleNamespace(GGUFReader=FakeReader))
    model_file = tmp_path / "sample.gguf"
    model_file.write_bytes(b"gguf")

    info = GGUFInventory().read_metadata(model_file)
    assert info.context_length == 32768
    assert info.chat_template is None
    assert info.fim is None
    assert "chat_template" in (info.missing_metadata or [])
    assert "fim" in (info.missing_metadata or [])
