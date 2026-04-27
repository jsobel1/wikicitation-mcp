"""
citation_utils.py
Citation counting, extraction, parsing, and quality metrics.
Pure Python (re + mwparserfromhell). Text operations need no network;
article-level functions fetch wikitext via wiki_api.

Per-(article, date_limit) wikitext is cached for the lifetime of the process so
a single analysis pass that calls multiple article-level functions on the same
article does not refetch the wikitext seven times.
"""
from __future__ import annotations

import re
import threading
from collections import Counter
from typing import Optional

import mwparserfromhell

# ---------------------------------------------------------------------------
# Compiled regex patterns (mirrors wikilite pkg.env regexps)
# ---------------------------------------------------------------------------

DOI_RE    = re.compile(r'10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+')
URL_RE    = re.compile(r'https?://[^\s\]<>"|{}\\^`]+')
REF_RE    = re.compile(
    r'<ref(?:\s[^>]*)?(?<!/)>.*?</ref>|<ref(?:\s[^>]*)?/>',
    re.DOTALL | re.IGNORECASE,
)
ISBN_RE   = re.compile(r'(?i)\bisbn\s*[=:]?\s*([-0-9X ]{9,18})')
WIKILINK_RE         = re.compile(r'\[\[.*?\]\]', re.DOTALL)
WIKILINK_DISPLAY_RE = re.compile(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]')
PMID_RE   = re.compile(r'(?:pmid|PMID)\s*[=:]\s*(\d{5,9})')
CITE_RE   = re.compile(r'\{\{[Cc]ite\b[^{}]*(?:\{\{[^{}]*\}\}[^{}]*)?\}\}',
                        re.DOTALL)

ALL_PATTERNS: dict[str, re.Pattern] = {
    "doi":      DOI_RE,
    "url":      URL_RE,
    "ref":      REF_RE,
    "isbn":     ISBN_RE,
    "wikilink": WIKILINK_RE,
    "pmid":     PMID_RE,
    "cite_all": CITE_RE,
}


# ---------------------------------------------------------------------------
# Template helpers
# ---------------------------------------------------------------------------

def _is_cs1(name: str) -> bool:
    n = name.strip().lower()
    return n.startswith("cite ") or n == "citation"


def _cite_type(template_name: str) -> str:
    n = template_name.strip().lower()
    return n.replace("cite ", "", 1) if n.startswith("cite ") else n


# ---------------------------------------------------------------------------
# Group 2 — counting (text-based, no network)
# ---------------------------------------------------------------------------

def get_doi_count(text: str) -> int:
    return len(DOI_RE.findall(text))


def get_ref_count(text: str) -> int:
    return len(REF_RE.findall(text))


def get_url_count(text: str) -> int:
    return len(URL_RE.findall(text))


def get_isbn_count(text: str) -> int:
    return len(ISBN_RE.findall(text))


def get_hyperlink_count(text: str) -> int:
    return len(WIKILINK_RE.findall(text))


def get_any_count(text: str, regexp: str) -> int:
    return len(re.findall(regexp, text))


# ---------------------------------------------------------------------------
# Group 2 — extraction (text-based, no network)
# ---------------------------------------------------------------------------

def extract_citations(text: str) -> list[str]:
    """Return all CS1 citation templates found in wikitext."""
    wikicode = mwparserfromhell.parse(text)
    return [str(t) for t in wikicode.filter_templates() if _is_cs1(str(t.name))]


def extract_wikihyperlinks(text: str) -> list[str]:
    """Return all [[...]] wikilinks."""
    return WIKILINK_RE.findall(text)


def replace_wikihyperlinks(text: str) -> str:
    """Replace [[Link|Display]] → Display, [[Link]] → Link."""
    return WIKILINK_DISPLAY_RE.sub(r'\1', text)


def parse_cite_type(text: str) -> dict:
    """
    Parse a single CS1 template string.
    Returns {"cite_type": str, "fields": {param: value, …}}.
    """
    wikicode = mwparserfromhell.parse(text)
    templates = [t for t in wikicode.filter_templates() if _is_cs1(str(t.name))]
    if not templates:
        return {}
    t = templates[0]
    return {
        "cite_type": _cite_type(str(t.name)),
        "fields": {
            str(p.name).strip(): str(p.value).strip()
            for p in t.params
            if str(p.value).strip()
        },
    }


def get_source_type_counts(text: str) -> list[dict]:
    """Count CS1 citation types in raw wikitext."""
    wikicode = mwparserfromhell.parse(text)
    counts: Counter[str] = Counter()
    for t in wikicode.filter_templates():
        if _is_cs1(str(t.name)):
            counts[_cite_type(str(t.name))] += 1
    return [{"cite_type": ct, "count": c} for ct, c in counts.most_common()]


# ---------------------------------------------------------------------------
# Internal: fetch + cache wikitext
#
# Without this cache, a single analysis pass that calls (e.g.) get_sci_score,
# parse_citations, get_citation_types, and get_top_cited_papers on the same
# article hits the Wikipedia API four times for the same revision. The cache
# also pins the revid so every metric in one pass references the same snapshot.
# ---------------------------------------------------------------------------

_wikitext_cache: dict[tuple[str, Optional[str]], tuple[int, str]] = {}
_cache_lock = threading.Lock()


def _get_wikitext(article_name: str, date_limit: Optional[str]) -> tuple[int, str]:
    """Return (revid, wikitext) for the most recent revision up to date_limit."""
    key = (article_name, date_limit)
    with _cache_lock:
        if key in _wikitext_cache:
            return _wikitext_cache[key]

    from wiki_api import get_article_recent
    result = get_article_recent(article_name, date_limit)
    revid = result["metadata"].get("revid", 0) or 0
    wikitext = result["wikitext"]

    with _cache_lock:
        _wikitext_cache[key] = (revid, wikitext)
    return revid, wikitext


def clear_wikitext_cache() -> None:
    """Drop cached wikitext (call between independent analysis passes)."""
    with _cache_lock:
        _wikitext_cache.clear()


# ---------------------------------------------------------------------------
# Group 2 — article-level functions (require network on cache miss)
#
# date_limit=None means "current" — using a stale literal default silently
# pinned analyses to old snapshots, which was the source of the run report's
# UNCERTAIN_1 (parse_citations returned outdated revids).
# ---------------------------------------------------------------------------

def extract_with_regex(
    article_name: str,
    regexp: str,
    date_limit: Optional[str] = None,
) -> list[dict]:
    """Apply a regex to the most recent article wikitext."""
    revid, wikitext = _get_wikitext(article_name, date_limit)
    return [
        {"art": article_name, "revid": revid, "match": m}
        for m in re.findall(regexp, wikitext)
    ]


def extract_all_regex(
    article_name: str,
    date_limit: Optional[str] = None,
) -> list[dict]:
    """Apply all built-in patterns to the most recent article wikitext."""
    revid, wikitext = _get_wikitext(article_name, date_limit)
    rows: list[dict] = []
    for pattern_name, compiled in ALL_PATTERNS.items():
        for m in compiled.findall(wikitext):
            match_str = m if isinstance(m, str) else (m[0] if m else "")
            rows.append({
                "art": article_name,
                "revid": revid,
                "pattern_name": pattern_name,
                "match": match_str,
            })
    return rows


def parse_citations(
    article_name: str,
    date_limit: Optional[str] = None,
) -> list[dict]:
    """Structured citation table (one row per citation template)."""
    revid, wikitext = _get_wikitext(article_name, date_limit)
    wikicode = mwparserfromhell.parse(wikitext)
    rows: list[dict] = []
    for i, t in enumerate(
        (t for t in wikicode.filter_templates() if _is_cs1(str(t.name))), start=1
    ):
        params = {str(p.name).strip(): str(p.value).strip() for p in t.params}
        rows.append({
            "art": article_name,
            "revid": revid,
            "cite_type": _cite_type(str(t.name)),
            "id_cite": i,
            "doi":    params.get("doi", ""),
            "author": params.get("author", params.get("author1",
                      params.get("last", params.get("last1", "")))),
            "year":   params.get("year", ""),
            "title":  params.get("title", ""),
        })
    return rows


def parse_all_citations(
    article_name: str,
    date_limit: Optional[str] = None,
) -> list[dict]:
    """Full long-form table: one row per citation *field*."""
    revid, wikitext = _get_wikitext(article_name, date_limit)
    wikicode = mwparserfromhell.parse(wikitext)
    rows: list[dict] = []
    cite_idx = 0
    for t in wikicode.filter_templates():
        if not _is_cs1(str(t.name)):
            continue
        cite_idx += 1
        ct = _cite_type(str(t.name))
        for p in t.params:
            rows.append({
                "art":       article_name,
                "revid":     revid,
                "cite_type": ct,
                "id_cite":   cite_idx,
                "variable":  str(p.name).strip(),
                "value":     str(p.value).strip(),
            })
    return rows


def get_citation_types(
    article_name: str,
    date_limit: Optional[str] = None,
) -> list[dict]:
    """Count CS1 citation types for an article."""
    _, wikitext = _get_wikitext(article_name, date_limit)
    return get_source_type_counts(wikitext)


def get_sci_score(
    article_name: str,
    date_limit: Optional[str] = None,
) -> dict:
    """
    sci_score:  fraction of CS1 templates that are cite-journal.
    sci_score2: ratio of DOI count to <ref> tag count.
    """
    revid, wikitext = _get_wikitext(article_name, date_limit)

    type_counts = get_source_type_counts(wikitext)
    total_cs1     = sum(r["count"] for r in type_counts)
    journal_count = next(
        (r["count"] for r in type_counts if r["cite_type"] == "journal"), 0
    )
    sci_score  = journal_count / total_cs1 if total_cs1 else 0.0
    doi_count  = get_doi_count(wikitext)
    ref_count  = get_ref_count(wikitext)
    sci_score2 = doi_count / ref_count if ref_count else 0.0

    return {
        "sci_score":  round(sci_score, 4),
        "sci_score2": round(sci_score2, 4),
        "article":    article_name,
        "revid":      revid,
    }


def get_top_cited_papers(
    article_name: str,
    date_limit: Optional[str] = None,
) -> list[dict]:
    """Top 40 most-cited DOIs in an article, annotated via EuropePMC."""
    from annotate_utils import annotate_dois_europmc

    _, wikitext = _get_wikitext(article_name, date_limit)
    # Normalize DOIs to lowercase for stable counting (DOIs are case-insensitive
    # per the DOI handbook, even though the registration metadata may preserve case).
    dois = [d.lower() for d in DOI_RE.findall(wikitext)]
    counter  = Counter(dois)
    top_dois = [doi for doi, _ in counter.most_common(40)]

    annotated = annotate_dois_europmc(top_dois)
    for row in annotated:
        doi = (row.get("doi") or "").lower()
        row["wiki_count"] = counter.get(doi, 0)

    return sorted(annotated, key=lambda r: r.get("wiki_count", 0), reverse=True)
