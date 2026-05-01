import logging
import warnings
from pydantic_settings import BaseSettings
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

_VALID_ENVS = ("development", "staging", "production")


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "超级助理"
    APP_ENV: str = "development"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./agent_dev.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # LLM (OpenAI-compatible)
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""
    LLM_MODEL: str = "glm-5-openclaw"
    LLM_CUSTOM_HEADER: str = ""

    # DeepSeek
    LLM_DEEPSEEK_API_KEY: str = "sk-b30d528e0f8f42988cf2ac89f6008b44"
    LLM_DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 10080  # 7 days

    # Brave Search API
    BRAVE_API_KEY: str = ""
    BRAVE_API_IPS: str = ""  # Optional comma-separated IPv4 fallback list

    # Tushare (stock data)
    TUSHARE_TOKEN: str = ""

    # Wenxin / BCE (Baidu AI)
    WENXIN_API_KEY: str = ""

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 20
    AUTH_RATE_LIMIT_PER_MINUTE: int = 5
    FREE_DAILY_CHAT_LIMIT: int = 20

    # Cache TTL (seconds)
    CACHE_TTL_SHORT: int = 30
    CACHE_TTL_MID: int = 300
    CACHE_TTL_LONG: int = 3600

    # Agent timeouts (seconds)
    LLM_TIMEOUT: int = 300           # per LLM API call
    TOOL_TIMEOUT: int = 300          # per tool execution
    REQUEST_TIMEOUT: int = 1800       # overall chat request wall-clock limit (30min for deep research)

    # Auto-Compact
    COMPACT_TOKEN_THRESHOLD: int = 24000   # token threshold to trigger mid-session compression
    COMPACT_RECENT_KEEP: int = 6           # number of recent message pairs to keep after compression

    # File download (超长报告/HTML → 生成文件)
    FILE_DOWNLOAD_DIR: str = "./tmp/generated_files"
    FILE_DOWNLOAD_TTL: int = 3600     # Redis key TTL in seconds
    FILE_DOWNLOAD_THRESHOLD: int = 2000  # chars threshold to trigger file generation

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    def model_post_init(self, __context) -> None:
        # APP_ENV validation
        if self.APP_ENV not in _VALID_ENVS:
            raise ValueError(
                f"APP_ENV must be one of {_VALID_ENVS}, got '{self.APP_ENV}'"
            )

        # Auto-enable DEBUG in development
        if self.APP_ENV == "development":
            self.DEBUG = True

        # JWT secret warning / enforcement
        if self.JWT_SECRET_KEY == "change-me-in-production":
            if self.APP_ENV != "development":
                raise ValueError(
                    "JWT_SECRET_KEY must be changed from default in production/staging"
                )
            warnings.warn(
                "JWT_SECRET_KEY is using the default value. "
                "Set a strong secret in .env before deploying.",
                stacklevel=2,
            )
            logger.warning("jwt_secret_using_default_value")

        # Critical field warnings
        if not self.LLM_API_KEY:
            logger.warning("LLM_API_KEY is not set; chat will fail")
        if not self.LLM_BASE_URL:
            logger.warning("LLM_BASE_URL is not set; chat will fail")


settings = Settings()


def _load_dynamic_providers() -> list:
    """Load dynamic provider configs from llm_providers.json."""
    import json, os
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "llm_providers.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def get_llm_providers() -> List[Dict[str, Any]]:
    """Return available LLM providers (static config + dynamic overrides)."""
    providers = [
        {
            "id": "default",
            "name": "默认模型",
            "base_url": settings.LLM_BASE_URL,
            "api_key": settings.LLM_API_KEY,
            "custom_header": settings.LLM_CUSTOM_HEADER,
            "models": [settings.LLM_MODEL],
        },
    ]
    if settings.LLM_DEEPSEEK_API_KEY:
        providers.append({
            "id": "deepseek",
            "name": "DeepSeek",
            "base_url": settings.LLM_DEEPSEEK_BASE_URL,
            "api_key": settings.LLM_DEEPSEEK_API_KEY,
            "custom_header": "",
            "models": ["deepseek-v4-flash", "deepseek-v4-pro"],
        })
    # Merge dynamic providers from admin config file
    for dp in _load_dynamic_providers():
        # If ID matches a static provider, override it
        existing = next((p for p in providers if p["id"] == dp["id"]), None)
        if existing:
            existing.update({k: v for k, v in dp.items() if k != "id"})
        else:
            providers.append(dp)
    return providers
