"""Telegram via a user account (Telethon): channel posts, their comments, chat messages."""

import asyncio
import logging
import re
from datetime import timedelta

from sqlalchemy import select
from telethon import TelegramClient, errors, functions, types
from telethon.sessions import StringSession

from .. import config
from ..db import Item, Source, get_setting, set_setting, utcnow
from . import keep_comment, store_item

log = logging.getLogger(__name__)

SESSION_KEY = "telegram_session"


def new_client(session: str = "") -> TelegramClient:
    return TelegramClient(
        StringSession(session), config.TG_API_ID, config.TG_API_HASH,
        device_model="Social monitor", app_version="1.0", system_lang_code="ru", lang_code="ru",
    )


async def connected_client(db) -> TelegramClient | None:
    session = get_setting(db, SESSION_KEY)
    if not (config.TG_API_ID and config.TG_API_HASH and session):
        return None
    client = new_client(session)
    await client.connect()
    if not await client.is_user_authorized():
        await client.disconnect()
        return None
    return client


def parse_link(url: str) -> tuple[str, str]:
    """('username', name) | ('invite', hash) | ('internal', channel_id)."""
    m = re.search(r"t\.me/(?:joinchat/|\+)([\w-]+)", url)
    if m:
        return "invite", m.group(1)
    m = re.search(r"t\.me/c/(\d+)", url)
    if m:
        return "internal", m.group(1)
    return "username", url.rstrip("/").rsplit("/", 1)[-1]


async def resolve(client: TelegramClient, source: Source, join: bool = False):
    kind, value = parse_link(source.url)
    if kind == "username":
        return await client.get_entity(value)
    if kind == "internal":
        # Only reachable when the account is already a member; get_dialogs fills the cache.
        try:
            return await client.get_entity(types.PeerChannel(int(value)))
        except ValueError:
            await client.get_dialogs()
            return await client.get_entity(types.PeerChannel(int(value)))
    invite = await client(functions.messages.CheckChatInviteRequest(value))
    if isinstance(invite, (types.ChatInviteAlready, types.ChatInvitePeek)):
        return invite.chat
    if not join:
        raise JoinNeeded(getattr(invite, "title", ""))
    updates = await client(functions.messages.ImportChatInviteRequest(value))
    return updates.chats[0]


class JoinNeeded(Exception):
    pass


def _author(message) -> str:
    sender = message.sender
    if sender is None:
        return message.post_author or ""
    if isinstance(sender, types.User):
        name = " ".join(filter(None, [sender.first_name, sender.last_name]))
        return name + (f" (@{sender.username})" if sender.username else "")
    return getattr(sender, "title", "")


def _link(entity, msg_id: int, comment_id: int | None = None) -> str:
    username = getattr(entity, "username", None)
    base = f"https://t.me/{username}" if username else f"https://t.me/c/{entity.id}"
    return f"{base}/{msg_id}" + (f"?comment={comment_id}" if comment_id else "")


def _naive(dt):
    return dt.replace(tzinfo=None)


async def collect_source(client: TelegramClient, db, source: Source, extra_keywords: list[str]) -> int:
    entity = await resolve(client, source)
    state = dict(source.state or {})
    is_channel = isinstance(entity, types.Channel) and entity.broadcast
    source.kind = "channel" if is_channel else "chat"
    source.title = getattr(entity, "title", "") or source.title
    window = config.PRIORITY_COMMENT_WINDOW_DAYS if source.role == "governor" else config.COMMENT_WINDOW_DAYS
    since = utcnow() - timedelta(days=max(config.BACKFILL_DAYS, window if is_channel else 0))
    last_id = state.get("last_id", 0)
    added = 0
    # Channels: re-read recent posts so their comment counters stay current.
    # Chats: only messages newer than the last one seen.
    min_id = 0 if is_channel else last_id
    async for message in client.iter_messages(entity, min_id=min_id, limit=300 if is_channel or not last_id else None):
        if _naive(message.date) < since:
            break
        last_id = max(last_id, message.id)
        text = message.message or ""
        if is_channel:
            item = store_item(
                db, source, kind="post", external_id=str(message.id), text=text,
                published_at=_naive(message.date), url=_link(entity, message.id), author=source.title,
                views=message.views or 0, replies=message.replies.replies if message.replies else 0,
                likes=_reactions(message),
            )
        else:
            if not keep_comment(source, text, extra_keywords):
                continue
            parent = None
            if message.reply_to and message.reply_to.reply_to_msg_id:
                parent = db.scalar(select(Item).where(
                    Item.source_id == source.id, Item.external_id == str(message.reply_to.reply_to_msg_id)))
            item = store_item(
                db, source, kind="chat", external_id=str(message.id), text=text,
                published_at=_naive(message.date), url=_link(entity, message.id), author=_author(message),
                parent=parent, likes=_reactions(message),
            )
        added += bool(item)
    state["last_id"] = last_id

    if is_channel:
        added += await _collect_comments(client, db, source, entity, state, extra_keywords)
    source.state = state
    return added


def _reactions(message) -> int:
    if not message.reactions:
        return 0
    return sum(r.count for r in message.reactions.results)


async def _collect_comments(client, db, source, entity, state, extra_keywords) -> int:
    """Comments live in the channel's linked discussion group; fetch them per post."""
    window = config.PRIORITY_COMMENT_WINDOW_DAYS if source.role == "governor" else config.COMMENT_WINDOW_DAYS
    since = utcnow() - timedelta(days=window)
    seen = state.get("comments", {})  # post id -> last comment id fetched
    posts = db.scalars(
        select(Item).where(Item.source_id == source.id, Item.kind == "post", Item.published_at >= since,
                           Item.replies > 0)
    ).all()
    added = 0
    for post in posts:
        key = post.external_id
        min_id = seen.get(key, 0)
        if min_id and post.replies <= state.get("counts", {}).get(key, 0):
            continue
        try:
            async for c in client.iter_messages(entity, reply_to=int(key), min_id=min_id, limit=3000):
                min_id = max(min_id, c.id)
                text = c.message or ""
                if not keep_comment(source, text, extra_keywords):
                    continue
                item = store_item(
                    db, source, kind="comment", external_id=f"{key}_c{c.id}", text=text,
                    published_at=_naive(c.date), url=_link(entity, int(key), c.id), author=_author(c),
                    parent=post, likes=_reactions(c),
                )
                added += bool(item)
        except errors.MsgIdInvalidError:
            continue
        seen[key] = min_id
        state.setdefault("counts", {})[key] = post.replies
        await asyncio.sleep(0.5)
    state["comments"] = dict(list(seen.items())[-300:])
    state["counts"] = dict(list(state.get("counts", {}).items())[-300:])
    return added


# Interactive login from the settings page: phone -> code -> optional 2FA password.
_pending: dict[str, TelegramClient] = {}


async def login_start(phone: str) -> str:
    client = new_client()
    await client.connect()
    sent = await client.send_code_request(phone)
    _pending[phone] = client
    return sent.phone_code_hash


async def login_finish(db, phone: str, code: str, phone_code_hash: str, password: str = "") -> str:
    client = _pending.get(phone)
    if not client:
        raise RuntimeError("Сначала запросите код")
    try:
        await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
    except errors.SessionPasswordNeededError:
        if not password:
            return "password_needed"
        await client.sign_in(password=password)
    set_setting(db, SESSION_KEY, client.session.save())
    me = await client.get_me()
    await client.disconnect()
    _pending.pop(phone, None)
    return f"ok:{me.first_name or ''} {('@' + me.username) if me.username else ''}".strip()
