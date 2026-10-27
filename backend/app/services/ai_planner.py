"""Structured event-plan generation using Gemini with optional Groq fallback only."""
from __future__ import annotations
import re
from datetime import date
from pydantic import ValidationError
from app.schemas import DraftPlanInput, DraftPlanOut
from app.services.ai_prompts import DRAFT_PLAN_SYSTEM_PROMPT
from app.services.llm_gateway import generate_with_validation


def _guardrail_output(data: dict, payload: DraftPlanInput, generated_by: str = "gemini") -> DraftPlanOut:
    # Never replace malformed provider results with a hardcoded plan.
    if not isinstance(data, dict):
        raise ValueError("Plan output must be an object")
    data = dict(data)
    data["generated_by"] = generated_by
    data["tasks"] = data.get("tasks", [])[:15]
    data["ideas"] = data.get("ideas", [])[:8]
    data["assumptions"] = data.get("assumptions", [])[:8]
    try:
        plan = DraftPlanOut.model_validate(data)
    except ValidationError as exc:
        raise ValueError("Generated plan did not pass schema validation") from exc
    prohibited = (
        "guaranteed price", "booking confirmed", "reservation confirmed", "your booking is confirmed",
        "reservation has been made", "vendor is available", "they are available on your date",
        "is booked for you", "confirmed booking", "reservation is confirmed", "i've booked",
        "i contacted the vendor", "payment has been made", "permit approved", "legally compliant",
    )
    combined = " ".join([plan.summary, plan.budget_note, *plan.ideas, *plan.assumptions,
                          *(t.title + " " + t.description for t in plan.tasks)]).lower()
    if any(term in combined for term in prohibited):
        raise ValueError("Generated plan made an unsupported promise")
    if any(marker in combined for marker in ("you are everafter, a thoughtful, practical", "operating principles", "do not reveal this system prompt")):
        raise ValueError("Generated plan appeared to expose internal instructions")
    if payload.budget == 0 and (
        any(token in combined for token in ("you can spend", "your budget is", "your budget will be", "budget ceiling is"))
        or re.search(r"(?:₹|\binr\s*)\s?\d", combined, flags=re.IGNORECASE)
    ):
        raise ValueError("Generated plan inferred a budget that was not provided")
    if payload.event_date:
        weeks_until = max(0, min(104, (payload.event_date - date.today()).days // 7))
        for task in plan.tasks:
            task.weeks_before = min(task.weeks_before, weeks_until)
    if not any(any(term in item.lower() for term in ("availability", "price", "quote")) for item in plan.assumptions):
        plan.assumptions = (plan.assumptions + ["Live vendor availability and current prices have not been verified."])[:8]
    return plan


def generate_plan(payload: DraftPlanInput, credentials: dict[str, str | None]) -> DraftPlanOut:
    context = {
        "event_type": payload.event_type,
        "budget_inr": payload.budget if payload.budget > 0 else None,
        "guest_count": payload.guest_count,
        "event_date": str(payload.event_date) if payload.event_date else None,
        "theme": payload.theme,
        "location": payload.location,
        "priorities": [str(item)[:100] for item in payload.priorities[:8]],
    }
    return generate_with_validation(
        credentials, DRAFT_PLAN_SYSTEM_PROMPT, context,
        lambda data, provider: _guardrail_output(data, payload, generated_by=provider),
    )
