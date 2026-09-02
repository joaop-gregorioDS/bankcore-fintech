from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routes import accounts, transactions

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
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "bankcore-transactions-service"}

app.include_router(accounts.router)
app.include_router(transactions.router)
