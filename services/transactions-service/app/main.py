import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.config import settings
from app.database import engine
from app.demo_mode import is_demo_mode_enabled
from app.routes import accounts, transactions
from app.deps import validate_public_key_material
from app.seed import seed_demo_accounts
from common.observability import RequestContextMiddleware, configure_logging
from common.tracing import configure_tracing, instrument_fastapi

configure_logging("transactions-service")
configure_tracing("transactions-service")

ALLOWED_ORIGINS = [
    "https://bankcore.vortexsoftware.tech",
    "https://vortexsoftware.tech",
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:80",
    "http://localhost:1420",
    "https://tauri.localhost",
    "tauri://localhost",
]

app = FastAPI(
    title="BankCore Transactions",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID", "X-Correlation-ID"],
    expose_headers=["X-Request-ID", "X-Correlation-ID"],
)
instrument_fastapi(app, "transactions-service")
app.add_middleware(RequestContextMiddleware, service="transactions-service")


@app.on_event("startup")
async def startup():
    validate_public_key_material()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1 FROM accounts LIMIT 0"))
            await conn.execute(text("SELECT 1 FROM ledger_transactions LIMIT 0"))
            await conn.execute(text("SELECT 1 FROM ledger_entries LIMIT 0"))
            await conn.execute(text("SELECT 1 FROM idempotency_records LIMIT 0"))
    except Exception as exc:
        raise RuntimeError("Transactions database schema is not migrated.") from exc
    for _ in range(10):
        try:
            if is_demo_mode_enabled(settings.DEMO_MODE):
                from app.database import AsyncSessionLocal
                async with AsyncSessionLocal() as session:
                    await seed_demo_accounts(session)
            break
        except Exception:
            await asyncio.sleep(2)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "bankcore-transactions-service"}


@app.get("/readiness")
async def readiness_check():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Banco de dados indisponível.") from exc
    return {"status": "ready", "service": "bankcore-transactions-service"}

app.include_router(accounts.router)
app.include_router(transactions.router)
