"""Disposable validation for Redis operational hardening and Auth degradation."""

import asyncio
import os
import pathlib
import sys
import uuid

import httpx
import redis.asyncio as redis


AUTH_A = os.environ["P4_AUTH_A_URL"]
AUTH_B = os.environ["P4_AUTH_B_URL"]
REDIS_URL = os.environ["P4_REDIS_URL"]
LIMIT = int(os.environ.get("RATE_LIMIT_MAX_ATTEMPTS", "5"))
MAXMEMORY = os.environ.get("P4_REDIS_MAXMEMORY", "64mb")


async def login(client: httpx.AsyncClient, base_url: str, tax_id: str) -> int:
    response = await client.post(
        f"{base_url}/auth/login",
        json={"tax_id": tax_id, "password": "wrong-password-for-rate-limit"},
    )
    return response.status_code


async def readiness(client: httpx.AsyncClient, base_url: str) -> None:
    response = await client.get(f"{base_url}/auth/readiness")
    assert response.status_code == 200, response.text


async def redis_client():
    last_error = None
    for _ in range(30):
        client = redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
            lib_name="",
            lib_version="",
        )
        try:
            await client.ping()
            return client
        except Exception as exc:
            last_error = exc
            await client.aclose()
            await asyncio.sleep(1)
    raise RuntimeError("Redis did not accept administrative connections") from last_error


async def verify_config() -> None:
    client = await redis_client()
    try:
        config = await client.config_get("maxmemory-policy")
        assert config.get("maxmemory-policy") == "noeviction", config
        config = await client.config_get("appendonly")
        assert config.get("appendonly") == "yes", config
        config = await client.config_get("maxmemory")
        assert int(config["maxmemory"]) > 0, config
    finally:
        await client.aclose()


async def flushdb() -> None:
    client = await redis_client()
    try:
        await client.flushdb()
    finally:
        await client.aclose()


async def assert_transactions_has_no_redis_route_dependency() -> None:
    routes = pathlib.Path("/workspace/services/transactions-service/app/routes")
    route_text = "\n".join(path.read_text() for path in routes.glob("*.py"))
    assert "get_redis" not in route_text, "Transactions route gained a Redis dependency"


async def healthy(client: httpx.AsyncClient) -> None:
    await verify_config()
    await flushdb()
    await readiness(client, AUTH_A)
    await readiness(client, AUTH_B)
    await assert_transactions_has_no_redis_route_dependency()
    print("healthy: config, AOF, noeviction, readiness and Transactions boundary passed")


async def memory_pressure(client: httpx.AsyncClient) -> None:
    redis_conn = await redis_client()
    try:
        await redis_conn.flushdb()
        await redis_conn.config_set("maxmemory", "1")
        try:
            await redis_conn.set("p4:memory-pressure", "x")
        except redis.ResponseError as exc:
            assert "maxmemory" in str(exc).lower() or "oom" in str(exc).lower(), exc
        else:
            raise AssertionError("Redis accepted a write under the noeviction memory limit")
    finally:
        await redis_conn.config_set("maxmemory", MAXMEMORY)
        await redis_conn.flushdb()
        await redis_conn.aclose()

    tax_id = f"4{uuid.uuid4().int % 10**10:010d}"
    statuses = [await login(client, AUTH_A, tax_id) for _ in range(LIMIT)]
    assert statuses == [401] * LIMIT, statuses
    assert await login(client, AUTH_A, tax_id) == 429
    await readiness(client, AUTH_A)
    print("memory-pressure: write rejection triggered bounded local fallback")


async def offline(client: httpx.AsyncClient) -> None:
    await readiness(client, AUTH_A)
    await readiness(client, AUTH_B)
    for base_url in (AUTH_A, AUTH_B):
        tax_id = f"3{uuid.uuid4().int % 10**10:010d}"
        statuses = [await login(client, base_url, tax_id) for _ in range(LIMIT)]
        assert statuses == [401] * LIMIT, statuses
        assert await login(client, base_url, tax_id) == 429
    await readiness(client, AUTH_A)
    await readiness(client, AUTH_B)
    print("offline: Auth stayed ready and local fallback remained bounded")


async def recovered(client: httpx.AsyncClient) -> None:
    await verify_config()
    await flushdb()
    tax_id = f"2{uuid.uuid4().int % 10**10:010d}"
    statuses = []
    for base_url in (AUTH_A, AUTH_A, AUTH_A, AUTH_B, AUTH_B):
        statuses.append(await login(client, base_url, tax_id))
    assert statuses == [401] * LIMIT, statuses
    assert await login(client, AUTH_A, tax_id) == 429
    await flushdb()
    await readiness(client, AUTH_A)
    print("recovered: distributed limiter resumed after Redis restart")


async def main(command: str) -> None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        if command == "healthy":
            await healthy(client)
        elif command == "memory":
            await memory_pressure(client)
        elif command == "offline":
            await offline(client)
        elif command == "recovered":
            await recovered(client)
        else:
            raise SystemExit(f"unknown command: {command}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "healthy"))
