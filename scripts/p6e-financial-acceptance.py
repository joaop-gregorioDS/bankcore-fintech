"""Host adapter for the disposable P6-E financial acceptance probe."""

from __future__ import annotations

import os
import subprocess
import sys


def required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"P6-E acceptance requires {name} from the deployment runner.")
    return value


def main() -> int:
    project = required("P6E_COMPOSE_PROJECT")
    image = required("P6E_PROBE_IMAGE")
    password = required("POSTGRES_PASSWORD")
    user = os.environ.get("POSTGRES_USER", "bankadmin")
    networks = subprocess.run(
        ["docker", "network", "ls", "--format", "{{.Name}}"],
        text=True,
        capture_output=True,
        check=False,
    )
    if networks.returncode:
        raise SystemExit("P6-E acceptance could not enumerate Docker networks.")
    expected_network = f"{project}_bankcore_net"
    inspected = subprocess.run(["docker", "network", "inspect", expected_network], capture_output=True, check=False)
    candidates = [line.strip() for line in networks.stdout.splitlines() if line.strip()]
    network = expected_network if inspected.returncode == 0 else next(
        (line for line in candidates if line.endswith("_bankcore_net")), None
    )
    if not network:
        raise SystemExit(
            "P6-E acceptance could not find the internal BankCore network; "
            f"candidates={','.join(candidates[-10:])}"
        )

    mode = sys.argv[1] if len(sys.argv) == 2 else "smoke"
    if mode not in {"snapshot", "smoke"}:
        raise SystemExit(f"unsupported acceptance mode: {mode}")
    environment = {
        "E2E_BASE_URL": "http://nginx:8080",
        "E2E_DATABASE_URL": f"postgresql://{user}:{password}@postgres:5432/bankcore_transactions",
        "E2E_RISK_DATABASE_URL": f"postgresql://{user}:{password}@postgres:5432/bankcore_risk",
        "E2E_AUDIT_DATABASE_URL": f"postgresql://{user}:{password}@audit-postgres:5432/bankcore_audit",
    }
    result = subprocess.run(
        ["docker", "run", "--rm", "--network", network, *sum((["--env", f"{key}={value}"] for key, value in environment.items()), []), "--env", f"P6E_PROBE_MODE={mode}", image],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        # Probe output contains no credentials or financial identifiers by contract.
        sys.stderr.write(result.stderr[-4000:])
        return result.returncode
    sys.stdout.write(result.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
