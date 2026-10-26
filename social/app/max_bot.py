"""Send reports to MAX: formatted text (markdown) plus the PDF as a file."""

import asyncio
import os
import ssl
from pathlib import Path

import certifi
import httpx

from . import config
from .reports import fmt
from .topics import SENTIMENTS

LIMIT = 3900  # MAX allows 4000 characters per message
# MAX's certificate is issued by the Russian Trusted Root CA (Минцифры).
RU_CA = Path(os.getenv("RU_CA_FILE", "/app/certs/russian_trusted_ca.pem"))


def _ssl() -> ssl.SSLContext:
    ctx = ssl.create_default_context(cafile=certifi.where())
    if RU_CA.exists():
        ctx.load_verify_locations(cafile=str(RU_CA))
    return ctx


def configured() -> bool:
    return bool(config.MAX_BOT_TOKEN and (config.MAX_CHAT_ID or config.MAX_USER_ID))


def _esc(text: str) -> str:
    return (text or "").replace("*", "").replace("_", " ").replace("[", "(").replace("]", ")").strip()


def _short(text: str, n: int = 160) -> str:
    text = " ".join((text or "").split())
    return _esc(text if len(text) <= n else text[: n - 1] + "…")


def render_markdown(report: dict) -> str:
    lines = [f"**{_esc(report['title'])}**", report.get("subtitle", ""), ""]
    if report["kind"] == "daily":
        s = report["stats"]
        lines += [f"Сообщений: {s['total']}, негатив: {s['negative']}, проблем: {len(report['problems'])}",
                  f"Комментарии у губернатора: {len(report['governor'])}", ""]
        if report["governor"]:
            lines.append("**🔴 Соцсети губернатора — в приоритете**")
            for item in report["governor"][:15]:
                lines.append(f"• {_short(item.summary or item.text)} — [{item.source.title}]({item.url})")
            lines.append("")
        lines.append("**Проблемы по приоритету**")
        for n, p in enumerate(report["problems"][:25], 1):
            where = f", {_esc(p['address'])}" if p["address"] else ""
            lines.append(f"{n}. **{_esc(p['title'])}** ({p['topic_label']}{where}) — упоминаний {p['mentions']}, "
                         f"комментариев {p['comments']}, негатив {p['negative_share']}% · [подробнее]({p['url']})")
        if len(report["problems"]) > 25:
            lines.append(f"…и ещё {len(report['problems']) - 25} в PDF")
    elif report["kind"] == "topics":
        for sec in report["sections"]:
            s = sec["stats"]
            delta = s["negative"] - sec["prev_negative"]
            lines.append(f"**{sec['label']}**: {s['total']} сообщ., негатив {s['negative']} "
                         f"({'+' if delta >= 0 else ''}{delta} к прошлому периоду)")
            for p in sec["problems"][:5]:
                lines.append(f"• {_esc(p['title'])} — {p['total']} сообщ. · [подробнее]({p['url']})")
            lines.append("")
    elif report["kind"] == "problem":
        s, tone = report["summary"], report["tone"]
        lines += [f"Период: {report['period']}",
                  f"Упоминаний: {s['mentions']}, комментариев: {s['comments']}, у губернатора: {s['governor']}",
                  "Тональность комментариев: " + ", ".join(f"{SENTIMENTS[k].lower()} {v}" for k, v in tone.items()),
                  f"Где писали: {', '.join(t for t, _ in report['by_source'][:8])}", ""]
        for item in report["items"][:12]:
            lines.append(f"• {fmt(item.published_at)} [{item.source.title}]({item.url}): {_short(item.text, 200)}")
    lines += ["", f"Дашборд: {config.BASE_URL}"]
    return "\n".join(lines)


def split(text: str) -> list[str]:
    parts, current = [], ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > LIMIT:
            parts.append(current)
            current = ""
        current += line + "\n"
    if current.strip():
        parts.append(current)
    return parts


async def _post_message(http: httpx.AsyncClient, body: dict) -> dict:
    target = {"chat_id": config.MAX_CHAT_ID} if config.MAX_CHAT_ID else {"user_id": config.MAX_USER_ID}
    for attempt in range(5):
        resp = await http.post(f"{config.MAX_API}/messages", params={**target, "disable_link_preview": "true"},
                               json=body, headers={"Authorization": config.MAX_BOT_TOKEN})
        data = resp.json() if resp.content else {}
        if resp.status_code == 200 and "message" in data:
            return data
        if data.get("code") == "attachment.not.ready" and attempt < 4:
            await asyncio.sleep(2 * (attempt + 1))
            continue
        raise RuntimeError(data.get("message") or data.get("code") or f"HTTP {resp.status_code}")
    raise RuntimeError("attachment not ready")


async def send_report(report: dict, pdf: bytes | None, filename: str) -> str:
    if not configured():
        raise RuntimeError("MAX не настроен: заполните MAX_BOT_TOKEN и MAX_CHAT_ID (или MAX_USER_ID)")
    async with httpx.AsyncClient(timeout=60, verify=_ssl()) as http:
        for part in split(render_markdown(report)):
            await _post_message(http, {"text": part, "format": "markdown"})
            await asyncio.sleep(0.6)  # 2 messages per second per chat
        if pdf:
            up = await http.post(f"{config.MAX_API}/uploads", params={"type": "file"},
                                 headers={"Authorization": config.MAX_BOT_TOKEN})
            up.raise_for_status()
            info = up.json()
            sent = await http.post(info["url"], files={"data": (filename, pdf, "application/pdf")},
                                   headers={"Authorization": config.MAX_BOT_TOKEN})
            sent.raise_for_status()
            token = info.get("token") or sent.json().get("token")
            await _post_message(http, {"text": "PDF-версия отчёта",
                                       "attachments": [{"type": "file", "payload": {"token": token}}]})
    return "отправлено"
