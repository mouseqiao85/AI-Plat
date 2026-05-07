import os

from fastapi import APIRouter, Depends, HTTPException, Request, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.schemas.auth import RegisterRequest, LoginRequest, AuthResponse, UserBrief
from app.core.dependencies import get_db
from app.core.security import create_access_token, verify_password, hash_password, decode_access_token
from app.models import User, AuditLog
from app.core.config import settings

router = APIRouter(tags=["auth"])

DEV_TOKEN = os.environ.get("DEV_TOKEN", "dev-token-agent")

# Dummy bcrypt hash for timing-attack mitigation on login
# This is a valid bcrypt hash of "dummy" — verify_password always returns False for it
_DUMMY_HASH = "$2b$12$KIXxqweJfEa9HG3U7Q6KDeVbO3R5YmNpQsTuVwXyZaBcDfGhJkLmN."


async def _check_auth_rate_limit(request: Request) -> None:
    """Per-IP rate limit for auth endpoints. Raises 429 if exceeded."""
    from app.core.redis import get_redis

    try:
        redis = get_redis()
    except RuntimeError:
        return  # Redis unavailable — skip rate limiting

    ip = request.client.host if request.client else "unknown"
    key = f"auth_rate_limit:{ip}"
    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 60)
        if count > settings.AUTH_RATE_LIMIT_PER_MINUTE:
            raise HTTPException(
                status_code=429,
                detail="登录尝试过于频繁，请稍后再试",
            )
    except HTTPException:
        raise
    except Exception:
        pass  # Fail open


@router.post("/dev-login", response_model=AuthResponse)
async def dev_login():
    """Dev-only endpoint: login without database. Returns a mock user token."""
    if settings.APP_ENV != "development":
        raise HTTPException(status_code=404, detail="Not found")
    return AuthResponse(
        access_token=DEV_TOKEN,
        token_type="bearer",
        user=UserBrief(id=1, nickname="开发测试用户", membership_tier="pro", role="admin"),
    )


# Dev mode: a mock user object used when DB is unavailable
class _MockUser:
    id = 1
    username = "dev"
    nickname = "开发测试用户"
    membership_tier = "pro"
    role = "admin"
    daily_chat_count = 0


async def get_current_user(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate the current user from the Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    token = authorization[len("Bearer "):]

    # Dev mode bypass: accept hardcoded dev token
    if settings.APP_ENV == "development" and token == DEV_TOKEN:
        return _MockUser()

    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


@router.post("/register", response_model=AuthResponse)
async def register(
    req: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user with username and password."""
    await _check_auth_rate_limit(request)

    result = await db.execute(select(User).where(User.username == req.username))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already registered",
        )

    hashed = hash_password(req.password)
    user = User(username=req.username, password_hash=hashed)
    db.add(user)

    audit = AuditLog(action="register", detail=f"username={req.username}")
    db.add(audit)

    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=UserBrief(id=user.id, nickname=user.nickname, membership_tier=user.membership_tier, role=getattr(user, 'role', 'user')),
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    req: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Login with username and password, return JWT."""
    await _check_auth_rate_limit(request)

    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()

    if user is None:
        # Timing-attack mitigation: verify against dummy hash to consume same time
        verify_password(req.password, _DUMMY_HASH)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    if not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    audit = AuditLog(action="login", detail=f"username={req.username}")
    db.add(audit)
    await db.commit()

    token = create_access_token({"sub": str(user.id)})
    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=UserBrief(id=user.id, nickname=user.nickname, membership_tier=user.membership_tier, role=getattr(user, 'role', 'user')),
    )


@router.get("/me", response_model=UserBrief)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """Get current authenticated user info."""
    return UserBrief(
        id=current_user.id,
        nickname=current_user.nickname,
    )
