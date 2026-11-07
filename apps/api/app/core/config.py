from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "dev-insecure-secret-key-change-in-production-1234567890"

    DATABASE_URL: str = "sqlite:///./sellerresolve.db"

    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]

    SESSION_EXPIRY_SECONDS: int = 60 * 60 * 24 * 7  # 7 days
    SESSION_IDLE_SECONDS: int = 60 * 60 * 24  # 24 hours

    MAX_UPLOAD_BYTES: int = 5 * 1024 * 1024  # 5 MB
    UPLOAD_DIR: str = "./uploads"

    SEED_DEMO: bool = False

    ANTHROPIC_API_KEY: str | None = None
    LLM_MODEL: str = "claude-3-5-sonnet-20241022"

    SMTP_HOST: str | None = None
    SMTP_PORT: int | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None

    PROACTIVE_MONITOR_INTERVAL_MINUTES: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
