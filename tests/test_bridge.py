# tests/test_bridge.py
# Unit and integration tests for the Python -> R bridge.
# Network/R tests are marked @pytest.mark.integration and require
# wikilite to be installed in R.

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

ROOT = Path(__file__).parent.parent
R_SCRIPT = ROOT / "mcp_interface.R"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def r_available() -> bool:
    import shutil
    return shutil.which("Rscript") is not None


def wiki_package_available() -> bool:
    """Check whether wikilite is installed in R."""
    if not r_available():
        return False
    result = subprocess.run(
        ["Rscript", "-e",
         "suppressPackageStartupMessages(library(wikilite)); cat('OK')"],
        capture_output=True, text=True, timeout=30,
    )
    return result.returncode == 0 and "OK" in result.stdout


NEEDS_R = pytest.mark.skipif(
    not r_available(),
    reason="Rscript not found on PATH"
)
NEEDS_WIKI = pytest.mark.skipif(
    not wiki_package_available(),
    reason="wikilite not installed in R"
)


# ---------------------------------------------------------------------------
# Direct bridge tests — call mcp_interface.R via subprocess
# ---------------------------------------------------------------------------

@NEEDS_WIKI
def test_get_doi_count_direct():
    """R script should count DOIs correctly."""
    payload = json.dumps({
        "tool": "get_doi_count",
        "args": {"text": "See 10.1038/nature12373 and 10.1016/j.cell.2020.01.001"}
    })
    result = subprocess.run(
        ["Rscript", str(R_SCRIPT)],
        input=payload, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, f"R stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert data["count"] == 2


@NEEDS_WIKI
def test_get_ref_count_direct():
    payload = json.dumps({
        "tool": "get_ref_count",
        "args": {"text": "<ref>one</ref> text <ref name='r2'>two</ref>"}
    })
    result = subprocess.run(
        ["Rscript", str(R_SCRIPT)],
        input=payload, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["count"] == 2


@NEEDS_WIKI
def test_get_url_count_direct():
    payload = json.dumps({
        "tool": "get_url_count",
        "args": {"text": "See https://example.com and http://foo.org for details."}
    })
    result = subprocess.run(
        ["Rscript", str(R_SCRIPT)],
        input=payload, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["count"] == 2


@NEEDS_WIKI
def test_get_isbn_count_direct():
    payload = json.dumps({
        "tool": "get_isbn_count",
        "args": {"text": "{{cite book|isbn=978-3-16-148410-0}} and {{cite book|isbn=0-306-40615-2}}"}
    })
    result = subprocess.run(
        ["Rscript", str(R_SCRIPT)],
        input=payload, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["count"] == 2


@NEEDS_WIKI
def test_extract_citations_direct():
    text = "{{cite journal | author = Smith }} and {{cite book | title = X }}"
    payload = json.dumps({
        "tool": "extract_citations",
        "args": {"text": text}
    })
    result = subprocess.run(
        ["Rscript", str(R_SCRIPT)],
        input=payload, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert isinstance(data, list)
    assert len(data) == 2


@NEEDS_WIKI
def test_get_any_count_direct():
    payload = json.dumps({
        "tool": "get_any_count",
        "args": {"text": "abc ABC abc", "regexp": "abc"}
    })
    result = subprocess.run(
        ["Rscript", str(R_SCRIPT)],
        input=payload, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["count"] == 2  # case-sensitive: matches "abc" twice


@NEEDS_WIKI
def test_replace_wikihypelinks_direct():
    payload = json.dumps({
        "tool": "replace_wikihypelinks",
        "args": {"text": "See [[Circadian clock]] and [[Sleep|sleeping]]"}
    })
    result = subprocess.run(
        ["Rscript", str(R_SCRIPT)],
        input=payload, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "cleaned_text" in data
    assert "[[" not in data["cleaned_text"]


@NEEDS_WIKI
def test_unknown_tool_returns_error():
    """Unknown tool name should return {"error": true}."""
    payload = json.dumps({"tool": "does_not_exist", "args": {}})
    result = subprocess.run(
        ["Rscript", str(R_SCRIPT)],
        input=payload, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data.get("error") is True


@NEEDS_WIKI
def test_empty_stdin_exits_nonzero():
    """Empty stdin should cause R to exit with non-zero code."""
    result = subprocess.run(
        ["Rscript", str(R_SCRIPT)],
        input="", capture_output=True, text=True, timeout=30,
    )
    assert result.returncode != 0


# ---------------------------------------------------------------------------
# Python bridge tests (r_bridge.py) with mocking
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_call_r_async_success(monkeypatch):
    """call_r_async should deserialise JSON output correctly."""
    from r_bridge import call_r_async

    fake_output = json.dumps({"count": 3}).encode()

    async def fake_communicate(input=None):
        return fake_output, b""

    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.communicate = fake_communicate

    with patch("r_bridge._find_rscript", return_value="Rscript"), \
         patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        result = await call_r_async("get_doi_count", {"text": "test"})

    assert result == {"count": 3}


@pytest.mark.asyncio
async def test_call_r_async_r_error_propagates(monkeypatch):
    """call_r_async should raise RuntimeError when R returns {"error": true}."""
    from r_bridge import call_r_async

    fake_output = json.dumps({"error": True, "message": "Test error"}).encode()

    async def fake_communicate(input=None):
        return fake_output, b""

    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.communicate = fake_communicate

    with patch("r_bridge._find_rscript", return_value="Rscript"), \
         patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with pytest.raises(RuntimeError, match="Test error"):
            await call_r_async("bad_tool", {})


@pytest.mark.asyncio
async def test_call_r_async_nonzero_exit(monkeypatch):
    """call_r_async should raise RuntimeError when Rscript exits with non-zero code."""
    from r_bridge import call_r_async

    async def fake_communicate(input=None):
        return b"", b"Fatal error in R"

    mock_proc = AsyncMock()
    mock_proc.returncode = 1
    mock_proc.communicate = fake_communicate

    with patch("r_bridge._find_rscript", return_value="Rscript"), \
         patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with pytest.raises(RuntimeError, match="code 1"):
            await call_r_async("get_doi_count", {"text": "test"})


@pytest.mark.asyncio
async def test_call_r_async_invalid_json(monkeypatch):
    """call_r_async should raise RuntimeError if R returns non-JSON output."""
    from r_bridge import call_r_async

    async def fake_communicate(input=None):
        return b"not valid json {{}", b""

    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.communicate = fake_communicate

    with patch("r_bridge._find_rscript", return_value="Rscript"), \
         patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with pytest.raises(RuntimeError, match="non-JSON"):
            await call_r_async("get_doi_count", {"text": "test"})


# ---------------------------------------------------------------------------
# Integration tests — require internet + R + wikilite installed
# ---------------------------------------------------------------------------

@NEEDS_WIKI
@pytest.mark.integration
def test_get_article_history_zeitgeber():
    """Integration: fetch edit history for 'Zeitgeber'."""
    from r_bridge import call_r
    result = call_r("get_article_history", {
        "article_name": "Zeitgeber",
        "date_limit": "2022-01-01T00:00:00Z",
    })
    assert isinstance(result, list)
    assert len(result) > 0
    first = result[0]
    assert "revid" in first
    assert "user" in first
    assert "timestamp" in first


@NEEDS_WIKI
@pytest.mark.integration
def test_get_sci_score_zeitgeber():
    """Integration: SciScore for 'Zeitgeber'."""
    from r_bridge import call_r
    result = call_r("get_sci_score", {
        "article_name": "Zeitgeber",
        "date_limit": "2022-01-01T00:00:00Z",
    })
    assert "sci_score" in result
    assert "sci_score2" in result
    assert 0.0 <= result["sci_score"] <= 1.0


@NEEDS_WIKI
@pytest.mark.integration
def test_get_article_info_zeitgeber():
    """Integration: article info for 'Zeitgeber'."""
    from r_bridge import call_r
    result = call_r("get_article_info", {"article_name": "Zeitgeber"})
    assert "title" in result or "pageid" in result


@NEEDS_WIKI
@pytest.mark.integration
def test_parse_all_citations_zeitgeber():
    """Integration: parse all citations in 'Zeitgeber'."""
    from r_bridge import call_r
    result = call_r("parse_all_citations", {
        "article_name": "Zeitgeber",
        "date_limit": "2022-01-01T00:00:00Z",
    })
    assert isinstance(result, list)


@NEEDS_WIKI
@pytest.mark.integration
def test_get_category_pages_chronobiology():
    """Integration: list pages in Chronobiology category."""
    from r_bridge import call_r
    result = call_r("get_category_pages", {"category": "Chronobiology"})
    assert isinstance(result, list)
    assert len(result) > 0


@NEEDS_WIKI
@pytest.mark.integration
def test_get_subcat_table_chronobiology():
    """Integration: direct subcategories of Chronobiology."""
    from r_bridge import call_r
    result = call_r("get_subcat_table", {"catname": "Chronobiology"})
    assert isinstance(result, list)
