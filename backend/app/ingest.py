import uuid
from pathlib import Path

import meilisearch
import typer
from sqlalchemy import text
from sqlmodel import Session

from app.core.config import settings
from app.core.db import engine
from app.models.tables import Article, ArticleChunk
from app.services.chunker import chunk_sections
from app.services.pdf_parser import parse_pdf

app = typer.Typer()


@app.command()
def ingest(
    pdf_path: str = typer.Argument(help="Path to the PDF file"),
    title: str = typer.Option(..., "--title", help="Article title"),
    source_org: str = typer.Option("", "--source-org", help="Source organization"),
    pub_year: int | None = typer.Option(None, "--pub-year", help="Publication year"),
    tier: int = typer.Option(..., "--tier", help="Tier (1/2/3)"),
):
    path = Path(pdf_path)
    if not path.exists():
        typer.echo(f"Error: file not found: {pdf_path}")
        raise typer.Exit(1)

    if tier not in (1, 2, 3):
        typer.echo(f"Error: tier must be 1, 2, or 3, got {tier}")
        raise typer.Exit(1)

    typer.echo(f"Parsing {path.name}...")
    sections = parse_pdf(str(path))
    if not sections:
        typer.echo("Error: no text extracted from PDF")
        raise typer.Exit(1)
    typer.echo(f"  {len(sections)} pages extracted")

    chunks = chunk_sections(sections)
    if not chunks:
        typer.echo("Error: no chunks generated")
        raise typer.Exit(1)
    typer.echo(f"  {len(chunks)} chunks generated")

    article_id = uuid.uuid4()

    # Write to PG
    typer.echo("Writing to PostgreSQL...")
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    meili_docs = []
    with Session(engine) as session:
        article = Article(
            id=article_id,
            title=title,
            source_org=source_org,
            pub_year=pub_year,
            tier=tier,
        )
        session.add(article)

        for c in chunks:
            chunk_id = uuid.uuid4()
            session.add(ArticleChunk(
                id=chunk_id,
                article_id=article_id,
                chunk_index=c.chunk_index,
                content=c.content,
                section_title=c.section_title,
                page_number=c.page_number,
                chunk_type="text",
            ))
            meili_docs.append({
                "id": str(chunk_id),
                "article_id": str(article_id),
                "chunk_index": c.chunk_index,
                "content": c.content,
                "section_title": c.section_title,
                "page_number": c.page_number,
                "chunk_type": "text",
                "tier": tier,
            })
        session.commit()
        typer.echo(f"  article {article_id} + {len(chunks)} chunks saved")

    # Sync to Meili
    typer.echo("Syncing to Meilisearch...")
    client = meilisearch.Client(settings.meili_url, settings.meili_master_key)
    index = client.index("article_chunks")
    try:
        index.add_documents(meili_docs)
        typer.echo(f"  {len(meili_docs)} documents added to index")
    except meilisearch.errors.MeilisearchApiError as e:
        typer.echo(f"Error: Meili sync failed: {e}")
        raise typer.Exit(1)

    typer.echo(f"Done. article_id={article_id}")


if __name__ == "__main__":
    app()
