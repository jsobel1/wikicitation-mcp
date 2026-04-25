# server.py
# MCP server for the wikilite R package.
# Exposes all exported functions as MCP tools.
#
# Launch:
#   uv run python server.py                         <- stdio (Claude Code / Desktop)
#   uv run fastmcp run server.py \
#     --transport streamable-http --port 8000       <- HTTP (claude.ai)

from __future__ import annotations

from typing import Optional
from fastmcp import FastMCP
from r_bridge import call_r

# -- Server initialisation ----------------------------------------------------

mcp = FastMCP(
    name="wikilite",
    version="0.2.0",
    description=(
        "Retrieve and analyse Wikipedia article revision history, "
        "extract and count citations (DOIs, ISBNs, PMIDs, URLs, hyperlinks), "
        "annotate DOIs via EuropePMC / CrossRef / Altmetric, "
        "compute scientific quality metrics (SciScore), "
        "track revert-based edit trends, "
        "and generate static and interactive visualisations — "
        "all powered by the wikilite R package."
    ),
)


# =============================================================================
# GROUP 1 -- Wikipedia history & metadata
# =============================================================================

@mcp.tool()
def get_article_history(
    article_name: str,
    date_limit: Optional[str] = "2024-01-01T00:00:00Z",
) -> dict:
    """
    Retrieve the full revision history of a Wikipedia article.

    Returns a table of all revisions with columns: art, revid, parentid,
    user, userid, timestamp, size, comment.
    Raw wikitext is excluded for performance — use get_article_recent
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
def get_tables_all(
    article_name: str,
    date_limit: Optional[str] = "2024-01-01T00:00:00Z",
) -> dict:
    """
    Retrieve the initial revision, most recent revision, full history,
    and article info for a Wikipedia article in a single call.

    Returns a dict with keys: initial, recent, history, info.

    Args:
        article_name: English Wikipedia article title.
        date_limit:   Upper date limit in ISO 8601 format.
    """
    return call_r("get_tables_all", {
        "article_name": article_name,
        "date_limit": date_limit,
    })


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
def get_pages_in_cat_table(category: str) -> dict:
    """
    Retrieve a structured table of pages in a Wikipedia category,
    including page IDs and namespaces.

    Args:
        category: Wikipedia category name.
    """
    return call_r("get_pages_in_cat_table", {"category": category})


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
def get_subcat_multiple(catname_list: list[str]) -> dict:
    """
    Retrieve subcategories for multiple Wikipedia categories at once.

    Args:
        catname_list: List of Wikipedia category names.
    """
    return call_r("get_subcat_multiple", {"catname_list": catname_list})


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


@mcp.tool()
def get_page_in_cat_multiple(catname_list: list[str]) -> dict:
    """
    Retrieve all article titles for multiple Wikipedia categories at once.

    Args:
        catname_list: List of Wikipedia category names.
    """
    return call_r("get_page_in_cat_multiple", {"catname_list": catname_list})


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


# =============================================================================
# GROUP 2 -- Citation counting, extraction & quality metrics
# =============================================================================

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
def parse_cite_type(text: str) -> dict:
    """
    Parse a single Citation Style 1 template string and return the
    citation type and key-value fields.

    Args:
        text: A single CS1 template string
              (e.g. "{{cite journal |author=... |doi=...}}").

    Returns:
        Dict with citation type and field values.
    """
    return call_r("parse_cite_type", {"text": text})


@mcp.tool()
def extract_with_regex(
    article_name: str,
    regexp: str,
    date_limit: Optional[str] = "2024-01-01T00:00:00Z",
) -> dict:
    """
    Extract all matches of a regular expression from the most recent
    revision of a Wikipedia article.

    Built-in regexp patterns available in wikilite (via pkg.env):
      DOI:      10\\.\\d{4,9}/[-._;()/:a-z0-9A-Z]+
      PMID:     (?<=(pmid|PMID)\\s?[=:]\\s?)\\d{5,9}
      ISBN:     (?<=(isbn|ISBN)\\s?[=:]?\\s?)[-0-9X ]{13,17}
      URL:      http[s]?://...
      cite all: \\{\\{[cC]ite.*?\\}\\}
      ref tags: <ref.*?</ref>

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
def parse_all_citations(
    article_name: str,
    date_limit: Optional[str] = "2024-01-01T00:00:00Z",
) -> dict:
    """
    Full structured parse of all CS1 citation templates in an article into
    a long tidy table with one row per citation field.

    Columns: art, revid, cite_type, id_cite, variable, value.

    Args:
        article_name: English Wikipedia article title.
        date_limit:   Upper date limit in ISO 8601 format.
    """
    return call_r("parse_all_citations", {
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
                 (range 0-1; higher = more scientific sourcing).
    - SciScore2: ratio of DOIs to <ref> tags
                 (range 0-1; higher = more DOI-backed references).

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


@mcp.tool()
def get_revert_counts(
    start: Optional[str] = "2024-01-01",
    end: Optional[str] = "2024-12-31",
) -> dict:
    """
    Retrieve the count of revert-tagged edits (undo / rollback) for all
    English Wikipedia articles in the given date window, sourced from the
    Wikitrends module.

    Returns articles ranked by total revert count (descending), filtered to
    those with at least one revert.

    Args:
        start: Start date in YYYY-MM-DD format (default: "2024-01-01").
        end:   End date in YYYY-MM-DD format (default: "2024-12-31").
    """
    return call_r("get_revert_counts", {"start": start, "end": end})


# =============================================================================
# GROUP 3 -- DOI & ISBN annotation
# =============================================================================

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

    Requires rAltmetric to be installed:
      remotes::install_github("ropensci/rAltmetric")

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

    Requires rAltmetric to be installed:
      remotes::install_github("ropensci/rAltmetric")

    Args:
        isbn_list: List of ISBN strings.
    """
    return call_r("annotate_isbn_altmetric", {"isbn_list": isbn_list})


# =============================================================================
# GROUP 4 -- Static visualisations (base64-encoded PNG)
# =============================================================================

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
def plot_top_source(
    article_name: str,
    source_type: Optional[str] = "publisher",
    date_limit: Optional[str] = "2024-01-01T00:00:00Z",
) -> dict:
    """
    Generate a bar chart of the top 20 values for a citation field
    (e.g. publisher, journal, author) in a Wikipedia article.
    Returns a base64-encoded PNG image.

    Args:
        article_name: English Wikipedia article title.
        source_type:  Citation field to rank (default: "publisher").
                      Common values: "publisher", "journal", "author",
                      "year", "accessdate".
        date_limit:   Upper date limit in ISO 8601 format.
    """
    return call_r("plot_top_source", {
        "article_name": article_name,
        "source_type": source_type,
        "date_limit": date_limit,
    })


@mcp.tool()
def plot_page_views(
    article_name: str,
    start: Optional[str] = "2020010100",
    end: Optional[str] = "2024010100",
) -> dict:
    """
    Generate a daily page-view area chart for a Wikipedia article,
    sourced from the Wikimedia pageviews REST API.
    Returns a base64-encoded PNG image.

    Args:
        article_name: English Wikipedia article title.
        start:        Start date in YYYYMMDDHH format (default: "2020010100").
        end:          End date in YYYYMMDDHH format (default: "2024010100").
    """
    return call_r("plot_page_views", {
        "article_name": article_name,
        "start": start,
        "end": end,
    })


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


# =============================================================================
# GROUP 5 -- Interactive visualisations (self-contained HTML)
# =============================================================================

@mcp.tool()
def plot_interactive_timeline(
    article_list: list[str],
    date_limit: Optional[str] = "2024-01-01T00:00:00Z",
    color_by: Optional[str] = "sciscore",
) -> dict:
    """
    Generate an interactive Plotly Gantt-style timeline showing the edit
    lifetime of each Wikipedia article as a horizontal bar.

    Hover text includes creation date, first editor, and byte sizes.
    Returns a self-contained HTML string that can be saved as .html and
    opened in any browser.

    Args:
        article_list: List of English Wikipedia article titles.
        date_limit:   Upper date limit in ISO 8601 format.
        color_by:     Colour scheme — "sciscore" (default), "size", or "none".

    Returns:
        {"html": "<full self-contained HTML>", "format": "html", ...}
    """
    return call_r("plot_interactive_timeline", {
        "article_list": article_list,
        "date_limit": date_limit,
        "color_by": color_by,
    })


@mcp.tool()
def plot_publication_network(
    article_list: list[str],
    date_limit: Optional[str] = "2024-01-01T00:00:00Z",
    top_n_dois: Optional[int] = 50,
    min_wiki_count: Optional[int] = 2,
    annotate: Optional[bool] = False,
) -> dict:
    """
    Build an interactive bipartite network linking Wikipedia articles
    (blue squares) to the DOIs they cite (orange circles).

    Edge direction: article -> cited publication.
    Node size reflects citation degree.
    Clicking any node opens the Wikipedia or DOI URL in a new tab.
    Returns a self-contained HTML string.

    Args:
        article_list:   List of English Wikipedia article titles.
        date_limit:     Upper date limit in ISO 8601 format.
        top_n_dois:     Maximum number of publication nodes (default: 50).
        min_wiki_count: Minimum number of articles that must cite a DOI
                        for it to appear (default: 2).
        annotate:       If True, enrich publication labels with EuropePMC
                        paper titles (slower; requires network).
    """
    return call_r("plot_publication_network", {
        "article_list": article_list,
        "date_limit": date_limit,
        "top_n_dois": top_n_dois,
        "min_wiki_count": min_wiki_count,
        "annotate": annotate,
    })


@mcp.tool()
def plot_cocitation_network(
    article_list: list[str],
    date_limit: Optional[str] = "2024-01-01T00:00:00Z",
    min_shared_dois: Optional[int] = 1,
) -> dict:
    """
    Build an interactive article-article co-citation network.
    An edge between two articles means they share at least
    min_shared_dois common DOI citations.

    Edge thickness scales with shared DOI count.
    Hovering over an edge lists the top shared DOIs.
    Returns a self-contained HTML string, or a message if no pairs qualify.

    Args:
        article_list:    List of English Wikipedia article titles.
        date_limit:      Upper date limit in ISO 8601 format.
        min_shared_dois: Minimum shared DOIs for an edge (default: 1).
    """
    return call_r("plot_cocitation_network", {
        "article_list": article_list,
        "date_limit": date_limit,
        "min_shared_dois": min_shared_dois,
    })


@mcp.tool()
def plot_wikilink_network(
    article_list: list[str],
    date_limit: Optional[str] = "2024-01-01T00:00:00Z",
    only_internal: Optional[bool] = True,
    top_n_links: Optional[int] = 80,
) -> dict:
    """
    Build an interactive directed network of [[...]] wikilinks between
    Wikipedia articles.

    Input articles appear as blue squares; linked articles as grey ellipses.
    Node size reflects in-degree (incoming links).
    Clicking any node opens the Wikipedia article in a new tab.
    Returns a self-contained HTML string, or a message if no links are found.

    Args:
        article_list:  List of English Wikipedia article titles.
        date_limit:    Upper date limit in ISO 8601 format.
        only_internal: If True (default), show only links between articles
                       in article_list. If False, include top external targets.
        top_n_links:   Maximum number of external link targets when
                       only_internal is False (default: 80).
    """
    return call_r("plot_wikilink_network", {
        "article_list": article_list,
        "date_limit": date_limit,
        "only_internal": only_internal,
        "top_n_links": top_n_links,
    })


# =============================================================================
# Entry point
# =============================================================================

if __name__ == "__main__":
    # Default transport: stdio (compatible with Claude Code and Claude Desktop).
    # For HTTP: uv run fastmcp run server.py --transport streamable-http --port 8000
    mcp.run()
