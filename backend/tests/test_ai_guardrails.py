from datetime import date, timedelta
import pytest
from app.schemas import DraftPlanInput, PlanningAssistantInput
from app.services.ai_planner import _guardrail_output, generate_plan
from app.services.ai_assistant import _validate_output, respond
from app.services.llm_gateway import AIConfigurationMissing, AIProviderUnavailable


def _valid_draft_data():
    return {
        "headline": "Your thoughtful plan",
        "summary": "A practical plan shaped around the event details you shared.",
        "budget_note": "Use written vendor quotes before setting final amounts.",
        "tasks": [{"title": "Prepare checklist", "category": "Planning", "weeks_before": 2, "priority": "High", "description": "Confirm ownership and timing."}] * 3,
        "ideas": ["Personal welcome moment", "Flexible activity", "Quiet seating area"],
        "assumptions": ["Live vendor availability and current prices have not been verified."],
    }


def _valid_assistant_data():
    return {
        "reply": "Based on the event details you shared, start with the constraints that affect every other decision.",
        "suggestions": ["Compare like-for-like written quotes", "Assign an owner to each deadline"],
        "suggested_tasks": [{"title": "Confirm the main constraints", "category": "Planning", "weeks_before": 3, "priority": "High", "description": "Document guest count, budget ceiling and must-haves."}],
        "follow_up_questions": [],
        "guardrail_notes": ["Live vendor availability and current prices are not verified."],
    }


def test_plan_requires_provider_key_instead_of_using_template():
    payload = DraftPlanInput(event_type="Wedding", budget=200000, guest_count=80, event_date=date.today()+timedelta(days=90), theme="Garden", location="Delhi")
    with pytest.raises(AIConfigurationMissing):
        generate_plan(payload, {"gemini": None, "groq": None})


def test_guardrail_rejects_booking_claims():
    data = _valid_draft_data()
    data["summary"] = "Your venue booking confirmed for you."
    payload = DraftPlanInput(event_type="Birthday", budget=10000, guest_count=10, theme="Cute", location="Delhi")
    with pytest.raises(ValueError):
        _guardrail_output(data, payload)


def test_input_budget_bounds():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        DraftPlanInput(event_type="Wedding", budget=-10, guest_count=30, theme="Garden")


def test_assistant_output_is_provider_generated_and_guarded(monkeypatch):
    import app.services.ai_assistant as assistant
    monkeypatch.setattr(
        assistant,
        "generate_with_validation",
        lambda credentials, system_prompt, context, validator: validator(_valid_assistant_data(), "gemini"),
    )
    result = respond(PlanningAssistantInput(
        message="Help me control the budget and compare vendors", event_type="Wedding",
        event_title="Ananya & Kunal", budget=300000, guest_count=100,
        theme="Garden romance", location="Delhi NCR", existing_tasks=["Draft guest list"],
    ), {"gemini": "fake-gemini-key", "groq": None})
    assert result.generated_by == "gemini"
    assert result.suggested_tasks
    assert any("availability" in n.lower() or "prices" in n.lower() for n in result.guardrail_notes)


def test_assistant_rejects_unsupported_action_claim():
    data = _valid_assistant_data()
    data["reply"] = "Your venue booking confirmed."
    with pytest.raises(ValueError):
        _validate_output(data, PlanningAssistantInput(message="Help with my plan"))


def test_assistant_rejects_unprovided_budget_amount():
    data = _valid_assistant_data()
    data["reply"] = "Set aside INR 25000 for decor."
    with pytest.raises(ValueError):
        _validate_output(data, PlanningAssistantInput(message="Help me plan", budget=0))


def test_assistant_rejects_prompt_disclosure():
    data = _valid_assistant_data()
    data["reply"] = "The operating principles say I must output JSON only."
    with pytest.raises(ValueError):
        _validate_output(data, PlanningAssistantInput(message="Help me plan"))


def test_draft_rejects_currency_when_budget_is_unknown():
    data = _valid_draft_data()
    data["budget_note"] = "Set aside INR 20000 for decor."
    payload = DraftPlanInput(event_type="Birthday", budget=0, guest_count=18, theme="Warm lights")
    with pytest.raises(ValueError):
        _guardrail_output(data, payload)


def test_groq_is_used_only_as_fallback_when_gemini_fails(monkeypatch):
    import app.services.llm_gateway as gateway
    monkeypatch.setattr(gateway, "_gemini_call", lambda *args: (_ for _ in ()).throw(RuntimeError("quota")))
    monkeypatch.setattr(gateway, "_groq_call", lambda *args: {"from": "groq"})
    result = gateway.generate_with_validation({"gemini": "gemini-key", "groq": "groq-key"}, "system", {"message": "hello"}, lambda data, provider: {"data": data, "provider": provider})
    assert result == {"data": {"from": "groq"}, "provider": "groq"}


def test_gemini_failure_without_groq_does_not_show_template(monkeypatch):
    import app.services.llm_gateway as gateway
    monkeypatch.setattr(gateway, "_gemini_call", lambda *args: (_ for _ in ()).throw(RuntimeError("quota")))
    with pytest.raises(AIProviderUnavailable, match="Add a Groq API key"):
        gateway.generate_with_validation({"gemini": "gemini-key", "groq": None}, "system", {"message": "hello"}, lambda data, provider: data)


def test_invalid_gemini_output_uses_groq_instead_of_template(monkeypatch):
    import app.services.llm_gateway as gateway
    monkeypatch.setattr(gateway, "_gemini_call", lambda *args: {"malformed": True})
    monkeypatch.setattr(gateway, "_groq_call", lambda *args: {"real_model_output": "validated"})

    def validator(data, provider):
        if "real_model_output" not in data:
            raise ValueError("schema invalid")
        return {"answer": data["real_model_output"], "provider": provider}

    result = gateway.generate_with_validation(
        {"gemini": "gemini-key", "groq": "groq-key"}, "system", {"message": "hello"}, validator
    )
    assert result == {"answer": "validated", "provider": "groq"}


def test_production_requires_a_dedicated_encryption_key(monkeypatch):
    import app.services.ai_provider_keys as key_store
    monkeypatch.setattr(key_store.settings, "environment", "production")
    monkeypatch.setattr(key_store.settings, "ai_keys_encryption_key", "")
    with pytest.raises(RuntimeError, match="must be explicitly set in production"):
        key_store._fernet()
