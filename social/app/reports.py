"""Filters, dashboard aggregates and report data. One data builder feeds web, PDF and MAX."""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import Select, func, select
from sqlalchemy.orm import joinedload

from . import config
from .db import Item, Problem, Source, utcnow
from .topics import MAIN_TOPICS, SENTIMENTS, TOPICS

PERIODS = {
    "1h": ("Час", timedelta(hours=1)),
    "3h": ("3 часа", timedelta(hours=3)),
    "day": ("Сутки", timedelta(days=1)),
    "week": ("Неделя", timedelta(days=7)),
    "month": ("Месяц", timedelta(days=30)),
    "quarter": ("Квартал", timedelta(days=91)),
    "year": ("Год", timedelta(days=365)),
}


def to_utc(dt: datetime) -> datetime:
    """Local (Moscow) naive datetime -> naive UTC."""
    return dt.replace(tzinfo=config.TZ).astimezone(timezone.utc).replace(tzinfo=None)


def to_local(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc).astimezone(config.TZ).replace(tzinfo=None)


def fmt(dt: datetime | None, with_date: bool = True) -> str:
    local = to_local(dt)
    if local is None:
        return ""
    return local.strftime("%d.%m.%Y %H:%M" if with_date else "%H:%M")


def report_day_window(day: date) -> tuple[datetime, datetime]:
    """The daily report for `day` covers the previous day 08:00 to `day` 08:00, Moscow time."""
    end = datetime.combine(day, time(config.DAY_START_HOUR))
    return to_utc(end - timedelta(days=1)), to_utc(end)


def today_local() -> date:
    return to_local(utcnow()).date()


@dataclass
class Filters:
    start: datetime
    end: datetime
    topics: list[str] = field(default_factory=list)
    sentiments: list[str] = field(default_factory=list)
    platforms: list[str] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    source_ids: list[int] = field(default_factory=list)

    @classmethod
    def from_params(cls, params) -> "Filters":
        """From query parameters: period=day or from/to (local time), topic, sentiment, platform, role."""
        get_list = (lambda k: [v for v in params.getlist(k) if v]) if hasattr(params, "getlist") else (
            lambda k: [v for v in (params.get(k) or []) if v] if isinstance(params.get(k), list)
            else ([params[k]] if params.get(k) else []))
        period = params.get("period") or "day"
        end = utcnow()
        if period == "custom" and params.get("from"):
            start = to_utc(datetime.fromisoformat(params["from"]))
            if params.get("to"):
                end = to_utc(datetime.fromisoformat(params["to"]))
        else:
            start = end - PERIODS.get(period, PERIODS["day"])[1]
        return cls(
            start=start, end=end, topics=get_list("topic"), sentiments=get_list("sentiment"),
            platforms=get_list("platform"), roles=get_list("role"),
            source_ids=[int(v) for v in get_list("source")],
        )

    def apply(self, q: Select) -> Select:
        q = q.select_from(Item).join(Source, Item.source_id == Source.id).where(
            Item.relevant.is_(True), Item.published_at >= self.start, Item.published_at < self.end)
        if self.topics:
            q = q.where(Item.topic.in_(self.topics))
        if self.sentiments:
            q = q.where(Item.sentiment.in_(self.sentiments))
        if self.platforms:
            q = q.where(Source.platform.in_(self.platforms))
        if self.roles:
            q = q.where(Source.role.in_(self.roles))
        if self.source_ids:
            q = q.where(Source.id.in_(self.source_ids))
        return q

    def label(self) -> str:
        return f"{fmt(self.start)} — {fmt(self.end)}"


def dashboard_stats(db, f: Filters) -> dict:
    rows = db.execute(f.apply(select(Item.topic, Item.sentiment, Source.role, Item.kind, func.count())
                              ).group_by(Item.topic, Item.sentiment, Source.role, Item.kind)).all()
    by_topic = {t: Counter() for t in TOPICS}
    total, sentiments, governor = 0, Counter(), 0
    for topic, sentiment, role, kind, n in rows:
        total += n
        sentiments[sentiment] += n
        by_topic.setdefault(topic, Counter())[sentiment] += n
        if role == "governor" and kind != "post":
            governor += n
    problems = db.scalar(f.apply(select(func.count(func.distinct(Item.problem_id)))).where(
        Item.problem_id.is_not(None)))
    open_queue = db.scalar(f.apply(select(func.count())).where(Item.priority > 0, Item.status == "new"))
    return {
        "total": total, "negative": sentiments["negative"], "positive": sentiments["positive"],
        "neutral": sentiments["neutral"], "governor": governor, "problems": problems or 0,
        "queue": open_queue or 0,
        "topics": [
            {"key": t, "label": TOPICS[t], "total": sum(c.values()), "negative": c["negative"]}
            for t, c in by_topic.items() if t in TOPICS
        ],
    }


def heat_points(db, f: Filters) -> list[dict]:
    """Messages with coordinates, merged per place (about 10 m)."""
    rows = db.execute(f.apply(
        select(func.round(Item.lat, 4), func.round(Item.lon, 4), Item.topic, Item.sentiment, Item.problem_id,
               func.count())
    ).where(Item.lat.is_not(None)).group_by(func.round(Item.lat, 4), func.round(Item.lon, 4), Item.topic,
                                            Item.sentiment, Item.problem_id)).all()
    places: dict[tuple, dict] = {}
    for lat, lon, topic, sentiment, problem_id, n in rows:
        p = places.setdefault((lat, lon), {"lat": lat, "lon": lon, "count": 0, "negative": 0,
                                           "topics": Counter(), "problems": set()})
        p["count"] += n
        p["negative"] += n if sentiment == "negative" else 0
        p["topics"][topic] += n
        if problem_id:
            p["problems"].add(problem_id)
    titles = {}
    ids = {pid for p in places.values() for pid in p["problems"]}
    if ids:
        titles = dict(db.execute(select(Problem.id, Problem.title).where(Problem.id.in_(ids))).all())
    out = []
    for p in places.values():
        out.append({
            "lat": p["lat"], "lon": p["lon"], "count": p["count"], "negative": p["negative"],
            "topic": TOPICS.get(p["topics"].most_common(1)[0][0], ""),
            "problems": [{"id": pid, "title": titles.get(pid, "")} for pid in sorted(p["problems"])][:8],
        })
    return out


def problem_rows(db, f: Filters, limit: int = 50) -> list[dict]:
    """Problems with messages in the window, most discussed first."""
    items = db.scalars(f.apply(select(Item)).where(Item.problem_id.is_not(None))
                       .options(joinedload(Item.source))).all()
    groups: dict[int, list[Item]] = defaultdict(list)
    for item in items:
        groups[item.problem_id].append(item)
    problems = {p.id: p for p in db.scalars(select(Problem).where(Problem.id.in_(groups)))} if groups else {}
    rows = [problem_summary(problems[pid], its) for pid, its in groups.items() if pid in problems]
    rows.sort(key=lambda r: (r["score"], r["last_seen"]), reverse=True)
    return rows[:limit]


def problem_summary(problem: Problem, items: list[Item]) -> dict:
    mentions = sum(1 for i in items if i.kind in ("post", "chat"))
    comments = sum(1 for i in items if i.kind == "comment")
    governor = sum(1 for i in items if i.source.role == "governor" and i.kind != "post")
    sentiments = Counter(i.sentiment for i in items)
    reach = sum(i.views for i in items if i.kind == "post")
    return {
        "id": problem.id, "title": problem.title, "topic": problem.topic, "topic_label": TOPICS.get(problem.topic, ""),
        "address": problem.address, "lat": problem.lat, "lon": problem.lon, "status": problem.status,
        "mentions": mentions, "comments": comments, "governor": governor, "total": len(items),
        "reach": reach, "likes": sum(i.likes for i in items),
        "negative_share": round(100 * sentiments["negative"] / len(items)) if items else 0,
        "sentiments": dict(sentiments),
        # Mentions weigh more than comments; the governor's pages most of all.
        "score": mentions * 2 + comments + governor * 3,
        "sources": sorted({i.source.title for i in items}),
        "first_seen": min(i.published_at for i in items), "last_seen": max(i.published_at for i in items),
        "sample": sorted(items, key=lambda i: (i.sentiment != "negative", -i.likes))[:3],
        "url": f"{config.BASE_URL}/problems/{problem.id}",
    }


def priority_items(db, f: Filters, limit: int = 100, statuses=("new", "in_work")) -> list[Item]:
    q = f.apply(select(Item)).where(Item.priority > 0, Item.status.in_(statuses)).options(
        joinedload(Item.source), joinedload(Item.parent), joinedload(Item.problem))
    return db.scalars(q.order_by(Item.priority.desc(), Item.published_at.desc()).limit(limit)).unique().all()


# Reports -------------------------------------------------------------------------------------

def daily_report(db, day: date, base: Filters | None = None) -> dict:
    start, end = report_day_window(day)
    f = Filters(start=start, end=end, **({k: getattr(base, k) for k in
                                          ("topics", "sentiments", "platforms", "roles", "source_ids")} if base else {}))
    problems = problem_rows(db, f, limit=200)
    governor = db.scalars(f.apply(select(Item)).where(Source.role == "governor", Item.kind != "post")
                          .options(joinedload(Item.source), joinedload(Item.parent))
                          .order_by(Item.priority.desc(), Item.likes.desc())).unique().all()
    loose = db.scalars(f.apply(select(Item)).where(Item.problem_id.is_(None), Item.sentiment == "negative",
                                                   Source.role != "governor")
                       .options(joinedload(Item.source)).order_by(Item.priority.desc(), Item.likes.desc())
                       .limit(40)).unique().all()
    return {
        "kind": "daily",
        "title": f"Негатив в соцсетях за {fmt(start)} — {fmt(end)}",
        "subtitle": "Городской округ Мытищи. Проблемы по числу упоминаний и комментариев",
        "period": f.label(), "filters": f, "stats": dashboard_stats(db, f),
        "governor": governor, "problems": problems, "loose": loose,
    }


def topics_report(db, topics: list[str], period: str, day: date, base: Filters | None = None) -> dict:
    topics = [t for t in topics if t in TOPICS] or list(MAIN_TOPICS)
    length = timedelta(days=7 if period == "week" else 1)
    _, end = report_day_window(day)
    start = end - length
    extra = {k: getattr(base, k) for k in ("sentiments", "platforms", "roles", "source_ids")} if base else {}
    sections = []
    for topic in topics:
        f = Filters(start=start, end=end, topics=[topic], **extra)
        prev = Filters(start=start - length, end=start, topics=[topic], **extra)
        stats, prev_stats = dashboard_stats(db, f), dashboard_stats(db, prev)
        quotes = db.scalars(f.apply(select(Item)).where(Item.sentiment == "negative")
                            .options(joinedload(Item.source)).order_by(Item.likes.desc(), Item.priority.desc())
                            .limit(5)).unique().all()
        sections.append({
            "topic": topic, "label": TOPICS[topic], "stats": stats,
            "prev_negative": prev_stats["negative"], "prev_total": prev_stats["total"],
            "problems": problem_rows(db, f, limit=10), "quotes": quotes,
        })
    return {
        "kind": "topics",
        "title": f"Темы за {'неделю' if period == 'week' else 'сутки'}: {', '.join(TOPICS[t] for t in topics)}",
        "subtitle": "Городской округ Мытищи. Сравнение с предыдущим периодом",
        "period": f"{fmt(start)} — {fmt(end)}", "sections": sections, "period_kind": period,
    }


def problem_report(db, problem_id: int) -> dict | None:
    problem = db.get(Problem, problem_id)
    if not problem:
        return None
    items = db.scalars(select(Item).where(Item.problem_id == problem_id).options(
        joinedload(Item.source), joinedload(Item.parent)).order_by(Item.published_at)).unique().all()
    if not items:
        return None
    summary = problem_summary(problem, items)
    comments = [i for i in items if i.kind != "post"]
    tone = Counter(i.sentiment for i in comments)
    return {
        "kind": "problem", "title": problem.title,
        "subtitle": f"{TOPICS.get(problem.topic, '')} · {problem.address or 'адрес не указан'}",
        "period": f"{fmt(summary['first_seen'])} — {fmt(summary['last_seen'])}",
        "problem": problem, "summary": summary, "items": items,
        "tone": {k: tone[k] for k in SENTIMENTS}, "tone_total": len(comments),
        "by_source": Counter(i.source.title for i in items).most_common(),
    }
