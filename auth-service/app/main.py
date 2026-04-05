from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import router
from app.db.session import AsyncSessionLocal
from app.services.auth_service import ensure_admin_exists


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncSessionLocal() as session:
        await ensure_admin_exists(session)
    yield


app = FastAPI(title="Auth Service", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
