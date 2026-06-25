"""Rate limiting middleware using Redis."""

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Only rate limit API endpoints
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        from app.core.redis import get_redis

        try:
            redis = get_redis()
        except RuntimeError:
            return await call_next(request)

        # Get identifier: user_id from token or IP
        identifier = self._get_identifier(request)
        key = f"rate_limit:{identifier}"

        try:
            # Atomic INCR-first approach (eliminates TOCTOU race)
            count = await redis.incr(key)
            if count == 1:
                # First request in this window — set TTL
                await redis.expire(key, 60)
            if count > settings.RATE_LIMIT_PER_MINUTE:
                raise HTTPException(
                    status_code=429,
                    detail="请求过于频繁，请稍后再试",
                )
        except HTTPException:
            raise
        except Exception:
            pass  # Fail open if Redis is down

        return await call_next(request)

    def _get_identifier(self, request: Request) -> str:
        # Try to get user_id from auth header
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            from app.core.security import decode_access_token
            payload = decode_access_token(auth[7:])
            if payload and "sub" in payload:
                return f"user:{payload['sub']}"

        # Fall back to IP
        ip = request.client.host if request.client else "unknown"
        return f"ip:{ip}"
