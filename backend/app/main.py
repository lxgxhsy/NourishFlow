from contextlib import asynccontextmanager

import meilisearch
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlmodel import SQLModel

from app.core.config import settings
from app.core.db import engine
from app.models.tables import Article, ArticleChunk, Conversation, Message

from app.api import chat as chat_router
from app.api import citations as citations_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    SQLModel.metadata.create_all(engine)

    if not settings.deepseek_api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not set. Configure it in .env before starting.")

    client = meilisearch.Client(settings.meili_url, settings.meili_master_key)
    try:
        client.get_index("article_chunks")
    except meilisearch.errors.MeilisearchApiError:
        client.create_index("article_chunks", {"primaryKey": "id"})
        index = client.index("article_chunks")
        index.update_filterable_attributes(["article_id", "tier", "chunk_type"])
        index.update_searchable_attributes(["content", "section_title"])
    yield


app = FastAPI(title="NourishFlow", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router.router)
app.include_router(citations_router.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
