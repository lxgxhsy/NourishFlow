import meilisearch
from fastapi import FastAPI
from sqlalchemy import text
from sqlmodel import SQLModel

from app.core.config import settings
from app.core.db import engine
from app.models.tables import Article, ArticleChunk, Conversation, Message

app = FastAPI(title="NourishFlow")


@app.on_event("startup")
def startup():
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    SQLModel.metadata.create_all(engine)

    client = meilisearch.Client(settings.meili_url, settings.meili_master_key)
    try:
        client.get_index("article_chunks")
    except meilisearch.errors.MeilisearchApiError:
        client.create_index("article_chunks", {"primaryKey": "id"})
        index = client.index("article_chunks")
        index.update_filterable_attributes(["article_id", "tier", "chunk_type"])
        index.update_searchable_attributes(["content", "section_title"])


@app.get("/api/health")
def health():
    return {"status": "ok"}
