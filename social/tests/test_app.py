import json
import os
import tempfile
from datetime import date, datetime, timedelta

os.environ["DATA_DIR"] = tempfile.mkdtemp()
os.environ["DISABLE_SCHEDULER"] = "1"
os.environ["ADMIN_PASSWORD"] = "test-password"

import httpx2  # noqa: E402  (the Anthropic SDK is built on httpx2)
import pytest  # noqa: E402
from anthropic import AsyncAnthropic  # noqa: E402

from app import classify, config, geocode  # noqa: E402
from app.db import Item, Problem, SessionLocal, init_db, utcnow  # noqa: E402
from app.localities import SETTLEMENTS, find_settlement, mentions_district  # noqa: E402
from app.reports import report_day_window, to_local  # noqa: E402
from app.sources import add_source, normalize_url  # noqa: E402

init_db()


@pytest.fixture(autouse=True)
def fake_geocoder(monkeypatch):
    async def fake(query):
        q = query.lower()
        if "колонцова, 5" in q:
            return 55.9162, 37.7659, "house"
        if "колонцова" in q:
            return 55.9104, 37.7700, "street"
        if "пирогово" in q:
            return 55.9782, 37.7270, "locality"
        return None

    monkeypatch.setattr(geocode, "_nominatim", fake)


def test_all_92_settlements_listed():
    assert len(SETTLEMENTS) == 92
    assert ("Мытищи", "город") in SETTLEMENTS


@pytest.mark.parametrize("text,expected", [
    ("В Пирогове опять нет воды", True),
    ("Жостово: нет автобусов", True),
    ("дер. Юдино дорога разбита", True),
    ("В Тайнинке яма", True),
    ("Юдин сказал правильно", False),
    ("высоковольтная линия гудит", False),
    ("Зеленоград, Крюково, пробки", False),
    ("В Химках тоже без света", False),
])
def test_district_mentions(text, expected):
    assert mentions_district(text) is expected


def test_find_settlement():
    assert find_settlement("Мусор в Федоскино не вывозят") == "Федоскино"
    assert find_settlement("пос. Трудовая, свалка") == "Трудовая"
    assert find_settlement("Трудовая неделя") == ""


def test_clean_address():
    assert geocode.clean_address("на улице Колонцова, 5") == "улица Колонцова, 5"
    assert geocode.clean_address("Олимпийском проспекте, 29") == "Олимпийский проспект, 29"
    assert geocode.clean_address("Ярославском шоссе") == "Ярославское шоссе"


def test_normalize_url():
    assert normalize_url("vk.ru/andreyvorobiev/") == "https://vk.com/andreyvorobiev"
    assert normalize_url("http://t.me/mspeaks") == "https://t.me/mspeaks"


def test_daily_window_is_8_to_8_moscow():
    start, end = report_day_window(date(2026, 10, 26))
    assert to_local(start) == datetime(2026, 10, 25, 8, 0)
    assert to_local(end) == datetime(2026, 10, 26, 8, 0)


def _post(db, source, text, comments=(), hours=2):
    post = Item(source_id=source.id, kind="post", external_id=f"p{text[:10]}{hours}", text=text,
                published_at=utcnow() - timedelta(hours=hours), url="https://t.me/x/1")
    db.add(post)
    db.flush()
    for n, c in enumerate(comments):
        db.add(Item(source_id=source.id, kind="comment", external_id=f"{post.id}c{n}", text=c, parent_id=post.id,
                    published_at=post.published_at + timedelta(minutes=n + 1), url="https://t.me/x/1?comment=1"))
    db.commit()
    return post


async def test_rules_pipeline_groups_comments_into_problem():
    with SessionLocal() as db:
        src = add_source(db, "https://t.me/test_rules", "local")
        post = _post(db, src, "Жители дома на улице Колонцова, 5 третий день без горячей воды",
                     ["Сколько можно, опять нет воды!", "Спасибо, дали воду"])
        await classify.classify_pending(db)
        db.refresh(post)
        assert post.relevant and post.sentiment == "negative" and post.topic == "zhkh"
        assert post.geo_precision == "house" and post.problem_id
        comments = db.query(Item).filter(Item.parent_id == post.id).all()
        assert all(c.problem_id == post.problem_id for c in comments)
        assert {c.sentiment for c in comments} == {"negative", "positive"}


async def test_governor_comments_get_top_priority_and_others_are_dropped():
    with SessionLocal() as db:
        gov = add_source(db, "https://t.me/test_governor", "governor")
        post = _post(db, gov, "Совещание по ЖКХ", ["В Пирогово мусор не вывозят, безобразие", "В Химках нет воды"],
                     hours=3)
        await classify.classify_pending(db)
        local, other = db.query(Item).filter(Item.parent_id == post.id).order_by(Item.id).all()
        assert local.relevant and local.priority == 3
        assert not other.relevant and other.priority == 0


async def test_claude_request_and_parsing(monkeypatch):
    sent = {}

    def handler(request: httpx2.Request) -> httpx2.Response:
        sent["body"] = json.loads(request.content)
        sent["beta"] = request.headers.get("anthropic-beta")
        ids = [m["id"] for m in json.loads(sent["body"]["messages"][0]["content"].split("Сообщения:\n", 1)[1])]
        rows = [{"id": i, "relevant": True, "sentiment": "negative", "topic": "roads", "about_admin": False,
                 "summary": "Яма на дороге", "address": "Олимпийский проспект, 29", "locality": "Мытищи",
                 "problem_id": 0, "new_problem_title": "Яма: Олимпийский проспект, 29"} for i in ids]
        return httpx2.Response(200, json={
            "id": "msg_1", "type": "message", "role": "assistant", "model": config.CLAUDE_MODEL,
            "content": [{"type": "text", "text": json.dumps({"items": rows}, ensure_ascii=False)}],
            "stop_reason": "end_turn", "stop_sequence": None,
            "usage": {"input_tokens": 10, "output_tokens": 10},
        })

    client = AsyncAnthropic(api_key="test", http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler)))
    monkeypatch.setattr(classify, "_claude", lambda: client)
    with SessionLocal() as db:
        src = add_source(db, "https://t.me/test_claude", "local")
        post = _post(db, src, "Огромная яма на Олимпийском проспекте у дома 29", hours=5)
        await classify.classify_pending(db)
        db.refresh(post)
        assert post.classifier == "claude" and post.topic == "roads"
        problem = db.get(Problem, post.problem_id)
        assert problem.title == "Яма: Олимпийский проспект, 29"
    body = sent["body"]
    assert body["model"] == config.CLAUDE_MODEL
    assert body["output_config"]["format"]["type"] == "json_schema"
    assert body["output_config"]["effort"] == "low"
    assert body["fallbacks"] == "default" and "server-side-fallback-2026-07-01" in sent["beta"]
    assert "Федоскино" in body["system"][0]["text"]


def test_web_flow():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as web:
        assert web.get("/", follow_redirects=False).status_code == 303
        web.post("/login", data={"login": "admin", "password": "test-password"})
        data = web.get("/api/dashboard?period=week&sentiment=negative").json()
        assert data["stats"]["negative"] >= 1 and data["heat"]
        for url in ["/", "/queue", "/problems", "/reports", "/sources", "/settings",
                    "/reports/view?kind=daily&day=today", "/reports/view?kind=topics&period=week&day=today"]:
            assert web.get(url).status_code == 200, url
        problem_id = data["problems"][0]["id"]
        assert web.get(f"/problems/{problem_id}").status_code == 200
        pdf = web.get(f"/reports/pdf?kind=problem&problem_id={problem_id}")
        assert pdf.headers["content-type"] == "application/pdf" and pdf.content.startswith(b"%PDF")
        # Cross-site POSTs are refused.
        assert web.post("/collect", headers={"origin": "https://evil.example"}).status_code == 403


async def test_vk_collector_keeps_only_district_comments_under_governor():
    from app.collectors import vk

    now = int(utcnow().timestamp()) + 0

    class FakeVK:
        async def call(self, method, **params):
            if method == "wall.get":
                return {"items": [{"id": 10, "owner_id": -1, "date": now - 3600, "text": "Пост губернатора",
                                   "comments": {"count": 2}, "likes": {"count": 5}, "views": {"count": 100}}],
                        "groups": [{"id": 1, "name": "Андрей Воробьёв"}], "profiles": []}
            return {"items": [
                {"id": 1, "from_id": 7, "date": now - 600, "text": "В Мытищах на Мира 10 нет света", "likes": {"count": 3}},
                {"id": 2, "from_id": 8, "date": now - 500, "text": "В Подольске пробки", "likes": {"count": 1}},
            ], "profiles": [{"id": 7, "first_name": "Иван", "last_name": "П."}], "groups": []}

    with SessionLocal() as db:
        src = add_source(db, "https://vk.com/test_gov", "governor")
        added = await vk.collect_source(FakeVK(), db, src, [])
        db.commit()
        texts = [i.text for i in db.query(Item).filter(Item.source_id == src.id, Item.kind == "comment")]
        assert added == 2 and texts == ["В Мытищах на Мира 10 нет света"]
        assert src.title == "Андрей Воробьёв"
        # A second pass with the same comment count fetches nothing new.
        assert await vk.collect_source(FakeVK(), db, src, []) == 0
