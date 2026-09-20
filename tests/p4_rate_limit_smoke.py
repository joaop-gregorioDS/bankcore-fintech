"""Disposable two-Auth-instance validation for the P4-B limiter contract."""

import asyncio
import os
import sys
import uuid

import httpx
import redis.asyncio as redis


AUTH_A = os.environ["P4_AUTH_A_URL"]
AUTH_B = os.environ["P4_AUTH_B_URL"]
REDIS_URL = os.environ["P4_REDIS_URL"]
LIMIT = int(os.environ.get("RATE_LIMIT_MAX_ATTEMPTS", "5"))
WINDOW = int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "900"))


async def login(client: httpx.AsyncClient, base_url: str, tax_id: str) -> int:
    response = await client.post(
        f"{base_url}/auth/login",
        json={"tax_id": tax_id, "password": "wrong-password-for-rate-limit"},
    )
    return response.status_code


async def redis_keys() -> list[str]:
    client = redis.from_url(REDIS_URL, decode_responses=True)
    try:
        return [key async for key in client.scan_iter(match="auth:login:v1:*")]
    finally:
        await client.aclose()


async def clear_keys() -> None:
    client = redis.from_url(REDIS_URL, decode_responses=True)
    try:
        keys = await redis_keys()
        if keys:
            await client.delete(*keys)
    finally:
        await client.aclose()


async def distributed(client: httpx.AsyncClient) -> None:
    tax_id = f"9{uuid.uuid4().int % 10**10:010d}"
    statuses = []
    for base_url in (AUTH_A, AUTH_A, AUTH_A, AUTH_B, AUTH_B):
        statuses.append(await login(client, base_url, tax_id))
    assert statuses == [401] * LIMIT, statuses
    assert await login(client, AUTH_A, tax_id) == 429

    keys = await redis_keys()
    assert len(keys) == 1, keys
    assert tax_id not in keys[0], keys[0]
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    try:
        ttl = await redis_client.ttl(keys[0])
        assert 0 < ttl <= WINDOW, ttl
    finally:
        await redis_client.aclose()

    await clear_keys()
    concurrent_tax_id = f"8{uuid.uuid4().int % 10**10:010d}"
    concurrent_statuses = await asyncio.gather(
        *(login(client, (AUTH_A, AUTH_B)[index % 2], concurrent_tax_id) for index in range(20))
    )
    assert concurrent_statuses.count(401) == LIMIT, concurrent_statuses
    assert concurrent_statuses.count(429) == 20 - LIMIT, concurrent_statuses
    await clear_keys()

    ttl_tax_id = f"7{uuid.uuid4().int % 10**10:010d}"
    assert await login(client, AUTH_A, ttl_tax_id) == 401
    await asyncio.sleep(WINDOW + 0.5)
    assert await login(client, AUTH_B, ttl_tax_id) == 401
    print("distributed: shared limit, atomic concurrency, opaque key and TTL passed")


async def fallback(client: httpx.AsyncClient) -> None:
    tax_id = f"6{uuid.uuid4().int % 10**10:010d}"
    statuses = [await login(client, AUTH_A, tax_id) for _ in range(LIMIT)]
    assert statuses == [401] * LIMIT, statuses
    assert await login(client, AUTH_A, tax_id) == 429
    print("fallback: local bounded protection passed")


async def recovery(client: httpx.AsyncClient) -> None:
    tax_id = f"5{uuid.uuid4().int % 10**10:010d}"
    statuses = await asyncio.gather(
        *(login(client, (AUTH_A, AUTH_B)[index % 2], tax_id) for index in range(LIMIT + 1))
    )
    assert statuses.count(401) == LIMIT, statuses
    assert statuses.count(429) == 1, statuses
    assert any(key.startswith("auth:login:v1:") for key in await redis_keys())
    print("recovery: distributed limiter resumed without service restart")


async def main(command: str) -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        if command == "distributed":
            await distributed(client)
        elif command == "fallback":
            await fallback(client)
        elif command == "recovery":
            await recovery(client)
        else:
            raise SystemExit(f"unknown command: {command}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "distributed"))
