# server.py
# MCP server exposing Wikipedia citation-science tools.
# Pure Python — no R dependency.
#
# Launch:
#   uv run python server.py                         <- stdio (Claude Code / Desktop)
#   uv run fastmcp run server.py \
#     --transport streamable-http --port 8000       <- HTTP (claude.ai)

from __future__ import annotations

from typing import Optional
from fastmcp import FastMCP

import wiki_api
import citation_utils
import annotate_utils

# -- Server initialisation ----------------------------------------------------

mcp = FastMCP(
    name="wikilite",
    version="0.3.0",
)


# =============================================================================
# GROUP 1 -- Wikipedia history & metadata
# =============================================================================

@mcp.tool()
def get_article_history(
    article_name: str,
    date_limit: Optional[str] = "2024-01-01T00:00:00Z",
) -> list:
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
    return wiki_api.get_article_history(article_name, date_limit)


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
    return wiki_api.get_article_recent(article_name, date_limit)


@mcp.tool()
def get_article_initial(article_name: str) -> dict:
    """
    Retrieve the very first (creation) revision of a Wikipedia article,
    including its wikitext.

    Args:
        article_name: English Wikipedia article title.
    """
    return wiki_api.get_article_initial(article_name)


@mcp.tool()
def get_article_info(article_name: str) -> dict:
    """
    Retrieve current metadata for a Wikipedia article:
    page ID, title, and byte length.

    Args:
        article_name: English Wikipedia article title.
    """
    return wiki_api.get_article_info(article_name)


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
    return wiki_api.get_tables_all(article_name, date_limit)


@mcp.tool()
def get_category_pages(category: str) -> list:
    """
    List all article titles belonging to a Wikipedia category.
    Filters out user pages and subcategory entries.

    Args:
        category: Wikipedia category name (e.g. "Circadian rhythm").
    """
    return wiki_api.get_category_pages(category)


@mcp.tool()
def get_pages_in_cat_table(category: str) -> list:
    """
    Retrieve a structured table of pages in a Wikipedia category,
    including page IDs and namespaces.

    Args:
        category: Wikipedia category name.
    """
    return wiki_api.get_pages_in_cat_table(category)


@mcp.tool()
def get_subcat_table(
    catname: str,
    replacement: Optional[str] = "_",
) -> list:
    """
    Retrieve direct subcategories of a Wikipedia category.

    Args:
        catname:     Category name with or without the "Category:" prefix.
        replacement: Character used to replace spaces (default: "_").
    """
    return wiki_api.get_subcat_table(catname, replacement)


@mcp.tool()
def get_subcat_multiple(catname_list: list[str]) -> list:
    """
    Retrieve subcategories for multiple Wikipedia categories at once.

    Args:
        catname_list: List of Wikipedia category names.
    """
    return wiki_api.get_subcat_multiple(catname_list)


@mcp.tool()
def get_subcat_with_depth(
    catname: str,
    depth: Optional[int] = 1,
    replacement: Optional[str] = "_",
) -> list:
    """
    Recursively retrieve subcategories up to a given depth.

    Args:
        catname:     Root category name.
        depth:       Number of levels to descend (default: 1).
        replacement: Character used to replace spaces (default: "_").
    """
    return wiki_api.get_subcat_with_depth(catname, depth, replacement)


@mcp.tool()
def get_page_in_cat_multiple(catname_list: list[str]) -> list:
    """
    Retrieve all article titles for multiple Wikipedia categories at once.

    Args:
        catname_list: List of Wikipedia category names.
    """
    return wiki_api.get_page_in_cat_multiple(catname_list)


@mcp.tool()
def get_category_history(article_list: list[str]) -> list:
    """
    Retrieve the full revision history (without wikitext) for a list
    of Wikipedia articles.

    Args:
        article_list: List of English Wikipedia article titles.
    """
    return wiki_api.get_category_history(article_list)


@mcp.tool()
def get_category_recent(
    article_list: list[str],
    date_limit: Optional[str] = "2024-01-01T00:00:00Z",
) -> dict:
    """
    Retrieve the most recent revision metadata and wikitext for a list
    of Wikipedia articles.

    Args:
        article_list: List of English Wikipedia article titles.
        date_limit:   Upper date limit in ISO 8601 format.
    """
    return wiki_api.get_category_recent(article_list, date_limit)


@mcp.tool()
def get_category_creation(article_list: list[str]) -> list:
    """
    Retrieve the creation (first) revision metadata for a list of articles.
    Useful for building article-creation timelines.

    Args:
        article_list: List of English Wikipedia article titles.
    """
    return wiki_api.get_category_creation(article_list)


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
    return {"count": citation_utils.get_doi_count(text)}


@mcp.tool()
def get_ref_count(text: str) -> dict:
    """
    Count the number of <ref>...</ref> tags in a wikitext string.

    Args:
        text: Raw wikitext string.

    Returns:
        {"count": <integer>}
    """
    return {"count": citation_utils.get_ref_count(text)}


@mcp.tool()
def get_url_count(text: str) -> dict:
    """
    Count the number of URLs (http/https) in a text string.

    Args:
        text: Raw wikitext or any text string.

    Returns:
        {"count": <integer>}
    """
    return {"count": citation_utils.get_url_count(text)}


@mcp.tool()
def get_isbn_count(text: str) -> dict:
    """
    Count the number of ISBNs in a wikitext string.

    Args:
        text: Raw wikitext string.

    Returns:
        {"count": <integer>}
    """
    return {"count": citation_utils.get_isbn_count(text)}


@mcp.tool()
def get_hyperlink_count(text: str) -> dict:
    """
    Count the number of [[...]] Wikipedia hyperlinks in a wikitext string.

    Args:
        text: Raw wikitext string.

    Returns:
        {"count": <integer>}
    """
    return {"count": citation_utils.get_hyperlink_count(text)}


@mcp.tool()
def get_any_count(text: str, regexp: str) -> dict:
    """
    Count matches of a custom regular expression in a text string.

    Args:
        text:   Text to search.
        regexp: Regular expression string (Python re syntax).

    Returns:
        {"count": <integer>}
    """
    return {"count": citation_utils.get_any_count(text, regexp)}


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
    return citation_utils.extract_citations(text)


@mcp.tool()
def extract_wikihypelinks(text: str) -> list:
    """
    Extract all [[...]] Wikipedia hyperlinks from a wikitext string.

    Args:
        text: Raw wikitext string.

    Returns:
        List of matched hyperlink strings.
    """
    return citation_utils.extract_wikihyperlinks(text)


@mcp.tool()
def replace_wikihypelinks(text: str) -> dict:
    """
    Replace [[Link|display]] syntax with plain display text in wikitext.

    Args:
        text: Raw wikitext string.

    Returns:
        {"cleaned_text": <string>}
    """
    return {"cleaned_text": citation_utils.replace_wikihyperlinks(text)}


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
    return citation_utils.parse_cite_type(text)


@mcp.tool()
def extract_with_regex(
    article_name: str,
    regexp: str,
    date_limit: Optional[str] = "2024-01-01T00:00:00Z",
) -> list:
    """
    Extract all matches of a regular expression from the most recent
    revision of a Wikipedia article.

    Built-in regexp patterns (Python re syntax):
      DOI:      10\\.\\d{4,9}/[-._;()/:a-zA-Z0-9]+
      PMID:     (?:pmid|PMID)\\s*[=:]\\s*(\\d{5,9})
      ISBN:     (?i)\\bisbn\\s*[=:]?\\s*([-0-9X ]{9,18})
      URL:      https?://[^\\s\\]<>"...]+
      cite all: \\{\\{[Cc]ite\\b[^{}]*\\}\\}
      ref tags: <ref.*?</ref>

    Args:
        article_name: English Wikipedia article title.
        regexp:       Python re regular expression string.
        date_limit:   Upper date limit in ISO 8601 format.
    """
    return citation_utils.extract_with_regex(article_name, regexp, date_limit)


@mcp.tool()
def extract_all_regex(
    article_name: str,
    date_limit: Optional[str] = "2024-01-01T00:00:00Z",
) -> list:
    """
    Apply all built-in regular expressions (DOI, ISBN, PMID, URL,
    hyperlinks, all CS1 types) to the most recent revision of an article.
    Returns a combined table with a 'pattern_name' column.

    Args:
        article_name: English Wikipedia article title.
        date_limit:   Upper date limit in ISO 8601 format.
    """
    return citation_utils.extract_all_regex(article_name, date_limit)


@mcp.tool()
def parse_citations(
    article_name: str,
    date_limit: Optional[str] = "2024-01-01T00:00:00Z",
) -> list:
    """
    Fetch the most recent revision of a Wikipedia article and parse all
    CS1 citations into a structured tidy table.

    Each row contains: art, revid, cite_type (e.g. "journal"), id_cite,
    doi, author, year, title.

    Args:
        article_name: English Wikipedia article title.
        date_limit:   Upper date limit in ISO 8601 format.
    """
    return citation_utils.parse_citations(article_name, date_limit)


@mcp.tool()
def parse_all_citations(
    article_name: str,
    date_limit: Optional[str] = "2024-01-01T00:00:00Z",
) -> list:
    """
    Full structured parse of all CS1 citation templates in an article into
    a long tidy table with one row per citation field.

    Columns: art, revid, cite_type, id_cite, variable, value.

    Args:
        article_name: English Wikipedia article title.
        date_limit:   Upper date limit in ISO 8601 format.
    """
    return citation_utils.parse_all_citations(article_name, date_limit)


@mcp.tool()
def get_citation_types(
    article_name: str,
    date_limit: Optional[str] = "2024-01-01T00:00:00Z",
) -> list:
    """
    Count citations by CS1 type (journal, book, web, news, etc.)
    for the most recent revision of an article.

    Args:
        article_name: English Wikipedia article title.
        date_limit:   Upper date limit in ISO 8601 format.
    """
    return citation_utils.get_citation_types(article_name, date_limit)


@mcp.tool()
def get_source_type_counts(text: str) -> list:
    """
    Count CS1 citation types directly from a wikitext string.
    Returns a frequency table with keys cite_type and count.

    Args:
        text: Raw wikitext string.
    """
    return citation_utils.get_source_type_counts(text)


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
    return citation_utils.get_sci_score(article_name, date_limit)


@mcp.tool()
def get_top_cited_papers(
    article_name: str,
    date_limit: Optional[str] = "2024-01-01T00:00:00Z",
) -> list:
    """
    Identify the top 40 most-cited DOIs in a Wikipedia article,
    annotated with EuropePMC metadata.

    Args:
        article_name: English Wikipedia article title.
        date_limit:   Upper date limit in ISO 8601 format.
    """
    return citation_utils.get_top_cited_papers(article_name, date_limit)


@mcp.tool()
def get_revert_counts(
    start: Optional[str] = "2024-01-01",
    end: Optional[str] = "2024-12-31",
) -> list:
    """
    Retrieve the count of revert-tagged edits (undo / rollback) for all
    English Wikipedia articles in the given date window.

    Returns articles ranked by total revert count (descending), filtered to
    those with at least one revert.

    Note: limited to the Wikipedia recentchanges retention window (~30 days).

    Args:
        start: Start date in YYYY-MM-DD format (default: "2024-01-01").
        end:   End date in YYYY-MM-DD format (default: "2024-12-31").
    """
    return wiki_api.get_revert_counts(start, end)


# =============================================================================
# GROUP 3 -- DOI & ISBN annotation
# =============================================================================

@mcp.tool()
def annotate_dois_europmc(doi_list: list[str]) -> list:
    """
    Annotate a list of DOIs using EuropePMC.

    Returns for each DOI: id, source, pmid, pmcid, doi, title,
    authorString, journalTitle, pubYear, pubType, isOpenAccess,
    citedByCount, firstPublicationDate.

    Args:
        doi_list: List of DOI strings (e.g. ["10.1038/nature12373"]).
    """
    return annotate_utils.annotate_dois_europmc(doi_list)


@mcp.tool()
def annotate_dois_crossref(doi_list: list[str]) -> list:
    """
    Annotate a list of DOIs using CrossRef.
    Returns bibliographic metadata and CrossRef citation counts.

    Args:
        doi_list: List of DOI strings.
    """
    return annotate_utils.annotate_dois_crossref(doi_list)


@mcp.tool()
def annotate_dois_altmetric(doi_list: list[str]) -> list:
    """
    Annotate a list of DOIs using Altmetric.
    Returns social-media and news attention scores
    (tweets, Facebook, news mentions, Altmetric score, etc.).

    Args:
        doi_list: List of DOI strings.
    """
    return annotate_utils.annotate_dois_altmetric(doi_list)


@mcp.tool()
def annotate_dois_bibtex(doi_list: list[str]) -> dict:
    """
    Retrieve BibTeX entries for a list of DOIs via CrossRef.

    Args:
        doi_list: List of DOI strings.

    Returns:
        {"bibtex_entries": [<bibtex string>, ...]}
    """
    return annotate_utils.annotate_dois_bibtex(doi_list)


@mcp.tool()
def annotate_isbn_google(isbn: str) -> dict:
    """
    Retrieve book metadata for a single ISBN using the Google Books API.
    Returns title, publisher, publishedDate, description, categories,
    and authors.

    Args:
        isbn: ISBN-10 or ISBN-13 string (hyphens are stripped automatically).
    """
    return annotate_utils.annotate_isbn_google(isbn)


@mcp.tool()
def annotate_isbn_openlib(isbn: str) -> dict:
    """
    Retrieve book metadata for a single ISBN using the Open Library API.

    Args:
        isbn: ISBN-10 or ISBN-13 string.
    """
    return annotate_utils.annotate_isbn_openlib(isbn)


@mcp.tool()
def annotate_isbns_altmetric(isbn_list: list[str]) -> list:
    """
    Retrieve Altmetric attention scores for a list of ISBNs.

    Args:
        isbn_list: List of ISBN strings.
    """
    return annotate_utils.annotate_isbns_altmetric(isbn_list)


# ---------------------------------------------------------------------------
# Entry point — enables  uvx wikicitation-mcp  after PyPI install
# ---------------------------------------------------------------------------

def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
