from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

class Settings(BaseSettings):
    PROJECT_NAME: str = "Birthday Builder API"
    PROJECT_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    DATABASE_URL: str
    SUPABASE_URL: str
    SUPABASE_KEY: str
    # Server-only key used exclusively by the authenticated upload service.
    SUPABASE_STORAGE_SERVICE_ROLE_KEY: str | None = None

    JWT_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    PERMANENT_ROLES: List[str] = ["admin", "super_admin"]
    SMTP_PASSWORD: str | None = None

    model_config = SettingsConfigDict(env_file=str(ENV_FILE))

try:
    settings = Settings()
except Exception as e:
    import sys
    print("=" * 60)
    print("❌ FATAL ERROR: Missing or Invalid Environment Variables!")
    print("Please make sure you have configured all required variables")
    print("such as DATABASE_URL, SUPABASE_URL, etc.")
    print(f"Details: {e}")
    print("=" * 60)
    sys.exit(1)
