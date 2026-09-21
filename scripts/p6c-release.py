import hashlib
import json
import os
import secrets
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from e2e import generate_keys


ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_FILES = ("-f", "docker-compose.production.yml", "-f", "docker-compose.production.local.yml")
SOURCE_URL = "https://github.com/joaop-gregorioDS/bankcore-fintech"


def redact(output: str, environment: dict[str, str]) -> str:
    result = output
    for name in (
        "POSTGRES_PASSWORD",
        "AUTH_SERVICE_TOKEN",
        "RATE_LIMIT_KEY_SECRET",
        "GRAFANA_ADMIN_PASSWORD",
    ):
        value = environment.get(name)
        if value:
            result = result.replace(value, "[REDACTED]")
    return result[-4000:]


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


def compose(
    project: str,
    environment: dict[str, str],
    *arguments: str,
    extra_files: tuple[str, ...] = (),
) -> subprocess.CompletedProcess[str]:
    files: list[str] = ["-f", "docker-compose.production.yml", "-f", "docker-compose.production.local.yml"]
    for extra_file in extra_files:
        files.extend(("-f", extra_file))
    return run_command(["docker", "compose", "-p", project, *files, *arguments], environment)


def require_compose(
    project: str,
    environment: dict[str, str],
    *arguments: str,
    extra_files: tuple[str, ...] = (),
) -> str:
    result = compose(project, environment, *arguments, extra_files=extra_files)
    if result.returncode:
        raise RuntimeError(
            f"Compose step failed ({result.returncode}): {' '.join(arguments)}\n"
            f"{redact(result.stderr or result.stdout, environment)}"
        )
    return result.stdout


def git_revision() -> str:
    return require_command(["git", "rev-parse", "HEAD"], {}).strip()


def image_info(image: str, environment: dict[str, str]) -> dict[str, object]:
    output = require_command(["docker", "image", "inspect", image], environment)
    return json.loads(output)[0]


def ensure_image(image: str, environment: dict[str, str]) -> None:
    result = run_command(["docker", "image", "inspect", image], environment)
    if result.returncode:
        require_command(["docker", "pull", image], environment)


def image_digest(image: str, environment: dict[str, str]) -> tuple[str, dict[str, object]]:
    info = image_info(image, environment)
    repo_digests = info.get("RepoDigests") or []
    for repo_digest in repo_digests:
        if "@sha256:" in repo_digest:
            return repo_digest.rsplit("@", 1)[1], info
    image_id = str(info.get("Id", ""))
    if image_id.startswith("sha256:"):
        return image_id, info
    raise RuntimeError(f"Image has no SHA-256 content identity: {image}")


def compose_records(
    project: str,
    environment: dict[str, str],
    *,
    extra_files: tuple[str, ...] = (),
) -> list[dict[str, object]]:
    output = require_compose(project, environment, "ps", "-a", "--format", "json", extra_files=extra_files)
    if output.lstrip().startswith("["):
        return list(json.loads(output))
    return [json.loads(line) for line in output.splitlines() if line.strip()]


def service_container_id(records: list[dict[str, object]], service: str) -> str:
    for record in records:
        if record.get("Service") == service:
            return str(record["ID"])
    raise RuntimeError(f"Service was not created: {service}")


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_sbom(image: str, destination: Path, environment: dict[str, str]) -> None:
    require_command(
        [
            "docker",
            "scout",
            "sbom",
            f"local://{image}",
            "--format",
            "cyclonedx",
            "--output",
            str(destination),
        ],
        environment,
    )
    try:
        sbom = json.loads(destination.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Generated SBOM is not valid JSON: {destination}") from error
    if sbom.get("bomFormat") != "CycloneDX" or not sbom.get("specVersion"):
        raise RuntimeError(f"Generated SBOM is not a CycloneDX document: {destination}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def scan_artifacts_and_image_metadata(
    output_dir: Path,
    image_names: list[str],
    environment: dict[str, str],
) -> None:
    forbidden_values = [
        value
        for name in (
            "POSTGRES_PASSWORD",
            "AUTH_SERVICE_TOKEN",
            "RATE_LIMIT_KEY_SECRET",
            "GRAFANA_ADMIN_PASSWORD",
        )
        if (value := environment.get(name))
    ]
    forbidden_markers = (
        "BEGIN PRIVATE KEY",
        "JWT_PRIVATE_KEY=",
        "POSTGRES_PASSWORD=",
        "AUTH_SERVICE_TOKEN=",
        "RATE_LIMIT_KEY_SECRET=",
        "Authorization: Bearer",
    )
    for path in output_dir.rglob("*"):
        if path.is_file():
            content = path.read_text(encoding="utf-8", errors="replace")
            if any(value in content for value in forbidden_values) or any(
                marker in content for marker in forbidden_markers
            ):
                raise RuntimeError(f"Sensitive material detected in release artifact: {path}")

    for image in image_names:
        info = image_info(image, environment)
        history = require_command(["docker", "history", "--no-trunc", "--format", "{{.CreatedBy}}", image], environment)
        inspected = json.dumps(info, sort_keys=True)
        metadata = inspected + history
        if any(value in metadata for value in forbidden_values) or any(
            marker in metadata for marker in forbidden_markers
        ):
            raise RuntimeError(f"Sensitive material detected in image metadata/history: {image}")


def write_checksums(output_dir: Path) -> None:
    files = sorted(
        path
        for path in output_dir.rglob("*")
        if path.is_file() and path.name != "checksums.sha256"
    )
    lines = [f"{sha256_file(path)}  {path.relative_to(output_dir).as_posix()}" for path in files]
    (output_dir / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify_runtime_digests(
    project: str,
    environment: dict[str, str],
    service_to_image: dict[str, str],
    images: dict[str, dict[str, str]],
    *,
    extra_files: tuple[str, ...],
) -> None:
    records = compose_records(project, environment, extra_files=extra_files)
    for service, logical_image in service_to_image.items():
        container_id = service_container_id(records, service)
        actual_id = require_command(
            ["docker", "inspect", "--format", "{{.Image}}", container_id], environment
        ).strip()
        expected = images[logical_image]["digest"]
        if actual_id != expected:
            raise RuntimeError(
                f"Immutable image mismatch for {service}: expected {expected}, got {actual_id}"
            )


def verify_no_project_residue(project: str, environment: dict[str, str]) -> None:
    containers = compose(project, environment, "ps", "-aq").stdout.strip()
    volumes = require_command(
        [
            "docker",
            "volume",
            "ls",
            "-q",
            "--filter",
            f"label=com.docker.compose.project={project}",
        ],
        environment,
    ).strip()
    if containers or volumes:
        raise RuntimeError("P6-C teardown left Docker resources behind.")


def main() -> int:
    docker_info = run_command(["docker", "info", "--format", "{{.ServerVersion}}"])
    if docker_info.returncode:
        raise RuntimeError("Docker Engine is not available for the P6-C release test.")

    revision = git_revision()
    release = f"p6c-local-{revision[:12]}"
    output_dir = ROOT / "artifacts" / "p6c" / release
    if output_dir.exists():
        shutil.rmtree(output_dir)
    (output_dir / "sbom").mkdir(parents=True)

    project = f"bankcore-p6c-{uuid.uuid4().hex[:8]}"
    recheck_image = f"bankcore.local/bankcore-auth-rebuild-check:{release}"
    environment = os.environ.copy()
    with tempfile.TemporaryDirectory(prefix="bankcore-p6c-") as temporary_root:
        key_dir = Path(temporary_root)
        generate_keys(key_dir)
        environment.update(
            {
                "POSTGRES_PASSWORD": secrets.token_urlsafe(24),
                "AUTH_SERVICE_TOKEN": secrets.token_urlsafe(32),
                "RATE_LIMIT_KEY_SECRET": secrets.token_urlsafe(32),
                "GRAFANA_ADMIN_PASSWORD": secrets.token_urlsafe(24),
                "JWT_ACTIVE_KID": "e2e",
                "JWT_PRIVATE_KEY_FILE": (key_dir / "jwt-private.pem").as_posix(),
                "JWT_PUBLIC_KEYS_HOST_DIR": (key_dir / "jwt-public").as_posix(),
                "BANKCORE_IMAGE_REGISTRY": "bankcore.local",
                "BANKCORE_RELEASE_VERSION": release,
                "BANKCORE_GIT_COMMIT": revision,
                "GATEWAY_PORT": os.environ.get("P6C_GATEWAY_PORT", "18088"),
                "PROMETHEUS_PORT": os.environ.get("P6C_PROMETHEUS_PORT", "19098"),
                "GRAFANA_PORT": os.environ.get("P6C_GRAFANA_PORT", "13008"),
                "DEMO_MODE": "false",
            }
        )
        exit_code = 1
        immutable_file = output_dir / "docker-compose.production.immutable.yml"
        try:
            require_compose(project, environment, "--profile", "verification", "config", "--quiet")
            require_compose(
                project,
                environment,
                "--profile",
                "verification",
                "build",
                "auth-service",
                "transactions-service",
                "risk-service",
                "migrate-audit",
                "p6b-e2e-runner",
            )

            custom_images = {
                "auth": f"bankcore.local/bankcore-auth:{release}",
                "transactions": f"bankcore.local/bankcore-transactions:{release}",
                "risk": f"bankcore.local/bankcore-risk:{release}",
                "audit": f"bankcore.local/bankcore-audit:{release}",
            }
            infrastructure_images = {
                "postgres": "postgres:16.4-alpine3.20",
                "redis": "redis:7.4.1-alpine3.20",
                "kafka": "apache/kafka:3.9.0",
                "otel-collector": "otel/opentelemetry-collector-contrib:0.123.0",
                "prometheus": "prom/prometheus:v2.55.1",
                "grafana": "grafana/grafana:11.3.1",
                "nginx": "nginxinc/nginx-unprivileged:1.27.1-alpine",
            }
            for image in infrastructure_images.values():
                ensure_image(image, environment)

            images: dict[str, dict[str, str]] = {}
            for logical_name, image in {**custom_images, **infrastructure_images}.items():
                digest, info = image_digest(image, environment)
                if image.endswith(":latest") or image.rsplit(":", 1)[-1] == "latest":
                    raise RuntimeError(f"Mutable latest tag is forbidden in the release: {image}")
                image_labels = info.get("Config", {}).get("Labels", {}) or {}
                if logical_name in custom_images:
                    expected_labels = {
                        "org.opencontainers.image.source": SOURCE_URL,
                        "org.opencontainers.image.revision": revision,
                        "org.opencontainers.image.version": release,
                    }
                    for label, expected in expected_labels.items():
                        if image_labels.get(label) != expected:
                            raise RuntimeError(f"OCI metadata mismatch for {logical_name}: {label}")
                images[logical_name] = {
                    "image": image,
                    "repository": image.rsplit(":", 1)[0],
                    "tag": image.rsplit(":", 1)[1],
                    "digest": digest,
                    "immutable_ref": f"{image.rsplit(':', 1)[0]}@{digest}",
                }
                if "@sha256:" not in images[logical_name]["immutable_ref"]:
                    raise RuntimeError(f"Release image is not digest-addressable: {image}")

            sbom_files: dict[str, str] = {}
            for logical_name in custom_images:
                filename = f"{logical_name}.cdx.json"
                build_sbom(images[logical_name]["image"], output_dir / "sbom" / filename, environment)
                sbom_files[logical_name] = f"sbom/{filename}"

            manifest = {
                "schema_version": 1,
                "release": release,
                "git_commit": revision,
                "source": SOURCE_URL,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "images": images,
                "sbom": sbom_files,
                "signing": {"status": "not-configured", "phase": "P6-D"},
            }
            write_json(output_dir / "manifest.json", manifest)

            service_to_image = {
                "postgres": "postgres",
                "audit-postgres": "postgres",
                "redis": "redis",
                "kafka": "kafka",
                "kafka-init": "kafka",
                "otel-collector": "otel-collector",
                "prometheus": "prometheus",
                "grafana": "grafana",
                "migrate-auth": "auth",
                "migrate-transactions": "transactions",
                "migrate-risk": "risk",
                "migrate-audit": "audit",
                "auth-service": "auth",
                "transactions-service": "transactions",
                "risk-service": "risk",
                "outbox-publisher": "transactions",
                "audit-consumer": "audit",
                "nginx": "nginx",
            }
            immutable_lines = ["services:"]
            for service, logical_image in service_to_image.items():
                immutable_lines.extend(
                    [f"  {service}:", f"    image: {images[logical_image]['immutable_ref']}"]
                )
            immutable_file.write_text("\n".join(immutable_lines) + "\n", encoding="utf-8")

            recheck_output = run_command(
                [
                    "docker",
                    "build",
                    "--no-cache",
                    "--build-arg",
                    f"OCI_SOURCE={SOURCE_URL}",
                    "--build-arg",
                    f"OCI_REVISION={revision}",
                    "--build-arg",
                    f"OCI_VERSION={release}",
                    "--tag",
                    recheck_image,
                    "--file",
                    "services/auth-service/Dockerfile",
                    ".",
                ],
                environment,
            )
            if recheck_output.returncode:
                raise RuntimeError(
                    f"Unchanged-source rebuild failed ({recheck_output.returncode}):\n"
                    f"{redact(recheck_output.stderr or recheck_output.stdout, environment)}"
                )
            rebuilt_digest, _ = image_digest(recheck_image, environment)
            original_digest = images["auth"]["digest"]
            reproducibility = {
                "image": "auth",
                "source_commit": revision,
                "original_digest": original_digest,
                "rebuild_digest": rebuilt_digest,
                "status": "byte-identical" if original_digest == rebuilt_digest else "different",
                "explanation": (
                    "Same local toolchain and unchanged source produced the same content identity."
                    if original_digest == rebuilt_digest
                    else "Difference is recorded because the Dockerfile uses external base/package inputs; P6-C does not claim byte-for-byte reproducibility."
                ),
            }
            write_json(output_dir / "reproducibility.json", reproducibility)
            run_command(["docker", "image", "rm", recheck_image], environment)

            immutable_relative = str(immutable_file.relative_to(ROOT))
            immutable_files = (immutable_relative,)
            require_compose(
                project,
                environment,
                "--profile",
                "verification",
                "config",
                "--quiet",
                extra_files=immutable_files,
            )
            require_compose(project, environment, "up", "-d", "--wait", extra_files=immutable_files)
            verify_runtime_digests(
                project,
                environment,
                service_to_image,
                images,
                extra_files=immutable_files,
            )
            require_compose(
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
                extra_files=immutable_files,
            )

            require_compose(
                project,
                environment,
                "stop",
                "otel-collector",
                "prometheus",
                "grafana",
                extra_files=immutable_files,
            )
            require_compose(
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
                extra_files=immutable_files,
            )
            scan_artifacts_and_image_metadata(
                output_dir,
                list(custom_images.values()),
                environment,
            )
            write_checksums(output_dir)
            exit_code = 0
        finally:
            teardown = compose(project, environment, "down", "-v", "--remove-orphans")
            if teardown.returncode and exit_code == 0:
                exit_code = teardown.returncode
            if teardown.returncode == 0:
                verify_no_project_residue(project, environment)
            run_command(["docker", "image", "rm", recheck_image], environment)

        if exit_code == 0:
            print(f"P6C RELEASE PASS: {release}; artifacts={output_dir}")
        return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
