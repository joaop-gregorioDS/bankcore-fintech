import importlib.util
import json
import subprocess
import sys
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "p6d-verify-release.py"


def load_verifier():
    spec = importlib.util.spec_from_file_location("p6d_verify_release", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class P6DVerifierTests(unittest.TestCase):
    def test_run_returns_stdout_and_reports_command_failures(self):
        verifier = load_verifier()

        with mock.patch.object(
            verifier.subprocess,
            "run",
            return_value=subprocess.CompletedProcess(
                args=["tool", "success"], returncode=0, stdout="safe output\n", stderr=""
            ),
        ):
            self.assertEqual(verifier.run(["tool", "success"]), "safe output\n")

        with mock.patch.object(
            verifier.subprocess,
            "run",
            return_value=subprocess.CompletedProcess(
                args=["tool", "failure"], returncode=7, stdout="", stderr="failure details\n"
            ),
        ):
            with self.assertRaises(RuntimeError) as raised:
                verifier.run(["tool", "failure"])
            self.assertIn("Command failed (7)", str(raised.exception))
            self.assertIn("failure details", str(raised.exception))

    def test_main_verifies_digest_sbom_cosign_and_provenance(self):
        verifier = load_verifier()
        tmp_path = Path(__import__("tempfile").mkdtemp())
        digest = "sha256:" + "a" * 64
        image = "ghcr.io/joaop-gregoriods/bankcore-auth"
        immutable_ref = f"{image}@{digest}"
        manifest = tmp_path / "manifest.json"
        sbom = tmp_path / "sbom" / "auth.cdx.json"
        sbom.parent.mkdir()
        sbom.write_text(json.dumps({"bomFormat": "CycloneDX", "components": []}), encoding="utf-8")
        manifest.write_text(
            json.dumps(
                {
                    "repository": "joaop-gregorioDS/bankcore-fintech",
                    "workflow": "p6d-release.yml",
                    "images": [
                        {
                            "name": "auth",
                            "image": image,
                            "digest": digest,
                            "immutable_ref": immutable_ref,
                            "sbom": "sbom/auth.cdx.json",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        calls = []

        def fake_run(command, *, env=None):
            calls.append(command)
            if command[:3] == ["docker", "image", "inspect"]:
                return json.dumps([{"RepoDigests": [immutable_ref]}])
            if command[:2] == ["docker", "history"]:
                return "safe layer\n"
            return ""

        with mock.patch.object(verifier, "run", side_effect=fake_run):
            with mock.patch.object(verifier.shutil, "which", side_effect=lambda name: f"/bin/{name}"):
                with mock.patch.object(
                    sys,
                    "argv",
                    [
                        str(SCRIPT),
                        "--manifest",
                        str(manifest),
                        "--repository",
                        "joaop-gregorioDS/bankcore-fintech",
                        "--workflow",
                        "p6d-release.yml",
                        "--ref",
                        "refs/heads/main",
                    ],
                ):
                    self.assertEqual(verifier.main(), 0)

        self.assertIn(["docker", "pull", immutable_ref], calls)
        self.assertIn(["docker", "image", "inspect", immutable_ref], calls)
        self.assertIn(["docker", "history", "--no-trunc", "--format", "{{.CreatedBy}}", immutable_ref], calls)
        self.assertIn(
            [
                "cosign",
                "verify",
                immutable_ref,
                "--certificate-identity",
                "https://github.com/joaop-gregorioDS/bankcore-fintech/.github/workflows/p6d-release.yml@refs/heads/main",
                "--certificate-oidc-issuer",
                "https://token.actions.githubusercontent.com",
            ],
            calls,
        )
        self.assertIn(
            [
                "gh",
                "attestation",
                "verify",
                f"oci://{immutable_ref}",
                "-R",
                "joaop-gregorioDS/bankcore-fintech",
                "--signer-workflow",
                "joaop-gregorioDS/bankcore-fintech/.github/workflows/p6d-release.yml",
            ],
            calls,
        )
