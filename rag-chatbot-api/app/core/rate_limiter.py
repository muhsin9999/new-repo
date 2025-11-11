"""
Rate limiting middleware using Redis.
Implements token bucket algorithm for rate limiting.
"""
import time
from typing import Optional

import redis.asyncio as aioredis
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.core.exceptions import RateLimitExceededError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using Redis.
    Implements sliding window rate limiting per user/IP.
    """

    def __init__(self, app, redis_url: str = None):
        super().__init__(app)
        self.redis_url = redis_url or settings.REDIS_URL
        self.redis: Optional[aioredis.Redis] = None

    async def dispatch(self, request: Request, call_next):
        """Process the request with rate limiting."""
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/health/ready", "/health/live"]:
            return await call_next(request)

        # Get user identifier (API key or IP)
        identifier = self._get_identifier(request)

        # Check rate limit
        try:
            allowed, retry_after = await self._check_rate_limit(identifier)

            if not allowed:
                logger.warning(
                    "rate_limit_exceeded",
                    identifier=identifier[:10] + "..." if len(identifier) > 10 else identifier,
                    path=request.url.path
                )
                raise RateLimitExceededError(
                    message="Rate limit exceeded. Please try again later.",
                    retry_after=retry_after
                )

            # Process request
            response = await call_next(request)

            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_PER_MINUTE)
            response.headers["X-RateLimit-Remaining"] = str(
                await self._get_remaining_requests(identifier)
            )
            response.headers["X-RateLimit-Reset"] = str(
                int(time.time()) + 60
            )

            return response

        except RateLimitExceededError:
            # Return rate limit error response
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "details": {"retry_after": retry_after},
                    "status_code": 429
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(settings.RATE_LIMIT_PER_MINUTE),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + retry_after)
                }
            )

    def _get_identifier(self, request: Request) -> str:
        """Get unique identifier for rate limiting (API key or IP)."""
        # Try to get API key from header
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api_key:{api_key}"

        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"

    async def _get_redis(self) -> aioredis.Redis:
        """Get or create Redis connection."""
        if self.redis is None:
            self.redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=settings.REDIS_MAX_CONNECTIONS
            )
        return self.redis

    async def _check_rate_limit(self, identifier: str) -> tuple[bool, int]:
        """
        Check if request is within rate limit.

        Args:
            identifier: Unique identifier for the client

        Returns:
            Tuple of (allowed, retry_after_seconds)
        """
        try:
            redis = await self._get_redis()
            key = f"rate_limit:{identifier}"
            current_time = int(time.time())
            window_start = current_time - 60  # 1 minute window

            # Use sorted set to store timestamps
            pipe = redis.pipeline()

            # Remove old entries outside the time window
            pipe.zremrangebyscore(key, 0, window_start)

            # Count requests in current window
            pipe.zcard(key)

            # Add current request timestamp
            pipe.zadd(key, {str(current_time): current_time})

            # Set expiration
            pipe.expire(key, 60)

            results = await pipe.execute()
            request_count = results[1]

            # Check if within limit
            if request_count >= settings.RATE_LIMIT_PER_MINUTE:
                # Calculate retry after
                oldest_timestamp = await redis.zrange(key, 0, 0, withscores=True)
                if oldest_timestamp:
                    retry_after = int(60 - (current_time - oldest_timestamp[0][1]))
                    return False, max(retry_after, 1)
                return False, 60

            return True, 0

        except Exception as e:
            logger.error("rate_limit_check_failed", error=str(e))
            # Fail open - allow request if Redis is unavailable
            return True, 0

    async def _get_remaining_requests(self, identifier: str) -> int:
        """Get number of remaining requests in current window."""
        try:
            redis = await self._get_redis()
            key = f"rate_limit:{identifier}"
            current_time = int(time.time())
            window_start = current_time - 60

            # Count requests in current window
            count = await redis.zcount(key, window_start, current_time)
            remaining = max(0, settings.RATE_LIMIT_PER_MINUTE - count)

            return remaining

        except Exception as e:
            logger.error("get_remaining_requests_failed", error=str(e))
            return settings.RATE_LIMIT_PER_MINUTE


async def check_user_rate_limit(user_id: str, tier: str = "free") -> bool:
    """
    Check rate limit for a specific user based on their tier.

    Args:
        user_id: User ID
        tier: User's rate limit tier

    Returns:
        True if within limit, False otherwise
    """
    # Define tier limits
    tier_limits = {
        "free": 60,
        "basic": 300,
        "premium": 1000,
        "enterprise": 10000
    }

    limit = tier_limits.get(tier, 60)

    try:
        redis = await aioredis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        key = f"rate_limit:user:{user_id}"
        current_time = int(time.time())
        window_start = current_time - 3600  # 1 hour window

        # Count requests in current window
        count = await redis.zcount(key, window_start, current_time)

        if count >= limit:
            return False

        # Add current request
        await redis.zadd(key, {str(current_time): current_time})
        await redis.expire(key, 3600)

        return True

    except Exception as e:
        logger.error("user_rate_limit_check_failed", error=str(e), user_id=user_id)
        # Fail open
        return True
