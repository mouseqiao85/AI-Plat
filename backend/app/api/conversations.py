"""Conversations API

GET    /api/v1/conversations/              — list current user's conversations (latest first)
GET    /api/v1/conversations/{id}/messages — load message history of a conversation
PATCH  /api/v1/conversations/{id}          — rename a conversation
DELETE /api/v1/conversations/{id}          — delete a conversation and its messages
GET    /api/v1/conversations/user-profile  — get the user's long-term memory profile
DELETE /api/v1/conversations/user-profile  — clear the user's long-term memory profile
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.api.auth import get_current_user
from app.core.dependencies import get_db, get_redis_client
from app.models import User, Conversation, Message

router = APIRouter(tags=["conversations"])


# ── Schemas ─────────────────────────────────────────────────────────────────

class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: str
    updated_at: str


class MessageOut(BaseModel):
    id: int
    role: str
    content: Optional[str]
    created_at: str


class RenameRequest(BaseModel):
    title: str


# ── Helpers ──────────────────────────────────────────────────────────────────

def _conv_out(conv: Conversation) -> ConversationOut:
    return ConversationOut(
        id=conv.id,
        title=conv.title or "新对话",
        created_at=conv.created_at.isoformat() if conv.created_at else "",
        updated_at=conv.updated_at.isoformat() if conv.updated_at else "",
    )


async def _get_conv_or_404(
    conv_id: int, user_id: int, db: AsyncSession
) -> Conversation:
    stmt = select(Conversation).where(
        Conversation.id == conv_id,
        Conversation.user_id == user_id,
    )
    result = await db.execute(stmt)
    conv = result.scalar_one_or_none()
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")
    return conv


# ── Routes ───────────────────────────────────────────────────────────────────
# IMPORTANT: static paths (/user-profile) must be registered BEFORE
# parameterized paths (/{conv_id}) to avoid routing conflicts.

@router.get("/user-profile")
async def get_user_profile(
    current_user: User = Depends(get_current_user),
    redis=Depends(get_redis_client),
):
    """Return the current user's long-term memory profile stored in Redis."""
    if redis is None:
        return {"profile": None}
    import json
    from app.agent.long_term_memory import _KEY_PREFIX
    key = f"{_KEY_PREFIX}:{current_user.id}"
    try:
        raw = await redis.get(key)
        if raw is None:
            return {"profile": None}
        return {"profile": json.loads(raw)}
    except Exception:
        return {"profile": None}


@router.delete("/user-profile", status_code=status.HTTP_204_NO_CONTENT)
async def clear_user_profile(
    current_user: User = Depends(get_current_user),
    redis=Depends(get_redis_client),
):
    """Clear (forget) the current user's long-term memory profile."""
    if redis is None:
        return
    from app.agent.long_term_memory import _KEY_PREFIX
    key = f"{_KEY_PREFIX}:{current_user.id}"
    try:
        await redis.delete(key)
    except Exception:
        pass


@router.get("/", response_model=List[ConversationOut])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all conversations for the current user, newest first."""
    stmt = (
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
    )
    result = await db.execute(stmt)
    convs = result.scalars().all()
    return [_conv_out(c) for c in convs]


@router.get("/{conv_id}/messages", response_model=List[MessageOut])
async def get_messages(
    conv_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return visible messages for a conversation (excludes summary and tool rows)."""
    await _get_conv_or_404(conv_id, current_user.id, db)
    stmt = (
        select(Message)
        .where(
            Message.conversation_id == conv_id,
            Message.role.in_(["user", "assistant"]),
        )
        .order_by(Message.id.asc())
    )
    result = await db.execute(stmt)
    msgs = result.scalars().all()
    return [
        MessageOut(
            id=m.id,
            role=m.role,
            content=m.content,
            created_at=m.created_at.isoformat() if m.created_at else "",
        )
        for m in msgs
    ]


@router.patch("/{conv_id}", response_model=ConversationOut)
async def rename_conversation(
    conv_id: int,
    body: RenameRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rename a conversation title."""
    title = body.title.strip()
    if not title:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="标题不能为空")
    conv = await _get_conv_or_404(conv_id, current_user.id, db)
    conv.title = title[:200]
    await db.commit()
    await db.refresh(conv)
    return _conv_out(conv)


@router.delete("/{conv_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conv_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation and all its messages."""
    conv = await _get_conv_or_404(conv_id, current_user.id, db)
    await db.execute(delete(Message).where(Message.conversation_id == conv.id))
    await db.delete(conv)
    await db.commit()
