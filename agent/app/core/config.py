import logging
import warnings
from pydantic_settings import BaseSettings
from typing import List

logger = logging.getLogger(__name__)

_VALID_ENVS = ("development", "staging", "production")


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Agent Service"
    APP_ENV: str = "development"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/agent_service.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # LLM (OpenAI-compatible)
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_CUSTOM_HEADER: str = ""

    # DeepSeek (dedicated API)
    LLM_DEEPSEEK_API_KEY: str = ""
    LLM_DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"

    # Go Gateway callback URL
    GO_CALLBACK_URL: str = "http://localhost:8080"

    # Service
    HOST: str = "0.0.0.0"
    PORT: int = 8001

    # JWT
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 10080

    # Dev token for Go gateway (from env, never committed)
    GO_DEV_TOKEN: str = ""

    # Brave Search API
    BRAVE_API_KEY: str = ""

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000", "http://localhost:8080"]

    # Agent timeouts (seconds)
    LLM_TIMEOUT: int = 300
    TOOL_TIMEOUT: int = 300
    REQUEST_TIMEOUT: int = 1800

    # Auto-Compact
    COMPACT_TOKEN_THRESHOLD: int = 24000
    COMPACT_RECENT_KEEP: int = 6

    # Session sandbox
    SANDBOX_ENABLED: bool = True
    SANDBOX_ROOT: str = ""

    # Skills
    SKILLS_DIR: str = "./skills"
    SKILL_SCRIPT_TIMEOUT: int = 30

    # Memory
    MEMORY_TTL_DAYS: int = 90

    # Tool loop
    MAX_ITERATIONS: int = 80

    # File generation
    GENERATED_FILES_DIR: str = "./data/generated"

    # Cache TTL
    CACHE_TTL_SHORT: int = 30
    CACHE_TTL_MID: int = 300
    CACHE_TTL_LONG: int = 3600

    model_config = {
        "env_file": (".env", "../.env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    def model_post_init(self, __context) -> None:
        if self.APP_ENV not in _VALID_ENVS:
            raise ValueError(f"APP_ENV must be one of {_VALID_ENVS}, got '{self.APP_ENV}'")
        if self.APP_ENV == "development":
            self.DEBUG = True
        if self.JWT_SECRET_KEY == "change-me-in-production" and self.APP_ENV != "development":
            raise ValueError("JWT_SECRET_KEY must be changed from default in production")
        if not self.LLM_API_KEY:
            logger.warning("LLM_API_KEY is not set; chat will fail")
        if not self.LLM_BASE_URL:
            logger.warning("LLM_BASE_URL is not set; chat will fail")


settings = Settings()
