from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import (
    AIProviderSettingsInput, AIProviderSettingsOut, DraftPlanInput, DraftPlanOut,
    PlanningAssistantInput, PlanningAssistantOut,
)
from app.services.ai_planner import generate_plan
from app.services.ai_assistant import respond
from app.services.ai_provider_keys import public_status, update_user_keys, credentials_for_user
from app.services.llm_gateway import AIConfigurationMissing, AIProviderUnavailable

router = APIRouter(prefix="/api/ai", tags=["AI planning"])


@router.get("/settings", response_model=AIProviderSettingsOut)
def get_ai_settings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return public_status(db, user)


@router.put("/settings", response_model=AIProviderSettingsOut)
def save_ai_settings(
    payload: AIProviderSettingsInput,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        return update_user_keys(
            db, user,
            gemini_api_key=payload.gemini_api_key,
            groq_api_key=payload.groq_api_key,
            clear_gemini=payload.clear_gemini,
            clear_groq=payload.clear_groq,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _ai_error(exc: Exception) -> HTTPException:
    if isinstance(exc, AIConfigurationMissing):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, AIProviderUnavailable):
        return HTTPException(status_code=503, detail=str(exc))
    # Schema/guardrail failures are not disguised as valid AI suggestions.
    return HTTPException(status_code=502, detail="The AI response did not pass validation. Please try again.")


@router.post("/draft-plan", response_model=DraftPlanOut)
def draft_plan(payload: DraftPlanInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # This endpoint only creates a draft response; it never mutates saved workspace data.
    try:
        credentials = credentials_for_user(db, user)
        return generate_plan(payload, credentials)
    except Exception as exc:
        raise _ai_error(exc) from exc


@router.post("/assistant", response_model=PlanningAssistantOut)
def planning_assistant(
    payload: PlanningAssistantInput,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # The assistant recommends and drafts only; saving tasks is a separate explicit user action.
    try:
        credentials = credentials_for_user(db, user)
        return respond(payload, credentials)
    except Exception as exc:
        raise _ai_error(exc) from exc
