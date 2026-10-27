"""Per-account AI provider key storage.

Keys are encrypted before persistence and are never returned to the browser in full.
Set AI_KEYS_ENCRYPTION_KEY in production; the development fallback derives a key from
JWT_SECRET so a fresh local install remains easy to run.
"""
from __future__ import annotations

import base64
import hashlib
from sqlalchemy import select
from sqlalchemy.orm import Session
from cryptography.fernet import Fernet, InvalidToken
from app.config import settings
from app.models import UserAIProviderKeys, User


def _fernet() -> Fernet:
    configured = settings.ai_keys_encryption_key.strip()
    if configured:
        try:
            return Fernet(configured.encode("utf-8"))
        except (ValueError, TypeError) as exc:
            raise RuntimeError("AI_KEYS_ENCRYPTION_KEY must be a valid Fernet key.") from exc
    if settings.environment.lower() == "production":
        raise RuntimeError("AI_KEYS_ENCRYPTION_KEY must be explicitly set in production.")
    # Development convenience only; production requires a dedicated encryption key.
    digest = hashlib.sha256(("everafter-provider-key-encryption:" + settings.jwt_secret).encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_api_key(value: str | None) -> str | None:
    cleaned = (value or "").strip()
    if not cleaned:
        return None
    return _fernet().encrypt(cleaned.encode("utf-8")).decode("ascii")


def decrypt_api_key(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return _fernet().decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, UnicodeDecodeError) as exc:
        raise RuntimeError("Stored AI credentials could not be decrypted. Check AI_KEYS_ENCRYPTION_KEY.") from exc


def get_or_create_record(db: Session, user: User) -> UserAIProviderKeys:
    record = db.scalar(select(UserAIProviderKeys).where(UserAIProviderKeys.user_id == user.id))
    if record is None:
        record = UserAIProviderKeys(user_id=user.id)
        db.add(record)
        db.commit()
        db.refresh(record)
    return record


def credentials_for_user(db: Session, user: User) -> dict[str, str | None]:
    record = get_or_create_record(db, user)
    return {
        "gemini": decrypt_api_key(record.gemini_key_encrypted),
        "groq": decrypt_api_key(record.groq_key_encrypted),
    }


def masked(value: str | None) -> str | None:
    if not value:
        return None
    return f"••••••••{value[-4:]}"


def public_status(db: Session, user: User) -> dict:
    credentials = credentials_for_user(db, user)
    gemini = credentials["gemini"]
    groq = credentials["groq"]
    # Gemini is the required primary provider. Groq is used only as a fallback.
    return {
        "gemini_configured": bool(gemini),
        "gemini_masked": masked(gemini),
        "groq_configured": bool(groq),
        "groq_masked": masked(groq),
        "ai_enabled": bool(gemini),
        "primary_provider": "gemini" if gemini else "none",
        "fallback_provider": "groq" if gemini and groq else "none",
    }


def update_user_keys(
    db: Session,
    user: User,
    *,
    gemini_api_key: str | None = None,
    groq_api_key: str | None = None,
    clear_gemini: bool = False,
    clear_groq: bool = False,
) -> dict:
    record = get_or_create_record(db, user)
    # Empty strings mean "leave the current key unchanged". Explicit clear flags remove it.
    if clear_gemini:
        record.gemini_key_encrypted = None
    elif gemini_api_key and gemini_api_key.strip():
        record.gemini_key_encrypted = encrypt_api_key(gemini_api_key)
    if clear_groq:
        record.groq_key_encrypted = None
    elif groq_api_key and groq_api_key.strip():
        record.groq_key_encrypted = encrypt_api_key(groq_api_key)
    db.add(record)
    db.commit()
    db.refresh(record)
    return public_status(db, user)
