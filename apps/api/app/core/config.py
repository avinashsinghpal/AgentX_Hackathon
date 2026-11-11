from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Kept for local development only.  It is rejected outside development/testing.
INSECURE_SECRET_DEFAULT = "dev-insecure-secret-key-change-in-production-1234567890"

DEFAULT_DATABASE_URL = (
    "postgresql+psycopg://sellerresolve:buntykishunty@localhost:5432/sellerresolve"
)


class Settings(BaseSettings):
    ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = INSECURE_SECRET_DEFAULT

    # PostgreSQL is the default development database.  SQLite stays supported
    # for isolated tests (sqlite:///:memory:) and existing local workflows.
    DATABASE_URL: str = DEFAULT_DATABASE_URL

    # Connection pool (ignored for SQLite, which uses StaticPool for :memory:).
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    DB_ECHO: bool = False
    DB_USE_NULL_POOL: bool = False

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

    GEMINI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    LLM_PROVIDER: str = "fake"
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

    @model_validator(mode="after")
    def validate_secret_key(self) -> "Settings":
        env = (self.ENV or "development").lower()
        if env in {"production", "prod", "staging"}:
            if self.SECRET_KEY == INSECURE_SECRET_DEFAULT or len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "SECRET_KEY must be explicitly configured with at least 32 characters "
                    "outside development/testing. Refusing to start with the development default."
                )
        return self


settings = Settings()
