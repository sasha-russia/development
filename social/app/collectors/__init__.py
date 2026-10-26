"""Collectors fetch new posts and comments and store them as Items."""

from datetime import datetime

from sqlalchemy import select

from ..db import Item, Source
from ..topics import mentions_local


def store_item(
    db, source: Source, *, kind: str, external_id: str, text: str, published_at: datetime,
    url: str = "", author: str = "", parent: Item | None = None, likes: int = 0, views: int = 0,
    replies: int = 0,
) -> Item | None:
    """Insert an item or refresh the counters of an existing one. Returns new items only."""
    existing = db.scalar(select(Item).where(Item.source_id == source.id, Item.external_id == external_id))
    if existing:
        existing.likes, existing.views, existing.replies = likes, views, replies
        return None
    item = Item(
        source_id=source.id, kind=kind, external_id=external_id, text=text or "", url=url,
        author=author[:200], parent_id=parent.id if parent else None, published_at=published_at,
        likes=likes, views=views, replies=replies,
    )
    db.add(item)
    db.flush()
    return item


def keep_comment(source: Source, text: str, extra_keywords: list[str]) -> bool:
    """Under the governor's posts keep only comments about the Mytishchi district."""
    if source.role != "governor":
        return bool(text and text.strip())
    return mentions_local(text, extra_keywords)
