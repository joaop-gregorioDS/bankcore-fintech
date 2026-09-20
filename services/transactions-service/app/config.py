from pydantic_settings import BaseSettings
from typing import Literal

class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_ALGORITHM: Literal["RS256"] = "RS256"
    JWT_ISSUER: str = "bankcore-auth"
    JWT_AUDIENCE: str = "bankcore-api"
    JWT_ACTIVE_KID: str
    JWT_PUBLIC_KEYS_DIR: str = "/run/secrets/jwt-public"
    AUTH_SERVICE_URL: str = "http://auth-service:8000"
    AUTH_SERVICE_TOKEN: str
    RISK_SERVICE_URL: str = "http://risk-service:8080"
    RISK_TIMEOUT_SECONDS: float = 3.0
    RISK_RETRY_COUNT: int = 1
    RISK_RETRY_DELAY_SECONDS: float = 0.1
    RISK_CIRCUIT_FAILURE_THRESHOLD: int = 3
    RISK_CIRCUIT_OPEN_SECONDS: float = 5.0
    DEMO_MODE: bool = False
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_TOPIC: str = "bankcore.transaction.completed.v1"
    OUTBOX_BATCH_SIZE: int = 100
    OUTBOX_POLL_INTERVAL_SECONDS: float = 1.0
    OUTBOX_LEASE_SECONDS: int = 30
    OUTBOX_PUBLISHER_ID: str = ""
    OUTBOX_CRASH_AFTER_KAFKA_ACK: bool = False

settings = Settings()
