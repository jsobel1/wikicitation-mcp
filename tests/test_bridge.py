# tests/test_bridge.py
# Tests unitaires du bridge Python → R.
# Les tests réseau sont marqués skip_on_ci=True et nécessitent
# que WikiCitationHistoRy soit installé dans R.

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

ROOT = Path(__file__).parent.parent
R_SCRIPT = ROOT / "mcp_interface.R"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def r_available() -> bool:
    """Vérifie si Rscript est disponible sur le PATH."""
    import shutil
    return shutil.which("Rscript") is not None


def wiki_package_available() -> bool:
    """Vérifie si WikiCitationHistoRy est installé dans R."""
    if not r_available():
        return False
    result = subprocess.run(
        ["Rscript", "-e",
         "suppressPackageStartupMessages(library(WikiCitationHistoRy)); cat('OK')"],
        capture_output=True, text=True, timeout=30,
    )
    return result.returncode == 0 and "OK" in result.stdout


NEEDS_R = pytest.mark.skipif(
    not r_available(),
    reason="Rscript introuvable dans le PATH"
)
NEEDS_WIKI = pytest.mark.skipif(
    not wiki_package_available(),
    reason="WikiCitationHistoRy non installé dans R"
)


# ─────────────────────────────────────────────────────────────────────────────
# Tests du bridge — appels directs à mcp_interface.R
# ─────────────────────────────────────────────────────────────────────────────

@NEEDS_WIKI
def test_get_doi_count_direct():
    """Le script R doit compter correctement les DOIs."""
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
def test_unknown_tool_returns_error():
    """Un outil inconnu doit retourner {"error": true}."""
    payload = json.dumps({"tool": "does_not_exist", "args": {}})
    result = subprocess.run(
        ["Rscript", str(R_SCRIPT)],
        input=payload, capture_output=True, text=True, timeout=30,
    )
    # R ne doit pas crasher
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data.get("error") is True


@NEEDS_WIKI
def test_empty_stdin_exits_nonzero():
    """Un stdin vide doit faire quitter R avec un code non-zéro."""
    result = subprocess.run(
        ["Rscript", str(R_SCRIPT)],
        input="", capture_output=True, text=True, timeout=30,
    )
    assert result.returncode != 0


# ─────────────────────────────────────────────────────────────────────────────
# Tests du bridge Python (r_bridge.py) avec mocking
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_call_r_async_success(monkeypatch):
    """call_r_async doit désérialiser la sortie JSON correctement."""
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
    """call_r_async doit lever RuntimeError si R retourne {"error": true}."""
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
    """call_r_async doit lever RuntimeError si Rscript quitte avec code != 0."""
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
    """call_r_async doit lever RuntimeError si R retourne du non-JSON."""
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


# ─────────────────────────────────────────────────────────────────────────────
# Tests d'intégration réseau — nécessitent connexion internet + R installé
# ─────────────────────────────────────────────────────────────────────────────

@NEEDS_WIKI
@pytest.mark.integration
def test_get_article_history_zeitgeber():
    """Test d'intégration : récupérer l'historique de 'Zeitgeber'."""
    from r_bridge import call_r
    result = call_r("get_article_history", {
        "article_name": "Zeitgeber",
        "date_limit": "2022-01-01T00:00:00Z",
    })
    # Le résultat doit être une liste de révisions
    assert isinstance(result, list)
    assert len(result) > 0
    first = result[0]
    assert "revid" in first
    assert "user" in first
    assert "timestamp" in first


@NEEDS_WIKI
@pytest.mark.integration
def test_get_sci_score_zeitgeber():
    """Test d'intégration : SciScore pour 'Zeitgeber'."""
    from r_bridge import call_r
    result = call_r("get_sci_score", {
        "article_name": "Zeitgeber",
        "date_limit": "2022-01-01T00:00:00Z",
    })
    assert "sci_score" in result
    assert "sci_score2" in result
    assert 0.0 <= result["sci_score"] <= 1.0
