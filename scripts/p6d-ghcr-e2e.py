import argparse
import json
import os
import secrets
import subprocess
import tempfile
import uuid
from pathlib import Path

from e2e import generate_keys


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILES = ("-f", "docker-compose.production.yml", "-f", "docker-compose.production.local.yml")
CUSTOM_SERVICES = {
    "auth": ("migrate-auth", "auth-service"),
    "transactions": ("migrate-transactions", "transactions-service", "outbox-publisher"),
    "risk": ("migrate-risk", "risk-service"),
    "audit": ("migrate-audit", "audit-consumer"),
}


def redact(text: str, environment: dict[str, str]) -> str:
    result = text
    for key in ("POSTGRES_PASSWORD", "AUTH_SERVICE_TOKEN", "RATE_LIMIT_KEY_SECRET", "GRAFANA_ADMIN_PASSWORD"):
        value = environment.get(key)
        if value:
            result = result.replace(value, "[REDACTED]")
    return result[-4000:]


def run(command: list[str], environment: dict[str, str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if check and result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {command[0]} {command[1] if len(command) > 1 else ''}\n{redact(result.stderr, environment)}")
    return result


def compose(project: str, environment: dict[str, str], *arguments: str, extra_file: Path | None = None) -> subprocess.CompletedProcess[str]:
    command = ["docker", "compose", "-p", project, *COMPOSE_FILES]
    if extra_file:
        command.extend(("-f", str(extra_file)))
    command.extend(arguments)
    return run(command, environment)


def load_manifest(path: Path) -> dict[str, dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    images = {item["name"]: item for item in data["images"]}
    if set(images) != set(CUSTOM_SERVICES):
        raise RuntimeError("P6-D E2E manifest must contain auth, transactions, risk and audit images.")
    for name, item in images.items():
        if "@sha256:" not in item["immutable_ref"] or ":latest" in item["immutable_ref"]:
            raise RuntimeError(f"Non-immutable image reference for {name}.")
    return images


def write_override(path: Path, images: dict[str, dict[str, str]]) -> None:
    lines = ["services:"]
    for logical_name, services in CUSTOM_SERVICES.items():
        image = images[logical_name]["immutable_ref"]
        for service in services:
            lines.extend((f"  {service}:", f"    image: {image}", "    pull_policy: never"))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify_no_residue(project: str, environment: dict[str, str]) -> None:
    containers = compose(project, environment, "ps", "-aq").stdout.strip()
    volumes = run(
        ["docker", "volume", "ls", "-q", "--filter", f"label=com.docker.compose.project={project}"],
        environment,
    ).stdout.strip()
    if containers or volumes:
        raise RuntimeError("P6-D E2E teardown left Docker resources behind.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the production-like PIX E2E using GHCR digest references.")
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    images = load_manifest(args.manifest)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    project = f"bankcore-p6d-{uuid.uuid4().hex[:8]}"
    release = f"p6d-ghcr-{uuid.uuid4().hex[:12]}"

    with tempfile.TemporaryDirectory(prefix="bankcore-p6d-") as temporary_root:
        temporary = Path(temporary_root)
        key_dir = temporary / "keys"
        key_dir.mkdir()
        generate_keys(key_dir)
        override = temporary / "immutable.yml"
        write_override(override, images)
        environment = os.environ.copy()
        environment.update(
            {
                "POSTGRES_PASSWORD": secrets.token_urlsafe(24),
                "AUTH_SERVICE_TOKEN": secrets.token_urlsafe(32),
                "RATE_LIMIT_KEY_SECRET": secrets.token_urlsafe(32),
                "GRAFANA_ADMIN_PASSWORD": secrets.token_urlsafe(24),
                "JWT_ACTIVE_KID": "e2e",
                "JWT_PRIVATE_KEY_FILE": (key_dir / "jwt-private.pem").as_posix(),
                "JWT_PUBLIC_KEYS_HOST_DIR": (key_dir / "jwt-public").as_posix(),
                "BANKCORE_IMAGE_REGISTRY": "ghcr.io/joaop-gregoriods",
                "BANKCORE_RELEASE_VERSION": release,
                "BANKCORE_GIT_COMMIT": manifest["git_commit"],
                "GATEWAY_PORT": os.environ.get("P6D_GATEWAY_PORT", "18089"),
                "PROMETHEUS_PORT": os.environ.get("P6D_PROMETHEUS_PORT", "19099"),
                "GRAFANA_PORT": os.environ.get("P6D_GRAFANA_PORT", "13009"),
                "DEMO_MODE": "false",
            }
        )
        exit_code = 1
        try:
            compose(project, environment, "--profile", "verification", "config", "--quiet", extra_file=override)
            compose(project, environment, "--profile", "verification", "build", "p6b-e2e-runner", extra_file=override)
            compose(project, environment, "up", "-d", "--wait", extra_file=override)
            compose(
                project,
                environment,
                "--profile",
                "verification",
                "run",
                "--rm",
                "--no-deps",
                "p6b-e2e-runner",
                "python",
                "tests/p3g_e2e.py",
                "happy",
                extra_file=override,
            )
            exit_code = 0
            print("P6D GHCR E2E PASS: digest-pinned images, migrations, PIX flow and audit path")
        finally:
            teardown = compose(project, environment, "down", "-v", "--remove-orphans", extra_file=override)
            if teardown.returncode == 0:
                verify_no_residue(project, environment)
            elif exit_code == 0:
                exit_code = teardown.returncode
        return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
