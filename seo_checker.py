"""
SEO rank checker for minesweeper.org.

Queries two sources for each supported language:
  - Google Search Console API  (28-day average position, clicks, impressions)
  - Bing Web Search API v7     (live position in top-50 results)

Required .env keys:
  GSC_SERVICE_ACCOUNT_JSON  — absolute path to a service-account .json file
                              that has Search Console read access to GSC_SITE_URL
  GSC_SITE_URL              — verified property URL (e.g. https://minesweeper.org/)
  BING_SEARCH_API_KEY       — Azure Cognitive Services / Bing Search v7 key
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import requests
from starlette.config import Config

log = logging.getLogger(__name__)
_cfg = Config(".env")

GSC_SERVICE_ACCOUNT_JSON: str = _cfg("GSC_SERVICE_ACCOUNT_JSON", default="")
GSC_SITE_URL: str = _cfg("GSC_SITE_URL", default="https://minesweeper.org/")
BING_SEARCH_API_KEY: str = _cfg("BING_SEARCH_API_KEY", default="")
_BING_ENDPOINT = "https://api.bing.microsoft.com/v7.0/search"
_TARGET_HOST = "minesweeper.org"

# ---------------------------------------------------------------------------
# Per-language search configuration.
# gsc_country: ISO 3166-1 alpha-3, lowercase (GSC API format).
# bing_mkt:    BCP-47 market tag accepted by Bing Web Search.
# ---------------------------------------------------------------------------
LANG_SEO: dict[str, dict] = {
    "en":      {"term": "minesweeper",           "country": "US", "gsc_country": "usa", "bing_mkt": "en-US"},
    "de":      {"term": "Minesweeper",           "country": "DE", "gsc_country": "deu", "bing_mkt": "de-DE"},
    "es":      {"term": "Buscaminas",            "country": "ES", "gsc_country": "esp", "bing_mkt": "es-ES"},
    "fr":      {"term": "Démineur",              "country": "FR", "gsc_country": "fra", "bing_mkt": "fr-FR"},
    "it":      {"term": "Prato fiorito",         "country": "IT", "gsc_country": "ita", "bing_mkt": "it-IT"},
    "pt":      {"term": "Campo Minado",          "country": "BR", "gsc_country": "bra", "bing_mkt": "pt-BR"},
    "nl":      {"term": "Mijnenveger",           "country": "NL", "gsc_country": "nld", "bing_mkt": "nl-NL"},
    "sv":      {"term": "Minfält",               "country": "SE", "gsc_country": "swe", "bing_mkt": "sv-SE"},
    "da":      {"term": "Minesweeper spil",      "country": "DK", "gsc_country": "dnk", "bing_mkt": "da-DK"},
    "pl":      {"term": "Saper gra",             "country": "PL", "gsc_country": "pol", "bing_mkt": "pl-PL"},
    "ru":      {"term": "Сапёр игра",            "country": "RU", "gsc_country": "rus", "bing_mkt": "ru-RU"},
    "uk":      {"term": "Сапер гра",             "country": "UA", "gsc_country": "ukr", "bing_mkt": "uk-UA"},
    "fi":      {"term": "Miinaharava",           "country": "FI", "gsc_country": "fin", "bing_mkt": "fi-FI"},
    "el":      {"term": "Minesweeper",           "country": "GR", "gsc_country": "grc", "bing_mkt": "el-GR"},
    "ko":      {"term": "지뢰찾기",               "country": "KR", "gsc_country": "kor", "bing_mkt": "ko-KR"},
    "ja":      {"term": "マインスウィーパー",      "country": "JP", "gsc_country": "jpn", "bing_mkt": "ja-JP"},
    "zh":      {"term": "扫雷游戏",               "country": "CN", "gsc_country": "chn", "bing_mkt": "zh-CN"},
    "zh-hant": {"term": "掃雷遊戲",               "country": "TW", "gsc_country": "twn", "bing_mkt": "zh-TW"},
    "hi":      {"term": "माइनस्वीपर",           "country": "IN", "gsc_country": "ind", "bing_mkt": "hi-IN"},
    "bn":      {"term": "মাইনসুইপার",           "country": "BD", "gsc_country": "bgd", "bing_mkt": "en-BD"},
    "th":      {"term": "มายน์สวีปเปอร์",        "country": "TH", "gsc_country": "tha", "bing_mkt": "th-TH"},
    "tl":      {"term": "minesweeper",           "country": "PH", "gsc_country": "phl", "bing_mkt": "en-PH"},
    "id":      {"term": "Minesweeper",           "country": "ID", "gsc_country": "idn", "bing_mkt": "id-ID"},
    "ms":      {"term": "Minesweeper",           "country": "MY", "gsc_country": "mys", "bing_mkt": "ms-MY"},
    "he":      {"term": "שדה מוקשים",           "country": "IL", "gsc_country": "isr", "bing_mkt": "he-IL"},
    # Fun / novelty languages — use the English term in a US context
    "eo":      {"term": "minesweeper",           "country": "US", "gsc_country": "usa", "bing_mkt": "en-US"},
    "pgl":     {"term": "minesweeper",           "country": "US", "gsc_country": "usa", "bing_mkt": "en-US"},
    "tlh":     {"term": "minesweeper",           "country": "US", "gsc_country": "usa", "bing_mkt": "en-US"},
}


def _build_gsc_service():
    if not GSC_SERVICE_ACCOUNT_JSON:
        raise RuntimeError("GSC_SERVICE_ACCOUNT_JSON not configured in .env")
    from google.oauth2 import service_account
    from googleapiclient.discovery import build as _gapi_build

    creds = service_account.Credentials.from_service_account_file(
        GSC_SERVICE_ACCOUNT_JSON,
        scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
    )
    return _gapi_build("searchconsole", "v1", credentials=creds, cache_discovery=False)


def fetch_gsc_position(service, lang: str) -> dict:
    """
    Returns {"position": float|None, "clicks": int, "impressions": int}.
    Queries the last 28 days (GSC has ~3-day data delay).
    """
    cfg = LANG_SEO.get(lang)
    if not cfg:
        return {"position": None, "clicks": 0, "impressions": 0}

    end_date = date.today() - timedelta(days=3)
    start_date = end_date - timedelta(days=27)

    body = {
        "startDate": start_date.strftime("%Y-%m-%d"),
        "endDate":   end_date.strftime("%Y-%m-%d"),
        "dimensions": ["query", "country"],
        "dimensionFilterGroups": [{
            "filters": [
                {"dimension": "query",   "operator": "equals", "expression": cfg["term"]},
                {"dimension": "country", "operator": "equals", "expression": cfg["gsc_country"]},
            ]
        }],
        "rowLimit": 1,
    }
    try:
        resp = service.searchanalytics().query(siteUrl=GSC_SITE_URL, body=body).execute()
        rows = resp.get("rows", [])
        if rows:
            r = rows[0]
            return {
                "position":    round(float(r.get("position", 0)), 1),
                "clicks":      int(r.get("clicks", 0)),
                "impressions": int(r.get("impressions", 0)),
            }
    except Exception as exc:
        log.warning("GSC query failed lang=%s: %s", lang, exc)
    return {"position": None, "clicks": 0, "impressions": 0}


def fetch_bing_position(lang: str) -> Optional[int]:
    """
    Returns the 1-based position of minesweeper.org in Bing results (max 50),
    or None if the key is missing or the site isn't found.
    """
    if not BING_SEARCH_API_KEY:
        return None
    cfg = LANG_SEO.get(lang)
    if not cfg:
        return None

    headers = {"Ocp-Apim-Subscription-Key": BING_SEARCH_API_KEY}
    params = {
        "q":            cfg["term"],
        "mkt":          cfg["bing_mkt"],
        "count":        50,
        "offset":       0,
        "responseFilter": "Webpages",
        "safeSearch":   "Off",
    }
    try:
        resp = requests.get(_BING_ENDPOINT, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        items = resp.json().get("webPages", {}).get("value", [])
        for i, item in enumerate(items, start=1):
            if _TARGET_HOST in item.get("url", ""):
                return i
    except Exception as exc:
        log.warning("Bing query failed lang=%s: %s", lang, exc)
    return None


def update_all_rankings(db) -> int:
    """
    Full ranking refresh — inserts a new SeoRanking row per language.
    Returns the count of languages processed.
    Safe to call from APScheduler or an admin route.
    """
    from database import SeoRanking

    gsc_service = None
    if GSC_SERVICE_ACCOUNT_JSON:
        try:
            gsc_service = _build_gsc_service()
        except Exception as exc:
            log.error("Could not initialise GSC service: %s", exc)

    count = 0
    for lang, cfg in LANG_SEO.items():
        gsc = {"position": None, "clicks": 0, "impressions": 0}
        if gsc_service:
            gsc = fetch_gsc_position(gsc_service, lang)
            time.sleep(0.25)

        bing_pos = fetch_bing_position(lang)
        if BING_SEARCH_API_KEY:
            time.sleep(0.5)

        row = SeoRanking(
            lang=lang,
            search_term=cfg["term"],
            country=cfg["country"],
            google_position=gsc["position"],
            google_clicks=gsc["clicks"],
            google_impressions=gsc["impressions"],
            bing_position=bing_pos,
            checked_at=datetime.now(timezone.utc),
        )
        db.add(row)
        db.commit()
        count += 1
        log.info(
            "SEO [%s] Google=%s Bing=%s",
            lang,
            f"{gsc['position']:.1f}" if gsc["position"] else "—",
            bing_pos or "—",
        )

    return count
