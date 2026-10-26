"""VK walls: posts via wall.get, comments via wall.getComments (service key)."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select

from .. import config
from ..db import Item, Source, utcnow
from . import keep_comment, store_item

log = logging.getLogger(__name__)


class VKError(Exception):
    pass


class VK:
    def __init__(self, token: str):
        self.token = token
        self.http = httpx.AsyncClient(timeout=30)

    async def call(self, method: str, **params):
        params.update(access_token=self.token, v=config.VK_API_VERSION)
        for attempt in range(3):
            resp = await self.http.post(f"https://api.vk.com/method/{method}", data=params)
            data = resp.json()
            await asyncio.sleep(0.35)  # service keys allow 3 requests per second
            if "error" not in data:
                return data["response"]
            err = data["error"]
            if err.get("error_code") == 6 and attempt < 2:  # too many requests per second
                await asyncio.sleep(1.5)
                continue
            raise VKError(f"{err.get('error_code')}: {err.get('error_msg')}")

    async def close(self):
        await self.http.aclose()


def _ts(value: int) -> datetime:
    return datetime.fromtimestamp(value, timezone.utc).replace(tzinfo=None)


def _screen_name(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1]


def _names(resp) -> dict[int, str]:
    names = {p["id"]: f"{p.get('first_name', '')} {p.get('last_name', '')}".strip() for p in resp.get("profiles", [])}
    names.update({-g["id"]: g.get("name", "") for g in resp.get("groups", [])})
    return names


async def collect_source(vk: VK, db, source: Source, extra_keywords: list[str]) -> int:
    state = dict(source.state or {})
    domain = _screen_name(source.url)
    resp = await vk.call("wall.get", domain=domain, count=50, extended=1)
    names = _names(resp)
    if not source.kind:
        source.kind = "wall"
        groups = resp.get("groups") or []
        if groups:
            source.title = groups[0].get("name") or source.title
        elif resp.get("profiles"):
            source.title = names.get(resp["profiles"][0]["id"], source.title)

    since = utcnow() - timedelta(days=config.BACKFILL_DAYS)
    window_days = config.PRIORITY_COMMENT_WINDOW_DAYS if source.role == "governor" else config.COMMENT_WINDOW_DAYS
    comment_since = utcnow() - timedelta(days=window_days)
    added = 0
    seen_comments = state.get("comments", {})  # post id -> comments count when last fetched

    for post in resp.get("items", []):
        published = _ts(post["date"])
        if published < since and not post.get("is_pinned"):
            continue
        owner_id = post["owner_id"]
        text = post.get("text", "")
        if not text and post.get("copy_history"):
            text = post["copy_history"][0].get("text", "")
        comments_count = post.get("comments", {}).get("count", 0)
        item = store_item(
            db, source, kind="post", external_id=f"{owner_id}_{post['id']}", text=text,
            published_at=published, url=f"https://vk.com/wall{owner_id}_{post['id']}",
            author=names.get(post.get("from_id", owner_id), source.title),
            likes=post.get("likes", {}).get("count", 0), views=post.get("views", {}).get("count", 0),
            replies=comments_count,
        )
        added += bool(item)
        db.flush()
        post_item = item or db.scalar(
            select(Item).where(Item.source_id == source.id, Item.external_id == f"{owner_id}_{post['id']}")
        )
        key = str(post["id"])
        if published < comment_since or comments_count == 0 or seen_comments.get(key) == comments_count:
            continue
        added += await _collect_comments(vk, db, source, post_item, owner_id, post["id"], extra_keywords)
        seen_comments[key] = comments_count

    # Forget counters of posts that left the comment window.
    state["comments"] = dict(list(seen_comments.items())[-200:])
    source.state = state
    return added


async def _collect_comments(vk: VK, db, source: Source, post_item: Item, owner_id: int, post_id: int,
                            extra_keywords: list[str]) -> int:
    added, offset = 0, 0
    while offset < 2000:
        resp = await vk.call(
            "wall.getComments", owner_id=owner_id, post_id=post_id, count=100, offset=offset,
            sort="asc", extended=1, thread_items_count=10, need_likes=1,
        )
        names = _names(resp)
        items = resp.get("items", [])
        for c in items:
            for comment in [c] + c.get("thread", {}).get("items", []):
                text = comment.get("text", "")
                if not keep_comment(source, text, extra_keywords):
                    continue
                item = store_item(
                    db, source, kind="comment", external_id=f"{owner_id}_{post_id}_c{comment['id']}",
                    text=text, published_at=_ts(comment["date"]), parent=post_item,
                    url=f"https://vk.com/wall{owner_id}_{post_id}?reply={comment['id']}",
                    author=names.get(comment.get("from_id"), ""),
                    likes=comment.get("likes", {}).get("count", 0),
                )
                added += bool(item)
        offset += len(items)
        if len(items) < 100:
            break
    return added
