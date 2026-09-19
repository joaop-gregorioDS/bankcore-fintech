from pydantic_settings import BaseSettings
from typing import Literal

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    JWT_ALGORITHM: Literal["RS256"] = "RS256"
    JWT_ISSUER: str = "bankcore-auth"
    JWT_AUDIENCE: str = "bankcore-api"
    JWT_ACTIVE_KID: str
    JWT_PUBLIC_KEYS_DIR: str = "/run/secrets/jwt-public"
    AUTH_SERVICE_URL: str = "http://auth-service:8000"
    AUTH_SERVICE_TOKEN: str
    DEMO_MODE: bool = False

settings = Settings()
