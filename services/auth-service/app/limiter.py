import asyncio
import hashlib
import hmac
import logging
from time import monotonic

import redis.asyncio as redis
from fastapi import HTTPException, status
from app.config import settings

_client = None
_local_attempts: dict[str, tuple[int, float]] = {}
_local_lock = asyncio.Lock()
_logger = logging.getLogger(__name__)

_INCREMENT_WITH_TTL = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return count
"""


def _rate_limit_key(tax_id: str) -> str:
    opaque_identifier = hmac.new(
        settings.RATE_LIMIT_KEY_SECRET.encode("utf-8"),
        tax_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"auth:login:v1:{opaque_identifier}"


def _local_limit() -> int:
    return settings.RATE_LIMIT_MAX_ATTEMPTS


def _local_window_seconds() -> int:
    return settings.RATE_LIMIT_WINDOW_SECONDS


async def _redis():
    global _client
    if _client is None:
        _client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=settings.RATE_LIMIT_REDIS_TIMEOUT_SECONDS,
            socket_timeout=settings.RATE_LIMIT_REDIS_TIMEOUT_SECONDS,
        )
    return _client


async def assert_login_allowed(tax_id: str) -> None:
    try:
        r = await _redis()
        key = _rate_limit_key(tax_id)
        n = int(await r.eval(_INCREMENT_WITH_TTL, 1, key, settings.RATE_LIMIT_WINDOW_SECONDS))
        if n > settings.RATE_LIMIT_MAX_ATTEMPTS:
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
            if now - started_at >= _local_window_seconds():
                count, started_at = 0, now
            count += 1
            _local_attempts[tax_id] = (count, started_at)
            if len(_local_attempts) > 10000:
                _local_attempts.clear()
            if count > _local_limit():
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Muitas tentativas. Aguarde alguns minutos.",
                )


async def clear_login_failures(tax_id: str) -> None:
    async with _local_lock:
        _local_attempts.pop(tax_id, None)
    try:
        r = await _redis()
        await r.delete(_rate_limit_key(tax_id))
    except Exception:
        return
