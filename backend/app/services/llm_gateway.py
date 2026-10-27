"""Gemini-first JSON generation with Groq fallback and no template responses."""
from __future__ import annotations

import json
from typing import Any, Callable, TypeVar
import httpx

from app.config import settings

T = TypeVar("T")


class AIProviderUnavailable(RuntimeError):
    """A configured provider could not generate a valid response."""


class AIConfigurationMissing(RuntimeError):
    """Required account-level Gemini credentials are missing."""


def _parse_json_text(text: str) -> dict[str, Any]:
    # Models are instructed to return JSON; don't silently mine prose for fake results.
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("The AI provider returned invalid JSON.") from exc
    if not isinstance(data, dict):
        raise ValueError("The AI provider returned an unexpected response structure.")
    return data


def _gemini_call(api_key: str, system_prompt: str, context: dict[str, Any]) -> dict[str, Any]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
    body = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": json.dumps(context, ensure_ascii=False)}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.55, "maxOutputTokens": 2200},
    }
    try:
        with httpx.Client(timeout=httpx.Timeout(28.0, connect=8.0)) as client:
            response = client.post(url, headers={"x-goog-api-key": api_key}, json=body)
        if response.status_code >= 400:
            raise RuntimeError(f"Gemini returned HTTP {response.status_code}.")
        payload = response.json()
        candidates = payload.get("candidates") or []
        if not candidates:
            raise ValueError("Gemini returned no content.")
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
        if not text.strip():
            raise ValueError("Gemini returned empty content.")
        return _parse_json_text(text)
    except Exception as exc:
        raise RuntimeError("Gemini could not complete the request.") from exc


def _groq_call(api_key: str, system_prompt: str, context: dict[str, Any]) -> dict[str, Any]:
    body = {
        "model": settings.groq_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.55,
        "max_tokens": 2200,
    }
    try:
        with httpx.Client(timeout=httpx.Timeout(28.0, connect=8.0)) as client:
            response = client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=body,
            )
        if response.status_code >= 400:
            raise RuntimeError(f"Groq returned HTTP {response.status_code}.")
        payload = response.json()
        choices = payload.get("choices") or []
        if not choices:
            raise ValueError("Groq returned no content.")
        text = ((choices[0].get("message") or {}).get("content") or "").strip()
        if not text:
            raise ValueError("Groq returned empty content.")
        return _parse_json_text(text)
    except Exception as exc:
        raise RuntimeError("Groq could not complete the request.") from exc


def generate_with_validation(
    credentials: dict[str, str | None],
    system_prompt: str,
    context: dict[str, Any],
    validator: Callable[[dict[str, Any], str], T],
) -> T:
    """Return validated model output, using Groq if Gemini or its output fails.

    Missing credentials, provider errors, invalid JSON, schema errors, and guardrail
    rejection never cause a template response. They become explicit API errors instead.
    """
    gemini_key = credentials.get("gemini")
    groq_key = credentials.get("groq")
    if not gemini_key:
        raise AIConfigurationMissing("Add your Gemini API key in Settings to enable AI-generated suggestions.")
    try:
        return validator(_gemini_call(gemini_key, system_prompt, context), "gemini")
    except Exception as gemini_error:
        if not groq_key:
            raise AIProviderUnavailable(
                "Gemini could not answer or its response did not pass validation. Check your key, quota, and model access. "
                "Add a Groq API key in Settings to enable automatic fallback. No template suggestions were shown."
            ) from gemini_error
    try:
        return validator(_groq_call(groq_key, system_prompt, context), "groq")
    except Exception as groq_error:
        raise AIProviderUnavailable(
            "Neither Gemini nor Groq could produce a valid answer. Check both keys, model access, and provider quotas. "
            "No template suggestions were shown."
        ) from groq_error
