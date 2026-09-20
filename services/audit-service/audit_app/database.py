from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from audit_app.config import settings


engine = create_async_engine(settings.AUDIT_DATABASE_URL, echo=False)
AuditSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()
