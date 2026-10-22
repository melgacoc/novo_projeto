"""Geocodificação gratuita: Photon (komoot) com fallback no Nominatim. Cache de 1 dia no Redis.
Viés para o Rio de Janeiro. Respeita o limite do Nominatim (1 req/s) com uma trava no Redis."""
import json
import logging
import time

import httpx

from app.core.config import settings
from app.core.redis import redis_client

log = logging.getLogger("app.geocoding")
RIO = (-22.9068, -43.1729)


def _photon(q: str, lang: str) -> list[dict]:
    lang = lang if lang in ("en", "de", "fr", "it") else "default"  # photon não tem pt/es; "default" usa nomes locais
    r = httpx.get(
        "https://photon.komoot.io/api/",
        params={"q": q, "limit": 5, "lat": RIO[0], "lon": RIO[1], "lang": lang},
        headers={"User-Agent": settings.geocoding_user_agent},
        timeout=6,
    )
    r.raise_for_status()
    out = []
    for f in r.json().get("features", []):
        lon, lat = f["geometry"]["coordinates"]
        p = f.get("properties", {})
        parts = [p.get("name"), p.get("street"), p.get("district") or p.get("locality"), p.get("city"), p.get("state")]
        out.append({"label": ", ".join(dict.fromkeys(x for x in parts if x)), "lat": lat, "lng": lon})
    return out


def _nominatim(q: str, lang: str) -> list[dict]:
    # 1 requisição por segundo para toda a aplicação
    while not redis_client.set("geocode:nominatim:lock", "1", nx=True, px=1100):
        time.sleep(0.2)
    r = httpx.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": q, "format": "jsonv2", "limit": 5, "countrycodes": "br", "accept-language": lang},
        headers={"User-Agent": settings.geocoding_user_agent},
        timeout=8,
    )
    r.raise_for_status()
    return [{"label": i["display_name"], "lat": float(i["lat"]), "lng": float(i["lon"])} for i in r.json()]


def geocode(q: str, lang: str = "pt") -> list[dict]:
    q = q.strip()[:200]
    if len(q) < 3:
        return []
    cache_key = f"geocode:{lang}:{q.lower()}"
    try:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:  # noqa: BLE001
        log.warning("cache de geocodificação indisponível", exc_info=True)
    providers = [_photon, _nominatim] if settings.geocoding_provider == "photon" else [_nominatim, _photon]
    results: list[dict] = []
    for provider in providers:
        try:
            results = provider(q, lang)
            break
        except Exception:  # noqa: BLE001
            log.warning("geocodificação falhou em %s", provider.__name__, exc_info=True)
    try:
        redis_client.setex(cache_key, 86400, json.dumps(results))
    except Exception:  # noqa: BLE001
        pass
    return results
