import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class Article(SQLModel, table=True):
    __tablename__ = "articles"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str
    source_org: str
    pub_year: int | None = None
    tier: int
    url: str | None = None
    tags: list[str] | None = Field(default=None, sa_column=Column(JSONB))
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


class ArticleChunk(SQLModel, table=True):
    __tablename__ = "article_chunks"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    article_id: uuid.UUID = Field(foreign_key="articles.id")
    chunk_index: int
    content: str
    section_title: str | None = None
    page_number: int | None = None
    chunk_type: str = "text"
    embedding: list[float] | None = Field(
        default=None,
        sa_column=Column(Vector(1536), nullable=True),
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    conversation_id: uuid.UUID = Field(foreign_key="conversations.id")
    role: str
    content: str
    cited_chunk_ids: list[str] | None = Field(
        default=None,
        sa_column=Column(JSONB),
    )
    llm_model: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
