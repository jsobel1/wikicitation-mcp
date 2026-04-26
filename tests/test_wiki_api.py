# tests/test_wiki_api.py
# Unit tests (mocked httpx) and integration tests for wiki_api.py.

from unittest.mock import MagicMock, patch

import pytest

import wiki_api


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

def _mock_response(data: dict, status_code: int = 200) -> MagicMock:
    m = MagicMock()
    m.status_code = status_code
    m.json.return_value = data
    m.raise_for_status.return_value = None
    return m


def _wiki_pages_response(pages: list[dict], cont: dict | None = None) -> dict:
    """Build a minimal Wikipedia API pages response."""
    r: dict = {"query": {"pages": pages}}
    if cont:
        r["continue"] = cont
    return r


def _wiki_catmembers_response(members: list[dict], cont: dict | None = None) -> dict:
    r: dict = {"query": {"categorymembers": members}}
    if cont:
        r["continue"] = cont
    return r


# ---------------------------------------------------------------------------
# get_article_info — unit tests
# ---------------------------------------------------------------------------

def test_get_article_info_returns_dict():
    payload = _wiki_pages_response([{
        "pageid": 12345, "ns": 0, "title": "Zeitgeber",
        "length": 17000, "lastrevid": 999,
    }])
    with patch("wiki_api.httpx.get", return_value=_mock_response(payload)):
        result = wiki_api.get_article_info("Zeitgeber")
    assert result["title"] == "Zeitgeber"
    assert result["pageid"] == 12345


def test_get_article_info_empty_pages():
    payload = _wiki_pages_response([])
    with patch("wiki_api.httpx.get", return_value=_mock_response(payload)):
        result = wiki_api.get_article_info("NonExistent")
    assert result == {}


# ---------------------------------------------------------------------------
# get_article_history — unit tests
# ---------------------------------------------------------------------------

def test_get_article_history_sorted_oldest_first():
    revisions = [
        {"revid": 2, "parentid": 1, "user": "Bob", "userid": 2,
         "timestamp": "2022-06-01T00:00:00Z", "size": 200, "comment": "edit2"},
        {"revid": 1, "parentid": 0, "user": "Alice", "userid": 1,
         "timestamp": "2021-01-01T00:00:00Z", "size": 100, "comment": "edit1"},
    ]
    payload = _wiki_pages_response([{"pageid": 1, "title": "T", "revisions": revisions}])
    with patch("wiki_api.httpx.get", return_value=_mock_response(payload)):
        rows = wiki_api.get_article_history("T", "2023-01-01T00:00:00Z")
    assert rows[0]["timestamp"] < rows[1]["timestamp"]
    assert rows[0]["revid"] == 1
    assert rows[0]["art"] == "T"


def test_get_article_history_includes_art_field():
    rev = {"revid": 5, "parentid": 4, "user": "Eve", "userid": 5,
           "timestamp": "2022-01-01T00:00:00Z", "size": 500, "comment": ""}
    payload = _wiki_pages_response([{"pageid": 9, "title": "X", "revisions": [rev]}])
    with patch("wiki_api.httpx.get", return_value=_mock_response(payload)):
        rows = wiki_api.get_article_history("X")
    assert rows[0]["art"] == "X"


def test_get_article_history_pagination():
    """Two API pages should be concatenated."""
    page1 = _wiki_pages_response(
        [{"pageid": 1, "title": "T",
          "revisions": [{"revid": 2, "parentid": 1, "user": "B", "userid": 2,
                         "timestamp": "2022-01-02T00:00:00Z", "size": 200, "comment": ""}]}],
        cont={"rvcontinue": "abc", "continue": "||"},
    )
    page2 = _wiki_pages_response(
        [{"pageid": 1, "title": "T",
          "revisions": [{"revid": 1, "parentid": 0, "user": "A", "userid": 1,
                         "timestamp": "2022-01-01T00:00:00Z", "size": 100, "comment": ""}]}],
    )
    responses = iter([_mock_response(page1), _mock_response(page2)])
    with patch("wiki_api.httpx.get", side_effect=lambda *a, **kw: next(responses)):
        rows = wiki_api.get_article_history("T")
    assert len(rows) == 2


# ---------------------------------------------------------------------------
# get_article_recent — unit tests
# ---------------------------------------------------------------------------

def test_get_article_recent_returns_metadata_and_wikitext():
    rev = {
        "revid": 10, "parentid": 9, "user": "Editor", "userid": 7,
        "timestamp": "2023-12-01T00:00:00Z", "size": 5000, "comment": "update",
        "content": "== Wikitext ==\nSome content.",
    }
    payload = _wiki_pages_response([{"pageid": 1, "title": "Art", "revisions": [rev]}])
    with patch("wiki_api.httpx.get", return_value=_mock_response(payload)):
        result = wiki_api.get_article_recent("Art")
    assert result["metadata"]["revid"] == 10
    assert "Wikitext" in result["wikitext"]


def test_get_article_recent_empty():
    payload = _wiki_pages_response([{"pageid": 1, "title": "Art", "revisions": []}])
    with patch("wiki_api.httpx.get", return_value=_mock_response(payload)):
        result = wiki_api.get_article_recent("Art")
    assert result["wikitext"] == ""
    assert result["metadata"] == {}


# ---------------------------------------------------------------------------
# get_article_initial — unit tests
# ---------------------------------------------------------------------------

def test_get_article_initial_returns_first_rev():
    rev = {
        "revid": 1, "parentid": 0, "user": "Creator", "userid": 1,
        "timestamp": "2001-01-01T00:00:00Z", "size": 200, "comment": "created",
        "content": "First version.",
    }
    payload = _wiki_pages_response([{"pageid": 1, "title": "Art", "revisions": [rev]}])
    with patch("wiki_api.httpx.get", return_value=_mock_response(payload)):
        result = wiki_api.get_article_initial("Art")
    assert result["metadata"]["revid"] == 1
    assert result["wikitext"] == "First version."


# ---------------------------------------------------------------------------
# get_category_pages — unit tests
# ---------------------------------------------------------------------------

def test_get_category_pages_filters_subcats():
    members = [
        {"pageid": 1, "ns": 0,  "title": "Article A", "type": "page"},
        {"pageid": 2, "ns": 14, "title": "Category:Sub", "type": "subcat"},
    ]
    payload = _wiki_catmembers_response(members)
    with patch("wiki_api.httpx.get", return_value=_mock_response(payload)):
        pages = wiki_api.get_category_pages("TestCat")
    assert "Article A" in pages
    assert "Category:Sub" not in pages


def test_get_category_pages_empty():
    payload = _wiki_catmembers_response([])
    with patch("wiki_api.httpx.get", return_value=_mock_response(payload)):
        assert wiki_api.get_category_pages("Empty") == []


# ---------------------------------------------------------------------------
# get_subcat_table — unit tests
# ---------------------------------------------------------------------------

def test_get_subcat_table_replacement():
    members = [{"pageid": 5, "ns": 14, "title": "Category:Sleep Science", "type": "subcat"}]
    payload = _wiki_catmembers_response(members)
    with patch("wiki_api.httpx.get", return_value=_mock_response(payload)):
        rows = wiki_api.get_subcat_table("Bio", replacement="_")
    assert rows[0]["title"] == "Category:Sleep_Science"


def test_get_subcat_table_no_replacement():
    members = [{"pageid": 5, "ns": 14, "title": "Category:Sleep Science", "type": "subcat"}]
    payload = _wiki_catmembers_response(members)
    with patch("wiki_api.httpx.get", return_value=_mock_response(payload)):
        rows = wiki_api.get_subcat_table("Bio", replacement=" ")
    assert rows[0]["title"] == "Category:Sleep Science"


# ---------------------------------------------------------------------------
# get_subcat_multiple — unit tests
# ---------------------------------------------------------------------------

def test_get_subcat_multiple_source_category():
    members = [{"pageid": 1, "ns": 14, "title": "Category:Sub", "type": "subcat"}]
    payload = _wiki_catmembers_response(members)
    with patch("wiki_api.httpx.get", return_value=_mock_response(payload)):
        rows = wiki_api.get_subcat_multiple(["CatA", "CatB"])
    sources = {r["source_category"] for r in rows}
    assert "CatA" in sources
    assert "CatB" in sources


# ---------------------------------------------------------------------------
# get_revert_counts — unit tests
# ---------------------------------------------------------------------------

def test_get_revert_counts_aggregates_tags():
    rc_payload = {"query": {"recentchanges": [
        {"title": "Article A"},
        {"title": "Article B"},
        {"title": "Article A"},
    ]}}
    with patch("wiki_api.httpx.get", return_value=_mock_response(rc_payload)):
        rows = wiki_api.get_revert_counts("2024-01-01", "2024-01-31")
    by_title = {r["title"]: r["revert_count"] for r in rows}
    # Each of the 3 tags (mw-reverted, mw-undo, mw-rollback) hits the same mock
    # so counts are multiplied by 3
    assert by_title["Article A"] == 6   # 2 occurrences × 3 tags
    assert by_title["Article B"] == 3   # 1 occurrence × 3 tags


# ---------------------------------------------------------------------------
# Integration tests — require network, no R
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_integration_get_article_info_zeitgeber():
    result = wiki_api.get_article_info("Zeitgeber")
    assert result.get("title") == "Zeitgeber"
    assert "pageid" in result
    assert "length" in result


@pytest.mark.integration
def test_integration_get_article_history_zeitgeber():
    rows = wiki_api.get_article_history("Zeitgeber", "2022-01-01T00:00:00Z")
    assert isinstance(rows, list)
    assert len(rows) > 0
    first = rows[0]
    assert "revid" in first
    assert "user" in first
    assert "timestamp" in first
    assert first["art"] == "Zeitgeber"
    # Sorted oldest first
    assert rows[0]["timestamp"] <= rows[-1]["timestamp"]


@pytest.mark.integration
def test_integration_get_article_recent_zeitgeber():
    result = wiki_api.get_article_recent("Zeitgeber", "2024-01-01T00:00:00Z")
    assert result["wikitext"] != ""
    assert result["metadata"]["art"] == "Zeitgeber"


@pytest.mark.integration
def test_integration_get_article_initial_zeitgeber():
    result = wiki_api.get_article_initial("Zeitgeber")
    assert result["metadata"]["parentid"] == 0
    assert result["wikitext"] != ""


@pytest.mark.integration
def test_integration_get_category_pages_chronobiology():
    pages = wiki_api.get_category_pages("Chronobiology")
    assert isinstance(pages, list)
    assert len(pages) > 0
    assert all(isinstance(p, str) for p in pages)
    # "Zeitgeber" may be in a subcategory; check a stable direct member instead
    assert "Chronobiology" in pages or "Biological rhythm" in pages


@pytest.mark.integration
def test_integration_get_subcat_table_chronobiology():
    rows = wiki_api.get_subcat_table("Chronobiology")
    assert isinstance(rows, list)
    assert len(rows) > 0
    for row in rows:
        assert "title" in row


@pytest.mark.integration
def test_integration_get_category_creation():
    results = wiki_api.get_category_creation(["Zeitgeber", "Melatonin"])
    assert len(results) == 2
    for r in results:
        assert r["parentid"] == 0
