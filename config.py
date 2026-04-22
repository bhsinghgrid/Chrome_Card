"""
config.py — All settings loaded from environment variables.
App fails loudly at startup if anything is missing.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # ── Google OAuth ──────────────────────────────────────────────
    google_client_id: str = Field(..., validation_alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(..., validation_alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(
        default="http://localhost:8080/",
        validation_alias="GOOGLE_REDIRECT_URI",
    )
    # Scopes we need — read+write calendar, read+send gmail
    google_scopes: list[str] = [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.readonly",
    ]

    # ── Token storage (swap for encrypted DB in production) ───────
    token_path: str = Field(default="token.json", validation_alias="TOKEN_PATH")

    # ── Redis ─────────────────────────────────────────────────────
    redis_url: str = Field(default="redis://localhost:6379/0", validation_alias="REDIS_URL")
    cache_ttl_seconds: int = Field(default=300, validation_alias="CACHE_TTL")  # 5 min

    # ── MCP server ────────────────────────────────────────────────
    mcp_host: str = Field(default="0.0.0.0", validation_alias="MCP_HOST")
    mcp_port: int = Field(default=8001, validation_alias="MCP_PORT")
    mcp2_host: str = Field(default="127.0.0.1", validation_alias="MCP2_HOST")
    mcp2_port: int = Field(default=8002, validation_alias="MCP2_PORT")

    # ── LLM ───────────────────────────────────────────────────────
    gemini_api_key: str = Field(..., validation_alias="GEMINI_API_KEY")
    llm_model: str = Field(default="gemini-2.5-pro", validation_alias="LLM_MODEL")
    llm_max_iterations: int = Field(default=10, validation_alias="LLM_MAX_ITERATIONS")

    # ── Timezone ──────────────────────────────────────────────────
    default_timezone: str = Field(default="Asia/Kolkata", validation_alias="DEFAULT_TIMEZONE")
    email_delay_minutes: int = Field(default=5, validation_alias="EMAIL_DELAY_MINUTES")

    # ── Logging ───────────────────────────────────────────────────
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")


# Single global instance — import this everywhere
settings = Settings()
