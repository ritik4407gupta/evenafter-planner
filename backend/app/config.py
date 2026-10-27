from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "EverAfter"
    environment: str = "development"
    database_url: str = "sqlite:///./everafter.db"
    jwt_secret: str = "dev-only-change-me-please-32-characters"
    jwt_expire_minutes: int = 1440
    frontend_origin: str = "http://localhost:5173"
    # Per-user provider keys are entered in Settings; keys are encrypted at rest.
    ai_keys_encryption_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    groq_model: str = "openai/gpt-oss-120b"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
