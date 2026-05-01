"""Admin endpoints for managing LLM provider configurations."""

import json
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_db
from app.api.auth import get_current_user
from app.models import User

router = APIRouter(tags=["admin"])

# Path to the dynamic providers config file
_PROVIDERS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "llm_providers.json")


def _require_admin(user: User) -> None:
    """Raise 403 if user is not admin."""
    if getattr(user, "role", "user") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


def _load_dynamic_providers() -> List[Dict[str, Any]]:
    """Load dynamic provider configs from JSON file."""
    if not os.path.exists(_PROVIDERS_FILE):
        return []
    try:
        with open(_PROVIDERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_dynamic_providers(providers: List[Dict[str, Any]]) -> None:
    """Save dynamic provider configs to JSON file."""
    with open(_PROVIDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(providers, f, ensure_ascii=False, indent=2)


# ── Schemas ──────────────────────────────────────────────────────────────────

class ProviderInput(BaseModel):
    id: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    base_url: str = Field(..., min_length=1)
    api_key: str = Field(..., min_length=1)
    custom_header: str = ""
    models: List[str] = Field(..., min_length=1)


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/providers")
async def list_providers_admin(current_user: User = Depends(get_current_user)):
    """List all LLM providers with full API keys (admin only)."""
    _require_admin(current_user)
    from app.core.config import get_llm_providers
    static = get_llm_providers()
    dynamic = _load_dynamic_providers()
    return {"providers": static + dynamic, "static_count": len(static), "dynamic_count": len(dynamic)}


@router.post("/providers")
async def add_provider(
    req: ProviderInput,
    current_user: User = Depends(get_current_user),
):
    """Add a new LLM provider (admin only)."""
    _require_admin(current_user)
    providers = _load_dynamic_providers()

    # Check for duplicate ID
    if any(p["id"] == req.id for p in providers):
        raise HTTPException(status_code=409, detail=f"Provider '{req.id}' already exists")

    providers.append(req.model_dump())
    _save_dynamic_providers(providers)
    return {"added": True, "id": req.id}


@router.put("/providers/{provider_id}")
async def update_provider(
    provider_id: str,
    req: ProviderInput,
    current_user: User = Depends(get_current_user),
):
    """Update an existing dynamic LLM provider (admin only)."""
    _require_admin(current_user)
    providers = _load_dynamic_providers()

    for i, p in enumerate(providers):
        if p["id"] == provider_id:
            providers[i] = req.model_dump()
            _save_dynamic_providers(providers)
            return {"updated": True, "id": provider_id}

    raise HTTPException(status_code=404, detail=f"Dynamic provider '{provider_id}' not found")


@router.delete("/providers/{provider_id}")
async def delete_provider(
    provider_id: str,
    current_user: User = Depends(get_current_user),
):
    """Delete a dynamic LLM provider (admin only)."""
    _require_admin(current_user)
    providers = _load_dynamic_providers()

    before = len(providers)
    providers = [p for p in providers if p["id"] != provider_id]
    if len(providers) == before:
        raise HTTPException(status_code=404, detail=f"Dynamic provider '{provider_id}' not found")

    _save_dynamic_providers(providers)
    return {"deleted": True, "id": provider_id}
