from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models, rag
from .api import router
from .config import settings
from .db import Base, SessionLocal, engine
from .seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        seed(db)
        rag.ensure_index(db)
    finally:
        db.close()
    yield


app = FastAPI(title="Ridley AI", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"], allow_credentials=True)
app.include_router(router)
