# server.py — FastMCP entry point for the wikicitation MCP server

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from r_bridge import call_r_async

mcp = FastMCP(
    "wikicitation",
    instructions="Wikipedia citation analysis via wikilite"
)


@mcp.tool()
async def get_article_most_recent(
    article_name: str,
    lang: str = "en",
    date_an: str | None = None,
) -> dict:
    """Retrieve the most recent Wikipedia revision for an article."""
    return await call_r_async("get_article_most_recent", {
        "article_name": article_name,
        "lang": lang,
        "date_an": date_an,
    })


@mcp.tool()
async def get_article_history(
    article_name: str,
    lang: str = "en",
    date_an: str | None = None,
) -> dict:
    """Retrieve the full revision history for a Wikipedia article."""
    return await call_r_async("get_article_history", {
        "article_name": article_name,
        "lang": lang,
        "date_an": date_an,
    })


@mcp.tool()
async def get_sci_score(text: str) -> dict:
    """Compute SciScore (proportion of journal citations) for wikitext."""
    return await call_r_async("get_sci_score", {"text": text})


@mcp.tool()
async def get_sci_score2(text: str) -> dict:
    """Compute SciScore2 (DOI-to-ref ratio) for wikitext."""
    return await call_r_async("get_sci_score2", {"text": text})


@mcp.tool()
async def get_doi_count(text: str) -> dict:
    """Count DOIs in a wikitext string."""
    return await call_r_async("get_doi_count", {"text": text})


@mcp.tool()
async def extract_citations(text: str) -> dict:
    """Extract all Citation Style 1 templates from wikitext."""
    return await call_r_async("extract_citations", {"text": text})


@mcp.tool()
async def annotate_dois(doi_list: list[str]) -> dict:
    """Annotate a list of DOIs using EuropePMC."""
    return await call_r_async("annotate_dois", {"doi_list": doi_list})


@mcp.tool()
async def annotate_dois_crossref(
    doi_list: list[str],
    batch_size: int = 50,
) -> dict:
    """
    Annotate a list of DOIs using the CrossRef /works API.

    Returns a tidy table with columns doi, title, authorString, journalTitle,
    pubYear, pubType, publisher, issn, volume, issue, page, citedByCount.
    Column names are aligned with annotate_dois (EuropePMC) for easy merging.

    batch_size: number of DOIs per CrossRef request (default 50).
    """
    return await call_r_async("annotate_dois_crossref", {
        "doi_list": doi_list,
        "batch_size": batch_size,
    })


@mcp.tool()
async def get_revert_counts(
    start: str,
    end: str,
    rev_eds: bool = True,
) -> dict:
    """
    Count Wikipedia edits for a time window (YYYYMMDDHHmmss).

    When rev_eds=True (default), counts only revert-tagged edits.
    When rev_eds=False, counts all edits.
    """
    return await call_r_async("get_revert_counts", {
        "start": start,
        "end": end,
        "rev_eds": rev_eds,
    })


@mcp.tool()
async def get_top_cited_papers(
    article_name: str,
    lang: str = "en",
) -> dict:
    """Find top-cited DOIs in a Wikipedia article with EuropePMC annotations."""
    return await call_r_async("get_top_cited", {
        "article_name": article_name,
        "lang": lang,
    })


@mcp.tool()
async def probe_article_over_time(
    article_name: str,
    dates_to_probe: list[str],
    lang: str = "en",
    metrics: list[str] | None = None,
) -> dict:
    """
    Probe a Wikipedia article at multiple time points and return quality metrics.

    dates_to_probe: list of ISO 8601 timestamps (e.g. "2021-01-01T00:00:00Z")
    metrics: subset of ["sci_score", "doi_count", "ref_count", "size"]
    """
    return await call_r_async("probe_article", {
        "article_name": article_name,
        "dates_to_probe": dates_to_probe,
        "lang": lang,
        "metrics": metrics or ["sci_score", "doi_count", "ref_count", "size"],
    })


@mcp.tool()
async def get_ref_count(text: str) -> dict:
    """Count <ref> tags in a wikitext string."""
    return await call_r_async("get_ref_count", {"text": text})


@mcp.tool()
async def get_url_count(text: str) -> dict:
    """Count external URLs in a wikitext string."""
    return await call_r_async("get_url_count", {"text": text})


@mcp.tool()
async def get_isbn_count(text: str) -> dict:
    """Count ISBNs in a wikitext string."""
    return await call_r_async("get_isbn_count", {"text": text})


@mcp.tool()
async def get_any_count(text: str, pattern: str) -> dict:
    """Count regex pattern matches in a wikitext string."""
    return await call_r_async("get_any_count", {"text": text, "pattern": pattern})


@mcp.tool()
async def replace_wikihypelinks(text: str, replacement: str = "") -> dict:
    """Remove or replace [[wikilinks]] in a wikitext string."""
    return await call_r_async("replace_wikihypelinks", {
        "text": text,
        "replacement": replacement,
    })


@mcp.tool()
async def get_article_info(article_name: str, lang: str = "en") -> dict:
    """Retrieve metadata (title, pageid, size, last revid) for a Wikipedia article."""
    return await call_r_async("get_article_info", {
        "article_name": article_name,
        "lang": lang,
    })


@mcp.tool()
async def parse_all_citations(
    article_name: str,
    lang: str = "en",
    date_an: str | None = None,
) -> dict:
    """Parse every CS1 citation template in a Wikipedia article into a tidy table."""
    return await call_r_async("parse_all_citations", {
        "article_name": article_name,
        "lang": lang,
        "date_an": date_an,
    })


@mcp.tool()
async def get_citation_type_counts(
    article_name: str,
    lang: str = "en",
    date_an: str | None = None,
) -> dict:
    """
    Count CS1 citations by display category for a Wikipedia article.

    Returns counts grouped into: Journal, Book, Web, News/Magazine, Preprint,
    Thesis, Conference, Report, Multimedia, Legal/Patent, Social Media, Other.
    """
    return await call_r_async("get_citation_type_counts", {
        "article_name": article_name,
        "lang": lang,
        "date_an": date_an,
    })


@mcp.tool()
async def get_category_pages(category: str, lang: str = "en") -> dict:
    """List article titles in a Wikipedia category."""
    return await call_r_async("get_category_pages", {
        "category": category,
        "lang": lang,
    })


@mcp.tool()
async def get_subcat_table(catname: str, lang: str = "en") -> dict:
    """List direct subcategories of a Wikipedia category."""
    return await call_r_async("get_subcat_table", {
        "catname": catname,
        "lang": lang,
    })


if __name__ == "__main__":
    mcp.run()
