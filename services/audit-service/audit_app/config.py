from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    AUDIT_DATABASE_URL: str
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_TOPIC: str = "bankcore.transaction.completed.v1"
    KAFKA_GROUP_ID: str = "bankcore-audit-v1"
    CONSUMER_VERSION: str = "audit-consumer-v1"


settings = Settings()
