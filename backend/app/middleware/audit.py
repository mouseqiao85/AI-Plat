"""Audit logging middleware."""

from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.audit_log import AuditLog


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # Audit sensitive operations
        path = request.url.path
        if path.startswith("/api/v1/") and request.method in ("POST", "PUT", "DELETE"):
            await self._log_action(request)

        return response

    async def _log_action(self, request):
        try:
            async with async_session_factory() as db:
                user_id = None
                auth = request.headers.get("Authorization", "")
                if auth.startswith("Bearer "):
                    from app.core.security import decode_access_token
                    payload = decode_access_token(auth[7:])
                    if payload:
                        user_id = int(payload.get("sub", 0))

                log = AuditLog(
                    user_id=user_id,
                    action=f"{request.method} {request.url.path}",
                    detail={"query": str(request.query_params)},
                    ip_address=request.client.host if request.client else None,
                )
                db.add(log)
                await db.commit()
        except Exception:
            pass  # Don't fail requests due to audit errors
