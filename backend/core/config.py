from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Support Copilot"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production-use-secrets-generate"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str = "sqlite:///./support_copilot.db"

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./chroma_db"

    # mem0
    MEM0_API_KEY: Optional[str] = None

    # Email (SendGrid)
    SENDGRID_API_KEY: Optional[str] = None
    FROM_EMAIL: str = "support@yourdomain.com"

    # Twilio (WhatsApp)
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_WHATSAPP_NUMBER: Optional[str] = None

    # Slack
    SLACK_BOT_TOKEN: Optional[str] = None
    SLACK_SIGNING_SECRET: Optional[str] = None

    # Redis (for Celery / SLA tasks)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Frontend URL (for CORS)
    FRONTEND_URL: str = "http://localhost:3000"

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production", "false", "0", "no", "off"}:
                return False
            if normalized in {"debug", "dev", "development", "true", "1", "yes", "on"}:
                return True
        return value

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
