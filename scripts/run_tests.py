import os
import tempfile
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def generate_test_keys(root: Path) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_path = root / "jwt-private.pem"
    public_dir = root / "jwt-public"
    public_dir.mkdir()
    private_path.write_bytes(
        private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    (public_dir / "test-runner.pem").write_bytes(
        private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    os.environ.update(
        {
            "JWT_ALGORITHM": "RS256",
            "JWT_ACTIVE_KID": "test-runner",
            "JWT_PRIVATE_KEY_PATH": str(private_path),
            "JWT_PUBLIC_KEYS_DIR": str(public_dir),
        }
    )


def main() -> int:
    selector = os.getenv("TEST_SUITE", "all")
    with tempfile.TemporaryDirectory(prefix="bankcore-test-keys-") as temporary_root:
        generate_test_keys(Path(temporary_root))
        if os.getenv("TEST_FORCE_FAILURE", "").lower() == "true":
            return 97
        args = ["-q"]
        if selector != "all":
            args.extend(["-m", selector])
        return pytest.main(args)


if __name__ == "__main__":
    raise SystemExit(main())
