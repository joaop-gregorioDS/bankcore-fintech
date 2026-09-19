import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from app.config import settings

bearer_scheme = HTTPBearer(auto_error=False)


def validate_public_key_material() -> None:
    kid = settings.JWT_ACTIVE_KID
    if not re.fullmatch(r"[A-Za-z0-9._-]+", kid):
        raise RuntimeError("JWT active key id is invalid.")
    try:
        (Path(settings.JWT_PUBLIC_KEYS_DIR) / f"{kid}.pem").read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise RuntimeError("JWT public key is unavailable.") from exc


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    if creds is None or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acesso ausente.",
        )
    try:
        header = jwt.get_unverified_header(creds.credentials)
        if header.get("alg") != settings.JWT_ALGORITHM or not header.get("kid"):
            raise JWTError("unexpected jwt header")
        kid = header["kid"]
        if not re.fullmatch(r"[A-Za-z0-9._-]+", kid):
            raise JWTError("invalid kid")
        public_key = (Path(settings.JWT_PUBLIC_KEYS_DIR) / f"{kid}.pem").read_text(encoding="utf-8")
        payload = jwt.decode(
            creds.credentials,
            public_key,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
        )
        required = ("sub", "iss", "aud", "iat", "nbf", "exp", "jti")
        if any(payload.get(claim) in (None, "") for claim in required):
            raise JWTError("missing required claim")
        if any(isinstance(payload[claim], bool) or not isinstance(payload[claim], int) for claim in ("iat", "nbf", "exp")):
            raise JWTError("invalid temporal claim")
        now = int(datetime.now(timezone.utc).timestamp())
        if payload["iat"] > now or payload["nbf"] > now or payload["exp"] <= now:
            raise JWTError("token outside validity window")
    except (JWTError, OSError, UnicodeError, KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
        )
    if not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sem identificação de correntista.",
        )
    return payload


def current_user_id(current_user: dict = Depends(get_current_user)) -> UUID:
    return UUID(current_user["sub"])
