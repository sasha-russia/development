"""Web app: dashboard, queue, problems, reports, sources, settings."""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from . import config, max_bot, worker
from .auth import COOKIE, MAX_AGE, check_password, current_user, hash_password, make_cookie, require_admin, require_user
from .collectors import telegram
from .db import Delivery, Item, Problem, ReportPreset, SessionLocal, Source, User, get_setting, init_db, set_setting, utcnow
from .reports import PERIODS, Filters, dashboard_stats, fmt, heat_points, priority_items, problem_rows, to_local
from .sources import add_source
from .topics import STATUSES, TOPICS
from .web_reports import HERE, KINDS, build_report, pdf_filename, report_html, report_pdf, send_to_max, templates

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = None if config.DISABLE_SCHEDULER else asyncio.create_task(worker.loop())
    yield
    if task:
        task.cancel()
    await worker.reset_telegram()


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")


@app.exception_handler(401)
async def _to_login(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    return RedirectResponse(f"/login?next={request.url.path}", status_code=303)


def page(request: Request, name: str, user, **ctx):
    return templates.TemplateResponse(request, name, {"user": user, "nav": name.split(".")[0], **ctx})


def item_json(i: Item) -> dict:
    return {
        "id": i.id, "kind": i.kind, "text": i.text[:1500], "url": i.url, "author": i.author,
        "source": i.source.title, "platform": i.source.platform, "role": i.source.role,
        "published": fmt(i.published_at), "sentiment": i.sentiment, "topic": i.topic,
        "topic_label": TOPICS.get(i.topic, ""), "summary": i.summary, "address": i.address,
        "priority": i.priority, "status": i.status, "likes": i.likes, "problem_id": i.problem_id,
        "problem": i.problem.title if i.problem else "",
        "parent": i.parent.text[:300] if i.parent else "", "parent_url": i.parent.url if i.parent else "",
    }


# Auth ----------------------------------------------------------------------------------------

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, next: str = "/"):
    return page(request, "login.html", None, next=next, error="")


@app.post("/login")
def login(request: Request, login: str = Form(...), password: str = Form(...), next: str = Form("/")):
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.login == login.strip()))
    if not user or not check_password(password, user.password_hash):
        return page(request, "login.html", None, next=next, error="Неверный логин или пароль")
    resp = RedirectResponse(next if next.startswith("/") and not next.startswith("//") else "/", status_code=303)
    resp.set_cookie(COOKIE, make_cookie(user), max_age=MAX_AGE, httponly=True, samesite="lax",
                    secure=config.BASE_URL.startswith("https"))
    return resp


@app.post("/logout")
def logout():
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie(COOKIE)
    return resp


# Dashboard -----------------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, user=Depends(require_user)):
    return page(request, "dashboard.html", user, periods=PERIODS)


@app.get("/api/dashboard")
def api_dashboard(request: Request, user=Depends(require_user)):
    f = Filters.from_params(request.query_params)
    with SessionLocal() as db:
        return {
            "period": f.label(), "stats": dashboard_stats(db, f), "heat": heat_points(db, f),
            "problems": [{k: v for k, v in p.items() if k != "sample"} | {
                "first_seen": fmt(p["first_seen"]), "last_seen": fmt(p["last_seen"])}
                for p in problem_rows(db, f, limit=30)],
            "queue": [item_json(i) for i in priority_items(db, f, limit=30, statuses=("new",))],
        }


@app.get("/api/items")
def api_items(request: Request, user=Depends(require_user)):
    """Messages for a map place (lat/lon) or a problem, within the dashboard filters."""
    f = Filters.from_params(request.query_params)
    q = request.query_params
    with SessionLocal() as db:
        stmt = f.apply(select(Item)).options(joinedload(Item.source), joinedload(Item.parent),
                                              joinedload(Item.problem))
        if q.get("lat") and q.get("lon"):
            stmt = stmt.where(func.round(Item.lat, 4) == float(q["lat"]), func.round(Item.lon, 4) == float(q["lon"]))
        if q.get("problem"):
            stmt = stmt.where(Item.problem_id == int(q["problem"]))
        items = db.scalars(stmt.order_by(Item.priority.desc(), Item.published_at.desc()).limit(200)).unique().all()
        return [item_json(i) for i in items]


@app.post("/api/items/{item_id}/status")
async def api_item_status(item_id: int, request: Request, user=Depends(require_user)):
    status = (await request.json()).get("status")
    if status not in STATUSES:
        raise HTTPException(400)
    with SessionLocal() as db:
        item = db.get(Item, item_id)
        if not item:
            raise HTTPException(404)
        item.status = status
        db.commit()
    return {"ok": True}


@app.post("/api/items/{item_id}/reclassify")
async def api_item_reclassify(item_id: int, request: Request, user=Depends(require_user)):
    """Manual correction of the topic, tone or relevance."""
    data = await request.json()
    with SessionLocal() as db:
        item = db.get(Item, item_id)
        if not item:
            raise HTTPException(404)
        if data.get("topic") in TOPICS:
            item.topic = data["topic"]
        if data.get("sentiment") in ("negative", "neutral", "positive"):
            item.sentiment = data["sentiment"]
        if "relevant" in data:
            item.relevant = bool(data["relevant"])
        from .classify import priority_of

        item.priority = priority_of(item)
        db.commit()
    return {"ok": True}


# Queue and problems --------------------------------------------------------------------------

@app.get("/queue", response_class=HTMLResponse)
def queue(request: Request, user=Depends(require_user)):
    params = dict(request.query_params)
    params.setdefault("period", "week")
    f = Filters.from_params(params)
    status = request.query_params.get("status", "new")
    with SessionLocal() as db:
        items = priority_items(db, f, limit=300, statuses=(status,) if status != "all" else tuple(STATUSES))
        counts = dict(db.execute(f.apply(select(Item.status, func.count())).where(Item.priority > 0)
                                 .group_by(Item.status)).all())
        items_json = json.dumps([item_json(i) for i in items], ensure_ascii=False).replace("</", "<\\/")
    return page(request, "queue.html", user, items_json=items_json, status=status, counts=counts, periods=PERIODS,
                period=params["period"])


@app.get("/problems", response_class=HTMLResponse)
def problems(request: Request, user=Depends(require_user)):
    params = dict(request.query_params)
    params.setdefault("period", "week")
    f = Filters.from_params(params)
    with SessionLocal() as db:
        rows = problem_rows(db, f, limit=300)
    return page(request, "problems.html", user, rows=rows, periods=PERIODS, period=params["period"],
                topic=request.query_params.get("topic", ""))


@app.get("/problems/{problem_id}", response_class=HTMLResponse)
def problem_page(problem_id: int, request: Request, user=Depends(require_user)):
    with SessionLocal() as db:
        report = build_report(db, "problem", {"problem_id": problem_id})
        if not report:
            raise HTTPException(404)
        others = db.scalars(select(Problem).where(Problem.id != problem_id, Problem.topic == report["problem"].topic,
                                                  Problem.last_seen >= utcnow() - timedelta(days=30))
                            .order_by(Problem.last_seen.desc()).limit(50)).all()
        return page(request, "problem.html", user, report=report, others=others,
                    report_kind="problem", report_params={"problem_id": problem_id}, max_ready=max_bot.configured())


@app.post("/problems/{problem_id}")
def problem_update(problem_id: int, status: str = Form(None), title: str = Form(None), note: str = Form(None),
                   merge_into: int = Form(None), user=Depends(require_user)):
    with SessionLocal() as db:
        problem = db.get(Problem, problem_id)
        if not problem:
            raise HTTPException(404)
        if merge_into:
            target = db.get(Problem, merge_into)
            if target:
                for item in problem.items:
                    item.problem_id = target.id
                target.first_seen = min(target.first_seen, problem.first_seen)
                target.last_seen = max(target.last_seen, problem.last_seen)
                db.delete(problem)
                db.commit()
                return RedirectResponse(f"/problems/{target.id}", status_code=303)
        if status in STATUSES:
            problem.status = status
            for item in problem.items:
                if item.status in ("new", "in_work"):
                    item.status = status
        if title:
            problem.title = title.strip()[:300]
        if note is not None:
            problem.note = note
        db.commit()
    return RedirectResponse(f"/problems/{problem_id}", status_code=303)


# Reports -------------------------------------------------------------------------------------

def _report_params(request: Request) -> tuple[str, dict]:
    q = request.query_params
    kind = q.get("kind", "daily")
    params = {k: q.getlist(k) if k in ("topic", "sentiment", "platform", "role") else q.get(k) for k in q.keys()}
    params.pop("kind", None)
    return kind, params


@app.get("/reports", response_class=HTMLResponse)
def reports(request: Request, user=Depends(require_user)):
    with SessionLocal() as db:
        presets = db.scalars(select(ReportPreset).order_by(ReportPreset.id)).all()
        deliveries = db.scalars(select(Delivery).order_by(Delivery.id.desc()).limit(20)).all()
        problems = db.scalars(select(Problem).order_by(Problem.last_seen.desc()).limit(200)).all()
    return page(request, "reports.html", user, presets=presets, deliveries=deliveries, kinds=KINDS,
                problems=problems, max_ready=max_bot.configured(),
                today=to_local(utcnow()).date().isoformat())


@app.get("/reports/view", response_class=HTMLResponse)
def report_view(request: Request, user=Depends(require_user)):
    kind, params = _report_params(request)
    with SessionLocal() as db:
        report = build_report(db, kind, params)
        if not report:
            raise HTTPException(404, "Нет данных для отчёта")
        return page(request, "report_view.html", user, report=report, report_kind=kind, report_params=params,
                    query=request.url.query, max_ready=max_bot.configured())


@app.get("/reports/pdf")
async def report_pdf_download(request: Request, user=Depends(require_user)):
    kind, params = _report_params(request)
    with SessionLocal() as db:
        report = build_report(db, kind, params)
        if not report:
            raise HTTPException(404)
        pdf = await asyncio.to_thread(report_pdf, report)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{pdf_filename(report)}"'})


@app.get("/reports/print", response_class=HTMLResponse)
def report_print(request: Request, user=Depends(require_user)):
    kind, params = _report_params(request)
    with SessionLocal() as db:
        report = build_report(db, kind, params)
        if not report:
            raise HTTPException(404)
        return HTMLResponse(report_html(report))


@app.post("/reports/send")
async def report_send(request: Request, user=Depends(require_user)):
    kind, params = _report_params(request)
    with SessionLocal() as db:
        report = build_report(db, kind, params)
        if not report:
            raise HTTPException(404)
        delivery = await send_to_max(db, report)
    return {"ok": delivery.ok, "detail": delivery.detail}


@app.post("/reports/presets")
async def preset_save(request: Request, user=Depends(require_user)):
    form = await request.form()
    params = {k: form.getlist(k) if k in ("topic", "sentiment", "platform", "role") else form.get(k)
              for k in form.keys() if k not in ("name", "kind", "auto_send", "send_time", "preset_id")}
    with SessionLocal() as db:
        preset = db.get(ReportPreset, int(form["preset_id"])) if form.get("preset_id") else ReportPreset()
        preset.name = (form.get("name") or KINDS.get(form.get("kind"), "Отчёт")).strip()[:200]
        preset.kind = form.get("kind") if form.get("kind") in KINDS else "daily"
        preset.params = params
        preset.auto_send = form.get("auto_send") == "on"
        preset.send_time = form.get("send_time") or "08:05"
        db.add(preset)
        db.commit()
    return RedirectResponse("/reports", status_code=303)


@app.post("/reports/presets/{preset_id}/delete")
def preset_delete(preset_id: int, user=Depends(require_user)):
    with SessionLocal() as db:
        preset = db.get(ReportPreset, preset_id)
        if preset:
            db.delete(preset)
            db.commit()
    return RedirectResponse("/reports", status_code=303)


# Sources -------------------------------------------------------------------------------------

@app.get("/sources", response_class=HTMLResponse)
def sources_page(request: Request, user=Depends(require_user)):
    with SessionLocal() as db:
        sources = db.scalars(select(Source).order_by(Source.role != "governor", Source.platform, Source.id)).all()
        counts = dict(db.execute(select(Item.source_id, func.count()).where(
            Item.published_at >= utcnow() - timedelta(days=1)).group_by(Item.source_id)).all())
    return page(request, "sources.html", user, sources=sources, counts=counts,
                tg_ready=bool(config.TG_API_ID), vk_ready=bool(config.VK_TOKEN))


@app.post("/sources")
def source_add(url: str = Form(...), role: str = Form("local"), user=Depends(require_user)):
    with SessionLocal() as db:
        add_source(db, url, role if role in ("local", "official", "governor") else "local")
    return RedirectResponse("/sources", status_code=303)


@app.post("/sources/{source_id}")
def source_update(source_id: int, role: str = Form(None), enabled: str = Form(None), delete: str = Form(None),
                  user=Depends(require_user)):
    with SessionLocal() as db:
        source = db.get(Source, source_id)
        if not source:
            raise HTTPException(404)
        if delete:
            db.delete(source)
        else:
            if role in ("local", "official", "governor"):
                source.role = role
            if enabled is not None:
                source.enabled = enabled == "1"
        db.commit()
    return RedirectResponse("/sources", status_code=303)


@app.post("/sources/{source_id}/join")
async def source_join(source_id: int, user=Depends(require_user)):
    with SessionLocal() as db:
        source = db.get(Source, source_id)
        client = await worker._telegram(db)
        if not source or client is None:
            raise HTTPException(400, "Telegram не подключён")
        try:
            await telegram.resolve(client, source, join=True)
            source.status, source.last_error = "new", ""
        except Exception as e:
            source.status, source.last_error = "error", f"{type(e).__name__}: {e}"[:500]
        db.commit()
    return RedirectResponse("/sources", status_code=303)


@app.post("/collect")
async def collect_now(user=Depends(require_user)):
    asyncio.create_task(worker.run_cycle(force=True))
    return RedirectResponse("/sources?started=1", status_code=303)


# Settings ------------------------------------------------------------------------------------

@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, user=Depends(require_admin)):
    with SessionLocal() as db:
        users = db.scalars(select(User).order_by(User.id)).all()
        keywords = get_setting(db, "extra_keywords")
        tg_session = bool(get_setting(db, telegram.SESSION_KEY))
        unclassified = db.scalar(select(func.count()).select_from(Item).where(Item.classified.is_(False)))
    return page(request, "settings.html", user, users=users, keywords=keywords, tg_session=tg_session,
                config=config, max_ready=max_bot.configured(), unclassified=unclassified,
                msg=request.query_params.get("msg", ""))


@app.post("/settings/telegram/code")
async def tg_code(phone: str = Form(...), user=Depends(require_admin)):
    if not (config.TG_API_ID and config.TG_API_HASH):
        return JSONResponse({"error": "Заполните TG_API_ID и TG_API_HASH в .env"}, status_code=400)
    try:
        code_hash = await telegram.login_start(phone.strip())
    except Exception as e:
        return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=400)
    return {"phone_code_hash": code_hash}


@app.post("/settings/telegram/login")
async def tg_login(phone: str = Form(...), code: str = Form(...), phone_code_hash: str = Form(...),
                   password: str = Form(""), user=Depends(require_admin)):
    with SessionLocal() as db:
        try:
            result = await telegram.login_finish(db, phone.strip(), code.strip(), phone_code_hash, password)
        except Exception as e:
            return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=400)
    await worker.reset_telegram()
    return {"result": result}


@app.post("/settings/telegram/logout")
async def tg_logout(user=Depends(require_admin)):
    await worker.reset_telegram()
    with SessionLocal() as db:
        set_setting(db, telegram.SESSION_KEY, "")
    return RedirectResponse("/settings?msg=Telegram+отключён", status_code=303)


@app.post("/settings/keywords")
def keywords_save(keywords: str = Form(""), user=Depends(require_admin)):
    with SessionLocal() as db:
        set_setting(db, "extra_keywords", keywords)
    return RedirectResponse("/settings?msg=Сохранено", status_code=303)


@app.post("/settings/users")
def user_add(login: str = Form(...), password: str = Form(...), is_admin: str = Form(None),
             user=Depends(require_admin)):
    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.login == login.strip()))
        if existing:
            existing.password_hash = hash_password(password)
        else:
            db.add(User(login=login.strip(), password_hash=hash_password(password), is_admin=is_admin == "on"))
        db.commit()
    return RedirectResponse("/settings?msg=Пользователь+сохранён", status_code=303)


@app.post("/settings/users/{user_id}/delete")
def user_delete(user_id: int, user=Depends(require_admin)):
    with SessionLocal() as db:
        target = db.get(User, user_id)
        if target and target.id != user.id:
            db.delete(target)
            db.commit()
    return RedirectResponse("/settings", status_code=303)


@app.get("/healthz")
def healthz():
    return {"ok": True}


__all__ = ["app", "current_user"]
