import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.config import settings
from app.database import engine
from app.demo_mode import is_demo_mode_enabled
from app.routes import auth
from app.security import validate_key_material
from app.seed import seed_demo_users

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
    title="BankCore Auth",
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
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


@app.on_event("startup")
async def startup():
    validate_key_material()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1 FROM users LIMIT 0"))
    except Exception as exc:
        raise RuntimeError("Auth database schema is not migrated.") from exc
    for _ in range(10):
        try:
            if is_demo_mode_enabled(settings.DEMO_MODE):
                from app.database import AsyncSessionLocal
                async with AsyncSessionLocal() as session:
                    await seed_demo_users(session)
            break
        except Exception:
            await asyncio.sleep(2)


@app.get("/auth/health", tags=["Health"])
async def health_check():
    return {"service": "bankcore-auth-service", "status": "UP"}


@app.get("/auth/readiness", tags=["Health"])
async def readiness_check():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Banco de dados indisponível.") from exc
    return {"service": "bankcore-auth-service", "status": "READY"}

app.include_router(auth.router)
