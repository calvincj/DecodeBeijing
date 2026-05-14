from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import engine, Base
from app.api import documents, terms, candidates


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup if they don't exist
    # (In production, use Alembic migrations instead)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="Decode Beijing API",
    description="Track language shifts in Chinese political documents",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(terms.router)
app.include_router(candidates.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
