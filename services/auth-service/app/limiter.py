import redis.asyncio as redis
from fastapi import HTTPException, status
from app.config import settings

_client = None


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
        return


async def clear_login_failures(tax_id: str) -> None:
    try:
        r = await _redis()
        await r.delete(f"auth:login:{tax_id}")
    except Exception:
        return
