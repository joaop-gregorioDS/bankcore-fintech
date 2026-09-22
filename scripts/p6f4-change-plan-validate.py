"""Static validation for the P6-F4 review-only VPS change plan."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs" / "P6F4_VPS_CHANGE_PLAN.md"
EXPECTED_BASE = "6fb4e4dc56dc0c16b062e4011fdfd46d9064376e"
CHANGE_IDS = tuple(f"VPS-{number:02d}" for number in range(1, 15))
REQUIRED_FIELDS = (
    "Preconditions:",
    "Proposed action:",
    "Execution owner:",
    "Risk:",
    "Validation:",
    "Rollback:",
    "Stop condition:",
)
FORBIDDEN_PATTERNS = (
    re.compile(r"(?im)^\s*(?:sudo\s+|ssh\s+|apt(?:-get)?\s+|docker\s+(?:compose\s+)?(?:up|down|stop|rm|restart|exec|run)\b)"),
    re.compile(r"(?im)^\s*(?:ufw|iptables|ip6tables|nft)\s+(?:allow|deny|delete|add|flush|insert|replace|set)\b"),
    re.compile(r"(?im)^\s*(?:systemctl\s+(?:restart|stop|start|enable|disable|reload)|chmod\s|chown\s|useradd\s|usermod\s|mkdir\s|rm\s+-|mv\s)"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)\b(?:password|token|secret|private[_-]?key)\s*[:=]\s*[^$\{\n][^\n]*"),
)


def fail(message: str) -> None:
    raise ValueError(f"P6-F4 PLAN VALIDATION FAILED: {message}")


def validate_plan_text(text: str) -> None:
    if EXPECTED_BASE not in text:
        fail("baseline commit is missing or does not match main")
    if "no mutation authorized" not in text.lower() or "No first mutation is authorized" not in text:
        fail("plan must explicitly state that no mutation is authorized")
    if "Mandatory stop conditions" not in text:
        fail("mandatory stop conditions section is missing")
    if "Unresolved blocker" not in text:
        fail("live financial data transition blocker is not explicit")
    if "no ready-to-run mutation commands" not in text.lower():
        fail("review-only boundary is missing")

    positions = []
    for change_id in CHANGE_IDS:
        matches = list(re.finditer(rf"^### {re.escape(change_id)} — .+$", text, re.MULTILINE))
        if len(matches) != 1:
            fail(f"expected exactly one change section for {change_id}")
        start = matches[0].end()
        next_heading = re.search(r"^### VPS-\d{2} — .+$|^## ", text[start:], re.MULTILINE)
        end = start + next_heading.start() if next_heading else len(text)
        section = text[start:end]
        for field in REQUIRED_FIELDS:
            if f"**{field}**" not in section:
                fail(f"{change_id} is missing required field {field[:-1]}")
        positions.append(matches[0].start())
    if positions != sorted(positions):
        fail("change sections are not ordered by change ID")

    for pattern in FORBIDDEN_PATTERNS:
        match = pattern.search(text)
        if match:
            fail(f"possible executable mutation/secret content: {match.group(0).strip()[:80]}")

    for required in (
        "verified backup and restore gate",
        "rootless Docker",
        "/opt/bankcore",
        "P6 configuration/secrets contract",
        "image@sha256",
        "Start the candidate stack privately",
        "Prove capacity and coexistence",
        "Switch the host Nginx upstream",
        "Restrict the legacy 8080 publication",
        "Cockpit/9090 separately",
        "Internal financial and event-flow acceptance",
        "observation window",
        "retire the legacy stack",
    ):
        if required.lower() not in text.lower():
            fail(f"required planning topic is missing: {required}")


def main() -> int:
    if not PLAN.is_file():
        fail(f"missing {PLAN.relative_to(ROOT)}")
    text = PLAN.read_text(encoding="utf-8")
    validate_plan_text(text)
    print("P6-F4 STATIC VALIDATION PASS: ordered change plan, review gates, stop conditions and no executable mutations")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
