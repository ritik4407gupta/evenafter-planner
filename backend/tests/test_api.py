from fastapi.testclient import TestClient
from app.main import app


def login(client, email="hello@everafter.app", password="EverAfter2026!"):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_private_routes_require_authentication():
    with TestClient(app) as client:
        response = client.get("/api/events")
        assert response.status_code == 401


def test_demo_user_can_load_persisted_workspace():
    with TestClient(app) as client:
        headers = login(client)
        response = client.get("/api/events", headers=headers)
        assert response.status_code == 200
        assert response.json(), "Development seed should provide a demo event"
        event_id = response.json()[0]["id"]
        dash = client.get(f"/api/dashboard/{event_id}", headers=headers)
        assert dash.status_code == 200
        data = dash.json()
        assert data["tasks"]["total"] >= 1
        assert data["budget"]["limit"] > 0


def test_users_cannot_read_another_users_event():
    with TestClient(app) as client:
        first_headers = login(client)
        created = client.post("/api/auth/register", json={
            "name": "Test Owner", "email": "ownership-check@example.com", "password": "Correct-Horse-72!"
        })
        if created.status_code == 409:
            second = client.post("/api/auth/login", json={"email": "ownership-check@example.com", "password": "Correct-Horse-72!"})
            assert second.status_code == 200
            second_token = second.json()["access_token"]
        else:
            assert created.status_code == 201, created.text
            second_token = created.json()["access_token"]
        second_headers = {"Authorization": f"Bearer {second_token}"}
        event_response = client.post("/api/events", headers=second_headers, json={
            "title": "Private Test Event", "event_type": "Birthday", "guest_count": 24,
            "budget": 40000, "theme": "Little garden party", "location": "Delhi"
        })
        assert event_response.status_code == 201, event_response.text
        event_id = event_response.json()["id"]
        forbidden = client.get(f"/api/events/{event_id}", headers=first_headers)
        assert forbidden.status_code == 404
        forbidden_dash = client.get(f"/api/dashboard/{event_id}", headers=first_headers)
        assert forbidden_dash.status_code == 404


def ai_user(client, email="ai-setup-test@example.com", password="Strong-AI-Password-823!"):
    registered = client.post("/api/auth/register", json={"name": "AI Settings Test", "email": email, "password": password})
    if registered.status_code == 201:
        token = registered.json()["access_token"]
    else:
        assert registered.status_code == 409, registered.text
        login_response = client.post("/api/auth/login", json={"email": email, "password": password})
        assert login_response.status_code == 200, login_response.text
        token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_ai_draft_requires_real_provider_key_not_template():
    with TestClient(app) as client:
        headers = ai_user(client)
        # Test is repeatable: remove credentials left by an earlier run.
        client.put("/api/ai/settings", headers=headers, json={"clear_gemini": True, "clear_groq": True})
        response = client.post("/api/ai/draft-plan", headers=headers, json={
            "event_type": "Wedding", "budget": 150000, "guest_count": 60,
            "theme": "Soft garden romance", "location": "Gurugram", "priorities": ["Accessible for everyone"]
        })
        assert response.status_code == 400, response.text
        assert "Gemini API key" in response.json()["detail"]


def test_assistant_requires_ai_credentials_and_does_not_show_canned_suggestions():
    with TestClient(app) as client:
        headers = ai_user(client, email="ai-missing-key@example.com")
        client.put("/api/ai/settings", headers=headers, json={"clear_gemini": True, "clear_groq": True})
        response = client.post("/api/ai/assistant", headers=headers, json={
            "message": "Help me stay on budget and build a vendor checklist",
            "event_type": "Wedding", "event_title": "A thoughtful wedding",
            "budget": 220000, "guest_count": 70, "theme": "Blush garden",
            "location": "Delhi NCR", "existing_tasks": ["Draft guest list"]
        })
        assert response.status_code == 400, response.text
        assert "Gemini API key" in response.json()["detail"]
        assert "suggestions" not in response.json()


def test_ai_provider_keys_are_encrypted_masked_and_account_scoped():
    from app.database import SessionLocal
    from app.models import User, UserAIProviderKeys
    from sqlalchemy import select
    with TestClient(app) as client:
        headers = ai_user(client, email="ai-encryption-test@example.com")
        # Reset to avoid a previous run changing this assertion.
        client.put("/api/ai/settings", headers=headers, json={"clear_gemini": True, "clear_groq": True})
        saved = client.put("/api/ai/settings", headers=headers, json={
            "gemini_api_key": "AIzaSyDemoGeminiKey1234567890",
            "groq_api_key": "gsk_demoGroqKey1234567890",
        })
        assert saved.status_code == 200, saved.text
        body = saved.json()
        assert body["ai_enabled"] is True
        assert body["gemini_configured"] is True and body["groq_configured"] is True
        assert body["gemini_masked"].endswith("7890")
        assert "AIzaSyDemoGeminiKey1234567890" not in saved.text
        db = SessionLocal()
        try:
            user = db.scalar(select(User).where(User.email == "ai-encryption-test@example.com"))
            record = db.scalar(select(UserAIProviderKeys).where(UserAIProviderKeys.user_id == user.id))
            assert record.gemini_key_encrypted != "AIzaSyDemoGeminiKey1234567890"
            assert record.groq_key_encrypted != "gsk_demoGroqKey1234567890"
        finally:
            db.close()
        # Another account must not inherit this key configuration.
        other = ai_user(client, email="ai-other-account@example.com")
        status = client.get("/api/ai/settings", headers=other)
        assert status.status_code == 200
        assert status.json()["gemini_configured"] is False
        assert status.json()["groq_configured"] is False


def test_provider_key_settings_never_return_full_keys_and_can_be_removed():
    with TestClient(app) as client:
        headers = ai_user(client, email="ai-key-removal@example.com")
        client.put("/api/ai/settings", headers=headers, json={"clear_gemini": True, "clear_groq": True})
        response = client.put("/api/ai/settings", headers=headers, json={"gemini_api_key": "AIzaExampleKeyValue123456"})
        assert response.status_code == 200
        assert "AIzaExampleKeyValue123456" not in response.text
        removed = client.put("/api/ai/settings", headers=headers, json={"clear_gemini": True})
        assert removed.status_code == 200
        assert removed.json()["ai_enabled"] is False


def test_relogin_restores_same_account_events():
    with TestClient(app) as client:
        email = "persistence-roundtrip@example.com"
        password = "Strong-Password-823!"
        registered = client.post("/api/auth/register", json={"name": "Persistence Test", "email": email, "password": password})
        if registered.status_code == 409:
            logged = client.post("/api/auth/login", json={"email": email, "password": password})
            assert logged.status_code == 200
            token = logged.json()["access_token"]
        else:
            assert registered.status_code == 201, registered.text
            token = registered.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        created = client.post("/api/events", headers=headers, json={
            "title": "Saved Birthday", "event_type": "Birthday", "guest_count": 22,
            "budget": 35000, "theme": "Warm lights", "location": "Gurugram"
        })
        assert created.status_code == 201, created.text
        first_id = created.json()["id"]
        # Authenticate again with credentials; the stored event must remain linked to the same user.
        relogin = client.post("/api/auth/login", json={"email": email, "password": password})
        assert relogin.status_code == 200
        relogin_headers = {"Authorization": f"Bearer {relogin.json()['access_token']}"}
        events = client.get("/api/events", headers=relogin_headers)
        assert events.status_code == 200
        assert any(event["id"] == first_id for event in events.json())
