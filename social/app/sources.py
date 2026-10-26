"""The initial list of communities. More can be added on the «Источники» page."""

import re

from sqlalchemy import select

from .db import Source

GOVERNOR = ["https://t.me/vorobiev_live", "https://vk.com/andreyvorobiev"]

# Pages of the administration and its services: negative comments there need a reply.
OFFICIAL = [
    "https://vk.com/mytishchi_adm",
    "https://vk.com/juliakupetskaya",
    "https://t.me/mytishiadmin",
    "https://t.me/juliakupetskaya",
    "https://t.me/pressmytyshi",
    "https://t.me/mytischi_official",
    "https://t.me/obr_mytyshi",
    "https://t.me/mokb_med",
    "https://t.me/ckpodmoskovie",
]

LOCAL = [
    "https://vk.com/tipmytischi",
    "https://vk.com/podslushano.mytischi",
    "https://vk.com/podslushano_mytishchi",
    "https://vk.com/mspeaks",
    "https://t.me/zamkadye_new",
    "https://t.me/Mytishchi_tut",
    "https://t.me/nashepirogovo",
    "https://t.me/Tipichnye_Mytishchi",
    "https://t.me/podslushano_mytischi",
    "https://t.me/mytischi_live",
    "https://t.me/joinchat/ycbEqPdIqZQyMDg6",
    "https://t.me/mitischi_universe",
    "https://t.me/Mytishchy1",
    "https://t.me/pirogovo_riviera",
    "https://t.me/kupetckayachat",
    "https://t.me/park_mitihi",
    "https://t.me/mytischi_chat",
    "https://t.me/c/1531678910/188739",
    "https://t.me/c/1853464166/225223",
    "https://t.me/c/1708299473/147299",
    "https://t.me/pirogovomo",
    "https://t.me/mspeaks",
    "https://t.me/activ0054",
    "https://t.me/joinchat/lkcJw7kZOQ02ZTZi",
    "https://t.me/park_mytishchi",
    "https://t.me/artsuvorov_live",
]


def normalize_url(url: str) -> str:
    url = url.strip().rstrip("/")
    url = re.sub(r"^(https?://)?(www\.|m\.)?", "https://", url)
    url = url.replace("https://vk.ru/", "https://vk.com/").replace("https://telegram.me/", "https://t.me/")
    return url


def platform_of(url: str) -> str:
    return "vk" if "://vk.com/" in url else "tg"


def add_source(db, url: str, role: str = "local") -> Source:
    url = normalize_url(url)
    existing = db.scalar(select(Source).where(Source.url == url))
    if existing:
        return existing
    src = Source(url=url, platform=platform_of(url), role=role, title=url.split("/", 3)[-1])
    db.add(src)
    db.commit()
    return src


def seed_sources(db) -> None:
    if db.scalar(select(Source.id).limit(1)):
        return
    for role, urls in (("governor", GOVERNOR), ("official", OFFICIAL), ("local", LOCAL)):
        for url in urls:
            add_source(db, url, role)
