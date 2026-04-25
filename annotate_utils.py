"""
annotate_utils.py
DOI and ISBN annotation via external REST APIs.
Pure Python / httpx, no R required.
"""
from __future__ import annotations

import httpx

_HEADERS = {
    "User-Agent": (
        "wikicitation-mcp/0.3 "
        "(https://github.com/jsobel1/wikicitation-mcp)"
    )
}


def _get(url: str, **kwargs) -> httpx.Response:
    return httpx.get(url, headers=_HEADERS, timeout=20, **kwargs)


# ---------------------------------------------------------------------------
# EuropePMC
# ---------------------------------------------------------------------------

_EPMC_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

def annotate_dois_europmc(doi_list: list[str]) -> list[dict]:
    """Annotate DOIs via EuropePMC (batches of 10)."""
    if not doi_list:
        return []
    results: list[dict] = []
    for i in range(0, len(doi_list), 10):
        chunk = doi_list[i : i + 10]
        query = " OR ".join(f'DOI:"{doi}"' for doi in chunk)
        r = _get(_EPMC_URL, params={
            "query":      query,
            "resultType": "core",
            "pageSize":   len(chunk) * 2,
            "format":     "json",
        })
        if r.status_code == 200:
            results.extend(
                r.json().get("resultList", {}).get("result", [])
            )
    return results


# ---------------------------------------------------------------------------
# CrossRef
# ---------------------------------------------------------------------------

_CROSSREF_BASE = "https://api.crossref.org/works"

def annotate_dois_crossref(doi_list: list[str]) -> list[dict]:
    """Annotate DOIs via CrossRef REST API (one request per DOI)."""
    results: list[dict] = []
    for doi in doi_list:
        r = _get(f"{_CROSSREF_BASE}/{doi}")
        if r.status_code != 200:
            results.append({"doi": doi, "error": f"HTTP {r.status_code}"})
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
    """Altmetric attention scores for a list of DOIs."""
    results: list[dict] = []
    for doi in doi_list:
        r = _get(f"{_ALTMETRIC_BASE}/doi/{doi}")
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
        r = httpx.get(
            f"https://doi.org/{doi}",
            headers={**_HEADERS, "Accept": "application/x-bibtex"},
            follow_redirects=True,
            timeout=20,
        )
        entries.append(
            r.text.strip() if r.status_code == 200
            else f"% DOI {doi}: HTTP {r.status_code}"
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
    if r.status_code != 200:
        return {"isbn": isbn, "error": f"HTTP {r.status_code}"}
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
    if r.status_code != 200:
        return {"isbn": isbn, "error": f"HTTP {r.status_code}"}
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
