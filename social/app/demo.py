"""Demo data for a local check: python -m app.demo. Never run it on the production server."""

import asyncio
import random
from datetime import timedelta

from .classify import classify_pending
from .db import Item, SessionLocal, Source, init_db, utcnow
from .sources import add_source

POSTS = [
    ("Жители дома на улице Колонцова, 5 третий день без горячей воды. В УК не отвечают.", [
        "У нас тоже нет воды, сколько можно!", "Звонили в аварийку, сказали ждите", "Позор управляющей компании",
        "Дети не могут помыться, кошмар"]),
    ("Огромная яма на Олимпийском проспекте у дома 29, машины бьют колёса", [
        "Каждый день объезжаю, когда уже залатают", "Писала в Добродел, отписка", "Вчера пробил колесо там же"]),
    ("В поликлинике на улице Каргина невозможно записаться к терапевту, талонов нет на две недели", [
        "Та же история, записи нет", "Регистратура не берёт трубку", "Спасибо врачам, но запись ужасная"]),
    ("В Пирогово второй день не вывозят мусор, контейнеры переполнены", [
        "Воняет на всю улицу", "Уже собаки растаскивают", "Администрация, вы где?"]),
    ("Во дворе на улице Веры Волошиной, 19 сломана детская площадка", [
        "Качели висят на одной цепи, опасно", "Писали в УК месяц назад"]),
    ("Школа №1 Мытищи: в классах холодно, батареи еле тёплые", [
        "Дети сидят в куртках", "Холодно и в садике рядом"]),
    ("Автобус 314 в Жостово не приходит по полчаса, люди мёрзнут на остановке", [
        "Опять стояли 40 минут", "Нужно больше рейсов"]),
    ("На улице Мира, 10 не горят фонари во дворе, темно и страшно ходить", [
        "Уже неделю темно", "Спасибо, сегодня починили!"]),
    ("В Федоскино разбита дорога к школе, после дождя не пройти", ["Грязь по колено", "Когда уже асфальт?"]),
    ("Благодарим администрацию за новый сквер на Новомытищинском проспекте", ["Красиво получилось", "Спасибо!"]),
]
GOVERNOR = [
    "Андрей Юрьевич, в Мытищах на улице Колонцова нет горячей воды уже неделю, помогите!",
    "В Пирогово мусор не вывозят, администрация Мытищ бездействует",
    "Спасибо за новые автобусы в Мытищах",
    "Когда отремонтируют поликлинику в Мытищах на Каргина? Записи нет",
    "В Химках тоже проблемы с водой",  # not about the district: filtered out
]


async def main() -> None:
    init_db()
    with SessionLocal() as db:
        local = add_source(db, "https://t.me/demo_mytishchi", "local")
        local.title, local.kind = "Демо: Подслушано Мытищи", "channel"
        gov = add_source(db, "https://t.me/demo_governor", "governor")
        gov.title, gov.kind, gov.enabled, local.enabled = "Демо: канал губернатора", "channel", False, False
        db.commit()
        now = utcnow()
        rnd = random.Random(1)
        for n, (text, comments) in enumerate(POSTS):
            when = now - timedelta(hours=rnd.uniform(1, 30))
            post = Item(source_id=local.id, kind="post", external_id=f"demo{n}", text=text, published_at=when,
                        url=f"https://t.me/demo_mytishchi/{n}", author=local.title, views=rnd.randint(800, 9000),
                        replies=len(comments))
            db.add(post)
            db.flush()
            for k, c in enumerate(comments):
                db.add(Item(source_id=local.id, kind="comment", external_id=f"demo{n}_c{k}", text=c,
                            parent_id=post.id, published_at=when + timedelta(minutes=10 * (k + 1)),
                            url=f"https://t.me/demo_mytishchi/{n}?comment={k}", author=f"Житель {k + 1}",
                            likes=rnd.randint(0, 25)))
        gpost = Item(source_id=gov.id, kind="post", external_id="g1", text="Сегодня провели совещание по ЖКХ.",
                     published_at=now - timedelta(hours=5), url="https://t.me/demo_governor/1", author=gov.title)
        db.add(gpost)
        db.flush()
        for k, c in enumerate(GOVERNOR):
            db.add(Item(source_id=gov.id, kind="comment", external_id=f"g1_c{k}", text=c, parent_id=gpost.id,
                        published_at=now - timedelta(hours=4, minutes=k * 7), url=f"https://t.me/demo_governor/1?comment={k}",
                        author=f"Комментатор {k + 1}", likes=rnd.randint(0, 40)))
        db.commit()
        print("classified", await classify_pending(db))


if __name__ == "__main__":
    asyncio.run(main())
