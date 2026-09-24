from __future__ import annotations

from dataclasses import asdict, dataclass

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
        reserved = self.output_reserve + int(self.ctx_size * self.safety_margin)
        effective_capacity = max(1, self.ctx_size - reserved)
        ratio = used_tokens / effective_capacity
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


@dataclass
class RoleCapacityPercentages:
    reserve_output: float
    compact_at: float
    hard_stop_at: float
    max_response: float


ROLE_CAPACITY_PERCENTAGES: dict[str, RoleCapacityPercentages] = {
    "Task Master": RoleCapacityPercentages(0.20, 0.62, 0.76, 0.10),
    "Architect": RoleCapacityPercentages(0.20, 0.64, 0.78, 0.10),
    "Implementer": RoleCapacityPercentages(0.1875, 0.68359375, 0.79345703125, 0.125),
    "Reviewer": RoleCapacityPercentages(0.20, 0.66, 0.80, 0.10),
    "Test/Debug": RoleCapacityPercentages(0.18, 0.66, 0.80, 0.10),
    "Vision Specialist": RoleCapacityPercentages(0.22, 0.60, 0.74, 0.08),
    "Custom": RoleCapacityPercentages(0.20, 0.65, 0.78, 0.10),
}


@dataclass
class RoleContextBudget:
    role: str
    endpoint: str
    ctx_size: int
    reserve_output_tokens: int
    compact_at_tokens: int
    hard_stop_at_tokens: int
    max_response_tokens: int
    checkpoint_format: str = "structured_json"
    auto_compact: bool = True

    @classmethod
    def from_capacity(
        cls, role: str, endpoint: str, ctx_size: int, percentages: RoleCapacityPercentages | None = None
    ) -> "RoleContextBudget":
        if ctx_size <= 0:
            raise ValueError("ctx_size must be positive")
        policy = percentages or ROLE_CAPACITY_PERCENTAGES.get(role, ROLE_CAPACITY_PERCENTAGES["Custom"])
        reserve = int(ctx_size * policy.reserve_output)
        compact = int(ctx_size * policy.compact_at)
        hard_stop = int(ctx_size * policy.hard_stop_at)
        max_response = int(ctx_size * policy.max_response)
        return cls(
            role=role.lower().replace(" ", "_"),
            endpoint=endpoint,
            ctx_size=ctx_size,
            reserve_output_tokens=reserve,
            compact_at_tokens=compact,
            hard_stop_at_tokens=hard_stop,
            max_response_tokens=max_response,
        )

    def as_dict(self) -> dict:
        return asdict(self)
