import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base, AsyncSessionLocal
from app.routes import auth
from app.seed import seed_demo_users

app = FastAPI(
    title="BankCore - Auth Service",
    description="Microsserviço de Autenticação e Gestão de Correntistas",
    version="1.0.0",
    docs_url="/auth/docs",
    openapi_url="/auth/openapi.json"
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
