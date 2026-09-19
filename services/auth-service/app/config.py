from pydantic_settings import BaseSettings
from typing import Literal

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    JWT_ALGORITHM: Literal["RS256"] = "RS256"
    JWT_ISSUER: str = "bankcore-auth"
    JWT_AUDIENCE: str = "bankcore-api"
    JWT_PRIVATE_KEY_PATH: str = "/run/secrets/jwt-private.pem"
    JWT_PUBLIC_KEYS_DIR: str = "/run/secrets/jwt-public"
    JWT_ACTIVE_KID: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    INTERNAL_TOKEN_EXPIRE_SECONDS: int = 60
    AUTH_SERVICE_TOKEN: str
    DEMO_MODE: bool = False

settings = Settings()
