"""Tests for server.py — all R calls are mocked so no R installation is needed."""
import pytest
from unittest.mock import AsyncMock, patch


# ── Helpers ──────────────────────────────────────────────────────────────────

def _patch_r(return_value):
    return patch("server.call_r_async", new_callable=AsyncMock,
                 return_value=return_value)


# ── Count helpers ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_doi_count_calls_r():
    with _patch_r({"count": 3}) as mock_r:
        from server import get_doi_count
        result = await get_doi_count("text with 10.1038/nature12373")
        mock_r.assert_called_once_with(
            "get_doi_count", {"text": "text with 10.1038/nature12373"}
        )
        assert result["count"] == 3


@pytest.mark.asyncio
async def test_get_ref_count_calls_r():
    with _patch_r({"count": 2}) as mock_r:
        from server import get_ref_count
        result = await get_ref_count("<ref>one</ref> <ref>two</ref>")
        mock_r.assert_called_once_with(
            "get_ref_count",
            {"text": "<ref>one</ref> <ref>two</ref>"}
        )
        assert result["count"] == 2


@pytest.mark.asyncio
async def test_get_url_count_calls_r():
    with _patch_r({"count": 1}) as mock_r:
        from server import get_url_count
        result = await get_url_count("https://example.com")
        mock_r.assert_called_once_with("get_url_count", {"text": "https://example.com"})
        assert result["count"] == 1


@pytest.mark.asyncio
async def test_get_isbn_count_calls_r():
    with _patch_r({"count": 1}) as mock_r:
        from server import get_isbn_count
        result = await get_isbn_count("isbn=978-3-16-148410-0")
        mock_r.assert_called_once_with("get_isbn_count", {"text": "isbn=978-3-16-148410-0"})
        assert result["count"] == 1


@pytest.mark.asyncio
async def test_get_any_count_passes_pattern():
    with _patch_r({"count": 3}) as mock_r:
        from server import get_any_count
        await get_any_count("foo bar foo baz foo", "foo")
        call_args = mock_r.call_args[0]
        assert call_args[1]["pattern"] == "foo"


# ── Quality scores ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_sci_score_returns_float():
    with _patch_r({"sci_score": 0.75}):
        from server import get_sci_score
        result = await get_sci_score("wikitext")
        assert 0.0 <= result["sci_score"] <= 1.0


# ── Article retrieval ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_article_most_recent_returns_dict():
    with _patch_r({"art": "Zeitgeber", "revid": 12345}) as mock_r:
        from server import get_article_most_recent
        result = await get_article_most_recent("Zeitgeber")
        assert isinstance(result, dict)
        mock_r.assert_called_once()


@pytest.mark.asyncio
async def test_get_article_most_recent_passes_lang():
    with _patch_r({}) as mock_r:
        from server import get_article_most_recent
        await get_article_most_recent("COVID-19", lang="fr")
        args = mock_r.call_args[0]
        assert args[1]["lang"] == "fr"


@pytest.mark.asyncio
async def test_get_article_history_passes_date_an():
    with _patch_r([]) as mock_r:
        from server import get_article_history
        await get_article_history("Zeitgeber", date_an="2022-01-01T00:00:00Z")
        args = mock_r.call_args[0]
        assert args[1]["date_an"] == "2022-01-01T00:00:00Z"


@pytest.mark.asyncio
async def test_get_article_info_calls_r():
    with _patch_r({"title": "Zeitgeber", "pageid": 1234}) as mock_r:
        from server import get_article_info
        result = await get_article_info("Zeitgeber")
        mock_r.assert_called_once()
        assert isinstance(result, dict)


# ── Citation tools ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_extract_citations_returns_list():
    with _patch_r(["{{cite journal|author=Smith}}"]):
        from server import extract_citations
        result = await extract_citations("{{cite journal|author=Smith}}")
        assert isinstance(result, list)


@pytest.mark.asyncio
async def test_parse_all_citations_calls_r():
    with _patch_r([{"type": "journal", "variable": "author", "value": "Smith"}]) as mock_r:
        from server import parse_all_citations
        await parse_all_citations("Zeitgeber")
        mock_r.assert_called_once()
        args = mock_r.call_args[0]
        assert args[1]["article_name"] == "Zeitgeber"


@pytest.mark.asyncio
async def test_replace_wikihypelinks_calls_r():
    with _patch_r({"cleaned_text": "Circadian clock"}):
        from server import replace_wikihypelinks
        result = await replace_wikihypelinks("[[Circadian clock]]")
        assert "cleaned_text" in result


@pytest.mark.asyncio
async def test_get_citation_type_counts_calls_r():
    with _patch_r([{"category": "Journal", "count": 14},
                   {"category": "Web",     "count": 5}]) as mock_r:
        from server import get_citation_type_counts
        result = await get_citation_type_counts("Zeitgeber")
        mock_r.assert_called_once_with(
            "get_citation_type_counts",
            {"article_name": "Zeitgeber", "lang": "en", "date_an": None}
        )
        assert isinstance(result, list)


@pytest.mark.asyncio
async def test_get_citation_type_counts_passes_lang():
    with _patch_r([]) as mock_r:
        from server import get_citation_type_counts
        await get_citation_type_counts("COVID-19", lang="fr")
        args = mock_r.call_args[0]
        assert args[1]["lang"] == "fr"


# ── Annotation ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_annotate_dois_passes_list():
    with _patch_r([{"doi": "10.1038/nature12373", "title": "A paper"}]) as mock_r:
        from server import annotate_dois
        doi_list = ["10.1038/nature12373"]
        result = await annotate_dois(doi_list)
        args = mock_r.call_args[0]
        assert args[1]["doi_list"] == doi_list


# ── Category tools ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_category_pages_calls_r():
    with _patch_r(["Zeitgeber", "Sleep deprivation"]) as mock_r:
        from server import get_category_pages
        result = await get_category_pages("Circadian rhythm")
        mock_r.assert_called_once()
        args = mock_r.call_args[0]
        assert args[1]["category"] == "Circadian rhythm"


@pytest.mark.asyncio
async def test_get_subcat_table_calls_r():
    with _patch_r([{"subcat": "Chronobiology"}]) as mock_r:
        from server import get_subcat_table
        result = await get_subcat_table("Biology")
        mock_r.assert_called_once()
        args = mock_r.call_args[0]
        assert args[1]["catname"] == "Biology"


# ── Top-cited papers ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_top_cited_papers_calls_r():
    with _patch_r([{"doi": "10.1038/nature12373", "count": 5}]) as mock_r:
        from server import get_top_cited_papers
        result = await get_top_cited_papers("Zeitgeber")
        mock_r.assert_called_once()


# ── Revert counts ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_revert_counts_default_rev_eds():
    with _patch_r([{"art": "Wikipedia", "sum_nb_reverts": 5}]) as mock_r:
        from server import get_revert_counts
        await get_revert_counts("20181212010000", "20181212000000")
        assert mock_r.call_args[0][1]["rev_eds"] is True


@pytest.mark.asyncio
async def test_get_revert_counts_all_edits():
    with _patch_r([{"art": "Wikipedia", "sum_nb_edits": 42}]) as mock_r:
        from server import get_revert_counts
        await get_revert_counts("20181212010000", "20181212000000", rev_eds=False)
        assert mock_r.call_args[0][1]["rev_eds"] is False


# ── Longitudinal probing ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_probe_article_over_time_passes_metrics():
    with _patch_r([{"date": "2021-01-01T00:00:00Z", "sci_score": 0.5}]) as mock_r:
        from server import probe_article_over_time
        dates = ["2021-01-01T00:00:00Z", "2022-01-01T00:00:00Z"]
        await probe_article_over_time("Zeitgeber", dates, metrics=["sci_score"])
        assert mock_r.call_args[0][1]["metrics"] == ["sci_score"]


@pytest.mark.asyncio
async def test_probe_article_over_time_default_metrics():
    with _patch_r([]) as mock_r:
        from server import probe_article_over_time
        await probe_article_over_time("Zeitgeber", ["2021-01-01T00:00:00Z"])
        sent_metrics = mock_r.call_args[0][1]["metrics"]
        assert "sci_score" in sent_metrics
        assert "doi_count" in sent_metrics


# ── Error propagation ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_r_error_propagates():
    with patch("server.call_r_async", new_callable=AsyncMock) as mock_r:
        mock_r.side_effect = RuntimeError("R error for tool 'bad_tool': Unknown tool")
        from server import get_article_most_recent
        with pytest.raises(RuntimeError, match="Unknown tool"):
            await get_article_most_recent("Zeitgeber")
