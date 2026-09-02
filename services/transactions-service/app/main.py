import asyncio
from fastapi import FastAPI
from app.database import engine, Base
from app.routes import accounts, transactions

app = FastAPI(
    title="BankCore - Transactions & Ledger Service",
    description="Motor Financeiro de Pix, Idempotência e Livro-Razão ACID",
    version="1.0.0",
    docs_url="/transactions/docs",
    openapi_url="/transactions/openapi.json"
)

@app.on_event("startup")
async def startup():
    for _ in range(10):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            break
        except Exception:
            await asyncio.sleep(2)

@app.get("/transactions/health", tags=["Health"])
async def health():
    return {"service": "bankcore-transactions-service", "status": "UP", "engine": "Ledger ACID Active"}

app.include_router(accounts.router)
app.include_router(transactions.router)
