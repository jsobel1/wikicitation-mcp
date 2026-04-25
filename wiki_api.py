"""
wiki_api.py
Wikipedia MediaWiki API client — pure Python replacement for wikilite Group-1 R calls.
"""
from __future__ import annotations

from typing import Any, Optional

import httpx

_ENDPOINT = "https://en.wikipedia.org/w/api.php"
_HEADERS = {
    "User-Agent": "wikicitation-mcp/0.3 (https://github.com/jsobel1/wikicitation-mcp)"
}
_RVPROP_META = "ids|user|userid|timestamp|size|comment"
_RVPROP_FULL = _RVPROP_META + "|content"


# ---------------------------------------------------------------------------
# Core HTTP helper
# ---------------------------------------------------------------------------

def _get(params: dict[str, Any]) -> dict:
    base: dict[str, Any] = {"format": "json", "formatversion": "2"}
    base.update(params)
    r = httpx.get(_ENDPOINT, params=base, headers=_HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise RuntimeError(
            f"Wikipedia API error: {data['error'].get('info', str(data['error']))}"
        )
    return data


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

    while len(revisions) < max_revisions:
        data = _get(params)
        pages = data.get("query", {}).get("pages", [])
        if not pages:
            break
        page = pages[0]
        if not page_meta:
            page_meta = {k: v for k, v in page.items() if k != "revisions"}
        revisions.extend(page.get("revisions", []))
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
    }


# ---------------------------------------------------------------------------
# Category helpers
# ---------------------------------------------------------------------------

def _fetch_category_members(category: str, cm_type: str = "page") -> list[dict]:
    cat_title = (
        category if category.startswith("Category:") else f"Category:{category}"
    )
    params: dict[str, Any] = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": cat_title,
        "cmtype": cm_type,
        "cmprop": "ids|title|type",
        "cmlimit": "max",
    }
    members: list[dict] = []
    while True:
        data = _get(params)
        members.extend(data.get("query", {}).get("categorymembers", []))
        if "continue" not in data:
            break
        params.update(data["continue"])
    return members


# ---------------------------------------------------------------------------
# Group 1 — article history & metadata
# ---------------------------------------------------------------------------

def get_article_info(article_name: str) -> dict:
    """Current metadata: pageid, title, byte length, last revid, …"""
    data = _get({"action": "query", "prop": "info", "titles": article_name})
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        return {}
    return dict(pages[0])


def get_article_history(
    article_name: str,
    date_limit: str = "2024-01-01T00:00:00Z",
) -> list[dict]:
    """
    Full revision history up to date_limit (upper / newest bound).
    Returns a list of revision dicts sorted oldest-first.
    """
    _, revisions = _fetch_revisions(article_name, rvstart=date_limit)
    rows = [_rev_to_row(r, article_name) for r in revisions]
    rows.sort(key=lambda r: r["timestamp"])
    return rows


def get_article_recent(
    article_name: str,
    date_limit: str = "2024-01-01T00:00:00Z",
) -> dict:
    """Most recent revision up to date_limit, including wikitext."""
    _, revisions = _fetch_revisions(
        article_name,
        rvprop=_RVPROP_FULL,
        rvstart=date_limit,
        rvlimit=1,
    )
    if not revisions:
        return {"metadata": {}, "wikitext": ""}
    rev = revisions[0]
    return {
        "metadata": _rev_to_row(rev, article_name),
        "wikitext": _extract_content(rev),
    }


def get_article_initial(article_name: str) -> dict:
    """First (creation) revision, including wikitext."""
    _, revisions = _fetch_revisions(
        article_name,
        rvprop=_RVPROP_FULL,
        rvdir="newer",
        rvlimit=1,
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
    date_limit: str = "2024-01-01T00:00:00Z",
) -> dict:
    """Initial + recent + full history + info in one call."""
    return {
        "info": get_article_info(article_name),
        "initial": get_article_initial(article_name),
        "recent": get_article_recent(article_name, date_limit),
        "history": get_article_history(article_name, date_limit),
    }


def get_category_pages(category: str) -> list[str]:
    """Article titles in a Wikipedia category (articles only, no subcats)."""
    members = _fetch_category_members(category, cm_type="page")
    return [m["title"] for m in members if m.get("ns", 0) == 0]


def get_pages_in_cat_table(category: str) -> list[dict]:
    """Structured table of pages (pageid, title, type) in a category."""
    return _fetch_category_members(category, cm_type="page")


def get_subcat_table(catname: str, replacement: str = "_") -> list[dict]:
    """Direct subcategories of a Wikipedia category."""
    members = _fetch_category_members(catname, cm_type="subcat")
    if replacement != " ":
        for m in members:
            m["title"] = m["title"].replace(" ", replacement)
    return members


def get_subcat_multiple(catname_list: list[str]) -> list[dict]:
    """Subcategories for multiple categories, concatenated."""
    result: list[dict] = []
    for cat in catname_list:
        for row in get_subcat_table(cat):
            result.append({**row, "source_category": cat})
    return result


def get_subcat_with_depth(
    catname: str,
    depth: int = 1,
    replacement: str = "_",
) -> list[dict]:
    """Recursively fetch subcategories up to depth levels."""
    seen: set[str] = set()
    result: list[dict] = []

    def _recurse(cat: str, level: int) -> None:
        if level > depth or cat in seen:
            return
        seen.add(cat)
        for s in _fetch_category_members(cat, cm_type="subcat"):
            title = s["title"]
            display = title.replace(" ", replacement)
            result.append({**s, "title": display, "depth": level})
            _recurse(title, level + 1)

    root = catname if catname.startswith("Category:") else f"Category:{catname}"
    _recurse(root, 1)
    return result


def get_page_in_cat_multiple(catname_list: list[str]) -> list[dict]:
    """Pages for multiple categories, concatenated."""
    result: list[dict] = []
    for cat in catname_list:
        for row in get_pages_in_cat_table(cat):
            result.append({**row, "source_category": cat})
    return result


def get_category_history(article_list: list[str]) -> list[dict]:
    """Full revision history for a list of articles."""
    result: list[dict] = []
    for art in article_list:
        result.extend(get_article_history(art))
    return result


def get_category_recent(
    article_list: list[str],
    date_limit: str = "2024-01-01T00:00:00Z",
) -> dict:
    """Most recent revision metadata + wikitext for a list of articles."""
    metadata_list: list[dict] = []
    wikitext_list: list[str] = []
    for art in article_list:
        r = get_article_recent(art, date_limit)
        metadata_list.append(r["metadata"])
        wikitext_list.append(r["wikitext"])
    return {"metadata": metadata_list, "wikitext": wikitext_list}


def get_category_creation(article_list: list[str]) -> list[dict]:
    """Creation (first) revision metadata for a list of articles."""
    return [get_article_initial(art)["metadata"] for art in article_list]


def get_revert_counts(
    start: str = "2024-01-01",
    end: str = "2024-12-31",
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
        while True:
            data = _get(params)
            for rc in data.get("query", {}).get("recentchanges", []):
                counts[rc["title"]] += 1
            if "continue" not in data:
                break
            params.update(data["continue"])

    return [
        {"title": title, "revert_count": count}
        for title, count in counts.most_common()
    ]
