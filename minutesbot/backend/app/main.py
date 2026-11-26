import logging

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.auth import require_key
from app.config import settings
from app.db import Base, engine, get_db
from app.routes import actions, meetings
from app.schemas import SearchResult
from app.search import search_chunks

logging.basicConfig(level=logging.INFO)

# fine for a small project. If the schema starts changing a lot, switch to alembic.
Base.metadata.create_all(engine)

app = FastAPI(title="MinutesBot")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api", dependencies=[Depends(require_key)])
api.include_router(meetings.router)
api.include_router(actions.router)


@api.get("/search", response_model=list[SearchResult])
def search(q: str, limit: int = 5, db: Session = Depends(get_db)):
    q = q.strip()
    if not q or len(q) > 500:
        raise HTTPException(422, "query must be 1-500 characters")
    return search_chunks(db, q, limit=max(1, min(limit, 20)))


app.include_router(api)


@app.get("/api/health")
def health():
    return {"ok": True, "ai": "openai" if settings.openai_api_key else "offline"}
