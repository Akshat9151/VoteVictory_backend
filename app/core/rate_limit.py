import time
from typing import Callable, Optional

import redis.asyncio as aioredis
from fastapi import Request

from app.core.config import settings
from app.core.exceptions import RateLimitExceededException

# In-memory sliding window fallback when Redis is offline
_in_memory_rate_limits: dict[str, list[int]] = {}


class RateLimiter:
    def __init__(self, limit_per_minute: int = 120, prefix: str = "rate_limit"):
        self.limit = limit_per_minute
        self.prefix = prefix
        self.redis: Optional[aioredis.Redis] = None

    async def get_redis(self) -> Optional[aioredis.Redis]:
        if self.redis is None and settings.REDIS_URL:
            try:
                self.redis = aioredis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_timeout=1.0,
                    socket_connect_timeout=1.0
                )
                await self.redis.ping()
            except Exception:
                self.redis = None
        return self.redis

    async def check_rate_limit(self, request: Request, identifier: Optional[str] = None, limit: Optional[int] = None) -> None:
        effective_limit = limit or self.limit
        client_ip = request.client.host if request.client else "127.0.0.1"
        key_id = identifier or client_ip
        key = f"{self.prefix}:{key_id}"

        redis_client = await self.get_redis()
        current_time = int(time.time())
        window_start = current_time - 60

        if redis_client:
            try:
                pipe = redis_client.pipeline()
                pipe.zremrangebyscore(key, 0, window_start)
                pipe.zadd(key, {str(current_time) + ":" + str(time.time_ns()): current_time})
                pipe.zcard(key)
                pipe.expire(key, 60)
                results = await pipe.execute()
                request_count = results[2]

                if request_count > effective_limit:
                    raise RateLimitExceededException(retry_after_seconds=60)
                return
            except RateLimitExceededException:
                raise
            except Exception:
                pass  # Fall back to in-memory

        # In-memory sliding window fallback
        timestamps = _in_memory_rate_limits.get(key, [])
        timestamps = [ts for ts in timestamps if ts > window_start]
        timestamps.append(current_time)
        _in_memory_rate_limits[key] = timestamps

        if len(timestamps) > effective_limit:
            raise RateLimitExceededException(retry_after_seconds=60)


rate_limiter = RateLimiter(limit_per_minute=settings.RATE_LIMIT_PER_MINUTE, prefix="rate_limit:general")
login_rate_limiter = RateLimiter(limit_per_minute=settings.RATE_LIMIT_LOGIN_PER_MINUTE, prefix="rate_limit:login")
broadcast_rate_limiter = RateLimiter(limit_per_minute=settings.RATE_LIMIT_BROADCAST_PER_MINUTE, prefix="rate_limit:broadcast")


def rate_limit_dependency(limiter: RateLimiter) -> Callable:
    async def _dependency(request: Request) -> None:
        await limiter.check_rate_limit(request)
    return _dependency
