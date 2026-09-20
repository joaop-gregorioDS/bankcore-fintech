import re
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from jwt import PyJWTError, decode, encode, get_unverified_header
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def _unauthorized(detail: str = "Token inválido ou expirado.") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def _load_private_key() -> str:
    try:
        return Path(settings.JWT_PRIVATE_KEY_PATH).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise RuntimeError("JWT private key is unavailable.") from exc


def _load_public_key(kid: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", kid):
        raise _unauthorized("Token com identificador de chave inválido.")
    try:
        return (Path(settings.JWT_PUBLIC_KEYS_DIR) / f"{kid}.pem").read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise _unauthorized("Token com chave desconhecida.") from exc


def _encode_token(data: dict, *, audience: str, expires_in: int, scope: str | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": data["sub"],
        "iss": settings.JWT_ISSUER,
        "aud": audience,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
        "jti": str(uuid4()),
    }
    for key in ("tax_id", "name"):
        if key in data:
            payload[key] = data[key]
    if scope:
        payload["scope"] = scope
    return encode(
        payload,
        _load_private_key(),
        algorithm=settings.JWT_ALGORITHM,
        headers={"kid": settings.JWT_ACTIVE_KID, "typ": "JWT"},
    )


def create_access_token(data: dict) -> str:
    return _encode_token(
        data,
        audience=settings.JWT_AUDIENCE,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def create_internal_service_token(service_name: str, scope: str | None = None) -> str:
    token_scope = scope or f"service:{service_name}"
    return _encode_token(
        {"sub": f"service:{service_name}"},
        audience="bankcore-internal",
        expires_in=settings.INTERNAL_TOKEN_EXPIRE_SECONDS,
        scope=token_scope,
    )


def validate_key_material() -> None:
    private_key = _load_private_key()
    public_key = _load_public_key(settings.JWT_ACTIVE_KID)
    probe = encode(
        {"probe": str(uuid4())},
        private_key,
        algorithm=settings.JWT_ALGORITHM,
        headers={"kid": settings.JWT_ACTIVE_KID},
    )
    try:
        decode(probe, public_key, algorithms=[settings.JWT_ALGORITHM])
    except PyJWTError as exc:
        raise RuntimeError("JWT private/public key pair is invalid.") from exc


def _validate_claims(payload: dict, *, audience: str) -> None:
    required = ("sub", "iss", "aud", "iat", "nbf", "exp", "jti")
    if any(payload.get(claim) in (None, "") for claim in required):
        raise _unauthorized("Token sem claims obrigatórias.")
    if payload["iss"] != settings.JWT_ISSUER or payload["aud"] != audience:
        raise _unauthorized("Token com emissor ou audiência inválidos.")
    if any(isinstance(payload[claim], bool) or not isinstance(payload[claim], int) for claim in ("iat", "nbf", "exp")):
        raise _unauthorized("Token com claims temporais inválidas.")
    now = int(datetime.now(timezone.utc).timestamp())
    if payload["iat"] > now or payload["nbf"] > now or payload["exp"] <= now:
        raise _unauthorized()


def decode_token(token: str, *, audience: str, required_scope: str | None = None) -> dict:
    try:
        header = get_unverified_header(token)
        if header.get("alg") != settings.JWT_ALGORITHM or not header.get("kid"):
            raise _unauthorized("Token com algoritmo ou chave inválidos.")
        payload = decode(
            token,
            _load_public_key(header["kid"]),
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=audience,
        )
        _validate_claims(payload, audience=audience)
        if required_scope and payload.get("scope") != required_scope:
            raise _unauthorized("Token sem escopo permitido.")
        return payload
    except HTTPException:
        raise
    except (PyJWTError, KeyError, TypeError, ValueError):
        raise _unauthorized()

def decode_access_token(token: str) -> dict:
    return decode_token(token, audience=settings.JWT_AUDIENCE)


def require_internal_service(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    if creds is None or not creds.credentials:
        raise _unauthorized("Credencial de serviço ausente.")
    return decode_token(
        creds.credentials,
        audience="bankcore-internal",
        required_scope="service:transactions",
    )


def validate_internal_service_secret(
    x_service_token: str | None = Header(default=None, alias="X-Service-Token"),
    x_service_name: str | None = Header(default=None, alias="X-Service-Name"),
    x_service_scope: str | None = Header(default=None, alias="X-Service-Scope"),
) -> str:
    allowed_scopes = {"service:transactions", "risk:assess"}
    requested_scope = x_service_scope or "service:transactions"
    if (
        x_service_name != "transactions"
        or not x_service_token
        or not secrets.compare_digest(x_service_token, settings.AUTH_SERVICE_TOKEN)
        or requested_scope not in allowed_scopes
    ):
        raise _unauthorized("Credencial de serviço inválida.")
    return requested_scope

def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    if creds is None or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acesso ausente.",
        )
    payload = decode_access_token(creds.credentials)
    if not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sem identificação de correntista.",
        )
    return payload
