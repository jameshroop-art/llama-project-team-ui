from __future__ import annotations

from llama_project_team_ui.context_policy import ContextPolicy, RoleContextBudget, StructuredCheckpoint


def test_context_thresholds() -> None:
    policy = ContextPolicy(
        ctx_size=1000,
        output_reserve=0,
        safety_margin=0.0,
        compact_threshold=0.7,
        hard_stop_threshold=0.9,
    )
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


def test_implementer_role_budget_matches_example_values() -> None:
    budget = RoleContextBudget.from_capacity(
        role="Implementer",
        endpoint="http://127.0.0.1:8082",
        ctx_size=16384,
    )
    assert budget.as_dict() == {
        "role": "implementer",
        "endpoint": "http://127.0.0.1:8082",
        "ctx_size": 16384,
        "reserve_output_tokens": 3072,
        "compact_at_tokens": 11200,
        "hard_stop_at_tokens": 13000,
        "max_response_tokens": 2048,
        "checkpoint_format": "structured_json",
        "auto_compact": True,
    }
