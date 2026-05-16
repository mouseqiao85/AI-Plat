"""Admin API routes: LLM Provider CRUD."""
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.core.providers import (
    LLMProvider,
    load_providers,
    get_provider,
    add_provider,
    update_provider,
    delete_provider,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


class ProviderCreateRequest(BaseModel):
    id: str
    name: str
    base_url: str
    api_key: str = ""
    custom_header: Optional[str] = None
    models: list[str] = []
    is_default: bool = False
    enabled: bool = True


class ProviderUpdateRequest(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    custom_header: Optional[str] = None
    models: Optional[list[str]] = None
    is_default: Optional[bool] = None
    enabled: Optional[bool] = None


@router.get("/providers")
async def list_providers():
    """List all LLM providers."""
    providers = load_providers()
    # Mask API keys in response
    result = []
    for p in providers:
        data = p.model_dump()
        if data.get("api_key"):
            data["api_key"] = data["api_key"][:4] + "****"
        result.append(data)
    return result


@router.get("/providers/{provider_id}")
async def get_provider_detail(provider_id: str):
    """Get a specific provider."""
    provider = get_provider(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider not found: {provider_id}")
    data = provider.model_dump()
    if data.get("api_key"):
        data["api_key"] = data["api_key"][:4] + "****"
    return data


@router.post("/providers")
async def create_provider(request: ProviderCreateRequest):
    """Create a new LLM provider."""
    try:
        provider = LLMProvider(**request.model_dump())
        add_provider(provider)
        return {"status": "created", "id": provider.id}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.put("/providers/{provider_id}")
async def update_provider_route(provider_id: str, request: ProviderUpdateRequest):
    """Update an existing LLM provider."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    provider = update_provider(provider_id, updates)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider not found: {provider_id}")
    return {"status": "updated", "id": provider_id}


@router.delete("/providers/{provider_id}")
async def delete_provider_route(provider_id: str):
    """Delete a LLM provider."""
    if not delete_provider(provider_id):
        raise HTTPException(status_code=404, detail=f"Provider not found: {provider_id}")
    return {"status": "deleted", "id": provider_id}
