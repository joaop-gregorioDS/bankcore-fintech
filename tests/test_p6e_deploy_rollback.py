import json
import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "p6e-deploy-rollback.py"
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("p6e_deploy_rollback", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["p6e_deploy_rollback"] = MODULE
SPEC.loader.exec_module(MODULE)

CUSTOM_SERVICES = MODULE.CUSTOM_SERVICES
load_verified_manifest = MODULE.load_verified_manifest
validate_migration_policy = MODULE.validate_migration_policy
write_override = MODULE.write_override
key_material_paths = MODULE.key_material_paths
validate_key_material = MODULE.validate_key_material
generate_keys = MODULE.generate_keys


def manifest(tmp_path: Path) -> Path:
    sbom = tmp_path / "sbom"
    sbom.mkdir()
    images = []
    for name in sorted(CUSTOM_SERVICES):
        (sbom / f"{name}.cdx.json").write_text('{"bomFormat":"CycloneDX","specVersion":"1.5"}\n', encoding="utf-8")
        image = f"ghcr.io/joaop-gregoriods/bankcore-{name}:p6e-a"
        digest = "sha256:" + __import__("hashlib").sha256(name.encode("utf-8")).hexdigest()
        images.append({"name": name, "image": image, "tag": "p6e-a", "digest": digest, "immutable_ref": f"{image}@{digest}", "sbom": f"sbom/{name}.cdx.json"})
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"schema_version": 1, "release": "p6e-a", "git_commit": "5b8557e", "repository": "joaop-gregorioDS/bankcore-fintech", "workflow": "p6d-release.yml", "images": images, "verification": {"registry": "ghcr.io", "signature": "cosign-keyless", "provenance": "github-artifact-attestation", "sbom_format": "CycloneDX JSON"}}), encoding="utf-8")
    return path


class P6EDeploymentRollbackTests(unittest.TestCase):
    def test_verified_manifest_requires_all_four_images_and_sboms(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            loaded = load_verified_manifest(manifest(Path(directory)))
            self.assertEqual({item["name"] for item in loaded["images"]}, set(CUSTOM_SERVICES))


    def test_override_pins_every_release_service(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = manifest(root)
            override = root / "override.yml"
            write_override(override, json.loads(source.read_text(encoding="utf-8")))
            text = override.read_text(encoding="utf-8")
            self.assertEqual(text.count("@sha256:"), 9)
            self.assertIn("pull_policy: always", text)
            self.assertNotIn("build:", text)


    def test_migration_policy_excludes_downgrades(self):
        self.assertEqual(validate_migration_policy(changed_paths=[]), [])


    def test_migration_policy_rejects_destructive_upgrade(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            root = Path(directory)
            version_dir = root / "infra/postgres/alembic/transactions/versions"
            version_dir.mkdir(parents=True)
            (version_dir / "bad.py").write_text("def upgrade():\n    op.drop_table('accounts')\n\ndef downgrade():\n    pass\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Destructive migration"):
                validate_migration_policy(root, changed_paths=[version_dir / "bad.py"])

    def test_p6e_key_material_uses_active_kid(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            root = Path(directory)
            generate_keys(root, kid="p6e", private_filename=Path("jwt-private") / "p6e.pem")
            private_path, public_path = key_material_paths(root, "p6e")
            self.assertTrue(private_path.is_file())
            self.assertTrue(public_path.is_file())
            validate_key_material(root, "p6e")

    def test_p6e_key_preflight_fails_before_rollout(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "key preflight failed"):
                validate_key_material(Path(directory), "p6e")


if __name__ == "__main__":
    unittest.main()
