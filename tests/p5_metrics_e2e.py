"""Small disposable checks used by the P5 metrics runner."""

import json
import os
import time
import urllib.error
import urllib.request
from uuid import uuid4


BASE_URL = os.environ["E2E_BASE_URL"].rstrip("/")


def request(path: str, payload: dict) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8", errors="replace"))


def redis_fallback() -> None:
    suffix = str(time.time_ns())[-10:]
    tax_id = f"8{suffix}"
    status, _ = request(
        "/auth/register",
        {
            "tax_id": tax_id,
            "full_name": "BankCore P5 metrics",
            "email": f"p5-metrics-{uuid4()}@example.com",
            "password": "BankCoreP5Metrics!123",
        },
    )
    assert status == 201, status
    status, _ = request("/auth/login", {"tax_id": tax_id, "password": "wrong-password"})
    assert status == 401, status
    print("P5-D REDIS FALLBACK PASS")


if __name__ == "__main__":
    command = os.sys.argv[1] if len(os.sys.argv) > 1 else "redis-fallback"
    if command != "redis-fallback":
        raise SystemExit(f"Unknown command: {command}")
    redis_fallback()
