import redis.asyncio as redis

from app.core.config import settings

redis_pool: redis.Redis | None = None


async def init_redis() -> redis.Redis:
    global redis_pool
    redis_pool = redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        max_connections=20,
        socket_timeout=5.0,
        socket_connect_timeout=5.0,
        health_check_interval=30,
        retry_on_timeout=True,
    )
    return redis_pool


async def close_redis():
    global redis_pool
    if redis_pool:
        await redis_pool.close()
        redis_pool = None


def get_redis() -> redis.Redis:
    if redis_pool is None:
        raise RuntimeError("Redis not initialized")
    return redis_pool


async def check_redis_health() -> bool:
    """Ping Redis and return True if reachable, False otherwise."""
    try:
        r = get_redis()
        return await r.ping()
    except Exception:
        return False
