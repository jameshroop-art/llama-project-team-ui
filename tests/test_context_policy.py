from __future__ import annotations

from llama_project_team_ui.context_policy import ContextPolicy, RoleCapacityPercentages, RoleContextBudget, StructuredCheckpoint


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
    payload = budget.as_dict()
    assert payload["role"] == "implementer"
    assert payload["endpoint"] == "http://127.0.0.1:8082"
    assert payload["ctx_size"] == 16384
    assert payload["reserve_output_tokens"] == 3072
    assert payload["compact_at_tokens"] == 11200
    assert payload["hard_stop_at_tokens"] == 13000
    assert payload["max_response_tokens"] == 2048
    assert payload["checkpoint_format"] == "structured_json"
    assert payload["auto_compact"] is True
    assert payload["guardrail_status"] == "ok"
    assert payload["guardrail_issues"] == []


def test_guardrail_warnings_detect_bad_percentage_policy() -> None:
    bad_policy = RoleCapacityPercentages(
        reserve_output=0.05,
        compact_at=0.04,
        hard_stop_at=0.03,
        max_response=0.10,
    )
    budget = RoleContextBudget.from_capacity(
        role="Implementer",
        endpoint="http://127.0.0.1:8082",
        ctx_size=10000,
        percentages=bad_policy,
    )
    assert budget.guardrail_status == "warning"
    assert "compact_at_tokens should be greater than reserve_output_tokens" in budget.guardrail_issues
    assert "hard_stop_at_tokens should be greater than compact_at_tokens" in budget.guardrail_issues
    assert "max_response_tokens should not exceed reserve_output_tokens" in budget.guardrail_issues
