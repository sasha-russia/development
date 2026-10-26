"""Turn report parameters into report data, HTML, PDF and MAX messages."""

import asyncio
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

from fastapi.templating import Jinja2Templates

from . import config, max_bot
from .db import Delivery
from .reports import Filters, daily_report, fmt, problem_report, today_local, topics_report
from .topics import MAIN_TOPICS, SENTIMENTS, STATUSES, TOPICS

HERE = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=HERE / "templates")


def qs(kind: str, params: dict) -> str:
    """Query string for a report: kind plus its parameters (lists repeat the key)."""
    pairs = [("kind", kind)] + [(k, v) for k, v in params.items() if v not in (None, "", [])]
    return urlencode(pairs, doseq=True)


templates.env.globals.update(qs=qs, TOPICS=TOPICS, MAIN_TOPICS=MAIN_TOPICS, SENTIMENTS=SENTIMENTS, STATUSES=STATUSES,
                             fmt=fmt, BASE_URL=config.BASE_URL)

KINDS = {"daily": "Сутки 8:00–8:00", "topics": "По темам", "problem": "По проблеме"}


def _day(value) -> date:
    if not value or value == "today":
        return today_local()
    return date.fromisoformat(str(value))


def _list(params: dict, key: str) -> list[str]:
    value = params.get(key) or []
    return [value] if isinstance(value, str) else [v for v in value if v]


def build_report(db, kind: str, params: dict) -> dict | None:
    base = Filters(start=None, end=None, sentiments=_list(params, "sentiment"),  # type: ignore[arg-type]
                   platforms=_list(params, "platform"), roles=_list(params, "role"),
                   topics=_list(params, "topic"))
    if kind == "daily":
        return daily_report(db, _day(params.get("day")), base)
    if kind == "topics":
        return topics_report(db, _list(params, "topic"), params.get("period") or "day", _day(params.get("day")), base)
    if kind == "problem" and params.get("problem_id"):
        return problem_report(db, int(params["problem_id"]))
    return None


def report_html(report: dict, for_pdf: bool = False) -> str:
    return templates.get_template("report_pdf.html").render(report=report, for_pdf=for_pdf)


def report_pdf(report: dict) -> bytes:
    from weasyprint import HTML

    return HTML(string=report_html(report, for_pdf=True), base_url=str(HERE / "static")).write_pdf()


def pdf_filename(report: dict) -> str:
    stamp = today_local().strftime("%Y-%m-%d")
    return {"daily": f"negativ-{stamp}.pdf", "topics": f"temy-{stamp}.pdf"}.get(
        report["kind"], f"problema-{report.get('problem').id if report.get('problem') else ''}.pdf")


async def send_to_max(db, report: dict) -> Delivery:
    delivery = Delivery(title=report["title"][:300])
    try:
        pdf = await asyncio.to_thread(report_pdf, report)
        delivery.detail = await max_bot.send_report(report, pdf, pdf_filename(report))
        delivery.ok = True
    except Exception as e:
        delivery.detail = f"{type(e).__name__}: {e}"[:1000]
    db.add(delivery)
    db.commit()
    return delivery
