import asyncio
import time

import httpx
from fastapi import HTTPException

from app.config import settings
from common.observability import current_correlation_id, current_request_id

_tokens: dict[tuple[str, str], tuple[str, float]] = {}
_lock = asyncio.Lock()


async def get_internal_service_token(*, scope: str = "service:transactions") -> str:
    cache_key = ("bankcore-internal", scope)
    now = time.monotonic()
    cached = _tokens.get(cache_key)
    if cached and now < cached[1]:
        return cached[0]

    async with _lock:
        now = time.monotonic()
        cached = _tokens.get(cache_key)
        if cached and now < cached[1]:
            return cached[0]
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{settings.AUTH_SERVICE_URL}/auth/internal-token",
                    headers={
                        "X-Service-Name": "transactions",
                        "X-Service-Token": settings.AUTH_SERVICE_TOKEN,
                        "X-Service-Scope": scope,
                        **(
                            {"X-Request-ID": current_request_id()}
                            if current_request_id()
                            else {}
                        ),
                        **(
                            {"X-Correlation-ID": current_correlation_id()}
                            if current_correlation_id()
                            else {}
                        ),
                    },
                )
            response.raise_for_status()
            body = response.json()
            token = body["access_token"]
            expires_in = int(body["expires_in"])
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=502, detail="Credencial interna indisponível.") from exc
        _tokens[cache_key] = (token, time.monotonic() + max(1, expires_in - 5))
        return token


async def invalidate_internal_service_token(*, scope: str = "service:transactions") -> None:
    _tokens.pop(("bankcore-internal", scope), None)
