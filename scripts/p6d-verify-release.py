import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path


DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
MARKERS = (
    "BEGIN PRIVATE KEY",
    "POSTGRES_PASSWORD=",
    "AUTH_SERVICE_TOKEN=",
    "RATE_LIMIT_KEY_SECRET=",
    "Authorization: Bearer",
)


def run(command: list[str], *, env: dict[str, str] | None = None) -> str:
    """Run a command and return stdout; callers must treat the result as text."""
    result = subprocess.run(command, text=True, capture_output=True, env=env, check=False)
    if result.returncode:
        raise RuntimeError(
            f"Command failed ({result.returncode}): {' '.join(command)}\n"
            f"{(result.stderr or result.stdout)[-4000:]}"
        )
    return result.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a published P6-D GHCR release.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--skip-attestations", action="store_true")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    manifest_text = args.manifest.read_text(encoding="utf-8", errors="replace")
    if any(marker in manifest_text for marker in MARKERS):
        raise SystemExit("Sensitive marker found in release manifest.")
    if manifest["repository"] != args.repository or manifest["workflow"] != args.workflow:
        raise SystemExit("Manifest repository/workflow does not match the verifier policy.")
    if ":latest" in json.dumps(manifest):
        raise SystemExit("latest is forbidden in a P6-D release manifest.")

    cosign = shutil.which("cosign")
    gh = shutil.which("gh")
    if not args.skip_attestations and (not cosign or not gh):
        raise SystemExit("cosign and gh are required for signature/provenance verification.")

    identity = f"https://github.com/{args.repository}/.github/workflows/{args.workflow}@{args.ref}"
    for image in manifest["images"]:
        digest = image["digest"]
        immutable_ref = image["immutable_ref"]
        if not DIGEST_RE.fullmatch(digest) or immutable_ref != f"{image['image']}@{digest}":
            raise SystemExit(f"Manifest digest/ref mismatch for {image['name']}.")

        sbom_path = args.manifest.parent / image["sbom"]
        sbom = json.loads(sbom_path.read_text(encoding="utf-8"))
        if sbom.get("bomFormat") != "CycloneDX":
            raise SystemExit(f"SBOM is not CycloneDX for {image['name']}.")
        sbom_text = sbom_path.read_text(encoding="utf-8", errors="replace")
        if any(marker in sbom_text for marker in MARKERS):
            raise SystemExit(f"Sensitive marker found in SBOM for {image['name']}.")

        run(["docker", "pull", immutable_ref])
        inspected = json.loads(run(["docker", "image", "inspect", immutable_ref]))[0]
        inspected_text = json.dumps(inspected, sort_keys=True)
        if any(marker in inspected_text for marker in MARKERS):
            raise SystemExit(f"Sensitive marker found in image metadata for {image['name']}.")
        repo_digests = inspected.get("RepoDigests") or []
        if immutable_ref not in repo_digests:
            raise SystemExit(f"Pulled image does not retain the manifest digest for {image['name']}.")
        history_text = run(["docker", "history", "--no-trunc", "--format", "{{.CreatedBy}}", immutable_ref])
        if any(marker in history_text for marker in MARKERS):
            raise SystemExit(f"Sensitive marker found in image history for {image['name']}.")

        if not args.skip_attestations:
            run(
                [
                    "cosign",
                    "verify",
                    immutable_ref,
                    "--certificate-identity",
                    identity,
                    "--certificate-oidc-issuer",
                    "https://token.actions.githubusercontent.com",
                ]
            )
            run(
                [
                    "gh",
                    "attestation",
                    "verify",
                    f"oci://{immutable_ref}",
                    "-R",
                    args.repository,
                    "--signer-workflow",
                    f"{args.repository}/.github/workflows/{args.workflow}",
                ]
            )

        print(f"P6D VERIFIED {image['name']} {digest}")

    print("P6D RELEASE VERIFICATION PASS: GHCR digest, pull, SBOM, signature and provenance")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
