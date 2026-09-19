import asyncio
import logging
from time import monotonic

import redis.asyncio as redis
from fastapi import HTTPException, status
from app.config import settings

_client = None
_local_attempts: dict[str, tuple[int, float]] = {}
_local_lock = asyncio.Lock()
_logger = logging.getLogger(__name__)
LOCAL_LIMIT = 5
LOCAL_WINDOW_SECONDS = 900


async def _redis():
    global _client
    if _client is None:
        _client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _client


async def assert_login_allowed(tax_id: str) -> None:
    try:
        r = await _redis()
        key = f"auth:login:{tax_id}"
        n = await r.incr(key)
        if n == 1:
            await r.expire(key, 900)
        if n > 15:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Muitas tentativas. Aguarde alguns minutos.",
            )
    except HTTPException:
        raise
    except Exception:
        _logger.warning("Redis indisponível; aplicando rate limit local conservador.")
        async with _local_lock:
            now = monotonic()
            count, started_at = _local_attempts.get(tax_id, (0, now))
            if now - started_at >= LOCAL_WINDOW_SECONDS:
                count, started_at = 0, now
            count += 1
            _local_attempts[tax_id] = (count, started_at)
            if len(_local_attempts) > 10000:
                _local_attempts.clear()
            if count > LOCAL_LIMIT:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Muitas tentativas. Aguarde alguns minutos.",
                )


async def clear_login_failures(tax_id: str) -> None:
    async with _local_lock:
        _local_attempts.pop(tax_id, None)
    try:
        r = await _redis()
        await r.delete(f"auth:login:{tax_id}")
    except Exception:
        return
