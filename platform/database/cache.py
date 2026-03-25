"""
Redis缓存服务
支持分布式缓存和会话管理
"""

import os
import json
import pickle
from typing import Optional, Any, List, Dict, Union
from datetime import timedelta
import logging
import hashlib

try:
    import redis
    from redis import Redis
    from redis.exceptions import RedisError
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    Redis = None

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "true").lower() == "true"


class CacheService:
    """缓存服务"""
    
    def __init__(self, redis_url: Optional[str] = None, enabled: bool = True):
        self.enabled = enabled and REDIS_AVAILABLE and REDIS_ENABLED
        self.redis_url = redis_url or REDIS_URL
        self._client: Optional[Redis] = None
        self._local_cache: Dict[str, Any] = {}
        self._local_ttl: Dict[str, float] = {}
        
        if self.enabled:
            try:
                self._client = redis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                self._client.ping()
                logger.info(f"Redis连接成功: {self.redis_url}")
            except Exception as e:
                logger.warning(f"Redis连接失败，使用本地缓存: {e}")
                self.enabled = False
                self._client = None
    
    @property
    def client(self) -> Optional[Redis]:
        return self._client
    
    def _generate_key(self, key: str, namespace: str = None) -> str:
        """生成缓存键"""
        if namespace:
            return f"{namespace}:{key}"
        return key
    
    def _serialize(self, value: Any) -> str:
        """序列化值"""
        return json.dumps(value, ensure_ascii=False, default=str)
    
    def _deserialize(self, value: str) -> Any:
        """反序列化值"""
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    
    def get(self, key: str, namespace: str = None) -> Optional[Any]:
        """获取缓存值"""
        full_key = self._generate_key(key, namespace)
        
        if self.enabled and self._client:
            try:
                value = self._client.get(full_key)
                if value is not None:
                    return self._deserialize(value)
            except RedisError as e:
                logger.error(f"Redis获取失败: {e}")
        
        import time
        if full_key in self._local_cache:
            if full_key in self._local_ttl:
                if time.time() > self._local_ttl[full_key]:
                    del self._local_cache[full_key]
                    del self._local_ttl[full_key]
                    return None
            return self._local_cache[full_key]
        
        return None
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: int = None,
        namespace: str = None
    ) -> bool:
        """设置缓存值"""
        full_key = self._generate_key(key, namespace)
        
        if self.enabled and self._client:
            try:
                serialized = self._serialize(value)
                if ttl:
                    self._client.setex(full_key, ttl, serialized)
                else:
                    self._client.set(full_key, serialized)
                return True
            except RedisError as e:
                logger.error(f"Redis设置失败: {e}")
        
        self._local_cache[full_key] = value
        if ttl:
            import time
            self._local_ttl[full_key] = time.time() + ttl
        
        return True
    
    def delete(self, key: str, namespace: str = None) -> bool:
        """删除缓存"""
        full_key = self._generate_key(key, namespace)
        
        if self.enabled and self._client:
            try:
                self._client.delete(full_key)
            except RedisError as e:
                logger.error(f"Redis删除失败: {e}")
        
        if full_key in self._local_cache:
            del self._local_cache[full_key]
        if full_key in self._local_ttl:
            del self._local_ttl[full_key]
        
        return True
    
    def exists(self, key: str, namespace: str = None) -> bool:
        """检查键是否存在"""
        full_key = self._generate_key(key, namespace)
        
        if self.enabled and self._client:
            try:
                return self._client.exists(full_key) > 0
            except RedisError as e:
                logger.error(f"Redis检查失败: {e}")
        
        import time
        if full_key in self._local_cache:
            if full_key in self._local_ttl:
                if time.time() > self._local_ttl[full_key]:
                    return False
            return True
        
        return False
    
    def expire(self, key: str, ttl: int, namespace: str = None) -> bool:
        """设置过期时间"""
        full_key = self._generate_key(key, namespace)
        
        if self.enabled and self._client:
            try:
                return self._client.expire(full_key, ttl)
            except RedisError as e:
                logger.error(f"Redis设置过期时间失败: {e}")
        
        if full_key in self._local_cache:
            import time
            self._local_ttl[full_key] = time.time() + ttl
            return True
        
        return False
    
    def incr(self, key: str, amount: int = 1, namespace: str = None) -> int:
        """递增"""
        full_key = self._generate_key(key, namespace)
        
        if self.enabled and self._client:
            try:
                return self._client.incrby(full_key, amount)
            except RedisError as e:
                logger.error(f"Redis递增失败: {e}")
        
        current = self._local_cache.get(full_key, 0)
        if not isinstance(current, int):
            current = 0
        new_value = current + amount
        self._local_cache[full_key] = new_value
        return new_value
    
    def decr(self, key: str, amount: int = 1, namespace: str = None) -> int:
        """递减"""
        return self.incr(key, -amount, namespace)
    
    def get_many(self, keys: List[str], namespace: str = None) -> Dict[str, Any]:
        """批量获取"""
        result = {}
        
        if self.enabled and self._client:
            try:
                full_keys = [self._generate_key(k, namespace) for k in keys]
                values = self._client.mget(full_keys)
                for k, v in zip(keys, values):
                    if v is not None:
                        result[k] = self._deserialize(v)
            except RedisError as e:
                logger.error(f"Redis批量获取失败: {e}")
        else:
            for k in keys:
                v = self.get(k, namespace)
                if v is not None:
                    result[k] = v
        
        return result
    
    def set_many(self, mapping: Dict[str, Any], ttl: int = None, namespace: str = None) -> bool:
        """批量设置"""
        if self.enabled and self._client:
            try:
                pipe = self._client.pipeline()
                for k, v in mapping.items():
                    full_key = self._generate_key(k, namespace)
                    serialized = self._serialize(v)
                    if ttl:
                        pipe.setex(full_key, ttl, serialized)
                    else:
                        pipe.set(full_key, serialized)
                pipe.execute()
                return True
            except RedisError as e:
                logger.error(f"Redis批量设置失败: {e}")
        else:
            for k, v in mapping.items():
                self.set(k, v, ttl, namespace)
        
        return True
    
    def delete_pattern(self, pattern: str, namespace: str = None) -> int:
        """删除匹配模式的所有键"""
        full_pattern = self._generate_key(pattern, namespace)
        count = 0
        
        if self.enabled and self._client:
            try:
                keys = self._client.keys(full_pattern)
                if keys:
                    count = self._client.delete(*keys)
            except RedisError as e:
                logger.error(f"Redis删除模式失败: {e}")
        else:
            import fnmatch
            keys_to_delete = [k for k in self._local_cache if fnmatch.fnmatch(k, full_pattern)]
            for k in keys_to_delete:
                self.delete(k)
                count += 1
        
        return count
    
    def clear_all(self, namespace: str = None) -> bool:
        """清空所有缓存"""
        if self.enabled and self._client:
            try:
                if namespace:
                    self.delete_pattern("*", namespace)
                else:
                    self._client.flushdb()
            except RedisError as e:
                logger.error(f"Redis清空失败: {e}")
        
        self._local_cache.clear()
        self._local_ttl.clear()
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        stats = {
            "enabled": self.enabled,
            "type": "redis" if self.enabled else "local",
            "local_cache_size": len(self._local_cache)
        }
        
        if self.enabled and self._client:
            try:
                info = self._client.info()
                stats.update({
                    "redis_version": info.get("redis_version"),
                    "used_memory": info.get("used_memory_human"),
                    "connected_clients": info.get("connected_clients"),
                    "total_keys": self._client.dbsize()
                })
            except RedisError as e:
                logger.error(f"获取Redis信息失败: {e}")
        
        return stats


_cache_service: Optional[CacheService] = None


def get_cache() -> CacheService:
    """获取缓存服务实例"""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service


class SessionCache:
    """会话缓存"""
    
    NAMESPACE = "session"
    DEFAULT_TTL = 3600
    
    def __init__(self, cache: CacheService = None):
        self.cache = cache or get_cache()
    
    def create_session(self, session_id: str, data: dict, ttl: int = None) -> bool:
        """创建会话"""
        return self.cache.set(
            session_id,
            data,
            ttl=ttl or self.DEFAULT_TTL,
            namespace=self.NAMESPACE
        )
    
    def get_session(self, session_id: str) -> Optional[dict]:
        """获取会话"""
        return self.cache.get(session_id, namespace=self.NAMESPACE)
    
    def update_session(self, session_id: str, data: dict) -> bool:
        """更新会话"""
        session = self.get_session(session_id)
        if session:
            session.update(data)
            return self.cache.set(
                session_id,
                session,
                ttl=self.DEFAULT_TTL,
                namespace=self.NAMESPACE
            )
        return False
    
    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        return self.cache.delete(session_id, namespace=self.NAMESPACE)


class RateLimiter:
    """速率限制器"""
    
    NAMESPACE = "rate_limit"
    
    def __init__(self, cache: CacheService = None):
        self.cache = cache or get_cache()
    
    def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> tuple:
        """检查是否允许请求"""
        full_key = self._generate_key(key)
        
        current = self.cache.get(full_key, namespace=self.NAMESPACE)
        
        if current is None:
            self.cache.set(
                full_key,
                1,
                ttl=window_seconds,
                namespace=self.NAMESPACE
            )
            return True, 1, max_requests - 1
        
        if current >= max_requests:
            return False, current, 0
        
        new_count = self.cache.incr(full_key, namespace=self.NAMESPACE)
        return True, new_count, max_requests - new_count
    
    def _generate_key(self, key: str) -> str:
        return hashlib.md5(key.encode()).hexdigest()[:16]
    
    def reset(self, key: str) -> bool:
        """重置计数"""
        full_key = self._generate_key(key)
        return self.cache.delete(full_key, namespace=self.NAMESPACE)
