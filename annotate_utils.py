"""
annotate_utils.py
DOI and ISBN annotation via external REST APIs.

Per-host rate limits (sources: provider docs / community guidance):
  - EuropePMC:   no published cap; ~10 req/s polite ceiling, supports batched DOI queries.
  - CrossRef:    50 req/s on the public pool; identical limit on the polite pool but
                 with priority + lower throttle risk when a `mailto=` is provided.
  - Altmetric:   1 req/s without an API key (this is the documented free-tier cap).
  - Google Books / Open Library: ~10 req/s polite ceiling.

All HTTP calls now share a connection-pooled httpx.Client, retry 429/5xx with
exponential backoff (honoring `Retry-After`), and throttle per-host so a
many-DOI batch can't accidentally exceed the documented rate.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Optional
from urllib.parse import urlsplit

import httpx

logger = logging.getLogger(__name__)

# Set CROSSREF_MAILTO env var (or edit here) to opt into the CrossRef polite pool.
_POLITE_MAILTO = "jsobel83@gmail.com"

_HEADERS = {
    "User-Agent": (
        f"wikicitation-mcp/0.4 "
        f"(https://github.com/jsobel1/wikicitation-mcp; mailto:{_POLITE_MAILTO})"
    )
}

# Per-host minimum interval (seconds). Keys are bare hostnames.
_MIN_INTERVAL_S: dict[str, float] = {
    "www.ebi.ac.uk":         0.10,   # EuropePMC: ~10/s polite
    "api.crossref.org":      0.05,   # CrossRef: 50/s public+polite
    "doi.org":               0.10,
    "api.altmetric.com":     1.00,   # Altmetric: 1/s free tier
    "www.googleapis.com":    0.10,
    "openlibrary.org":       0.10,
}
_DEFAULT_MIN_INTERVAL = 0.20

_MAX_RETRIES = 5
_BACKOFF_BASE = 1.0
_BACKOFF_CAP = 30.0

_client = httpx.Client(
    headers=_HEADERS,
    timeout=httpx.Timeout(20.0, connect=10.0),
    limits=httpx.Limits(max_connections=8, max_keepalive_connections=8),
    follow_redirects=False,
)

_throttle_lock = threading.Lock()
_last_call_ts: dict[str, float] = {}


def _throttle(url: str) -> None:
    host = urlsplit(url).hostname or ""
    interval = _MIN_INTERVAL_S.get(host, _DEFAULT_MIN_INTERVAL)
    with _throttle_lock:
        now = time.monotonic()
        wait = interval - (now - _last_call_ts.get(host, 0.0))
        if wait > 0:
            time.sleep(wait)
        _last_call_ts[host] = time.monotonic()


def _backoff(attempt: int, retry_after: Optional[str] = None) -> float:
    if retry_after:
        try:
            return min(float(retry_after), _BACKOFF_CAP)
        except ValueError:
            pass
    return min(_BACKOFF_BASE * (2 ** attempt), _BACKOFF_CAP)


def _get(
    url: str,
    *,
    params: Optional[dict] = None,
    extra_headers: Optional[dict] = None,
    follow_redirects: bool = False,
) -> Optional[httpx.Response]:
    """Throttled, retrying GET. Returns None after exhausting retries on transport errors."""
    headers = {**_HEADERS, **(extra_headers or {})}

    for attempt in range(_MAX_RETRIES):
        _throttle(url)
        try:
            r = _client.get(
                url,
                params=params,
                headers=headers,
                follow_redirects=follow_redirects,
            )
        except (httpx.TransportError, httpx.TimeoutException) as exc:
            sleep_s = _backoff(attempt)
            logger.warning("annotate_utils transport error %s (attempt %d) — sleeping %.1fs",
                           exc, attempt + 1, sleep_s)
            time.sleep(sleep_s)
            continue

        if r.status_code in (429, 503):
            sleep_s = _backoff(attempt, r.headers.get("Retry-After"))
            logger.warning("annotate_utils %s HTTP %d (attempt %d) — sleeping %.1fs",
                           url, r.status_code, attempt + 1, sleep_s)
            time.sleep(sleep_s)
            continue
        if 500 <= r.status_code < 600:
            time.sleep(_backoff(attempt))
            continue
        return r

    logger.error("annotate_utils: exhausted retries on %s", url)
    return None


# ---------------------------------------------------------------------------
# EuropePMC
# ---------------------------------------------------------------------------

_EPMC_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def _epmc_extract(rec: dict, doi: str) -> dict:
    """Map a raw EuropePMC `result` record to the analysis schema."""
    epmc_doi = (rec.get("doi") or "").lower() or doi.lower()
    return {
        "doi":              epmc_doi,
        "pmid":             rec.get("pmid", ""),
        "pmcid":            rec.get("pmcid", ""),
        "title":            rec.get("title", ""),
        "authors":          rec.get("authorString", ""),
        "journal":          rec.get("journalTitle", ""),
        "year":             rec.get("pubYear", ""),
        "citation_count":   rec.get("citedByCount", 0),
        "is_open_access":   rec.get("isOpenAccess", "N") == "Y",
        "source":           rec.get("source", ""),
    }


def annotate_dois_europmc(doi_list: list[str]) -> list[dict]:
    """
    Annotate DOIs via EuropePMC, batched by query size.

    Returns one row per input DOI; rows with no EuropePMC hit still appear so
    downstream joins (e.g. wiki_count attachment) don't silently drop entries.
    """
    if not doi_list:
        return []

    # Normalize + deduplicate while preserving input order.
    seen: set[str] = set()
    unique: list[str] = []
    for d in doi_list:
        d_norm = d.strip()
        key = d_norm.lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(d_norm)

    by_doi: dict[str, dict] = {}

    # EuropePMC accepts long boolean queries; 25 DOIs per call is a comfortable
    # ceiling that keeps URL length under provider/proxy limits.
    BATCH = 25
    for i in range(0, len(unique), BATCH):
        chunk = unique[i : i + BATCH]
        query = " OR ".join(f'DOI:"{d}"' for d in chunk)
        r = _get(_EPMC_URL, params={
            "query":      query,
            "resultType": "core",
            "pageSize":   max(25, len(chunk) * 2),
            "format":     "json",
        })
        if r is None or r.status_code != 200:
            for d in chunk:
                by_doi.setdefault(d.lower(), {
                    "doi": d.lower(),
                    "error": f"HTTP {r.status_code if r else 'transport'}",
                })
            continue

        results = r.json().get("resultList", {}).get("result", []) or []
        for rec in results:
            rec_doi = (rec.get("doi") or "").lower()
            if rec_doi:
                by_doi[rec_doi] = _epmc_extract(rec, rec_doi)

    # Emit rows in input order; fill misses with placeholder.
    rows: list[dict] = []
    for d in unique:
        key = d.lower()
        rows.append(by_doi.get(key, {"doi": key, "year": "", "citation_count": 0,
                                      "title": "", "authors": "", "journal": "",
                                      "not_found": True}))
    return rows


# ---------------------------------------------------------------------------
# CrossRef
# ---------------------------------------------------------------------------

_CROSSREF_BASE = "https://api.crossref.org/works"


def annotate_dois_crossref(doi_list: list[str]) -> list[dict]:
    """Annotate DOIs via CrossRef REST API (one request per DOI, polite pool)."""
    results: list[dict] = []
    for doi in doi_list:
        r = _get(
            f"{_CROSSREF_BASE}/{doi}",
            params={"mailto": _POLITE_MAILTO},
        )
        if r is None or r.status_code != 200:
            results.append({"doi": doi,
                            "error": f"HTTP {r.status_code if r else 'transport'}"})
            continue
        msg = r.json().get("message", {})
        pub = msg.get("published-print", msg.get("published-online", {}))
        year = (pub.get("date-parts", [[None]])[0] or [None])[0]
        results.append({
            "doi":                   doi,
            "title":                 " ".join(msg.get("title", [])),
            "authors":               [
                f"{a.get('given','')} {a.get('family','')}".strip()
                for a in msg.get("author", [])
            ],
            "journal":               " ".join(msg.get("container-title", [])),
            "year":                  year,
            "publisher":             msg.get("publisher", ""),
            "type":                  msg.get("type", ""),
            "is_referenced_by_count": msg.get("is-referenced-by-count", 0),
            "url":                   msg.get("URL", ""),
        })
    return results


# ---------------------------------------------------------------------------
# Altmetric
# ---------------------------------------------------------------------------

_ALTMETRIC_BASE = "https://api.altmetric.com/v1"


def annotate_dois_altmetric(doi_list: list[str]) -> list[dict]:
    """Altmetric attention scores for a list of DOIs (1 req/s free tier)."""
    results: list[dict] = []
    for doi in doi_list:
        r = _get(f"{_ALTMETRIC_BASE}/doi/{doi}")
        if r is None:
            results.append({"doi": doi, "error": "transport"})
            continue
        if r.status_code == 404:
            results.append({"doi": doi, "altmetric_score": None})
            continue
        if r.status_code != 200:
            results.append({"doi": doi, "error": f"HTTP {r.status_code}"})
            continue
        d = r.json()
        results.append({
            "doi":                      doi,
            "altmetric_score":          d.get("score"),
            "altmetric_id":             d.get("altmetric_id"),
            "cited_by_tweeters_count":  d.get("cited_by_tweeters_count", 0),
            "cited_by_accounts_count":  d.get("cited_by_accounts_count", 0),
            "cited_by_msm_count":       d.get("cited_by_msm_count", 0),
            "cited_by_fbwalls_count":   d.get("cited_by_fbwalls_count", 0),
            "readers_count":            d.get("readers_count", 0),
            "url":                      d.get("details_url", ""),
        })
    return results


# ---------------------------------------------------------------------------
# BibTeX via CrossRef content negotiation
# ---------------------------------------------------------------------------

def annotate_dois_bibtex(doi_list: list[str]) -> dict:
    """Retrieve BibTeX entries for DOIs via CrossRef content negotiation."""
    entries: list[str] = []
    for doi in doi_list:
        r = _get(
            f"https://doi.org/{doi}",
            extra_headers={"Accept": "application/x-bibtex"},
            follow_redirects=True,
        )
        entries.append(
            r.text.strip() if r and r.status_code == 200
            else f"% DOI {doi}: HTTP {r.status_code if r else 'transport'}"
        )
    return {"bibtex_entries": entries}


# ---------------------------------------------------------------------------
# ISBN — Google Books
# ---------------------------------------------------------------------------

_GOOGLE_BOOKS = "https://www.googleapis.com/books/v1/volumes"


def annotate_isbn_google(isbn: str) -> dict:
    """Book metadata from Google Books for one ISBN."""
    clean = isbn.replace("-", "").replace(" ", "")
    r = _get(_GOOGLE_BOOKS, params={"q": f"isbn:{clean}"})
    if r is None or r.status_code != 200:
        return {"isbn": isbn, "error": f"HTTP {r.status_code if r else 'transport'}"}
    items = r.json().get("items", [])
    if not items:
        return {"isbn": isbn, "error": "not found"}
    info = items[0].get("volumeInfo", {})
    return {
        "isbn":          isbn,
        "title":         info.get("title", ""),
        "authors":       info.get("authors", []),
        "publisher":     info.get("publisher", ""),
        "publishedDate": info.get("publishedDate", ""),
        "description":   info.get("description", "")[:500],
        "categories":    info.get("categories", []),
    }


# ---------------------------------------------------------------------------
# ISBN — Open Library
# ---------------------------------------------------------------------------

_OPENLIB = "https://openlibrary.org/api/books"


def annotate_isbn_openlib(isbn: str) -> dict:
    """Book metadata from Open Library for one ISBN."""
    clean = isbn.replace("-", "").replace(" ", "")
    r = _get(_OPENLIB, params={
        "bibkeys": f"ISBN:{clean}",
        "format":  "json",
        "jscmd":   "data",
    })
    if r is None or r.status_code != 200:
        return {"isbn": isbn, "error": f"HTTP {r.status_code if r else 'transport'}"}
    data = r.json()
    key  = f"ISBN:{clean}"
    if key not in data:
        return {"isbn": isbn, "error": "not found"}
    info = data[key]
    return {
        "isbn":            isbn,
        "title":           info.get("title", ""),
        "authors":         [a.get("name", "") for a in info.get("authors", [])],
        "publishers":      [p.get("name", "") for p in info.get("publishers", [])],
        "publish_date":    info.get("publish_date", ""),
        "number_of_pages": info.get("number_of_pages"),
        "subjects":        [s.get("name", "") for s in info.get("subjects", [])[:10]],
    }


# ---------------------------------------------------------------------------
# ISBN — Altmetric
# ---------------------------------------------------------------------------

def annotate_isbns_altmetric(isbn_list: list[str]) -> list[dict]:
    """Altmetric attention scores for a list of ISBNs."""
    results: list[dict] = []
    for isbn in isbn_list:
        clean = isbn.replace("-", "").replace(" ", "")
        r = _get(f"{_ALTMETRIC_BASE}/isbn/{clean}")
        if r is None:
            results.append({"isbn": isbn, "error": "transport"})
            continue
        if r.status_code == 404:
            results.append({"isbn": isbn, "altmetric_score": None})
            continue
        if r.status_code != 200:
            results.append({"isbn": isbn, "error": f"HTTP {r.status_code}"})
            continue
        d = r.json()
        results.append({
            "isbn":                     isbn,
            "altmetric_score":          d.get("score"),
            "cited_by_tweeters_count":  d.get("cited_by_tweeters_count", 0),
            "cited_by_accounts_count":  d.get("cited_by_accounts_count", 0),
            "url":                      d.get("details_url", ""),
        })
    return results
