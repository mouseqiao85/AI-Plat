"""LLM Provider management: CRUD operations for llm_providers.json."""
import json
import logging
from pathlib import Path
from typing import Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

PROVIDERS_FILE = "./data/llm_providers.json"


class LLMProvider(BaseModel):
    id: str
    name: str
    base_url: str
    api_key: str = ""
    custom_header: str = ""
    models: list[str] = []
    is_default: bool = False
    enabled: bool = True


def _get_providers_path() -> Path:
    path = Path(PROVIDERS_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_providers() -> list[LLMProvider]:
    """Load all providers from JSON file."""
    path = _get_providers_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [LLMProvider(**p) for p in data]
    except Exception as e:
        logger.warning("failed to load providers: %s", e)
        return []


def save_providers(providers: list[LLMProvider]) -> None:
    """Save providers to JSON file."""
    path = _get_providers_path()
    data = [p.model_dump() for p in providers]
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def get_provider(provider_id: str) -> Optional[LLMProvider]:
    """Get a provider by ID."""
    providers = load_providers()
    for p in providers:
        if p.id == provider_id:
            return p
    return None


def add_provider(provider: LLMProvider) -> LLMProvider:
    """Add a new provider."""
    providers = load_providers()
    # Check for duplicate ID
    for existing in providers:
        if existing.id == provider.id:
            raise ValueError(f"Provider with id '{provider.id}' already exists")
    providers.append(provider)
    save_providers(providers)
    return provider


def update_provider(provider_id: str, updates: dict) -> Optional[LLMProvider]:
    """Update an existing provider."""
    providers = load_providers()
    for i, p in enumerate(providers):
        if p.id == provider_id:
            data = p.model_dump()
            data.update(updates)
            providers[i] = LLMProvider(**data)
            save_providers(providers)
            return providers[i]
    return None


def delete_provider(provider_id: str) -> bool:
    """Delete a provider by ID."""
    providers = load_providers()
    original_len = len(providers)
    providers = [p for p in providers if p.id != provider_id]
    if len(providers) == original_len:
        return False
    save_providers(providers)
    return True
