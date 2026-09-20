"""Static guardrails for the P4 Redis ownership boundary."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRANSACTIONS_ROOT = ROOT / "services" / "transactions-service"
REDIS_CONFIG = ROOT / "infra" / "redis" / "redis.conf"
FORBIDDEN = re.compile(r"redis|REDIS_URL|get_redis", re.IGNORECASE)


def text_files(root: Path):
    yield from (path for path in root.rglob("*") if path.is_file())


def main() -> int:
    violations: list[str] = []
    for path in text_files(TRANSACTIONS_ROOT):
        try:
            contents = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(contents.splitlines(), start=1):
            if FORBIDDEN.search(line):
                violations.append(f"{path.relative_to(ROOT)}:{line_number}: {line.strip()}")

    if violations:
        print("Transactions Redis boundary violated:")
        print("\n".join(violations))
        return 1

    if not REDIS_CONFIG.is_file():
        print(f"Missing Redis policy file: {REDIS_CONFIG.relative_to(ROOT)}")
        return 1

    config = REDIS_CONFIG.read_text(encoding="utf-8")
    required = {
        "appendonly yes": re.compile(r"^\s*appendonly\s+yes\s*$", re.MULTILINE),
        "appendfsync everysec": re.compile(r"^\s*appendfsync\s+everysec\s*$", re.MULTILINE),
        "maxmemory-policy noeviction": re.compile(
            r"^\s*maxmemory-policy\s+noeviction\s*$", re.MULTILINE
        ),
        "positive maxmemory": re.compile(r"^\s*maxmemory\s+[1-9][0-9]*(?:kb|mb|gb)\s*$", re.MULTILINE | re.IGNORECASE),
    }
    missing = [description for description, pattern in required.items() if not pattern.search(config)]
    if missing:
        print("Redis policy validation failed:")
        print("missing: " + ", ".join(missing))
        return 1

    print("P4 architecture gate passed: Transactions is Redis-free and Redis policy is explicit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
