"""
wiki_api.py
Wikipedia MediaWiki API client — pure Python replacement for wikilite Group-1 R calls.

Rate-limit & reliability behavior:
  - Sends `maxlag=5` on every call (MediaWiki convention; server defers instead of
    hard-failing when replication is lagging).
  - Retries 429 / 5xx / maxlag / transport errors with exponential backoff,
    honoring `Retry-After` when present.
  - Uses a shared httpx.Client for connection pooling.
  - Token-bucket throttle to stay within ~10 req/s polite limit per IP.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

import httpx

from progress import Progress

logger = logging.getLogger(__name__)

DEFAULT_LANG = "en"


def _endpoint(lang: str = DEFAULT_LANG) -> str:
    """Return the MediaWiki API endpoint for a given Wikipedia language code.

    Validates the language code shape (2–12 lowercase letters, optionally
    hyphenated, e.g. 'en', 'fr', 'pt-br', 'zh-min-nan') so we don't construct
    arbitrary URLs from caller input.
    """
    import re as _re
    if not isinstance(lang, str) or not _re.fullmatch(r"[a-z]{2,12}(-[a-z]{2,12})*", lang):
        raise ValueError(
            f"invalid Wikipedia language code: {lang!r}; "
            "expected codes like 'en', 'fr', 'de', 'pt-br', 'zh-min-nan'"
        )
    return f"https://{lang}.wikipedia.org/w/api.php"


# Back-compat: legacy callers that referenced _ENDPOINT directly still resolve
# to the English endpoint.
_ENDPOINT = _endpoint(DEFAULT_LANG)
_HEADERS = {
    "User-Agent": "wikicitation-mcp/0.5 (https://github.com/jsobel1/wikicitation-mcp; jsobel83@gmail.com)"
}
_RVPROP_META = "ids|user|userid|timestamp|size|comment|tags"
_RVPROP_FULL = _RVPROP_META + "|content"

# Polite limits — Wikipedia asks unauthenticated clients to stay well under
# 200 req/s aggregated. 10 req/s per process is a safe ceiling.
_MIN_INTERVAL_S = 0.10
_MAX_RETRIES = 5
_BACKOFF_BASE = 1.0
_BACKOFF_CAP = 30.0
_MAXLAG = 5

_client = httpx.Client(
    headers=_HEADERS,
    timeout=httpx.Timeout(30.0, connect=10.0),
    limits=httpx.Limits(max_connections=4, max_keepalive_connections=4),
    follow_redirects=False,
)

_throttle_lock = threading.Lock()
_last_call_ts = 0.0


def _throttle() -> None:
    global _last_call_ts
    with _throttle_lock:
        now = time.monotonic()
        wait = _MIN_INTERVAL_S - (now - _last_call_ts)
        if wait > 0:
            time.sleep(wait)
        _last_call_ts = time.monotonic()


def _backoff(attempt: int, retry_after: Optional[str] = None) -> float:
    if retry_after:
        try:
            return min(float(retry_after), _BACKOFF_CAP)
        except ValueError:
            pass
    return min(_BACKOFF_BASE * (2 ** attempt), _BACKOFF_CAP)


# ---------------------------------------------------------------------------
# Core HTTP helper
# ---------------------------------------------------------------------------

def _get(params: dict[str, Any], lang: str = DEFAULT_LANG) -> dict:
    base: dict[str, Any] = {
        "format": "json",
        "formatversion": "2",
        "maxlag": _MAXLAG,
    }
    base.update(params)
    url = _endpoint(lang)

    last_exc: Optional[Exception] = None
    for attempt in range(_MAX_RETRIES):
        _throttle()
        try:
            r = _client.get(url, params=base)
        except (httpx.TransportError, httpx.TimeoutException) as exc:
            last_exc = exc
            sleep_s = _backoff(attempt)
            logger.warning("wiki_api transport error (attempt %d): %s — sleeping %.1fs",
                           attempt + 1, exc, sleep_s)
            time.sleep(sleep_s)
            continue

        # 429 / 503 are retryable; honor Retry-After.
        if r.status_code in (429, 503):
            sleep_s = _backoff(attempt, r.headers.get("Retry-After"))
            logger.warning("wiki_api HTTP %d (attempt %d) — sleeping %.1fs",
                           r.status_code, attempt + 1, sleep_s)
            time.sleep(sleep_s)
            continue
        if 500 <= r.status_code < 600:
            sleep_s = _backoff(attempt)
            logger.warning("wiki_api HTTP %d (attempt %d) — sleeping %.1fs",
                           r.status_code, attempt + 1, sleep_s)
            time.sleep(sleep_s)
            continue

        r.raise_for_status()
        try:
            data = r.json()
        except ValueError as exc:
            last_exc = exc
            time.sleep(_backoff(attempt))
            continue

        # MediaWiki maxlag soft-throttle: error.code == "maxlag" + Retry-After hint.
        if "error" in data:
            code = data["error"].get("code", "")
            if code in ("maxlag", "ratelimited", "readonly"):
                sleep_s = _backoff(attempt, r.headers.get("Retry-After"))
                logger.warning("wiki_api %s (attempt %d) — sleeping %.1fs",
                               code, attempt + 1, sleep_s)
                time.sleep(sleep_s)
                continue
            raise RuntimeError(
                f"Wikipedia API error: {data['error'].get('info', str(data['error']))}"
            )
        return data

    raise RuntimeError(
        f"Wikipedia API: exhausted {_MAX_RETRIES} retries"
        + (f" (last error: {last_exc})" if last_exc else "")
    )


# ---------------------------------------------------------------------------
# Revision helpers
# ---------------------------------------------------------------------------

def _extract_content(rev: dict) -> str:
    """Extract wikitext from a revision dict (handles both API response formats)."""
    if "content" in rev:
        return rev["content"]
    slots = rev.get("slots", {})
    if isinstance(slots, dict):
        return slots.get("main", {}).get("content", "")
    return ""


def _fetch_revisions(
    article_name: str,
    *,
    rvprop: str = _RVPROP_META,
    rvdir: str = "older",
    rvstart: Optional[str] = None,
    rvend: Optional[str] = None,
    rvlimit: int | str = "max",
    max_revisions: int = 100_000,
    lang: str = DEFAULT_LANG,
) -> tuple[dict, list[dict]]:
    """
    Fetch revisions for one article with full pagination.
    Returns (page_meta_dict, list_of_revision_dicts).
    """
    params: dict[str, Any] = {
        "action": "query",
        "prop": "revisions",
        "titles": article_name,
        "rvprop": rvprop,
        "rvdir": rvdir,
        "rvlimit": rvlimit,
    }
    if "content" in rvprop:
        params["rvslots"] = "main"
    if rvstart:
        params["rvstart"] = rvstart
    if rvend:
        params["rvend"] = rvend

    page_meta: dict = {}
    revisions: list[dict] = []

    # Pagination size is unknown up front (depends on continue tokens), so we
    # report in open-ended mode: "fetched N revisions so far".
    with Progress(f"fetch revisions: {article_name}", total=None,
                  tick_every=500) as p:
        while len(revisions) < max_revisions:
            data = _get(params, lang=lang)
            pages = data.get("query", {}).get("pages", [])
            if not pages:
                break
            page = pages[0]
            if not page_meta:
                page_meta = {k: v for k, v in page.items() if k != "revisions"}
            new_rows = page.get("revisions", [])
            revisions.extend(new_rows)
            p.update(len(new_rows))
            if "continue" not in data:
                break
            params.update(data["continue"])

    return page_meta, revisions


def _rev_to_row(rev: dict, article_name: str) -> dict:
    return {
        "art": article_name,
        "revid": rev.get("revid"),
        "parentid": rev.get("parentid"),
        "user": rev.get("user", ""),
        "userid": rev.get("userid", 0),
        "timestamp": rev.get("timestamp", ""),
        "size": rev.get("size", 0),
        "comment": rev.get("comment", ""),
        "tags": rev.get("tags", []),
    }


# ---------------------------------------------------------------------------
# Category helpers
# ---------------------------------------------------------------------------

def _fetch_category_members(
    category: str,
    cm_type: str = "page",
    max_iterations: int = 200,
    lang: str = DEFAULT_LANG,
) -> list[dict]:
    # The "Category:" prefix is itself language-dependent on non-English wikis
    # (e.g. "Catégorie:" on fr, "Kategorie:" on de). Callers can pass either
    # the local-language prefix or the canonical English "Category:" — the
    # MediaWiki API resolves both. We only auto-prefix if no namespace prefix
    # is present at all.
    cat_title = category if ":" in category else f"Category:{category}"
    params: dict[str, Any] = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": cat_title,
        "cmtype": cm_type,
        "cmprop": "ids|title|type",
        "cmlimit": "max",
    }
    members: list[dict] = []
    with Progress(f"fetch category {cm_type}: {cat_title}", total=None,
                  tick_every=500) as p:
        for _ in range(max_iterations):
            data = _get(params, lang=lang)
            new_rows = data.get("query", {}).get("categorymembers", [])
            members.extend(new_rows)
            p.update(len(new_rows))
            if "continue" not in data:
                break
            params.update(data["continue"])
    return members


# ---------------------------------------------------------------------------
# Group 1 — article history & metadata
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def get_article_info(article_name: str, lang: str = DEFAULT_LANG) -> dict:
    """Current metadata: pageid, title, byte length, last revid, …"""
    data = _get({"action": "query", "prop": "info", "titles": article_name}, lang=lang)
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        return {}
    return dict(pages[0])


def get_article_history(
    article_name: str,
    date_limit: Optional[str] = None,
    lang: str = DEFAULT_LANG,
) -> list[dict]:
    """
    Full revision history up to date_limit (upper / newest bound).
    date_limit defaults to 'now' so analyses don't silently use stale snapshots.
    Returns a list of revision dicts sorted oldest-first.
    """
    _, revisions = _fetch_revisions(
        article_name, rvstart=date_limit or _now_iso(), lang=lang
    )
    rows = [_rev_to_row(r, article_name) for r in revisions]
    rows.sort(key=lambda r: r["timestamp"])
    return rows


def get_article_recent(
    article_name: str,
    date_limit: Optional[str] = None,
    lang: str = DEFAULT_LANG,
) -> dict:
    """Most recent revision up to date_limit, including wikitext."""
    _, revisions = _fetch_revisions(
        article_name,
        rvprop=_RVPROP_FULL,
        rvstart=date_limit or _now_iso(),
        rvlimit=1,
        lang=lang,
    )
    if not revisions:
        return {"metadata": {}, "wikitext": ""}
    rev = revisions[0]
    return {
        "metadata": _rev_to_row(rev, article_name),
        "wikitext": _extract_content(rev),
    }


def get_article_initial(article_name: str, lang: str = DEFAULT_LANG) -> dict:
    """First (creation) revision, including wikitext."""
    _, revisions = _fetch_revisions(
        article_name,
        rvprop=_RVPROP_FULL,
        rvdir="newer",
        rvlimit=1,
        lang=lang,
    )
    if not revisions:
        return {"metadata": {}, "wikitext": ""}
    rev = revisions[0]
    return {
        "metadata": _rev_to_row(rev, article_name),
        "wikitext": _extract_content(rev),
    }


def get_tables_all(
    article_name: str,
    date_limit: Optional[str] = None,
    lang: str = DEFAULT_LANG,
) -> dict:
    """Initial + recent + full history + info in one call."""
    return {
        "info": get_article_info(article_name, lang=lang),
        "initial": get_article_initial(article_name, lang=lang),
        "recent": get_article_recent(article_name, date_limit, lang=lang),
        "history": get_article_history(article_name, date_limit, lang=lang),
    }


def get_category_pages(category: str, lang: str = DEFAULT_LANG) -> list[str]:
    """Article titles in a Wikipedia category (articles only, no subcats)."""
    members = _fetch_category_members(category, cm_type="page", lang=lang)
    return [m["title"] for m in members if m.get("ns", 0) == 0]


def get_pages_in_cat_table(category: str, lang: str = DEFAULT_LANG) -> list[dict]:
    """Structured table of pages (pageid, title, type) in a category."""
    return _fetch_category_members(category, cm_type="page", lang=lang)


def get_subcat_table(
    catname: str,
    replacement: str = "_",
    lang: str = DEFAULT_LANG,
) -> list[dict]:
    """Direct subcategories of a Wikipedia category."""
    members = _fetch_category_members(catname, cm_type="subcat", lang=lang)
    if replacement != " ":
        for m in members:
            m["title"] = m["title"].replace(" ", replacement)
    return members


def get_subcat_multiple(
    catname_list: list[str],
    lang: str = DEFAULT_LANG,
) -> list[dict]:
    """Subcategories for multiple categories, concatenated."""
    result: list[dict] = []
    for cat in catname_list:
        for row in get_subcat_table(cat, lang=lang):
            result.append({**row, "source_category": cat})
    return result


def get_subcat_with_depth(
    catname: str,
    depth: int = 1,
    replacement: str = "_",
    lang: str = DEFAULT_LANG,
) -> list[dict]:
    """Recursively fetch subcategories up to depth levels."""
    seen: set[str] = set()
    result: list[dict] = []

    def _recurse(cat: str, level: int) -> None:
        if level > depth or cat in seen:
            return
        seen.add(cat)
        for s in _fetch_category_members(cat, cm_type="subcat", lang=lang):
            title = s["title"]
            display = title.replace(" ", replacement)
            result.append({**s, "title": display, "depth": level})
            _recurse(title, level + 1)

    root = catname if ":" in catname else f"Category:{catname}"
    _recurse(root, 1)
    return result


def get_page_in_cat_multiple(
    catname_list: list[str],
    lang: str = DEFAULT_LANG,
) -> list[dict]:
    """Pages for multiple categories, concatenated."""
    result: list[dict] = []
    for cat in catname_list:
        for row in get_pages_in_cat_table(cat, lang=lang):
            result.append({**row, "source_category": cat})
    return result


def get_category_history(
    article_list: list[str],
    lang: str = DEFAULT_LANG,
) -> list[dict]:
    """Full revision history for a list of articles."""
    result: list[dict] = []
    with Progress("category history", total=len(article_list)) as p:
        for art in article_list:
            result.extend(get_article_history(art, lang=lang))
            p.update()
    return result


def get_category_recent(
    article_list: list[str],
    date_limit: Optional[str] = None,
    lang: str = DEFAULT_LANG,
) -> dict:
    """Most recent revision metadata + wikitext for a list of articles."""
    metadata_list: list[dict] = []
    wikitext_list: list[str] = []
    with Progress("category recent", total=len(article_list)) as p:
        for art in article_list:
            r = get_article_recent(art, date_limit, lang=lang)
            metadata_list.append(r["metadata"])
            wikitext_list.append(r["wikitext"])
            p.update()
    return {"metadata": metadata_list, "wikitext": wikitext_list}


def get_category_creation(
    article_list: list[str],
    lang: str = DEFAULT_LANG,
) -> list[dict]:
    """Creation (first) revision metadata for a list of articles."""
    out: list[dict] = []
    with Progress("category creation", total=len(article_list)) as p:
        for art in article_list:
            out.append(get_article_initial(art, lang=lang)["metadata"])
            p.update()
    return out


def get_revert_counts(
    start: str = "2024-01-01",
    end: str = "2024-12-31",
    lang: str = DEFAULT_LANG,
) -> list[dict]:
    """
    Count revert-tagged edits (mw-reverted, mw-undo, mw-rollback) grouped by
    article for the given date window, sorted descending by count.

    Note: limited to the Wikipedia recentchanges retention window (~30 days).
    For longer historical ranges the result will be partial or empty.
    """
    from collections import Counter

    start_ts = start if "T" in start else start + "T00:00:00Z"
    end_ts = end if "T" in end else end + "T23:59:59Z"

    counts: Counter[str] = Counter()
    for tag in ("mw-reverted", "mw-undo", "mw-rollback"):
        params: dict[str, Any] = {
            "action": "query",
            "list": "recentchanges",
            "rcprop": "title|tags",
            "rctag": tag,
            "rcstart": end_ts,
            "rcend": start_ts,
            "rclimit": "max",
            "rctype": "edit",
            "rcnamespace": "0",
        }
        with Progress(f"revert tag {tag}", total=None, tick_every=500) as p:
            while True:
                data = _get(params, lang=lang)
                rows = data.get("query", {}).get("recentchanges", [])
                for rc in rows:
                    counts[rc["title"]] += 1
                p.update(len(rows))
                if "continue" not in data:
                    break
                params.update(data["continue"])

    return [
        {"title": title, "revert_count": count}
        for title, count in counts.most_common()
    ]
