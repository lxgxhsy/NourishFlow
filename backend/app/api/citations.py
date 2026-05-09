import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.core.db import engine
from app.models.tables import Article, ArticleChunk

router = APIRouter()


class ArticleInfo(BaseModel):
    title: str
    source_org: str
    pub_year: int | None
    tier: int


class CitationResponse(BaseModel):
    chunk_id: uuid.UUID
    content: str
    section_title: str | None
    page_number: int | None
    article: ArticleInfo


@router.get("/api/citations/{chunk_id}", response_model=CitationResponse)
def get_citation(chunk_id: uuid.UUID):
    with Session(engine) as session:
        chunk = session.get(ArticleChunk, chunk_id)
        if chunk is None:
            raise HTTPException(status_code=404, detail="chunk not found")

        article = session.get(Article, chunk.article_id)

    return CitationResponse(
        chunk_id=chunk.id,
        content=chunk.content,
        section_title=chunk.section_title,
        page_number=chunk.page_number,
        article=ArticleInfo(
            title=article.title,
            source_org=article.source_org,
            pub_year=article.pub_year,
            tier=article.tier,
        ),
    )
