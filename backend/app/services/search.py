import meilisearch

from app.core.config import settings
from app.models.tables import Article
from app.core.db import engine


def search_chunks(query: str, limit: int = 5) -> list[dict]:
    """Meilisearch 全文检索,返回 chunks + PG 里的文章元数据."""
    client = meilisearch.Client(settings.meili_url, settings.meili_master_key)
    index = client.index("article_chunks")
    result = index.search(query, {"limit": limit})

    hits = result["hits"]
    if not hits:
        return []

    # 从 PG 反查文章 title / tier
    article_ids = list({hit["article_id"] for hit in hits})
    from sqlmodel import Session, select

    with Session(engine) as session:
        stmt = select(Article).where(Article.id.in_(article_ids))
        articles = session.exec(stmt).all()
        article_map = {str(a.id): {"title": a.title, "tier": a.tier} for a in articles}

    chunks = []
    for hit in hits:
        article_meta = article_map.get(hit["article_id"], {"title": "Unknown", "tier": 0})
        chunks.append({
            "id": hit["id"],
            "content": hit["content"],
            "article_id": hit["article_id"],
            "page_number": hit.get("page_number"),
            "section_title": hit.get("section_title"),
            "title": article_meta["title"],
            "tier": article_meta["tier"],
        })
    return chunks
