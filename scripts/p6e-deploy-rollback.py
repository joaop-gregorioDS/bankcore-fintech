"""Validate a disposable, digest-pinned deployment and rollback contract.

This runner deliberately consumes an already verified P6-D manifest. It never
builds application images, rewrites a release manifest, or connects to a
remote host. The optional smoke and snapshot commands are host-side test
adapters; they must be supplied by the disposable/staging test harness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

from e2e import generate_keys


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_BASE = ROOT / "docker-compose.production.yml"
PROBE_DOCKERFILE = ROOT / "scripts" / "p6e-probe.Dockerfile"
CUSTOM_SERVICES = {
    "auth": ("migrate-auth", "auth-service"),
    "transactions": ("migrate-transactions", "transactions-service", "outbox-publisher"),
    "risk": ("migrate-risk", "risk-service"),
    "audit": ("migrate-audit", "audit-consumer"),
}
MIGRATION_SERVICES = ("migrate-auth", "migrate-transactions", "migrate-risk", "migrate-audit")
READY_SERVICES = ("auth-service", "transactions-service", "risk-service", "nginx")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
EXPECTED_IMAGES = set(CUSTOM_SERVICES)
P6E_JWT_KID = "p6e"
SENSITIVE_MARKERS = (
    "BEGIN PRIVATE KEY",
    "Authorization: Bearer",
    "POSTGRES_PASSWORD=",
    "AUTH_SERVICE_TOKEN=",
    "RATE_LIMIT_KEY_SECRET=",
)


def redact(text: str, environment: dict[str, str]) -> str:
    result = text
    for name in (
        "POSTGRES_PASSWORD",
        "AUTH_SERVICE_TOKEN",
        "RATE_LIMIT_KEY_SECRET",
        "GRAFANA_ADMIN_PASSWORD",
    ):
        value = environment.get(name)
        if value:
            result = result.replace(value, "[REDACTED]")
    return result[-5000:]


def run_command(
    command: list[str],
    environment: dict[str, str] | None = None,
    *,
    cwd: Path = ROOT,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )


def require_command(
    command: list[str],
    environment: dict[str, str],
    *,
    cwd: Path = ROOT,
) -> str:
    result = run_command(command, environment, cwd=cwd)
    if result.returncode:
        raise RuntimeError(
            f"Command failed ({result.returncode}): {' '.join(command)}\n"
            f"{redact(result.stderr or result.stdout, environment)}"
        )
    return result.stdout


def load_verified_manifest(path: Path) -> dict[str, object]:
    """Validate the P6-D manifest shape without printing sensitive contents."""

    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("P6-E requires a schema_version 1 P6-D manifest.")
    verification = data.get("verification") or {}
    expected_verification = {
        "registry": "ghcr.io",
        "signature": "cosign-keyless",
        "provenance": "github-artifact-attestation",
        "sbom_format": "CycloneDX JSON",
    }
    if verification != expected_verification:
        raise ValueError("Manifest is not the verified P6-D supply-chain contract.")
    if data.get("repository") != "joaop-gregorioDS/bankcore-fintech" or data.get("workflow") != "p6d-release.yml":
        raise ValueError("Manifest was not produced by the BankCore P6-D release workflow.")
    manifest_text = path.read_text(encoding="utf-8", errors="replace")
    if any(marker in manifest_text for marker in SENSITIVE_MARKERS):
        raise ValueError("Sensitive marker found in release manifest.")

    images = data.get("images")
    if not isinstance(images, list) or {item.get("name") for item in images} != EXPECTED_IMAGES:
        raise ValueError("Manifest must contain exactly auth, transactions, risk and audit images.")
    for item in images:
        if not isinstance(item, dict):
            raise ValueError("Malformed image entry in release manifest.")
        image = str(item.get("image", ""))
        digest = str(item.get("digest", ""))
        immutable_ref = str(item.get("immutable_ref", ""))
        if not image.startswith("ghcr.io/joaop-gregoriods/bankcore-"):
            raise ValueError("P6-E only accepts the BankCore GHCR image namespace.")
        if not DIGEST_RE.fullmatch(digest) or immutable_ref != f"{image}@{digest}":
            raise ValueError(f"Image {item.get('name')} is not digest pinned.")
        if ":latest" in immutable_ref:
            raise ValueError("latest is forbidden in a deployment release.")
        sbom = Path(str(item.get("sbom", "")))
        if sbom.is_absolute() or ".." in sbom.parts:
            raise ValueError(f"Unsafe SBOM path for {item.get('name')}.")
        sbom_path = path.parent / sbom
        if not sbom_path.is_file() or not sbom_path.stat().st_size:
            raise ValueError(f"Verified SBOM is missing for {item.get('name')}.")
        sbom_text = sbom_path.read_text(encoding="utf-8", errors="replace")
        if any(marker in sbom_text for marker in SENSITIVE_MARKERS):
            raise ValueError(f"Sensitive marker found in SBOM for {item.get('name')}.")
        sbom_data = json.loads(sbom_text)
        if sbom_data.get("bomFormat") != "CycloneDX":
            raise ValueError(f"SBOM is not CycloneDX for {item.get('name')}.")
    if not data.get("release") or not data.get("git_commit"):
        raise ValueError("Manifest release identity is incomplete.")
    return data


def _upgrade_section(text: str, path: Path) -> str:
    if path.suffix == ".py":
        start = text.find("def upgrade")
        end = text.find("def downgrade", start + 1)
        return text[start:] if end < 0 else text[start:end]
    start = text.find("protected override void Up")
    end = text.find("protected override void Down", start + 1)
    return text[start:] if end < 0 else text[start:end]


def validate_migration_policy(
    root: Path = ROOT,
    *,
    changed_paths: list[Path] | None = None,
    revisions: tuple[str, str] | None = None,
) -> list[Path]:
    """Reject destructive operations in the automatic expand/contract path.

    Downgrade methods are intentionally excluded: they are recovery tooling,
    not automatic production rollout steps.
    """

    if changed_paths is None and revisions is not None:
        diff = run_command(
            ["git", "diff", "--name-only", revisions[0], revisions[1], "--", "infra/postgres/alembic", "services/risk-service"],
            {},
            cwd=root,
        )
        if diff.returncode:
            raise ValueError("Unable to determine migration changes between the two release commits.")
        changed_paths = [root / line.strip() for line in diff.stdout.splitlines() if line.strip()]
    if changed_paths is None:
        changed_paths = sorted(
            list((root / "infra" / "postgres" / "alembic").glob("**/versions/*.py"))
            + list((root / "services" / "risk-service").glob("**/Migrations/*.cs"))
        )
    migration_paths = sorted(path for path in changed_paths if path.suffix in {".py", ".cs"} and path.is_file())
    destructive = re.compile(r"\b(?:drop_table|drop_column|drop_index|DropTable|DropColumn|DropIndex)\b|\bDROP\s+(?:TABLE|COLUMN|INDEX)\b", re.I)
    violations: list[Path] = []
    for path in migration_paths:
        section = _upgrade_section(path.read_text(encoding="utf-8"), path)
        if destructive.search(section):
            violations.append(path)
    if violations:
        names = ", ".join(str(path.relative_to(root)) for path in violations)
        raise ValueError(f"Destructive migration in automatic rollout path: {names}")
    return migration_paths


def write_override(path: Path, manifest: dict[str, object], *, fail_readiness: bool = False) -> None:
    images = {str(item["name"]): str(item["immutable_ref"]) for item in manifest["images"]}
    lines = ["services:"]
    for logical_name, services in CUSTOM_SERVICES.items():
        for service in services:
            lines.extend((f"  {service}:", f"    image: {images[logical_name]}", "    pull_policy: always"))
            if fail_readiness and service == "risk-service":
                lines.extend(("    healthcheck:", '      test: ["CMD-SHELL", "exit 97"]'))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def key_material_paths(key_dir: Path, kid: str = P6E_JWT_KID) -> tuple[Path, Path]:
    return key_dir / "jwt-private" / f"{kid}.pem", key_dir / "jwt-public" / f"{kid}.pem"


def validate_key_material(key_dir: Path, kid: str = P6E_JWT_KID) -> None:
    private_path, public_path = key_material_paths(key_dir, kid)
    missing = [str(path) for path in (private_path, public_path) if not path.is_file() or not path.stat().st_size]
    if missing:
        raise RuntimeError(f"P6-E key preflight failed for kid {kid}: missing key material: {', '.join(missing)}")


def compose(
    project: str,
    environment: dict[str, str],
    override: Path,
    *arguments: str,
) -> subprocess.CompletedProcess[str]:
    command = ["docker", "compose", "-p", project, "-f", str(COMPOSE_BASE), "-f", str(override), *arguments]
    return run_command(command, environment)


def require_compose(
    project: str,
    environment: dict[str, str],
    override: Path,
    *arguments: str,
) -> str:
    result = compose(project, environment, override, *arguments)
    if result.returncode:
        raise RuntimeError(
            f"Compose step failed ({result.returncode}): {' '.join(arguments)}\n"
            f"{redact(result.stderr or result.stdout, environment)}"
        )
    return result.stdout


def compose_records(project: str, environment: dict[str, str], override: Path) -> list[dict[str, object]]:
    output = require_compose(project, environment, override, "ps", "-a", "--format", "json")
    if output.lstrip().startswith("["):
        return list(json.loads(output))
    return [json.loads(line) for line in output.splitlines() if line.strip()]


def verify_rollout(project: str, environment: dict[str, str], override: Path, manifest: dict[str, object]) -> None:
    records = {str(item.get("Service")): item for item in compose_records(project, environment, override)}
    for service in MIGRATION_SERVICES:
        record = records.get(service)
        if not record or str(record.get("State", "")).lower() != "exited" or int(record.get("ExitCode", 1)) != 0:
            raise RuntimeError(f"Ordered migration did not complete successfully: {service}")
    for service in READY_SERVICES:
        record = records.get(service)
        health = str(record.get("Health", "")).lower() if record else ""
        if not record or str(record.get("State", "")).lower() != "running" or health not in {"healthy", ""}:
            raise RuntimeError(f"Service is not ready after rollout: {service}")

    image_refs = {str(item["name"]): str(item["immutable_ref"]) for item in manifest["images"]}
    for logical_name, services in CUSTOM_SERVICES.items():
        for service in services:
            record = records.get(service)
            if not record:
                raise RuntimeError(f"Release service was not created: {service}")
            container_id = str(record["ID"])
            actual_id = require_command(["docker", "inspect", "--format", "{{.Image}}", container_id], environment).strip()
            image_info = json.loads(require_command(["docker", "image", "inspect", image_refs[logical_name]], environment))[0]
            repo_digests = image_info.get("RepoDigests") or []
            if image_refs[logical_name] not in repo_digests or actual_id != image_info.get("Id"):
                raise RuntimeError(f"Runtime image identity mismatch for {service}.")


def snapshot(command: str | None, environment: dict[str, str], *, label: str) -> str | None:
    if not command:
        return None
    result = subprocess.run(command, cwd=ROOT, env=environment, shell=True, text=True, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(f"Financial snapshot command failed for {label}: {redact(result.stderr, environment)}")
    value = result.stdout.strip()
    if not value:
        raise RuntimeError(f"Financial snapshot command returned no data for {label}.")
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    print(f"P6E SNAPSHOT PASS: {label}")
    return digest


def smoke(command: str | None, environment: dict[str, str], *, release: str, health_only: bool) -> None:
    if not command:
        if health_only:
            return
        raise ValueError("A financial --smoke-command is required unless --health-only is explicit.")
    smoke_env = dict(environment)
    smoke_env["BANKCORE_DEPLOYED_RELEASE"] = release
    result = subprocess.run(command, cwd=ROOT, env=smoke_env, shell=True, text=True, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(f"Smoke test failed for {release} ({result.returncode}): {redact(result.stderr, environment)}")
    print(f"P6E FINANCIAL SMOKE PASS: {release}")


@dataclass
class ReleaseState:
    current: dict[str, str] | None = None
    previous: dict[str, str] | None = None


def read_state(path: Path) -> ReleaseState:
    if not path.exists():
        return ReleaseState()
    data = json.loads(path.read_text(encoding="utf-8"))
    return ReleaseState(data.get("current"), data.get("previous"))


def write_state(path: Path, current: dict[str, str], previous: dict[str, str] | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"current": current, "previous": previous}, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def deployment_environment(key_dir: Path, release: str, revision: str) -> dict[str, str]:
    private_path, public_path = key_material_paths(key_dir)
    environment = os.environ.copy()
    environment.update(
        {
            "POSTGRES_PASSWORD": secrets.token_urlsafe(24),
            "AUTH_SERVICE_TOKEN": secrets.token_urlsafe(32),
            "RATE_LIMIT_KEY_SECRET": secrets.token_urlsafe(32),
            "GRAFANA_ADMIN_PASSWORD": secrets.token_urlsafe(24),
            "JWT_ACTIVE_KID": P6E_JWT_KID,
            "JWT_PRIVATE_KEY_FILE": str(private_path),
            "JWT_PUBLIC_KEYS_HOST_DIR": str(public_path.parent),
            "BANKCORE_RELEASE_VERSION": release,
            "BANKCORE_GIT_COMMIT": revision,
            "GATEWAY_PORT": os.environ.get("P6E_GATEWAY_PORT", "18092"),
            "PROMETHEUS_PORT": os.environ.get("P6E_PROMETHEUS_PORT", "19102"),
            "GRAFANA_PORT": os.environ.get("P6E_GRAFANA_PORT", "13012"),
            "DEMO_MODE": "false",
        }
    )
    return environment


def prepare_probe_image(project: str, environment: dict[str, str]) -> str:
    image = f"bankcore-p6e-probe:{project}"
    require_command(
        ["docker", "build", "--file", str(PROBE_DOCKERFILE), "--tag", image, "."],
        environment,
    )
    return image


def remove_probe_image(image: str, environment: dict[str, str]) -> None:
    result = run_command(["docker", "image", "rm", image], environment)
    if result.returncode:
        raise RuntimeError(f"P6-E probe image cleanup failed: {redact(result.stderr or result.stdout, environment)}")


def deploy(
    project: str,
    environment: dict[str, str],
    manifest: dict[str, object],
    override: Path,
    *,
    smoke_command: str | None,
    health_only: bool,
) -> None:
    require_compose(project, environment, override, "config", "--quiet")
    require_compose(project, environment, override, "up", "-d", "--wait")
    verify_rollout(project, environment, override, manifest)
    smoke(smoke_command, environment, release=str(manifest["release"]), health_only=health_only)


def verify_no_residue(project: str, environment: dict[str, str], override: Path) -> None:
    containers = compose(project, environment, override, "ps", "-aq").stdout.strip()
    volumes = require_command(
        ["docker", "volume", "ls", "-q", "--filter", f"label=com.docker.compose.project={project}"],
        environment,
    ).strip()
    if containers or volumes:
        raise RuntimeError("P6-E teardown left Docker resources behind.")


def run_scenario(args: argparse.Namespace) -> int:
    manifest_a = load_verified_manifest(args.release_a)
    manifest_b = load_verified_manifest(args.release_b)
    if manifest_a["release"] == manifest_b["release"]:
        raise ValueError("Release A and release B must have different release identities.")
    migration_paths = validate_migration_policy(
        revisions=(str(manifest_a["git_commit"]), str(manifest_b["git_commit"])),
    )
    project = f"bankcore-p6e-{uuid.uuid4().hex[:8]}"
    state = ReleaseState()
    with tempfile.TemporaryDirectory(prefix="bankcore-p6e-") as temporary_root:
        temporary = Path(temporary_root)
        key_dir = temporary / "keys"
        key_dir.mkdir()
        generate_keys(key_dir, kid=P6E_JWT_KID, private_filename=Path("jwt-private") / f"{P6E_JWT_KID}.pem")
        validate_key_material(key_dir)
        state_root = Path(args.state_dir) if args.state_dir else temporary / "state"
        state_path = state_root / "release-pointers.json"
        release_a_identity = {"release": str(manifest_a["release"]), "git_commit": str(manifest_a["git_commit"])}
        release_b_identity = {"release": str(manifest_b["release"]), "git_commit": str(manifest_b["git_commit"])}
        environment = deployment_environment(key_dir, str(manifest_a["release"]), str(manifest_a["git_commit"]))
        environment["P6E_COMPOSE_PROJECT"] = project
        probe_image = prepare_probe_image(project, environment)
        environment["P6E_PROBE_IMAGE"] = probe_image
        override_a = temporary / "release-a.yml"
        override_b = temporary / "release-b.yml"
        write_override(override_a, manifest_a)
        write_override(override_b, manifest_b, fail_readiness=args.failure_mode == "readiness")
        snapshot_before = None
        exit_code = 1
        try:
            deploy(project, environment, manifest_a, override_a, smoke_command=args.smoke_a, health_only=args.health_only)
            snapshot_before = snapshot(args.snapshot_command, environment, label="release A")
            write_state(state_path, release_a_identity, None)
            state = ReleaseState(release_a_identity, None)
            print(f"P6E RELEASE A PASS: {manifest_a['release']} ({len(migration_paths)} migration files checked)")

            environment.update({"BANKCORE_RELEASE_VERSION": str(manifest_b["release"]), "BANKCORE_GIT_COMMIT": str(manifest_b["git_commit"])})
            b_smoke = args.smoke_b
            if args.failure_mode == "smoke":
                b_smoke = args.failure_command
            try:
                deploy(project, environment, manifest_b, override_b, smoke_command=b_smoke, health_only=args.health_only)
                write_state(state_path, release_b_identity, state.current)
                state = ReleaseState(release_b_identity, state.current)
                current_state = read_state(state_path)
                if current_state.current != release_b_identity or current_state.previous != release_a_identity:
                    raise RuntimeError("Release pointers do not identify B as current and A as previous.")
                print(f"P6E RELEASE B PASS: {manifest_b['release']}")
            except Exception as failure:
                print(f"P6E EXPECTED FAILURE: {type(failure).__name__}")
                environment.update({"BANKCORE_RELEASE_VERSION": str(manifest_a["release"]), "BANKCORE_GIT_COMMIT": str(manifest_a["git_commit"])})
                # Restore A and compare the pre-failure snapshot before running
                # the post-rollback smoke. The smoke intentionally creates a
                # new controlled operation, so it must not contaminate the
                # preservation assertion.
                deploy(project, environment, manifest_a, override_a, smoke_command=None, health_only=True)
                after = snapshot(args.snapshot_command, environment, label="rollback")
                if snapshot_before is not None and after != snapshot_before:
                    raise RuntimeError("Financial snapshot changed across rollback.") from failure
                smoke(args.smoke_a, environment, release=str(manifest_a["release"]), health_only=args.health_only)
                write_state(state_path, release_a_identity, None)
                current_state = read_state(state_path)
                if current_state.current != release_a_identity or current_state.previous is not None:
                    raise RuntimeError("Release pointers do not identify A as the restored release.")
                print(f"P6E ROLLBACK PASS: restored {manifest_a['release']}; financial snapshot preserved")
            exit_code = 0
        finally:
            teardown = compose(project, environment, override_a, "down", "-v", "--remove-orphans")
            if teardown.returncode and exit_code == 0:
                exit_code = teardown.returncode
            try:
                if teardown.returncode == 0:
                    verify_no_residue(project, environment, override_a)
            finally:
                remove_probe_image(probe_image, environment)
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the disposable P6-E deployment and rollback contract.")
    parser.add_argument("--release-a", type=Path, required=True, help="Verified P6-D manifest for the known-good release.")
    parser.add_argument("--release-b", type=Path, required=True, help="Verified P6-D manifest for the candidate release.")
    parser.add_argument("--smoke-a", help="Command for the release-A financial smoke/E2E test.")
    parser.add_argument("--smoke-b", help="Command for the release-B financial smoke/E2E test.")
    parser.add_argument("--snapshot-command", help="Command returning a canonical financial-state snapshot.")
    parser.add_argument("--failure-command", default="exit 97", help="Controlled failure command for --failure-mode smoke.")
    parser.add_argument("--failure-mode", choices=("none", "readiness", "smoke"), default="none")
    parser.add_argument("--health-only", action="store_true", help="Structural-only local validation; not a financial acceptance run.")
    parser.add_argument("--state-dir", type=Path, help="Optional local directory for current/previous release pointers.")
    args = parser.parse_args()
    docker_info = run_command(["docker", "info", "--format", "{{.ServerVersion}}"])
    if docker_info.returncode:
        raise SystemExit("Docker Engine is not available for the disposable P6-E runner.")
    return run_scenario(args)


if __name__ == "__main__":
    raise SystemExit(main())
