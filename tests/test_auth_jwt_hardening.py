import importlib
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, PublicFormat
    from jose import jwt as jose_jwt
except ImportError:  # pragma: no cover - the service requirements provide these packages.
    rsa = None
    jose_jwt = None


ROOT = Path(__file__).resolve().parents[1]
AUTH_ROOT = ROOT / "services/auth-service"


@unittest.skipUnless(jose_jwt and rsa, "requires auth service crypto dependencies")
class AuthenticationHardeningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.keys_dir = Path(cls.temp_dir.name) / "public"
        cls.keys_dir.mkdir()
        cls.private_path = Path(cls.temp_dir.name) / "private.pem"
        cls.write_key("key-a")
        cls.env = patch.dict(
            os.environ,
            {
                "DATABASE_URL": "postgresql+asyncpg://test",
                "REDIS_URL": "redis://test",
                "JWT_ALGORITHM": "RS256",
                "JWT_ISSUER": "bankcore-auth",
                "JWT_AUDIENCE": "bankcore-api",
                "JWT_ACTIVE_KID": "key-a",
                "JWT_PRIVATE_KEY_PATH": str(cls.private_path),
                "JWT_PUBLIC_KEYS_DIR": str(cls.keys_dir),
                "AUTH_SERVICE_TOKEN": "service-test-token",
            },
        )
        cls.env.start()
        sys.path.insert(0, str(AUTH_ROOT))
        cls.security = importlib.import_module("app.security")

    @classmethod
    def tearDownClass(cls):
        for module_name in list(sys.modules):
            if module_name == "app" or module_name.startswith("app."):
                sys.modules.pop(module_name, None)
        if str(AUTH_ROOT) in sys.path:
            sys.path.remove(str(AUTH_ROOT))
        cls.env.stop()
        cls.temp_dir.cleanup()

    @classmethod
    def write_key(cls, kid):
        private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private_pem = private.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
        public_pem = private.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
        if kid == "key-a":
            cls.private_path.write_bytes(private_pem)
        (cls.keys_dir / f"{kid}.pem").write_bytes(public_pem)
        return private_pem

    def claims(self, **changes):
        now = int(datetime.now(timezone.utc).timestamp())
        payload = {
            "sub": "user-1",
            "iss": "bankcore-auth",
            "aud": "bankcore-api",
            "iat": now,
            "nbf": now,
            "exp": now + 300,
            "jti": "test-jti",
        }
        payload.update(changes)
        return payload

    def raw_token(self, payload=None, *, kid="key-a", algorithm="RS256", key=None):
        if key is None:
            key = self.private_path.read_bytes()
        return jose_jwt.encode(
            payload or self.claims(),
            key,
            algorithm=algorithm,
            headers={"kid": kid},
        )

    def assert_unauthorized(self, token):
        with self.assertRaises(HTTPException) as context:
            self.security.decode_access_token(token)
        self.assertEqual(context.exception.status_code, 401)

    def test_access_token_contains_required_claims_and_kid(self):
        token = self.security.create_access_token({"sub": "user-1", "tax_id": "123"})
        header = jose_jwt.get_unverified_header(token)
        payload = self.security.decode_access_token(token)
        self.assertEqual(header["alg"], "RS256")
        self.assertEqual(header["kid"], "key-a")
        self.assertTrue({"sub", "iss", "aud", "iat", "nbf", "exp", "jti"}.issubset(payload))

    def test_invalid_claims_and_signature_are_rejected(self):
        cases = [
            ("issuer", {"iss": "wrong-issuer"}),
            ("audience", {"aud": "wrong-audience"}),
            ("expired", {"exp": int(datetime.now(timezone.utc).timestamp()) - 1}),
            ("future nbf", {"nbf": int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp())}),
            ("missing sub", {"sub": None}),
            ("missing exp", {"exp": None}),
            ("unknown kid", {}, "unknown-kid"),
        ]
        for case in cases:
            with self.subTest(case=case[0]):
                kid = case[2] if len(case) > 2 else "key-a"
                self.assert_unauthorized(self.raw_token(self.claims(**case[1]), kid=kid))

        token = self.raw_token()
        header, payload, signature = token.split(".")
        replacement = "A" if signature[0] != "A" else "B"
        tampered = ".".join((header, payload, replacement + signature[1:]))
        self.assert_unauthorized(tampered)
        self.assert_unauthorized(self.raw_token(algorithm="HS256", key="wrong-secret"))

    def test_each_required_claim_is_enforced(self):
        for claim in ("sub", "iss", "aud", "iat", "nbf", "exp", "jti"):
            with self.subTest(claim=claim):
                payload = self.claims()
                payload.pop(claim)
                self.assert_unauthorized(self.raw_token(payload))

    def test_rotation_keeps_previous_key_until_removed(self):
        token_a = self.raw_token()
        private_b = self.write_key("key-b")
        self.security.settings.JWT_ACTIVE_KID = "key-b"
        token_b = self.raw_token(key=private_b, kid="key-b")
        self.security.decode_access_token(token_a)
        self.security.decode_access_token(token_b)
        (self.keys_dir / "key-a.pem").unlink()
        self.assert_unauthorized(token_a)
        self.security.decode_access_token(token_b)

    def test_internal_token_has_separate_audience_and_scope(self):
        token = self.security.create_internal_service_token("transactions")
        payload = self.security.decode_token(
            token,
            audience="bankcore-internal",
            required_scope="service:transactions",
        )
        self.assertEqual(payload["scope"], "service:transactions")
        self.assert_unauthorized(token)
        with self.assertRaises(HTTPException) as context:
            self.security.decode_token(
                self.security.create_access_token({"sub": "user-1"}),
                audience="bankcore-internal",
                required_scope="service:transactions",
            )
        self.assertEqual(context.exception.status_code, 401)

    def test_local_rate_limit_is_used_when_redis_is_unavailable(self):
        limiter = importlib.import_module("app.limiter")
        limiter._local_attempts.clear()

        async def unavailable():
            raise RuntimeError("redis unavailable")

        async def exercise():
            with patch.object(limiter, "_redis", new=unavailable):
                for _ in range(limiter.LOCAL_LIMIT):
                    await limiter.assert_login_allowed("12345678900")
                with self.assertRaises(HTTPException) as context:
                    await limiter.assert_login_allowed("12345678900")
                self.assertEqual(context.exception.status_code, 429)

        import asyncio
        asyncio.run(exercise())
        limiter._local_attempts.clear()


if __name__ == "__main__":
    unittest.main()
