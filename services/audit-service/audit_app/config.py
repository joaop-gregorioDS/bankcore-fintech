from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    AUDIT_DATABASE_URL: str
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_TOPIC: str = "bankcore.transaction.completed.v1"
    KAFKA_RETRY_TOPIC: str = "bankcore.transaction.completed.v1.retry"
    KAFKA_DLQ_TOPIC: str = "bankcore.transaction.completed.v1.dlq"
    KAFKA_GROUP_ID: str = "bankcore-audit-v1"
    KAFKA_RETRY_GROUP_ID: str = "bankcore-audit-retry-v1"
    MAX_RETRIES: int = 3
    LOCAL_RETRY_ATTEMPTS: int = 1
    LOCAL_RETRY_DELAY_SECONDS: float = 0.05
    CRASH_AFTER_DB_COMMIT: bool = False
    CONSUMER_VERSION: str = "audit-consumer-v1"


settings = Settings()
