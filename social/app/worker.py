"""Background loop: collect sources on schedule, classify, send scheduled reports."""

import asyncio
import logging
from datetime import timedelta

from sqlalchemy import select

from . import config
from .classify import classify_pending
from .collectors import telegram, vk
from .db import ReportPreset, SessionLocal, Source, get_setting, utcnow
from .reports import to_local

log = logging.getLogger(__name__)
_tg_client = None
_running = asyncio.Lock()


def extra_keywords(db) -> list[str]:
    raw = get_setting(db, "extra_keywords")
    return [w.strip().lower() for w in raw.replace("\n", ",").split(",") if w.strip()]


async def _telegram(db):
    global _tg_client
    if _tg_client is not None and _tg_client.is_connected():
        return _tg_client
    _tg_client = await telegram.connected_client(db)
    return _tg_client


async def reset_telegram():
    global _tg_client
    if _tg_client is not None:
        await _tg_client.disconnect()
    _tg_client = None


def _due(source: Source) -> bool:
    if source.last_checked is None:
        return True
    minutes = config.PRIORITY_POLL_MINUTES if source.role == "governor" else config.POLL_MINUTES
    return utcnow() - source.last_checked >= timedelta(minutes=minutes)


async def collect_one(db, source: Source, keywords: list[str]) -> int:
    try:
        if source.platform == "vk":
            if not config.VK_TOKEN:
                raise RuntimeError("Нет VK_TOKEN")
            client = vk.VK(config.VK_TOKEN)
            try:
                added = await vk.collect_source(client, db, source, keywords)
            finally:
                await client.close()
        else:
            client = await _telegram(db)
            if client is None:
                raise RuntimeError("Telegram не подключён (Настройки → Telegram)")
            added = await telegram.collect_source(client, db, source, keywords)
        source.status, source.last_error = "ok", ""
    except telegram.JoinNeeded as e:
        source.status, source.last_error, added = "join_needed", f"Нужно вступить: {e}", 0
    except telegram.errors.FloodWaitError as e:
        source.status, source.last_error, added = "error", f"Telegram просит подождать {e.seconds} с", 0
        await asyncio.sleep(min(e.seconds, 60))
    except Exception as e:  # one broken source must not stop the others
        log.exception("collect %s failed", source.url)
        db.rollback()
        source = db.get(Source, source.id)
        source.status, source.last_error, added = "error", f"{type(e).__name__}: {e}"[:500], 0
    source.last_checked = utcnow()
    db.commit()
    return added


async def run_cycle(force: bool = False) -> dict:
    if _running.locked():
        return {"skipped": True}
    async with _running:
        with SessionLocal() as db:
            keywords = extra_keywords(db)
            sources = db.scalars(select(Source).where(Source.enabled.is_(True))
                                 .order_by(Source.role != "governor", Source.id)).all()
            added = 0
            for source in sources:
                if force or _due(source):
                    added += await collect_one(db, source, keywords)
            classified = 0
            while True:
                n = await classify_pending(db)
                classified += n
                if n < 400:
                    break
        return {"added": added, "classified": classified}


async def send_scheduled_reports():
    from .web_reports import build_report, send_to_max  # avoid a cycle at import time

    now = to_local(utcnow())
    with SessionLocal() as db:
        presets = db.scalars(select(ReportPreset).where(ReportPreset.auto_send.is_(True))).all()
        for preset in presets:
            last = to_local(preset.last_sent)
            if preset.send_time > now.strftime("%H:%M") or (last and last.date() == now.date()):
                continue
            preset.last_sent = utcnow()
            db.commit()
            try:
                report = build_report(db, preset.kind, preset.params)
                if report:
                    await send_to_max(db, report)
            except Exception:
                log.exception("scheduled report %s failed", preset.name)


async def loop():
    await asyncio.sleep(5)
    while True:
        try:
            await run_cycle()
            await send_scheduled_reports()
        except Exception:
            log.exception("worker cycle failed")
        await asyncio.sleep(60)
