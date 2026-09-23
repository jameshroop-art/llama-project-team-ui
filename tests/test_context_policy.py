from __future__ import annotations

from llama_project_team_ui.context_policy import ContextPolicy, StructuredCheckpoint


def test_context_thresholds() -> None:
    policy = ContextPolicy(ctx_size=1000, compact_threshold=0.7, hard_stop_threshold=0.9)
    assert policy.evaluate(600) == "healthy"
    assert policy.evaluate(700) == "compact_now"
    assert policy.evaluate(900) == "hard_stop"


def test_checkpoint_schema_fields() -> None:
    model = StructuredCheckpoint(
        objective="ship",
        current_state="in_progress",
        next_agent_instruction="continue",
    )
    payload = model.model_dump()
    assert "objective" in payload
    assert "next_agent_instruction" in payload
