from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field


@dataclass
class ContextPolicy:
    ctx_size: int = 8192
    output_reserve: int = 1024
    safety_margin: float = 0.10
    compact_threshold: float = 0.75
    hard_stop_threshold: float = 0.90

    def evaluate(self, used_tokens: int) -> str:
        if self.ctx_size <= 0:
            raise ValueError("ctx_size must be positive")
        ratio = used_tokens / self.ctx_size
        if ratio >= self.hard_stop_threshold:
            return "hard_stop"
        if ratio >= self.compact_threshold:
            return "compact_now"
        return "healthy"


class StructuredCheckpoint(BaseModel):
    objective: str
    completed_work: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    current_state: str
    relevant_files: list[str] = Field(default_factory=list)
    commands_and_results: list[str] = Field(default_factory=list)
    remaining_work: list[str] = Field(default_factory=list)
    risks_or_questions: list[str] = Field(default_factory=list)
    next_agent_instruction: str


CHECKPOINT_SCHEMA = StructuredCheckpoint.model_json_schema()
