# server.py
# Serveur MCP pour WikiCitationHistoRy.
# Expose toutes les fonctions exportées du package R comme outils MCP.
#
# Lancement :
#   uv run python server.py              ← stdio (Claude Code / Desktop)
#   uv run fastmcp run server.py \
#     --transport streamable-http \
#     --port 8000                        ← HTTP (claude.ai)

from __future__ import annotations

from typing import Optional
from fastmcp import FastMCP
from r_bridge import call_r

# ── Initialisation du serveur ─────────────────────────────────────────────────

mcp = FastMCP(
    name="WikiCitationHistoRy",
    version="0.1.0",
    description=(
        "Retrieve and analyse Wikipedia article revision history, "
        "extract and count citations (DOIs, ISBNs, PMIDs, URLs, hyperlinks), "
        "annotate DOIs via EuropePMC / CrossRef / Altmetric, "
        "and generate visualisations — all powered by the R package "
        "WikiCitationHistoRy."
    ),
)


# ═══════════════════════════════════════════════════════════════════════════════
# GROUPE 1 — Historique et révisions Wikipedia
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def get_article_history(
    article_name: str,
    date_limit: Optional[str] = "2024-01-01T00:00:00Z",
) -> dict:
    """
    Retrieve the full revision history of a Wikipedia article.

    Returns a table of all revisions with columns: art, revid, parentid,
    user, userid, timestamp, size, comment.
    The raw wikitext is excluded for performance — use get_article_recent
    to access wikitext.

    Args:
        article_name: English Wikipedia article title (e.g. "Zeitgeber").
        date_limit:   Upper date limit in ISO 8601 format
                      (default: "2024-01-01T00:00:00Z").
    """
    return call_r("get_article_history", {
        "article_name": article_name,
        "date_limit": date_limit,
    })


@mcp.tool()
def get_article_recent(
    article_name: str,
    date_limit: Optional[str] = "2024-01-01T00:00:00Z",
) -> dict:
    """
    Retrieve the most recent revision of a Wikipedia article,
    including its full wikitext.

    Returns:
        metadata: revision metadata (revid, user, timestamp, size, comment).
        wikitext: raw wikitext of the revision.

    Args:
        article_name: English Wikipedia article title.
        date_limit:   Upper date limit in ISO 8601 format.
    """
    return call_r("get_article_recent", {
        "article_name": article_name,
        "date_limit": date_limit,
    })


@mcp.tool()
def get_article_initial(article_name: str) -> dict:
    """
    Retrieve the very first (creation) revision of a Wikipedia article,
    including its wikitext.

    Args:
        article_name: English Wikipedia article title.
    """
    return call_r("get_article_initial", {"article_name": article_name})


@mcp.tool()
def get_article_info(article_name: str) -> dict:
    """
    Retrieve current metadata for a Wikipedia article:
    page ID, title, and byte length.

    Args:
        article_name: English Wikipedia article title.
    """
    return call_r("get_article_info", {"article_name": article_name})


@mcp.tool()
def get_category_pages(category: str) -> list:
    """
    List all article titles belonging to a Wikipedia category.
    Filters out user pages and subcategory entries.

    Args:
        category: Wikipedia category name (e.g. "Circadian rhythm").
    """
    return call_r("get_category_pages", {"category": category})


@mcp.tool()
def get_category_history(article_list: list[str]) -> dict:
    """
    Retrieve the full revision history (without wikitext) for a list
    of Wikipedia articles.

    Args:
        article_list: List of English Wikipedia article titles.
    """
    return call_r("get_category_history", {"article_list": article_list})


@mcp.tool()
def get_category_recent(article_list: list[str]) -> dict:
    """
    Retrieve the most recent revision metadata and wikitext for a list
    of Wikipedia articles.

    Args:
        article_list: List of English Wikipedia article titles.
    """
    return call_r("get_category_recent", {"article_list": article_list})


@mcp.tool()
def get_category_creation(article_list: list[str]) -> dict:
    """
    Retrieve the creation (first) revision metadata for a list of articles.
    Useful for building article-creation timelines.

    Args:
        article_list: List of English Wikipedia article titles.
    """
    return call_r("get_category_creation", {"article_list": article_list})


@mcp.tool()
def get_subcat_table(
    catname: str,
    replecement: Optional[str] = "_",
) -> dict:
    """
    Retrieve direct subcategories of a Wikipedia category.

    Args:
        catname:     Category name with or without the "Category:" prefix.
        replecement: Character used to replace spaces (default: "_").
    """
    return call_r("get_subcat_table", {
        "catname": catname,
        "replecement": replecement,
    })


@mcp.tool()
def get_subcat_with_depth(
    catname: str,
    depth: Optional[int] = 1,
    replecement: Optional[str] = "_",
) -> dict:
    """
    Recursively retrieve subcategories up to a given depth.

    Args:
        catname:     Root category name.
        depth:       Number of levels to descend (default: 1).
        replecement: Character used to replace spaces (default: "_").
    """
    return call_r("get_subcat_with_depth", {
        "catname": catname,
        "depth": depth,
        "replecement": replecement,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# GROUPE 2 — Comptage et extraction de citations
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def get_doi_count(text: str) -> dict:
    """
    Count the number of DOIs in a text string.

    Args:
        text: Raw wikitext or any text string.

    Returns:
        {"count": <integer>}
    """
    return call_r("get_doi_count", {"text": text})


@mcp.tool()
def get_ref_count(text: str) -> dict:
    """
    Count the number of <ref>...</ref> tags in a wikitext string.

    Args:
        text: Raw wikitext string.

    Returns:
        {"count": <integer>}
    """
    return call_r("get_ref_count", {"text": text})


@mcp.tool()
def get_url_count(text: str) -> dict:
    """
    Count the number of URLs (http/https) in a text string.

    Args:
        text: Raw wikitext or any text string.

    Returns:
        {"count": <integer>}
    """
    return call_r("get_url_count", {"text": text})


@mcp.tool()
def get_isbn_count(text: str) -> dict:
    """
    Count the number of ISBNs in a wikitext string.

    Args:
        text: Raw wikitext string.

    Returns:
        {"count": <integer>}
    """
    return call_r("get_isbn_count", {"text": text})


@mcp.tool()
def get_hyperlink_count(text: str) -> dict:
    """
    Count the number of [[...]] Wikipedia hyperlinks in a wikitext string.

    Args:
        text: Raw wikitext string.

    Returns:
        {"count": <integer>}
    """
    return call_r("get_hyperlink_count", {"text": text})


@mcp.tool()
def get_any_count(text: str, regexp: str) -> dict:
    """
    Count matches of a custom regular expression in a text string.

    Args:
        text:   Text to search.
        regexp: Regular expression string (R-compatible PCRE syntax).

    Returns:
        {"count": <integer>}
    """
    return call_r("get_any_count", {"text": text, "regexp": regexp})


@mcp.tool()
def extract_citations(text: str) -> list:
    """
    Extract all Citation Style 1 (CS1) templates from wikitext.
    Matches {{cite journal}}, {{cite book}}, {{cite web}}, etc.

    Args:
        text: Raw wikitext string.

    Returns:
        List of matched citation template strings.
    """
    return call_r("extract_citations", {"text": text})


@mcp.tool()
def extract_wikihypelinks(text: str) -> list:
    """
    Extract all [[...]] Wikipedia hyperlinks from a wikitext string.

    Args:
        text: Raw wikitext string.

    Returns:
        List of matched hyperlink strings.
    """
    return call_r("extract_wikihypelinks", {"text": text})


@mcp.tool()
def replace_wikihypelinks(text: str) -> dict:
    """
    Replace [[Link|display]] syntax with plain display text in wikitext.

    Args:
        text: Raw wikitext string.

    Returns:
        {"cleaned_text": <string>}
    """
    return call_r("replace_wikihypelinks", {"text": text})


@mcp.tool()
def extract_with_regex(
    article_name: str,
    regexp: str,
    date_limit: Optional[str] = "2024-01-01T00:00:00Z",
) -> dict:
    """
    Extract all matches of a regular expression from the most recent
    revision of a Wikipedia article.

    Built-in regexp patterns:
      DOI:        10\\.\\d{4,9}/[-._;()/:a-z0-9A-Z]+
      PMID:       (?<=(pmid|PMID)\\s?[=:]\\s?)\\d{5,9}
      ISBN:       (?<=(isbn|ISBN)\\s?[=:]?\\s?)[-0-9X ]{13,17}
      URL:        http[s]?://...
      cite all:   \\{\\{[cC]ite.*?\\}\\}
      ref tags:   <ref.*?</ref>

    Args:
        article_name: English Wikipedia article title.
        regexp:       R-compatible PCRE regular expression string.
        date_limit:   Upper date limit in ISO 8601 format.
    """
    return call_r("extract_regex", {
        "article_name": article_name,
        "regexp": regexp,
        "date_limit": date_limit,
    })


@mcp.tool()
def extract_all_regex(
    article_name: str,
    date_limit: Optional[str] = "2024-01-01T00:00:00Z",
) -> dict:
    """
    Apply all built-in regular expressions (DOI, ISBN, PMID, URL,
    hyperlinks, all CS1 types) to the most recent revision of an article.
    Returns a combined table with a 'pattern_name' column.

    Args:
        article_name: English Wikipedia article title.
        date_limit:   Upper date limit in ISO 8601 format.
    """
    return call_r("extract_all_regex", {
        "article_name": article_name,
        "date_limit": date_limit,
    })


@mcp.tool()
def parse_citations(
    article_name: str,
    date_limit: Optional[str] = "2024-01-01T00:00:00Z",
) -> dict:
    """
    Fetch the most recent revision of a Wikipedia article and parse all
    CS1 citations into a structured tidy table.

    Each row contains: art, revid, type (e.g. "journal"), id_cite,
    variable (e.g. "author", "doi", "year"), value.

    Args:
        article_name: English Wikipedia article title.
        date_limit:   Upper date limit in ISO 8601 format.
    """
    return call_r("parse_citations", {
        "article_name": article_name,
        "date_limit": date_limit,
    })


@mcp.tool()
def get_citation_types(
    article_name: str,
    date_limit: Optional[str] = "2024-01-01T00:00:00Z",
) -> dict:
    """
    Count citations by CS1 type (journal, book, web, news, etc.)
    for the most recent revision of an article.

    Args:
        article_name: English Wikipedia article title.
        date_limit:   Upper date limit in ISO 8601 format.
    """
    return call_r("get_citation_types", {
        "article_name": article_name,
        "date_limit": date_limit,
    })


@mcp.tool()
def get_source_type_counts(text: str) -> dict:
    """
    Count CS1 citation types directly from a wikitext string.
    Returns a frequency table (cite_type, Freq).

    Args:
        text: Raw wikitext string.
    """
    return call_r("get_source_type_counts", {"text": text})


@mcp.tool()
def get_sci_score(
    article_name: str,
    date_limit: Optional[str] = "2024-01-01T00:00:00Z",
) -> dict:
    """
    Compute two scientific quality scores for a Wikipedia article:

    - SciScore:  proportion of CS1 citations that are journal citations
                 (range 0–1; higher = more scientific sourcing).
    - SciScore2: ratio of DOIs to <ref> tags
                 (range 0–1; higher = more DOI-backed references).

    Args:
        article_name: English Wikipedia article title.
        date_limit:   Upper date limit in ISO 8601 format.
    """
    return call_r("get_sci_score", {
        "article_name": article_name,
        "date_limit": date_limit,
    })


@mcp.tool()
def get_top_cited_papers(
    article_name: str,
    date_limit: Optional[str] = "2024-01-01T00:00:00Z",
) -> dict:
    """
    Identify the top 40 most-cited DOIs in a Wikipedia article,
    annotated with EuropePMC and CrossRef metadata.

    Args:
        article_name: English Wikipedia article title.
        date_limit:   Upper date limit in ISO 8601 format.
    """
    return call_r("get_top_cited_papers", {
        "article_name": article_name,
        "date_limit": date_limit,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# GROUPE 3 — Annotation DOIs et ISBN
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def annotate_dois_europmc(doi_list: list[str]) -> dict:
    """
    Annotate a list of DOIs using EuropePMC.

    Returns for each DOI: id, source, pmid, pmcid, doi, title,
    authorString, journalTitle, pubYear, pubType, isOpenAccess,
    citedByCount, firstPublicationDate.

    Args:
        doi_list: List of DOI strings (e.g. ["10.1038/nature12373"]).
    """
    return call_r("annotate_doi_europmc", {"doi_list": doi_list})


@mcp.tool()
def annotate_dois_crossref(doi_list: list[str]) -> dict:
    """
    Annotate a list of DOIs using CrossRef.
    Returns bibliographic metadata and CrossRef citation counts.

    Args:
        doi_list: List of DOI strings.
    """
    return call_r("annotate_doi_crossref", {"doi_list": doi_list})


@mcp.tool()
def annotate_dois_altmetric(doi_list: list[str]) -> dict:
    """
    Annotate a list of DOIs using Altmetric.
    Returns social-media and news attention scores
    (tweets, Facebook, news mentions, Altmetric score, etc.).

    Args:
        doi_list: List of DOI strings.
    """
    return call_r("annotate_doi_altmetric", {"doi_list": doi_list})


@mcp.tool()
def annotate_dois_bibtex(doi_list: list[str]) -> dict:
    """
    Retrieve BibTeX entries for a list of DOIs via CrossRef.

    Args:
        doi_list: List of DOI strings.

    Returns:
        {"bibtex_entries": [<bibtex string>, ...]}
    """
    return call_r("annotate_doi_bibtex", {"doi_list": doi_list})


@mcp.tool()
def annotate_isbn_google(isbn: str) -> dict:
    """
    Retrieve book metadata for a single ISBN using the Google Books API.
    Returns title, publisher, publishedDate, description, categories,
    and authors.

    Args:
        isbn: ISBN-10 or ISBN-13 string (hyphens are stripped automatically).
    """
    return call_r("annotate_isbn_google", {"isbn": isbn})


@mcp.tool()
def annotate_isbn_openlib(isbn: str) -> dict:
    """
    Retrieve book metadata for a single ISBN using the Open Library API.

    Args:
        isbn: ISBN-10 or ISBN-13 string.
    """
    return call_r("annotate_isbn_openlib", {"isbn": isbn})


@mcp.tool()
def annotate_isbns_altmetric(isbn_list: list[str]) -> dict:
    """
    Retrieve Altmetric attention scores for a list of ISBNs.

    Args:
        isbn_list: List of ISBN strings.
    """
    return call_r("annotate_isbn_altmetric", {"isbn_list": isbn_list})


# ═══════════════════════════════════════════════════════════════════════════════
# GROUPE 4 — Visualisations (PNG base64)
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def plot_article_creation(
    article_list: list[str],
    title: Optional[str] = "Article creation over time",
    cumsum: Optional[bool] = True,
) -> dict:
    """
    Generate a cumulative (or annual) article-creation timeline plot.
    Returns a base64-encoded PNG image.

    Args:
        article_list: List of English Wikipedia article titles.
        title:        Plot title.
        cumsum:       If True (default) plot cumulative counts;
                      if False plot annual counts.
    """
    return call_r("plot_article_creation", {
        "article_list": article_list,
        "title": title,
        "cumsum": cumsum,
    })


@mcp.tool()
def plot_static_timeline(article_list: list[str]) -> dict:
    """
    Generate a static labelled timeline of article creation dates.
    Returns a base64-encoded PNG image.

    Args:
        article_list: List of English Wikipedia article titles.
    """
    return call_r("plot_static_timeline", {"article_list": article_list})


@mcp.tool()
def plot_citation_distribution(article_list: list[str]) -> dict:
    """
    Generate a boxplot showing the distribution of citation-type counts
    (journal, news, web, book) across a set of articles.
    Returns a base64-encoded PNG image.

    Args:
        article_list: List of English Wikipedia article titles.
    """
    return call_r("plot_citation_distribution", {"article_list": article_list})


@mcp.tool()
def plot_page_edits(
    article_name: str,
    start: Optional[str] = "2020010100",
    end: Optional[str] = "2024010100",
) -> dict:
    """
    Generate a weekly edit-count area chart for a Wikipedia article.
    Returns a base64-encoded PNG image.

    Args:
        article_name: English Wikipedia article title.
        start:        Start date in YYYYMMDDHH format (default: "2020010100").
        end:          End date in YYYYMMDDHH format (default: "2024010100").
    """
    return call_r("plot_page_edits", {
        "article_name": article_name,
        "start": start,
        "end": end,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# Entrée principale
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Transport stdio par défaut — compatible Claude Code et Claude Desktop.
    # Pour HTTP : uv run fastmcp run server.py --transport streamable-http --port 8000
    mcp.run()
