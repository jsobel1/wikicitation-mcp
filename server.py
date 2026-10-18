# server.py
# MCP server exposing Wikipedia citation-science tools.
# Pure Python -- no R dependency.
#
# Launch:
#   uv run python server.py                         <- stdio (Claude Code / Desktop)
#   uv run fastmcp run server.py \
#     --transport streamable-http --port 8000       <- HTTP (claude.ai)

from __future__ import annotations

import datetime as _dt
import re
from typing import Optional

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

import annotate_utils
import citation_utils
import wiki_api

__version__ = "0.5.1"

mcp = FastMCP(
    name="wikicitation",
    version=__version__,
    instructions=(
        "Wikipedia citation-science tools: revision history, category "
        "traversal, citation parsing (en/fr/de/es/it/pt), SciScore, and DOI/ISBN "
        "annotation via EuropePMC, CrossRef, Google Books and Open Library. "
        "Article-level tools default to the current revision; pass date_limit "
        "(ISO 8601) for a historical snapshot and lang for another Wikipedia."
    ),
)

# -- Input limits -------------------------------------------------------------
# Tool arguments come from an LLM (and, indirectly, from whatever text it was
# shown), so every free-form argument is bounded before it reaches a network
# call or a regex engine.

MAX_TEXT_CHARS = 5_000_000
MAX_ARTICLES = 100
MAX_CATEGORIES = 20
MAX_DOIS = 200
MAX_REGEX_LEN = 500
MAX_DEPTH = 5

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}Z)?$")
_DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")
_ISBN_RE = re.compile(r"^[0-9][0-9\- ]{8,16}[0-9Xx]$")


def _text(value: str, name: str = "text") -> str:
    if not isinstance(value, str):
        raise ToolError(f"{name} must be a string")
    if len(value) > MAX_TEXT_CHARS:
        raise ToolError(f"{name} too large ({len(value)} chars; max {MAX_TEXT_CHARS})")
    return value


def _name(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ToolError(f"{name} must be a non-empty string")
    if len(value) > 300:
        raise ToolError(f"{name} too long (max 300 chars)")
    return value.strip()


def _names(values: list[str], name: str, limit: int) -> list[str]:
    if not isinstance(values, list) or not values:
        raise ToolError(f"{name} must be a non-empty list")
    if len(values) > limit:
        raise ToolError(f"{name} has {len(values)} items; max {limit} per call")
    return [_name(v, f"{name}[]") for v in values]


def _lang(value: str) -> str:
    try:
        wiki_api._endpoint(value)  # validates the language-code shape
    except ValueError as exc:
        raise ToolError(str(exc)) from None
    return value


def _date(value: Optional[str], name: str = "date_limit") -> Optional[str]:
    if value is None:
        return None
    if not _DATE_RE.match(value):
        raise ToolError(
            f"{name} must be ISO 8601, e.g. '2024-01-01' or '2024-01-01T00:00:00Z'"
        )
    return value if "T" in value else value + "T23:59:59Z"


def _regex(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ToolError("regexp must be a non-empty string")
    if len(value) > MAX_REGEX_LEN:
        raise ToolError(f"regexp too long (max {MAX_REGEX_LEN} chars)")
    try:
        re.compile(value)
    except re.error as exc:
        raise ToolError(f"invalid regexp: {exc}") from None
    return value


def _dois(values: list[str]) -> list[str]:
    values = _names(values, "doi_list", MAX_DOIS)
    bad = [d for d in values if not _DOI_RE.match(d)]
    if bad:
        raise ToolError(f"not a DOI (expected '10.xxxx/...'): {bad[:5]}")
    return values


def _isbn(value: str) -> str:
    value = _name(value, "isbn")
    if not _ISBN_RE.match(value):
        raise ToolError(f"not an ISBN: {value!r}")
    return value


# =============================================================================
# GROUP 1 -- Wikipedia history & metadata
# =============================================================================

@mcp.tool()
def get_article_history(
    article_name: str,
    date_limit: Optional[str] = None,
    lang: str = "en",
) -> list:
    """
    Retrieve the full revision history of a Wikipedia article.

    Returns one row per revision: art, revid, parentid, user, userid,
    timestamp, size, comment, tags -- sorted oldest first. Wikitext is not
    included; use get_article_recent for that.

    Args:
        article_name: Article title (e.g. "Zeitgeber").
        date_limit:   Upper date bound, ISO 8601 (default: now).
        lang:         Wikipedia language code (default "en").
    """
    return wiki_api.get_article_history(
        _name(article_name, "article_name"), _date(date_limit), lang=_lang(lang)
    )


@mcp.tool()
def get_article_recent(
    article_name: str,
    date_limit: Optional[str] = None,
    lang: str = "en",
) -> dict:
    """
    Retrieve the latest revision of an article (at or before date_limit),
    including its full wikitext. Returns {"metadata": {...}, "wikitext": "..."}.

    Args:
        article_name: Article title.
        date_limit:   Upper date bound, ISO 8601 (default: now).
        lang:         Wikipedia language code (default "en").
    """
    return wiki_api.get_article_recent(
        _name(article_name, "article_name"), _date(date_limit), lang=_lang(lang)
    )


@mcp.tool()
def get_article_initial(article_name: str, lang: str = "en") -> dict:
    """
    Retrieve the first (creation) revision of an article with its wikitext.
    Returns {"metadata": {...}, "wikitext": "..."}.

    Args:
        article_name: Article title.
        lang:         Wikipedia language code (default "en").
    """
    return wiki_api.get_article_initial(
        _name(article_name, "article_name"), lang=_lang(lang)
    )


@mcp.tool()
def get_article_info(article_name: str, lang: str = "en") -> dict:
    """
    Current page metadata: pageid, title, length, last revision id, touched
    timestamp. A non-existent page is reported with "missing": true.

    Args:
        article_name: Article title.
        lang:         Wikipedia language code (default "en").
    """
    return wiki_api.get_article_info(
        _name(article_name, "article_name"), lang=_lang(lang)
    )


@mcp.tool()
def get_tables_all(
    article_name: str,
    date_limit: Optional[str] = None,
    lang: str = "en",
) -> dict:
    """
    Info + initial revision + latest revision + full history in one call.
    Returns {"info", "initial", "recent", "history"}.

    Args:
        article_name: Article title.
        date_limit:   Upper date bound, ISO 8601 (default: now).
        lang:         Wikipedia language code (default "en").
    """
    return wiki_api.get_tables_all(
        _name(article_name, "article_name"), _date(date_limit), lang=_lang(lang)
    )


# =============================================================================
# GROUP 1b -- Categories
# =============================================================================

@mcp.tool()
def get_category_pages(category: str, lang: str = "en") -> list:
    """
    Article titles (namespace 0) directly in a category.

    Args:
        category: Category name, with or without the "Category:" prefix.
        lang:     Wikipedia language code (default "en").
    """
    return wiki_api.get_category_pages(_name(category, "category"), lang=_lang(lang))


@mcp.tool()
def get_pages_in_cat_table(category: str, lang: str = "en") -> list:
    """
    Pages directly in a category as a table (pageid, ns, title, type).

    Args:
        category: Category name.
        lang:     Wikipedia language code (default "en").
    """
    return wiki_api.get_pages_in_cat_table(_name(category, "category"), lang=_lang(lang))


@mcp.tool()
def get_subcat_table(catname: str, replacement: str = "_", lang: str = "en") -> list:
    """
    Direct subcategories of a category.

    Args:
        catname:     Category name.
        replacement: Character substituted for spaces in titles (default "_").
        lang:        Wikipedia language code (default "en").
    """
    return wiki_api.get_subcat_table(
        _name(catname, "catname"), replacement[:1] or "_", lang=_lang(lang)
    )


@mcp.tool()
def get_subcat_multiple(catname_list: list[str], lang: str = "en") -> list:
    """
    Direct subcategories for several categories (rows carry source_category).

    Args:
        catname_list: Category names (max 20).
        lang:         Wikipedia language code (default "en").
    """
    return wiki_api.get_subcat_multiple(
        _names(catname_list, "catname_list", MAX_CATEGORIES), lang=_lang(lang)
    )


@mcp.tool()
def get_subcat_with_depth(
    catname: str,
    depth: int = 1,
    replacement: str = "_",
    lang: str = "en",
) -> list:
    """
    Recursively collect subcategories down to `depth` levels (1-5).

    Args:
        catname:     Root category name.
        depth:       Levels to descend (default 1, max 5).
        replacement: Character substituted for spaces in titles (default "_").
        lang:        Wikipedia language code (default "en").
    """
    if not 1 <= depth <= MAX_DEPTH:
        raise ToolError(f"depth must be between 1 and {MAX_DEPTH}")
    return wiki_api.get_subcat_with_depth(
        _name(catname, "catname"), depth, replacement[:1] or "_", lang=_lang(lang)
    )


@mcp.tool()
def get_page_in_cat_multiple(catname_list: list[str], lang: str = "en") -> list:
    """
    Pages in several categories (rows carry source_category).

    Args:
        catname_list: Category names (max 20).
        lang:         Wikipedia language code (default "en").
    """
    return wiki_api.get_page_in_cat_multiple(
        _names(catname_list, "catname_list", MAX_CATEGORIES), lang=_lang(lang)
    )


@mcp.tool()
def get_category_history(article_list: list[str], lang: str = "en") -> list:
    """
    Full revision history for a list of articles, concatenated.

    Args:
        article_list: Article titles (max 100).
        lang:         Wikipedia language code (default "en").
    """
    return wiki_api.get_category_history(
        _names(article_list, "article_list", MAX_ARTICLES), lang=_lang(lang)
    )


@mcp.tool()
def get_category_recent(
    article_list: list[str],
    date_limit: Optional[str] = None,
    lang: str = "en",
) -> dict:
    """
    Latest revision metadata and wikitext for a list of articles.
    Returns {"metadata": [...], "wikitext": [...]} in input order.

    Args:
        article_list: Article titles (max 100).
        date_limit:   Upper date bound, ISO 8601 (default: now).
        lang:         Wikipedia language code (default "en").
    """
    return wiki_api.get_category_recent(
        _names(article_list, "article_list", MAX_ARTICLES),
        _date(date_limit),
        lang=_lang(lang),
    )


@mcp.tool()
def get_category_creation(article_list: list[str], lang: str = "en") -> list:
    """
    Creation (first revision) metadata for a list of articles.

    Args:
        article_list: Article titles (max 100).
        lang:         Wikipedia language code (default "en").
    """
    return wiki_api.get_category_creation(
        _names(article_list, "article_list", MAX_ARTICLES), lang=_lang(lang)
    )


# =============================================================================
# GROUP 2 -- Citation counting, extraction and parsing
# =============================================================================

@mcp.tool()
def get_doi_count(text: str) -> dict:
    """Count DOIs in a wikitext string. Returns {"count": n}."""
    return {"count": citation_utils.get_doi_count(_text(text))}


@mcp.tool()
def get_ref_count(text: str) -> dict:
    """Count <ref> tags in a wikitext string. Returns {"count": n}."""
    return {"count": citation_utils.get_ref_count(_text(text))}


@mcp.tool()
def get_url_count(text: str) -> dict:
    """Count http(s) URLs in a wikitext string. Returns {"count": n}."""
    return {"count": citation_utils.get_url_count(_text(text))}


@mcp.tool()
def get_isbn_count(text: str) -> dict:
    """Count ISBNs in a wikitext string. Returns {"count": n}."""
    return {"count": citation_utils.get_isbn_count(_text(text))}


@mcp.tool()
def get_hyperlink_count(text: str) -> dict:
    """Count [[wikilinks]] in a wikitext string. Returns {"count": n}."""
    return {"count": citation_utils.get_hyperlink_count(_text(text))}


@mcp.tool()
def get_any_count(text: str, regexp: str) -> dict:
    """
    Count matches of a regular expression in a text. Returns {"count": n}.

    Args:
        text:   Text to search.
        regexp: Python regular expression (max 500 chars).
    """
    return {"count": citation_utils.get_any_count(_text(text), _regex(regexp))}


@mcp.tool()
def extract_citations(text: str) -> list:
    """Return every {{cite ...}} template found in a wikitext string."""
    return citation_utils.extract_citations(_text(text))


@mcp.tool()
def extract_wikihypelinks(text: str) -> list:
    """Return every [[wikilink]] found in a wikitext string."""
    return citation_utils.extract_wikihyperlinks(_text(text))


@mcp.tool()
def replace_wikihypelinks(text: str) -> dict:
    """
    Replace [[Target|Label]] with Label and [[Target]] with Target.
    Returns {"cleaned_text": "..."}.
    """
    return {"cleaned_text": citation_utils.replace_wikihyperlinks(_text(text))}


@mcp.tool()
def parse_cite_type(text: str) -> dict:
    """
    Parse one {{cite ...}} template string.
    Returns {"cite_type": "journal", "fields": {...}}, or {} if none is found.
    """
    return citation_utils.parse_cite_type(_text(text))


@mcp.tool()
def extract_with_regex(
    article_name: str,
    regexp: str,
    date_limit: Optional[str] = None,
    lang: str = "en",
) -> list:
    """
    Apply a regular expression to an article's latest wikitext.

    Args:
        article_name: Article title.
        regexp:       Python regular expression (max 500 chars).
        date_limit:   Upper date bound, ISO 8601 (default: now).
        lang:         Wikipedia language code (default "en").
    """
    return citation_utils.extract_with_regex(
        _name(article_name, "article_name"),
        _regex(regexp),
        _date(date_limit),
        lang=_lang(lang),
    )


@mcp.tool()
def extract_all_regex(
    article_name: str,
    date_limit: Optional[str] = None,
    lang: str = "en",
) -> list:
    """
    Apply all built-in patterns (doi, url, ref, isbn, wikilink, pmid, cite_all)
    to an article's latest wikitext.

    Args:
        article_name: Article title.
        date_limit:   Upper date bound, ISO 8601 (default: now).
        lang:         Wikipedia language code (default "en").
    """
    return citation_utils.extract_all_regex(
        _name(article_name, "article_name"), _date(date_limit), lang=_lang(lang)
    )


@mcp.tool()
def parse_citations(
    article_name: str,
    date_limit: Optional[str] = None,
    lang: str = "en",
) -> list:
    """
    Structured citation table, one row per citation template (doi, isbn, pmid,
    url, title, author, year, journal, publisher, accessdate). Understands the
    native templates of en/fr/de/es/it/pt Wikipedias.

    Args:
        article_name: Article title.
        date_limit:   Upper date bound, ISO 8601 (default: now).
        lang:         Wikipedia language code (default "en").
    """
    return citation_utils.parse_citations(
        _name(article_name, "article_name"), _date(date_limit), lang=_lang(lang)
    )


@mcp.tool()
def parse_all_citations(
    article_name: str,
    date_limit: Optional[str] = None,
    lang: str = "en",
) -> list:
    """
    Long-form citation table, one row per template field (variable, value,
    canonical_field).

    Args:
        article_name: Article title.
        date_limit:   Upper date bound, ISO 8601 (default: now).
        lang:         Wikipedia language code (default "en").
    """
    return citation_utils.parse_all_citations(
        _name(article_name, "article_name"), _date(date_limit), lang=_lang(lang)
    )


@mcp.tool()
def get_citation_types(
    article_name: str,
    date_limit: Optional[str] = None,
    lang: str = "en",
) -> list:
    """
    Count citation templates by canonical type (journal, book, web, news, ...)
    for an article.

    Args:
        article_name: Article title.
        date_limit:   Upper date bound, ISO 8601 (default: now).
        lang:         Wikipedia language code (default "en").
    """
    return citation_utils.get_citation_types(
        _name(article_name, "article_name"), _date(date_limit), lang=_lang(lang)
    )


@mcp.tool()
def get_source_type_counts(text: str, lang: str = "en") -> list:
    """
    Count citation templates by canonical type in a raw wikitext string.

    Args:
        text: Wikitext.
        lang: Wikipedia language code whose templates to recognise (default "en").
    """
    return citation_utils.get_source_type_counts(_text(text), lang=_lang(lang))


# =============================================================================
# GROUP 2b -- Quality metrics and trends
# =============================================================================

@mcp.tool()
def get_sci_score(
    article_name: str,
    date_limit: Optional[str] = None,
    lang: str = "en",
) -> dict:
    """
    SciScore: the fraction of an article's citation templates that cite
    journals (0-1). Returns {"sci_score", "article", "lang", "revid"}.

    Args:
        article_name: Article title.
        date_limit:   Upper date bound, ISO 8601 (default: now).
        lang:         Wikipedia language code (default "en").
    """
    return citation_utils.get_sci_score(
        _name(article_name, "article_name"), _date(date_limit), lang=_lang(lang)
    )


@mcp.tool()
def get_top_cited_papers(
    article_name: str,
    date_limit: Optional[str] = None,
    lang: str = "en",
) -> list:
    """
    The (up to) 40 most-cited DOIs in an article, annotated through EuropePMC
    and ranked by how many times the article cites them (wiki_count).

    Args:
        article_name: Article title.
        date_limit:   Upper date bound, ISO 8601 (default: now).
        lang:         Wikipedia language code (default "en").
    """
    return citation_utils.get_top_cited_papers(
        _name(article_name, "article_name"), _date(date_limit), lang=_lang(lang)
    )


@mcp.tool()
def get_revert_counts(
    start: Optional[str] = None,
    end: Optional[str] = None,
    lang: str = "en",
) -> list:
    """
    Revert-tagged edits (mw-reverted, mw-undo, mw-rollback) per article in a
    date window, most reverted first.

    Wikipedia only keeps recent changes for about 30 days, so older windows
    return partial or empty results. The scan can take a minute or more.

    Args:
        start: First day, YYYY-MM-DD (default: 7 days before `end`).
        end:   Last day, YYYY-MM-DD (default: today, UTC).
        lang:  Wikipedia language code (default "en").
    """
    if end is None:
        end_d = _dt.datetime.now(_dt.timezone.utc).date()
    else:
        if not _DATE_RE.match(end):
            raise ToolError("end must be YYYY-MM-DD")
        end_d = _dt.date.fromisoformat(end[:10])
    if start is None:
        start_d = end_d - _dt.timedelta(days=7)
    else:
        if not _DATE_RE.match(start):
            raise ToolError("start must be YYYY-MM-DD")
        start_d = _dt.date.fromisoformat(start[:10])
    if start_d > end_d:
        raise ToolError("start must not be after end")
    return wiki_api.get_revert_counts(
        start_d.isoformat(), end_d.isoformat(), lang=_lang(lang)
    )


# =============================================================================
# GROUP 3 -- DOI & ISBN annotation
# =============================================================================

@mcp.tool()
def annotate_dois_europmc(doi_list: list[str]) -> list:
    """
    Annotate DOIs through EuropePMC: PMID/PMCID, title, authors, journal, year,
    citation_count, is_open_access. One row per input DOI.

    Args:
        doi_list: DOIs such as "10.1038/nature02260" (max 200).
    """
    return annotate_utils.annotate_dois_europmc(_dois(doi_list))


@mcp.tool()
def annotate_dois_crossref(doi_list: list[str]) -> list:
    """
    Annotate DOIs through CrossRef: title, authors, journal, year, publisher,
    type, is_referenced_by_count, url.

    Args:
        doi_list: DOIs (max 200).
    """
    return annotate_utils.annotate_dois_crossref(_dois(doi_list))


@mcp.tool()
def annotate_dois_bibtex(doi_list: list[str]) -> dict:
    """
    BibTeX entries for DOIs (CrossRef content negotiation).
    Returns {"bibtex_entries": [...]}.

    Args:
        doi_list: DOIs (max 200).
    """
    return annotate_utils.annotate_dois_bibtex(_dois(doi_list))


@mcp.tool()
def annotate_isbn_google(isbn: str) -> dict:
    """
    Book metadata from Google Books for one ISBN. The keyless quota is small;
    set GOOGLE_BOOKS_API_KEY in the server's environment to avoid HTTP 429, or
    use annotate_isbn_openlib instead.

    Args:
        isbn: ISBN-10 or ISBN-13, hyphens allowed.
    """
    return annotate_utils.annotate_isbn_google(_isbn(isbn))


@mcp.tool()
def annotate_isbn_openlib(isbn: str) -> dict:
    """
    Book metadata from Open Library for one ISBN.

    Args:
        isbn: ISBN-10 or ISBN-13, hyphens allowed.
    """
    return annotate_utils.annotate_isbn_openlib(_isbn(isbn))


def main(argv: Optional[list[str]] = None) -> None:
    """Console entry point: stdio by default, or HTTP for claude.ai."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="wikicitation-mcp", description="Wikipedia citation-science MCP server"
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "streamable-http", "sse"],
        default="stdio",
        help="transport protocol (default: stdio)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP bind address")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args(argv)

    if args.transport == "stdio":
        mcp.run()
    else:
        mcp.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
