# news_sources.py
import os, time, math, re
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from dateutil.relativedelta import relativedelta
from dateutil import parser as duparser
from dotenv import load_dotenv

load_dotenv(override=True)

REQUEST_TIMEOUT = int(float(os.getenv("REQUEST_TIMEOUT", "20")))
NEWSAPI_KEY       = os.getenv("NEWSAPI_KEY", "")
SERPAPI_API_KEY   = os.getenv("SERPAPI_API_KEY", "")

NEWSAPI_BASE      = os.getenv("NEWSAPI_BASE", "https://newsapi.org/v2/everything")
SERPAPI_BASE      = os.getenv("SERPAPI_BASE", "https://serpapi.com/search.json")

NEWSAPI_SOURCES   = os.getenv("NEWSAPI_SOURCES", "") or None
NEWSAPI_DOMAINS   = os.getenv("NEWSAPI_DOMAINS", "") or None
NEWSAPI_SEARCH_IN = os.getenv("NEWSAPI_SEARCH_IN", "title,description")
NEWSAPI_MAX_RESULTS = int(os.getenv("NEWSAPI_MAX_RESULTS", "100"))

SERPAPI_NUM       = int(os.getenv("SERPAPI_NUM", "100"))
SERPAPI_PAGES     = int(os.getenv("SERPAPI_PAGES", "2"))
SERPAPI_PHRASE    = os.getenv("SERPAPI_PHRASE", "0").lower() in ("1","true","yes")

def have_newsapi() -> bool:
    return bool(NEWSAPI_KEY)

def have_serpapi() -> bool:
    return bool(SERPAPI_API_KEY)

def _parse_date(s: str):
    """Parse a wide range of SerpApi/NewsAPI date strings into tz-aware UTC datetimes."""
    if not s:
        return None
    s = str(s).strip()

    # 0) Try dateparser (if available) – do NOT import at the top-level
    try:
        import dateparser as _dp
        dt = _dp.parse(
            s,
            settings={
                "RETURN_AS_TIMEZONE_AWARE": True,
                "PREFER_DATES_FROM": "past",
                "RELATIVE_BASE": datetime.now(timezone.utc),
                "TIMEZONE": "UTC",
                "TO_TIMEZONE": "UTC",
                "DATE_ORDER": "MDY",
            },
            languages=["en"],
        )
        if dt:
            return dt.astimezone(timezone.utc)
    except Exception:
        pass  # fall through to the other strategies

    # B) Normalize common SerpApi pattern: "10/21/2025, 08:55 PM, +0000 UTC"
    s2 = re.sub(r"\s*,\s*", " ", s)         # -> "10/21/2025 08:55 PM +0000 UTC"
    s2 = s2.replace("UTC", "").strip()      # -> "10/21/2025 08:55 PM +0000"
    # Try strict strptime on that pattern
    try:
        dt = datetime.strptime(s2, "%m/%d/%Y %I:%M %p %z")  # %z accepts +0000
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    # C) Make the offset ISO-like: +0000 -> +00:00, then try dateutil
    s3 = re.sub(r"([+-]\d{2})(\d{2})(\s*)$", r"\1:\2", s2)  # -> +00:00
    try:
        dt = duparser.parse(s3, tzinfos={"UTC": timezone.utc})
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    # D) Relative-time fallback: "3 hours ago"
    m = re.match(r"(?i)^\s*(\d+)\s*(second|minute|hour|day|week|month|year)s?\s+ago\s*$", s)
    if m:
        n = int(m.group(1)); unit = m.group(2).lower()
        base = datetime.now(timezone.utc)
        return {
            "second": base - timedelta(seconds=n),
            "minute": base - timedelta(minutes=n),
            "hour":   base - timedelta(hours=n),
            "day":    base - timedelta(days=n),
            "week":   base - timedelta(weeks=n),
            "month":  base - relativedelta(months=n),
            "year":   base - relativedelta(years=n),
        }[unit]

    if s.lower() == "yesterday":
        return datetime.now(timezone.utc) - timedelta(days=1)

    return None

class ApiError(Exception): ...

@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type(ApiError),
    reraise=True
)
def _http_get(url: str, params: Dict[str, Any] = None, headers: Dict[str, str] = None) -> Dict[str, Any]:
    r = requests.get(url, params=params or {}, headers=headers or {}, timeout=REQUEST_TIMEOUT)
    if r.status_code >= 500 or r.status_code in (429, 408):
        raise ApiError(f"{r.status_code} {r.text[:200]}")
    if r.status_code != 200:
        try:
            j = r.json()
            if isinstance(j, dict) and j.get("message"):
                raise Exception(f"HTTP {r.status_code}: {j.get('message')}")
        except Exception:
            pass
        raise Exception(f"HTTP {r.status_code}: {r.text[:200]}")
    try:
        return r.json()
    except Exception:
        raise Exception("Invalid JSON from API")

def _norm_row(title, url, summary, published_at, source):
    return {
        "title": (title or "").strip(),
        "url": url or "",
        "summary": (summary or "").strip(),
        "published_at": published_at,  # tz-aware UTC datetime
        "source": source,
    }

def fetch_newsapi(query: str, lang: str = "en", days: int = 7,
                  page_size: int = 50, max_pages: int = 2) -> List[Dict[str, Any]]:
    if not NEWSAPI_KEY:
        return []
    headers = {"X-Api-Key": NEWSAPI_KEY}
    out: List[Dict[str, Any]] = []

    now = datetime.now(timezone.utc)
    since = now - timedelta(days=int(days or 7))

    # Cap pages to plan limit
    allowed_pages = max(1, min(max_pages, math.ceil(NEWSAPI_MAX_RESULTS / max(1, page_size))))

    for page in range(1, allowed_pages + 1):
        params = {
            "q": query,
            "language": lang,
            "from": since.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "to": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sortBy": "publishedAt",
            "pageSize": page_size,
            "page": page,
            "searchIn": NEWSAPI_SEARCH_IN,
        }
        if NEWSAPI_SOURCES: params["sources"] = NEWSAPI_SOURCES
        if NEWSAPI_DOMAINS: params["domains"] = NEWSAPI_DOMAINS

        data = _http_get(NEWSAPI_BASE, params=params, headers=headers)
        if isinstance(data, dict) and data.get("status") == "error":
            code = data.get("code", "error")
            msg = data.get("message", "")
            if code == "maximumResultsReached":
                print("[NewsAPI] maximumResultsReached: partial results")
                break
            raise Exception(f"NewsAPI error {code}: {msg}")

        articles = data.get("articles") or []
        for a in articles:
            pub = _parse_date(a.get("publishedAt") or "")
            if not pub:      # keep timestamps honest
                continue
            out.append(_norm_row(a.get("title"), a.get("url"),
                                 a.get("description") or a.get("content") or "",
                                 pub, "newsapi"))
        if len(articles) < page_size:
            break
        time.sleep(0.3)

    out.sort(key=lambda x: x["published_at"], reverse=True)
    return out

def fetch_serpapi_google_news(query: str, lang: str = "en", pages: int = 2) -> List[Dict[str, Any]]:
    if not SERPAPI_API_KEY:
        return []
    q = f'"{query}"' if SERPAPI_PHRASE else query
    out: List[Dict[str, Any]] = []
    total_dropped = 0
    dropped_examples = []

    for page in range(1, pages + 1):
        params = {
            "engine": "google_news",
            "q": q,
            "hl": lang,
            "gl": "us",
            "api_key": SERPAPI_API_KEY,
            "num": SERPAPI_NUM,
            "page": page,
        }
        data = _http_get(SERPAPI_BASE, params=params)

        if isinstance(data, dict) and data.get("error"):
            print(f"[DEBUG] SerpApi ERROR page={page}: {data.get('error')}")
            break

        news = data.get("news_results") or []
        if not news:
            print(f"[DEBUG] SerpApi page={page} returned 0 results; meta={data.get('search_metadata', {})}")
            break

        for n in news:
            title = (n.get("title") or "").strip()
            url = n.get("link") or n.get("url") or ""
            summary = (n.get("snippet") or "").strip()

            # Prefer precise UTC if present
            raw_date = n.get("date_utc") or n.get("date") or n.get("published") or ""
            pub = _parse_date(raw_date)

            if not pub:
                total_dropped += 1
                if len(dropped_examples) < 5:
                    dropped_examples.append(raw_date)
                continue

            out.append({
                "source": "serpapi",
                "title": title,
                "summary": summary,
                "url": url,
                "published_at": pub,
                "language": lang,
                "raw": n,
            })
        time.sleep(0.5)

    if total_dropped:
        print(f"[DEBUG] SerpApi dropped {total_dropped} items due to unparseable date; examples={dropped_examples}")

    # Dedup by URL + sort
    seen, uniq = set(), []
    for it in out:
        u = it["url"]
        if u and u not in seen:
            uniq.append(it); seen.add(u)
    uniq.sort(key=lambda x: x["published_at"], reverse=True)
    return uniq


def fetch_both(query: str, lang: str = "en", days: int = 7,
               nc_page_size: int = 100, nc_pages: int = 2, serp_pages: int = 2) -> List[Dict[str, Any]]:
    a = fetch_newsapi(query, lang=lang, days=days, page_size=nc_page_size, max_pages=nc_pages) if have_newsapi() else []
    print(f"[DEBUG] NewsAPI returned {len(a)}")
    b = fetch_serpapi_google_news(query, lang=lang, pages=serp_pages) if have_serpapi() else []
    print(f"[DEBUG] SerpApi returned {len(b)}")

    seen, out = set(), []
    for it in a + b:
        key = it.get("url") or it.get("title")
        if key and key not in seen:
            out.append(it); seen.add(key)

    out.sort(key=lambda x: x["published_at"], reverse=True)
    return out
