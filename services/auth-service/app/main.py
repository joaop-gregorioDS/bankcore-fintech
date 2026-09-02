import asyncio
from fastapi import FastAPI
from app.database import engine, Base
from app.routes import auth

app = FastAPI(
    title="BankCore - Auth Service",
    description="Microsserviço de Autenticação e Gestão de Correntistas",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
    swagger_ui_parameters={"url": "/auth/openapi.json"}
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

@app.get("/health", tags=["Health"])
async def health_check():
    return {"service": "bankcore-auth-service", "status": "UP"}

app.include_router(auth.router)
