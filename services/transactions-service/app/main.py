import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base, AsyncSessionLocal, init_redis, close_redis
from app.routes import accounts, transactions
from app.seed import seed_demo_accounts

app = FastAPI(
    title="BankCore Transactions & Ledger Service",
    version="1.0.0",
    docs_url="/transactions/docs",
    openapi_url="/transactions/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await init_redis()
    for _ in range(10):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            async with AsyncSessionLocal() as session:
                await seed_demo_accounts(session)
            break
        except Exception:
            await asyncio.sleep(2)


@app.on_event("shutdown")
async def shutdown():
    await close_redis()


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "bankcore-transactions-service"}

app.include_router(accounts.router)
app.include_router(transactions.router)
