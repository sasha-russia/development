"""Classify new items: relevance, sentiment, topic, address, problem. Then geocode and cluster."""

import json
import logging
import re
from datetime import timedelta

import anthropic
from sqlalchemy import select

from . import config
from .db import Item, Problem, utcnow
from .geocode import clean_address, geocode
from .localities import SETTLEMENTS, find_settlement
from .topics import (
    ADMIN_PATTERN, MAIN_TOPICS, NEGATIVE_PATTERN, POSITIVE_PATTERN, TOPIC_PATTERNS, TOPICS,
    mentions_local, norm,
)

log = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""Ты аналитик, который мониторит соцсети городского округа Мытищи (Московская область) \
для администрации округа. Тебе дают сообщения из Telegram и ВКонтакте: посты, комментарии под \
постами и сообщения в чатах. Для каждого сообщения определи:

- relevant: касается ли сообщение жизни городского округа Мытищи (город Мытищи, Пирогово и другие \
населённые пункты округа), его жителей или администрации. Сообщения о других городах, реклама, \
спам, приветствия и пустые реплики без содержания — false.
- sentiment: negative — жалоба, недовольство, критика, сообщение о проблеме; positive — \
благодарность, одобрение; neutral — всё остальное (новости, вопросы без претензии, объявления).
- topic: {", ".join(f"{k} ({v})" for k, v in TOPICS.items())}.
- about_admin: упоминается ли администрация округа, глава округа, чиновники или муниципальные службы.
- summary: суть проблемы одной фразой до 120 знаков, без эмоций и имён (например «Нет горячей воды \
в доме»). Пусто, если проблемы нет.
- address: улица и номер дома, двор, объект (школа №, поликлиника, парк), как в тексте и в \
нормальной форме: «улица Колонцова, 5», «Олимпийский проспект, 10к1», «парк Яуза». Если адреса нет \
в самом сообщении, но он есть в родительском посте и комментарий про ту же проблему — возьми из поста. \
Пусто, если места нет.
- locality: населённый пункт округа из списка ниже, если понятен из сообщения или поста, иначе пусто. \
Мкр. Перловка, Тайнинка, Новые Мытищи, Леонидовка, Шараповка — это город Мытищи.
- problem_id: если сообщение про одну из уже известных проблем из списка (то же место и та же суть) — \
её id, иначе 0. Комментарий про ту же проблему, что и пост, получает проблему поста.
- new_problem_title: если problem_id = 0 и сообщение негативное и про конкретную проблему — короткое \
название новой проблемы с местом, до 100 знаков («Нет горячей воды: ул. Мира, 10»). Иначе пусто.

Сообщения о любом населённом пункте округа так же важны, как о самом городе Мытищи. \
Населённые пункты городского округа Мытищи: {", ".join(f"{n} ({t})" for n, t in SETTLEMENTS)}.

Отвечай только данными по схеме, по одному объекту на каждое сообщение, с тем же id."""

RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "relevant": {"type": "boolean"},
                    "sentiment": {"type": "string", "enum": ["negative", "neutral", "positive"]},
                    "topic": {"type": "string", "enum": list(TOPICS)},
                    "about_admin": {"type": "boolean"},
                    "summary": {"type": "string"},
                    "address": {"type": "string"},
                    "locality": {"type": "string"},
                    "problem_id": {"type": "integer"},
                    "new_problem_title": {"type": "string"},
                },
                "required": ["id", "relevant", "sentiment", "topic", "about_admin", "summary", "address",
                             "locality", "problem_id", "new_problem_title"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["items"],
    "additionalProperties": False,
}

_client: anthropic.AsyncAnthropic | None = None


def _claude() -> anthropic.AsyncAnthropic | None:
    global _client
    if not config.ANTHROPIC_API_KEY:
        return None
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


def _item_payload(item: Item) -> dict:
    data = {
        "id": item.id,
        "type": {"post": "пост", "comment": "комментарий", "chat": "сообщение в чате"}[item.kind],
        "source": item.source.title,
        "text": item.text[:2000],
    }
    if item.parent:
        data["parent_post"] = item.parent.text[:600]
        if item.parent.problem_id:
            data["parent_problem_id"] = item.parent.problem_id
    return data


async def classify_with_claude(client, items: list[Item], problems: list[Problem]) -> dict[int, dict]:
    known = [{"id": p.id, "topic": p.topic, "title": p.title} for p in problems]
    user = (
        "Известные проблемы за последние две недели:\n" + json.dumps(known, ensure_ascii=False)
        + "\n\nСообщения:\n" + json.dumps([_item_payload(i) for i in items], ensure_ascii=False)
    )
    kwargs = {}
    if config.CLAUDE_MODEL in ("claude-opus-5-5", "claude-opus-5", "claude-fable-5-1", "claude-sonnet-5-5"):
        # On a safety decline the API re-runs the request on Anthropic's recommended fallback model.
        kwargs = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}
    response = await client.beta.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=16000,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": RESULT_SCHEMA}},
        **kwargs,
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Claude declined the batch")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("Batch output was cut off")
    text = next(b.text for b in response.content if b.type == "text")
    return {row["id"]: row for row in json.loads(text)["items"]}


ADDRESS_RE = re.compile(
    r"(?:(?:ул\.|улиц[аеы]|пр-т|просп\.|проспект[ае]?|ш\.|шоссе|б-р|бульвар[ае]?|пер\.|переул[ок]+[ае]?|проезд[ае]?|мкр\.?|микрорайон[ае]?)"
    r"\s+[А-ЯЁ0-9][\w\-ё]*(?:\s[А-ЯЁ][\w\-ё]*)?"
    r"|[А-ЯЁ][\w\-ё]+(?:ая|ой|ий)\s+(?:улиц[аеы]|проспект[ае]?|шоссе|бульвар[ае]?))"
    r"(?:,?\s*(?:д\.|дом)?\s*\d+[а-я]?(?:\s?(?:к|корп\.?|стр\.?)\s?\d+)?)?"
)


def classify_with_rules(item: Item) -> dict:
    t = norm(item.text)
    scores = {topic: len(p.findall(t)) for topic, p in TOPIC_PATTERNS.items()}
    topic = max(scores, key=scores.get) if max(scores.values()) else "other"
    if topic == "other" and item.parent:
        topic = classify_with_rules(item.parent)["topic"]  # a short comment keeps its post's topic
    neg, pos = len(NEGATIVE_PATTERN.findall(t)), len(POSITIVE_PATTERN.findall(t))
    sentiment = "negative" if neg > pos else ("positive" if pos > neg else "neutral")
    relevant = len(t.strip()) >= 15 and (item.source.role != "governor" or mentions_local(t))
    m = ADDRESS_RE.search(item.text)
    address = m.group(0).strip(" ,") if m else ""
    if not address and item.parent:
        pm = ADDRESS_RE.search(item.parent.text)
        address = pm.group(0).strip(" ,") if pm else ""
    locality = find_settlement(item.text) or (find_settlement(item.parent.text) if item.parent else "")
    first = re.split(r"(?<=[.!?\n])\s", item.text.strip(), maxsplit=1)[0][:120]
    return {
        "relevant": relevant, "sentiment": sentiment, "topic": topic,
        "about_admin": bool(ADMIN_PATTERN.search(t)), "summary": first if sentiment == "negative" else "",
        "address": address, "locality": locality,
        "problem_id": item.parent.problem_id if item.parent and item.parent.problem_id else 0,
        "new_problem_title": "",
    }


def priority_of(item: Item) -> int:
    if not item.relevant:
        return 0
    negative = item.sentiment == "negative"
    if item.source.role == "governor" and item.kind != "post":
        return 3 if negative else 2
    if not negative:
        return 0
    if item.kind != "post" and item.source.role == "official":
        return 2
    if item.about_admin or item.likes >= 10 or item.replies >= 20:
        return 2
    return 1


def _street_key(address: str) -> str:
    return re.sub(r"[^а-яa-z0-9]", "", norm(address))


def same_place(a: str, b: str) -> bool:
    """Same address, or the same street when one of them has no house number."""
    ka, kb = _street_key(a), _street_key(b)
    if ka == kb:
        return True
    sa, sb = re.sub(r"\d.*$", "", ka), re.sub(r"\d.*$", "", kb)
    return bool(sa) and sa == sb and (sa == ka or sb == kb)


async def apply_result(db, item: Item, r: dict, classifier: str) -> None:
    item.classified, item.classifier = True, classifier
    item.relevant = bool(r["relevant"])
    item.sentiment = r["sentiment"] if r["sentiment"] in ("negative", "neutral", "positive") else "neutral"
    item.topic = r["topic"] if r["topic"] in TOPICS else "other"
    item.about_admin = bool(r["about_admin"])
    item.summary = (r.get("summary") or "")[:400]
    item.address = clean_address(r.get("address") or "")[:300]
    item.priority = priority_of(item)
    if not item.relevant:
        return

    locality = r.get("locality") or ""
    if item.address or (locality and locality.lower() != "мытищи"):
        found = await geocode(db, item.address, locality)
        if found:
            item.lat, item.lon, item.geo_precision = found
    if item.lat is None and item.parent and item.parent.lat is not None:
        item.lat, item.lon, item.geo_precision = item.parent.lat, item.parent.lon, item.parent.geo_precision

    problem = None
    if r.get("problem_id"):
        problem = db.get(Problem, r["problem_id"])
    parent = item.parent
    if problem is None and parent and parent.problem_id and parent.topic == item.topic:
        # A comment on the same topic as its post belongs to the post's problem.
        problem = db.get(Problem, parent.problem_id)
    if problem is None and item.sentiment == "negative":
        title = (r.get("new_problem_title") or "").strip()
        place = clean_address(item.address) or (locality if locality.lower() != "мытищи" else "")
        if not title and classifier == "rules" and place:
            # Rules: one problem per topic and place.
            for p in db.scalars(select(Problem).where(Problem.topic == item.topic,
                                                      Problem.last_seen >= utcnow() - timedelta(days=14))):
                if same_place(p.address, place):
                    problem = p
                    break
            title = f"{TOPICS[item.topic]}: {place}"
        if problem is None and title:
            problem = Problem(topic=item.topic, title=title[:300], address=place,
                              first_seen=item.published_at, last_seen=item.published_at)
            db.add(problem)
            db.flush()
    if problem is not None:
        item.problem_id = problem.id
        problem.last_seen = max(problem.last_seen, item.published_at)
        problem.first_seen = min(problem.first_seen, item.published_at)
        if problem.status == "done" and item.sentiment == "negative":
            problem.status = "new"  # people still complain
        if item.lat is not None and (problem.lat is None or item.geo_precision == "house"):
            problem.lat, problem.lon = item.lat, item.lon
            problem.address = problem.address or item.address


async def classify_pending(db, limit: int = 400) -> int:
    pending = db.scalars(
        select(Item).where(Item.classified.is_(False)).order_by(Item.kind != "post", Item.published_at).limit(limit)
    ).all()
    if not pending:
        return 0
    client = _claude()
    done = 0
    # Governor's posts and comments about other towns never reach the model.
    queue = []
    for item in pending:
        if not item.text.strip() or (item.source.role == "governor" and not mentions_local(item.text)):
            await apply_result(db, item, {**classify_with_rules(item), "relevant": False}, "rules")
            done += 1
        else:
            queue.append(item)
    db.commit()

    for start in range(0, len(queue), config.CLASSIFY_BATCH):
        batch = queue[start:start + config.CLASSIFY_BATCH]
        results, used = {}, "rules"
        if client:
            problems = db.scalars(
                select(Problem).where(Problem.last_seen >= utcnow() - timedelta(days=14))
                .order_by(Problem.last_seen.desc()).limit(80)
            ).all()
            try:
                results, used = await classify_with_claude(client, batch, problems), "claude"
            except (anthropic.APIError, RuntimeError, ValueError, KeyError) as e:
                log.warning("Claude classification failed, using rules: %s", e)
        for item in batch:
            r = results.get(item.id) or classify_with_rules(item)
            await apply_result(db, item, r, used if item.id in results else "rules")
            done += 1
        db.commit()
    return done


__all__ = ["classify_pending", "MAIN_TOPICS"]
