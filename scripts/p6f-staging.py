"""Run P6-F2 against a disposable Linux host inside Docker.

The target is a privileged, short-lived Docker-in-Docker container whose
inner daemon runs rootless as ``bankcore``. No host service, VPS, registry
credential, or production secret is used by this runner.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET_DOCKERFILE = ROOT / "infra" / "ansible" / "tests" / "p6f2-target.Dockerfile"
DEFAULT_BUNDLES = os.environ.get("P6E_BUNDLES_DIR")
RECAP = re.compile(r"changed=(\d+).*?failed=(\d+)")


def run(command: list[str], *, check: bool = True, timeout: int = 900) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if check and result.returncode:
        detail = (result.stderr or result.stdout)[-8000:]
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(command)}\n{detail}")
    return result


def docker_exec(container: str, command: list[str], *, user: str | None = None, check: bool = True, timeout: int = 900) -> subprocess.CompletedProcess[str]:
    args = ["docker", "exec"]
    if user:
        args.extend(["--user", user])
    args.extend([container, *command])
    return run(args, check=check, timeout=timeout)


def shell_exec(container: str, script: str, *, user: str | None = None, check: bool = True, timeout: int = 900) -> subprocess.CompletedProcess[str]:
    return docker_exec(container, ["sh", "-lc", script], user=user, check=check, timeout=timeout)


def wait_for_rootless_docker(container: str) -> None:
    last = ""
    for _ in range(60):
        result = shell_exec(
            container,
            "DOCKER_HOST=unix:///run/user/1000/docker.sock "
            "XDG_RUNTIME_DIR=/run/user/1000 docker info --format '{{json .SecurityOptions}}'",
            user="bankcore",
            check=False,
            timeout=30,
        )
        if result.returncode == 0 and "rootless" in result.stdout.lower():
            return
        last = (result.stderr or result.stdout).strip()
        time.sleep(2)
    raise RuntimeError(f"rootless Docker did not become ready in the disposable target: {last[-2000:]}")


def ansible_run(container: str, *, extra: list[str] | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    command = [
        "ansible-playbook",
        "-i",
        "/workspace/infra/ansible/inventory/disposable.yml",
        "/workspace/infra/ansible/site.yml",
        "--diff",
    ]
    if extra:
        command.extend(extra)
    return docker_exec(container, command, check=check, timeout=300)


def assert_recap(output: str, *, changed: int | None = None) -> None:
    matches = RECAP.findall(output)
    if not matches:
        raise RuntimeError(f"Ansible recap was not found:\n{output[-4000:]}")
    actual_changed, failed = (int(value) for value in matches[-1])
    if failed != 0:
        raise RuntimeError(f"Ansible reported failed={failed}:\n{output[-4000:]}")
    if changed is not None and actual_changed != changed:
        raise RuntimeError(f"Expected Ansible changed={changed}, got {actual_changed}:\n{output[-4000:]}")


def require_bundles(path: Path) -> tuple[Path, Path]:
    release_a = path / "release-a" / "manifest.json"
    release_b = path / "release-b" / "manifest.json"
    missing = [str(item) for item in (release_a, release_b) if not item.is_file()]
    if missing:
        raise RuntimeError("P6-F2 requires the verified local P6-D release bundles: " + ", ".join(missing))
    return release_a, release_b


def run_p6e(container: str, release_a: str, release_b: str, mode: str) -> None:
    command = [
        "python3",
        "/workspace/scripts/p6e-deploy-rollback.py",
        "--release-a",
        str(release_a),
        "--release-b",
        str(release_b),
        "--smoke-a",
        "python3 scripts/p6e-financial-acceptance.py smoke",
        "--smoke-b",
        "python3 scripts/p6e-financial-acceptance.py smoke",
        "--snapshot-command",
        "python3 scripts/p6e-financial-acceptance.py snapshot",
        "--failure-mode",
        mode,
    ]
    result = docker_exec(
        container,
        [
            "env",
            "GIT_CONFIG_GLOBAL=/tmp/p6e-gitconfig",
            "DOCKER_HOST=unix:///run/user/1000/docker.sock",
            "XDG_RUNTIME_DIR=/run/user/1000",
            *command,
        ],
        timeout=1800,
    )
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate P6-F2 on a disposable Linux/rootless-Docker target.")
    parser.add_argument("--bundles", type=Path, default=Path(DEFAULT_BUNDLES) if DEFAULT_BUNDLES else None, help="Directory containing release-a/ and release-b/.")
    args = parser.parse_args()
    if not args.bundles:
        raise SystemExit("--bundles or P6E_BUNDLES_DIR is required")
    release_a, release_b = require_bundles(args.bundles)
    run(["docker", "info", "--format", "{{.ServerVersion}}"], timeout=60)

    tag = f"bankcore-p6f2-target:{uuid.uuid4().hex[:12]}"
    container = f"bankcore-p6f2-{uuid.uuid4().hex[:10]}"
    try:
        run(["docker", "build", "--file", str(TARGET_DOCKERFILE), "--tag", tag, "."], timeout=900)
        run(
            [
                "docker",
                "run",
                "--detach",
                "--privileged",
                "--name",
                container,
                "--env",
                "DOCKER_TLS_CERTDIR=",
                "--volume",
                f"{ROOT}:/workspace:ro",
                "--volume",
                f"{ROOT / '.git'}:/workspace/.git:ro",
                "--volume",
                f"{args.bundles.resolve()}:/bundles:ro",
                tag,
            ],
            timeout=60,
        )
        wait_for_rootless_docker(container)
        rootless = shell_exec(
            container,
            "id bankcore && stat -c '%U:%G:%a' /run/user/1000 && "
            "DOCKER_HOST=unix:///run/user/1000/docker.sock "
            "XDG_RUNTIME_DIR=/run/user/1000 docker info --format '{{.SecurityOptions}}'",
            user="bankcore",
        )
        print("P6-F2 rootless Docker:\n" + rootless.stdout.strip())
        docker_exec(container, ["git", "config", "--file", "/tmp/p6e-gitconfig", "--add", "safe.directory", "/workspace"])

        first = ansible_run(container, extra=["-e", "bankcore_verify_docker_contract=true"])
        print(first.stdout)
        assert_recap(first.stdout)

        second = ansible_run(container, extra=["-e", "bankcore_verify_docker_contract=true"])
        print(second.stdout)
        assert_recap(second.stdout, changed=0)
        print("P6-F2 Ansible idempotency: PASS")

        negative = ansible_run(container, extra=["-e", "bankcore_environment=production"], check=False)
        if negative.returncode == 0:
            raise RuntimeError("Negative environment guard unexpectedly succeeded.")
        print("P6-F2 negative environment guard: PASS")

        filesystem = shell_exec(
            container,
            "test \"$(id -u bankcore)\" != 0 && "
            "test -d /opt/bankcore/releases && test -d /opt/bankcore/secrets && "
            "test \"$(stat -c '%a' /opt/bankcore/secrets)\" = 700 && "
            "test \"$(stat -c '%U:%G' /opt/bankcore/secrets)\" = bankcore:bankcore && "
            "test \"$(stat -c '%a' /opt/bankcore/config)\" = 750",
        )
        print("P6-F2 filesystem/permissions: PASS")

        for mode in ("none", "readiness", "smoke"):
            print(f"P6-F2 running P6-E scenario: {mode}")
            run_p6e(container, "/bundles/release-a/manifest.json", "/bundles/release-b/manifest.json", mode)
            print(f"P6-F2 P6-E scenario {mode}: PASS")
        print("P6-F2 PASS: disposable host, idempotent provisioning, negative guard, and A/B rollback scenarios")
        return 0
    finally:
        cleanup = run(["docker", "rm", "--force", container], check=False, timeout=60)
        if cleanup.returncode and "No such container" not in (cleanup.stderr or ""):
            print(cleanup.stderr, file=sys.stderr)
        run(["docker", "image", "rm", "--force", tag], check=False, timeout=120)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"P6-F2 BLOCKED: {error}", file=sys.stderr)
        raise SystemExit(1)
