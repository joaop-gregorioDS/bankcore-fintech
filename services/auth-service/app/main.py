import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base, AsyncSessionLocal
from app.routes import auth
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
    for _ in range(10):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            async with AsyncSessionLocal() as session:
                await seed_demo_users(session)
            break
        except Exception:
            await asyncio.sleep(2)


@app.get("/auth/health", tags=["Health"])
async def health_check():
    return {"service": "bankcore-auth-service", "status": "UP"}

app.include_router(auth.router)
