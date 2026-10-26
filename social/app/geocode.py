"""Addresses to coordinates via OpenStreetMap Nominatim, limited to the Mytishchi district."""

import asyncio
import logging
import re
import time

import httpx

from . import config
from .db import GeoCache

log = logging.getLogger(__name__)
_last_call = 0.0
_lock = asyncio.Lock()


# "на улице Колонцова" -> "улица Колонцова", "на Олимпийском проспекте" -> "Олимпийский проспект".
_NOMINATIVE = [
    (r"(?i)\bулиц[еыу]\b", "улица"), (r"(?i)\bпроспект[еау]\b", "проспект"), (r"(?i)\bшоссе\b", "шоссе"),
    (r"(?i)\bбульвар[еау]\b", "бульвар"), (r"(?i)\bпереулк[еау]\b", "переулок"), (r"(?i)\bпроезд[еау]\b", "проезд"),
    (r"(?i)\bмикрорайон[еау]\b", "микрорайон"),
    (r"(?i)\b([а-яё]+)(ом|ем)\s+(проспект|бульвар|переулок|проезд)\b", r"\1ий \3"),
    (r"(?i)\b([а-яё]+)(ой|ей)\s+улица\b", r"\1ая улица"),
    (r"(?i)\b([а-яё]+)(ом|ем)\s+шоссе\b", r"\1ое шоссе"),
]


def clean_address(address: str) -> str:
    a = re.sub(r"\s+", " ", address or "").strip(" ,.")
    a = re.sub(r"(?i)\b(г\.?\s*о\.?|городской округ)\s*", "", a)
    a = re.sub(r"(?i)^(на|в|во|у|около|возле)\s+", "", a)
    for pattern, repl in _NOMINATIVE:
        a = re.sub(pattern, repl, a)
    return a


class GeocodeUnavailable(Exception):
    """The service failed; unlike "not found", this is not cached."""


async def _nominatim(query: str) -> tuple[float, float, str] | None:
    global _last_call
    south, west, north, east = config.AREA_BBOX
    params = {
        "q": query, "format": "jsonv2", "limit": 1, "countrycodes": "ru", "accept-language": "ru",
        "viewbox": f"{west},{north},{east},{south}", "bounded": 1, "addressdetails": 0,
    }
    if config.NOMINATIM_EMAIL:
        params["email"] = config.NOMINATIM_EMAIL
    headers = {"User-Agent": f"social-monitor/1.0 ({config.BASE_URL})"}
    async with _lock:  # the public server allows one request per second
        wait = 1.1 - (time.monotonic() - _last_call)
        if wait > 0:
            await asyncio.sleep(wait)
        try:
            async with httpx.AsyncClient(timeout=20) as http:
                resp = await http.get(config.NOMINATIM_URL, params=params, headers=headers)
            _last_call = time.monotonic()
            resp.raise_for_status()
            rows = resp.json()
        except (httpx.HTTPError, ValueError) as e:
            raise GeocodeUnavailable(str(e)) from e
    if not rows:
        return None
    row = rows[0]
    kind = row.get("addresstype") or row.get("type") or ""
    precision = "house" if kind in ("building", "house") or row.get("category") == "building" else (
        "street" if kind in ("road", "street", "residential") or row.get("category") == "highway" else "locality")
    return float(row["lat"]), float(row["lon"]), precision


async def geocode(db, address: str, locality: str = "") -> tuple[float, float, str] | None:
    """Try the full address, then without the house number, then the locality alone."""
    address = clean_address(address)
    locality = clean_address(locality) or "Мытищи"
    if not address and locality == "Мытищи":
        return None
    candidates = []  # (query, precision if found)
    if address:
        full = f"{address}, {locality}" if locality.lower() not in address.lower() else address
        candidates.append((full, None))
        street = re.sub(r",?\s*(д\.?|дом)?\s*\d+[а-яА-Я]?(\s*(к|корп|стр)\.?\s*\d+)?\s*$", "", address).strip(" ,")
        if street and street != address:
            candidates.append((f"{street}, {locality}", "street"))
    if locality != "Мытищи":
        # A village is a fair point on the map; the whole city is not.
        candidates.append((f"{locality}, городской округ Мытищи", "locality"))

    for query, level in candidates:
        key = query.lower()
        cached = db.get(GeoCache, key)
        if cached is None:
            try:
                found = await _nominatim(query + ", Московская область")
            except GeocodeUnavailable as e:
                log.warning("geocoding failed for %r: %s", query, e)
                return None
            cached = GeoCache(query=key, lat=found[0] if found else None, lon=found[1] if found else None,
                              precision=found[2] if found else "")
            db.merge(cached)
            db.commit()
        if cached.lat is not None:
            return cached.lat, cached.lon, level or cached.precision
    return None
