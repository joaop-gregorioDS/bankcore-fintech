import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

redis_client = None


async def init_redis():
    global redis_client
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def close_redis():
    global redis_client
    if redis_client is not None:
        await redis_client.close()
        redis_client = None


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def get_redis():
    yield redis_client
