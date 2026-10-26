"""Database models. Times are stored as naive UTC."""

from datetime import datetime, timezone

from sqlalchemy import (
    JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint,
    create_engine, event, select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from . import config


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


engine = create_engine(config.DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 30})


@event.listens_for(engine, "connect")
def _sqlite_pragmas(conn, _record):
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


SessionLocal = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Source(Base):
    """A community to monitor: a Telegram channel or chat, or a VK wall."""

    __tablename__ = "sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(8))  # tg | vk
    url: Mapped[str] = mapped_column(String(300), unique=True)
    title: Mapped[str] = mapped_column(String(300), default="")
    # governor: comments get top priority; official: administration's own pages.
    role: Mapped[str] = mapped_column(String(16), default="local")  # local | official | governor
    kind: Mapped[str] = mapped_column(String(16), default="")  # channel | chat | wall
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    state: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="new")  # new | ok | error | join_needed
    last_error: Mapped[str] = mapped_column(Text, default="")
    last_checked: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Problem(Base):
    """A cluster of messages about one issue in one place."""

    __tablename__ = "problems"
    id: Mapped[int] = mapped_column(primary_key=True)
    topic: Mapped[str] = mapped_column(String(16), index=True)
    title: Mapped[str] = mapped_column(String(300))
    address: Mapped[str] = mapped_column(String(300), default="")
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(16), default="new")
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    note: Mapped[str] = mapped_column(Text, default="")
    items: Mapped[list["Item"]] = relationship(back_populates="problem")


class Item(Base):
    """A post, a comment under a post, or a message in a chat."""

    __tablename__ = "items"
    __table_args__ = (UniqueConstraint("source_id", "external_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(10))  # post | comment | chat
    external_id: Mapped[str] = mapped_column(String(64))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("items.id", ondelete="SET NULL"), index=True)
    url: Mapped[str] = mapped_column(String(400), default="")
    author: Mapped[str] = mapped_column(String(200), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    published_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    views: Mapped[int] = mapped_column(Integer, default=0)
    replies: Mapped[int] = mapped_column(Integer, default=0)

    # Filled by the classifier.
    classified: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    classifier: Mapped[str] = mapped_column(String(16), default="")  # claude | rules
    relevant: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    sentiment: Mapped[str] = mapped_column(String(10), default="neutral", index=True)
    topic: Mapped[str] = mapped_column(String(16), default="other", index=True)
    summary: Mapped[str] = mapped_column(String(400), default="")
    about_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    address: Mapped[str] = mapped_column(String(300), default="")
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)
    geo_precision: Mapped[str] = mapped_column(String(12), default="")  # house | street | locality
    priority: Mapped[int] = mapped_column(Integer, default=0, index=True)
    problem_id: Mapped[int | None] = mapped_column(ForeignKey("problems.id", ondelete="SET NULL"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="new", index=True)

    source: Mapped[Source] = relationship()
    parent: Mapped["Item | None"] = relationship(remote_side=[id])
    problem: Mapped[Problem | None] = relationship(back_populates="items")


class GeoCache(Base):
    __tablename__ = "geocache"
    query: Mapped[str] = mapped_column(String(300), primary_key=True)
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)
    precision: Mapped[str] = mapped_column(String(12), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ReportPreset(Base):
    """A saved report configuration, optionally sent to MAX every day."""

    __tablename__ = "report_presets"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(16))  # daily | topics | problem
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    auto_send: Mapped[bool] = mapped_column(Boolean, default=False)
    send_time: Mapped[str] = mapped_column(String(5), default="08:05")
    last_sent: Mapped[datetime | None] = mapped_column(DateTime)


class Delivery(Base):
    """A report sent to MAX."""

    __tablename__ = "deliveries"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    ok: Mapped[bool] = mapped_column(Boolean, default=False)
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(300))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")


def get_setting(db, key: str, default: str = "") -> str:
    row = db.get(Setting, key)
    return row.value if row else default


def set_setting(db, key: str, value: str) -> None:
    row = db.get(Setting, key)
    if row:
        row.value = value
    else:
        db.add(Setting(key=key, value=value))
    db.commit()


def init_db() -> None:
    Base.metadata.create_all(engine)
    from .sources import seed_sources

    with SessionLocal() as db:
        seed_sources(db)
        from .auth import ensure_admin

        ensure_admin(db)


__all__ = ["select"]
