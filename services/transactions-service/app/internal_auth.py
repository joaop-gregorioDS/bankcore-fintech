import asyncio
import time

import httpx
from fastapi import HTTPException

from app.config import settings

_token: str | None = None
_expires_at = 0.0
_lock = asyncio.Lock()


async def get_internal_service_token() -> str:
    global _token, _expires_at
    now = time.monotonic()
    if _token and now < _expires_at:
        return _token

    async with _lock:
        now = time.monotonic()
        if _token and now < _expires_at:
            return _token
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{settings.AUTH_SERVICE_URL}/auth/internal-token",
                    headers={
                        "X-Service-Name": "transactions",
                        "X-Service-Token": settings.AUTH_SERVICE_TOKEN,
                    },
                )
            response.raise_for_status()
            body = response.json()
            token = body["access_token"]
            expires_in = int(body["expires_in"])
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=502, detail="Credencial interna indisponível.") from exc
        _token = token
        _expires_at = time.monotonic() + max(1, expires_in - 5)
        return _token
