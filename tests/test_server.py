"""Tests for server.py -- tool registry, input validation and delegation.

The server runs in-process through a FastMCP client; the wiki_api /
citation_utils / annotate_utils layers are patched, so no network is used.
"""
import asyncio
from unittest.mock import patch

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

import server

EXPECTED_TOOLS = {
    # history & metadata
    "get_article_history", "get_article_recent", "get_article_initial",
    "get_article_info", "get_tables_all",
    # categories
    "get_category_pages", "get_pages_in_cat_table", "get_subcat_table",
    "get_subcat_multiple", "get_subcat_with_depth", "get_page_in_cat_multiple",
    "get_category_history", "get_category_recent", "get_category_creation",
    # counting / extraction / parsing
    "get_doi_count", "get_ref_count", "get_url_count", "get_isbn_count",
    "get_hyperlink_count", "get_any_count", "extract_citations",
    "extract_wikihypelinks", "replace_wikihypelinks", "parse_cite_type",
    "extract_with_regex", "extract_all_regex", "parse_citations",
    "parse_all_citations", "get_citation_types", "get_source_type_counts",
    # quality / trends
    "get_sci_score", "get_top_cited_papers", "get_revert_counts",
    # annotation
    "annotate_dois_europmc", "annotate_dois_crossref", "annotate_dois_bibtex",
    "annotate_isbn_google", "annotate_isbn_openlib",
}


def call(name: str, args: dict):
    async def _run():
        async with Client(server.mcp) as c:
            return await c.call_tool(name, args)
    return asyncio.run(_run())


def test_tool_registry_is_exactly_the_documented_set():
    async def _names():
        async with Client(server.mcp) as c:
            return {t.name for t in await c.list_tools()}
    names = asyncio.run(_names())
    assert names == EXPECTED_TOOLS
    assert len(names) == 38


def test_no_altmetric_or_sciscore2_tools():
    assert not any("altmetric" in n or "sci_score2" in n for n in EXPECTED_TOOLS)


def test_server_has_no_r_dependency():
    import importlib.util
    assert importlib.util.find_spec("r_bridge") is None


def test_count_tools_run_without_network():
    res = call("get_doi_count", {"text": "see 10.1038/nature02260 and 10.1126/science.1195262"})
    assert res.data["count"] == 2


def test_get_any_count_uses_regexp_argument():
    res = call("get_any_count", {"text": "aXbXc", "regexp": "X"})
    assert res.data["count"] == 2


def test_delegation_passes_lang_and_date():
    with patch("server.citation_utils.get_sci_score",
               return_value={"sci_score": 0.5}) as m:
        call("get_sci_score", {"article_name": "Aspirine", "lang": "fr",
                               "date_limit": "2024-01-01"})
    m.assert_called_once_with("Aspirine", "2024-01-01T23:59:59Z", lang="fr")


def test_default_date_is_none_meaning_now():
    with patch("server.wiki_api.get_article_recent",
               return_value={"metadata": {}, "wikitext": ""}) as m:
        call("get_article_recent", {"article_name": "Zeitgeber"})
    m.assert_called_once_with("Zeitgeber", None, lang="en")


@pytest.mark.parametrize("name,args,fragment", [
    ("get_article_info", {"article_name": ""}, "non-empty"),
    ("get_article_info", {"article_name": "X", "lang": "en.evil.com/"}, "language code"),
    ("get_article_recent", {"article_name": "X", "date_limit": "yesterday"}, "ISO 8601"),
    ("get_any_count", {"text": "a", "regexp": "("}, "invalid regexp"),
    ("get_any_count", {"text": "a", "regexp": "a" * 501}, "too long"),
    ("annotate_dois_crossref", {"doi_list": ["not-a-doi"]}, "not a DOI"),
    ("annotate_dois_crossref", {"doi_list": ["10.1234/x"] * 201}, "max 200"),
    ("annotate_isbn_openlib", {"isbn": "../../etc/passwd"}, "not an ISBN"),
    ("get_category_history", {"article_list": ["A"] * 101}, "max 100"),
    ("get_subcat_with_depth", {"catname": "C", "depth": 99}, "between 1 and 5"),
    ("get_revert_counts", {"start": "2024-02-01", "end": "2024-01-01"}, "not be after"),
])
def test_validation_rejects_bad_input(name, args, fragment):
    with pytest.raises(ToolError) as exc:
        call(name, args)
    assert fragment in str(exc.value)


def test_oversized_text_rejected():
    with pytest.raises(ToolError):
        call("get_doi_count", {"text": "a" * (server.MAX_TEXT_CHARS + 1)})


def test_revert_counts_defaults_to_recent_week():
    with patch("server.wiki_api.get_revert_counts", return_value=[]) as m:
        call("get_revert_counts", {})
    start, end = m.call_args.args
    assert (__import__("datetime").date.fromisoformat(end)
            - __import__("datetime").date.fromisoformat(start)).days == 7


def test_main_dispatches_transport():
    with patch.object(server.mcp, "run") as run:
        server.main([])
        run.assert_called_once_with()
        run.reset_mock()
        server.main(["--transport", "streamable-http", "--port", "9001"])
        run.assert_called_once_with(
            transport="streamable-http", host="127.0.0.1", port=9001
        )
