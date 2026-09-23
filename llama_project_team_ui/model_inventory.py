from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class GGUFModelInfo:
    path: str
    size_bytes: int
    architecture: str | None = None
    family: str | None = None
    parameter_count: int | None = None
    quantization: str | None = None
    context_length: int | None = None
    tokenizer: str | None = None
    chat_template: bool | None = None
    fim: bool | None = None
    multimodal: bool | None = None
    confidence: str = "low"
    metadata_source: str = "heuristic"
    missing_metadata: list[str] | None = None


@dataclass
class RoleSuggestion:
    role: str
    model_path: str
    score: float
    confidence: str
    rationale: str


class GGUFInventory:
    def discover(self, roots: list[str]) -> list[GGUFModelInfo]:
        discovered: list[GGUFModelInfo] = []
        for root in roots:
            root_path = Path(root).expanduser()
            if not root_path.exists() or not root_path.is_dir():
                continue
            for file in root_path.rglob("*.gguf"):
                discovered.append(self.read_metadata(file))
        return discovered

    def read_metadata(self, gguf_path: Path) -> GGUFModelInfo:
        info = GGUFModelInfo(path=str(gguf_path), size_bytes=gguf_path.stat().st_size)
        missing = ["architecture", "parameter_count", "context_length", "tokenizer", "chat_template", "fim"]
        try:
            from gguf import GGUFReader  # type: ignore

            reader = GGUFReader(str(gguf_path))
            fields = {k: v for k, v in reader.fields.items()}
            info.architecture = self._field_string(fields, "general.architecture")
            info.family = self._field_string(fields, "general.name")
            info.parameter_count = self._parameter_count_from_fields(fields)
            info.context_length = self._context_length_from_fields(fields)
            info.tokenizer = self._field_string(fields, "tokenizer.ggml.model")
            if "tokenizer.chat_template" in fields:
                info.chat_template = bool(self._field_value(fields, "tokenizer.chat_template"))
            fim_keys = [key for key in fields if key.startswith("tokenizer.fim")]
            if fim_keys:
                info.fim = True
            info.metadata_source = "gguf-reader"
            info.confidence = "high"
        except Exception:
            self._apply_heuristics(info)

        info.missing_metadata = [key for key in missing if getattr(info, key, None) is None]
        return info

    @staticmethod
    def _field_string(fields: dict, name: str) -> str | None:
        value = GGUFInventory._field_value(fields, name)
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="ignore")
        if isinstance(value, str):
            return value
        return None

    @staticmethod
    def _field_int(fields: dict, name: str) -> int | None:
        value = GGUFInventory._field_value(fields, name)
        if value is None:
            return None
        try:
            return int(value)
        except Exception:
            return None

    @staticmethod
    def _field_value(fields: dict, name: str):
        value = fields.get(name)
        if not value or not getattr(value, "parts", None):
            return None
        return value.parts[-1]

    def _context_length_from_fields(self, fields: dict) -> int | None:
        for key in (
            "llama.context_length",
            "qwen2.context_length",
            "gemma.context_length",
            "mistral.context_length",
            "general.context_length",
        ):
            value = self._field_int(fields, key)
            if value is not None:
                return value
        return None

    def _parameter_count_from_fields(self, fields: dict) -> int | None:
        for key in (
            "general.parameter_count",
            "general.params",
            "llama.parameter_count",
            "qwen2.parameter_count",
            "gemma.parameter_count",
            "mistral.parameter_count",
        ):
            value = self._field_int(fields, key)
            if value is not None:
                return value
        return None

    def _apply_heuristics(self, info: GGUFModelInfo) -> None:
        name = Path(info.path).name.lower()
        size_gb = info.size_bytes / (1024**3)

        quant = re.search(r"q\d(_k_[msl])?", name)
        if quant:
            info.quantization = quant.group(0)
        params = re.search(r"(\d{1,3})b", name)
        if params:
            info.parameter_count = int(params.group(1))
        if any(tag in name for tag in ["vision", "vl", "llava", "mmproj"]):
            info.multimodal = True
        if any(tag in name for tag in ["coder", "code", "fim"]):
            info.fim = True

        if info.parameter_count and not info.family:
            info.family = f"{info.parameter_count}B-class"
        info.architecture = info.architecture or "unknown"
        if size_gb > 30:
            info.confidence = "medium"

    def recommend_roles(self, models: list[GGUFModelInfo], available_ram_gb: float | None = None) -> dict[str, list[RoleSuggestion]]:
        roles = ["Task Master", "Architect", "Implementer", "Reviewer", "Test/Debug", "Vision Specialist"]
        scored = {role: [] for role in roles}
        for model in models:
            for role in roles:
                score, rationale = self._score(role, model, available_ram_gb)
                scored[role].append(
                    RoleSuggestion(
                        role=role,
                        model_path=model.path,
                        score=score,
                        confidence=model.confidence,
                        rationale=rationale,
                    )
                )
        for role in roles:
            scored[role].sort(key=lambda item: item.score, reverse=True)
        return scored

    def _score(self, role: str, model: GGUFModelInfo, available_ram_gb: float | None) -> tuple[float, str]:
        score = 0.0
        rationale: list[str] = []
        params = model.parameter_count or 7

        if role in {"Task Master", "Architect"}:
            score += min(params, 70) * 0.8
            rationale.append("larger parameter count helps planning")
        if role in {"Implementer", "Reviewer", "Test/Debug"} and model.fim:
            score += 20
            rationale.append("FIM/coding signals present")
        if role == "Vision Specialist" and model.multimodal:
            score += 35
            rationale.append("multimodal indicators present")
        if model.context_length:
            score += min(model.context_length / 2048, 16)
            rationale.append("context capacity contributes")
        if model.quantization and model.quantization.startswith("q4"):
            score += 5
            rationale.append("q4 quantization often balances speed/quality")

        size_gb = model.size_bytes / (1024**3)
        if available_ram_gb and size_gb > available_ram_gb * 0.7:
            score -= 15
            rationale.append("likely memory pressure")

        if model.metadata_source != "gguf-reader":
            score -= 5
            rationale.append("metadata partially heuristic")

        return score, "; ".join(rationale) if rationale else "limited metadata"


def detect_available_ram_gb() -> float | None:
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return (pages * page_size) / (1024**3)
    except Exception:
        return None
