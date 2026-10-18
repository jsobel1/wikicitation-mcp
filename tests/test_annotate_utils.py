# tests/test_annotate_utils.py
# Unit tests (mocked httpx) and integration tests for annotate_utils.py.

from unittest.mock import MagicMock, patch

import pytest

import annotate_utils as au


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

def _mock(data: dict | list | str, status: int = 200) -> MagicMock:
    m = MagicMock()
    m.status_code = status
    if isinstance(data, str):
        m.text = data
        m.json.side_effect = ValueError("not JSON")
    else:
        m.json.return_value = data
    return m


# ---------------------------------------------------------------------------
# annotate_dois_europmc — unit
# ---------------------------------------------------------------------------

def test_europmc_single_doi():
    payload = {
        "resultList": {"result": [{
            "doi": "10.1038/nature12373",
            "title": "Test paper",
            "authorString": "Smith J",
            "journalTitle": "Nature",
            "pubYear": "2020",
            "citedByCount": 100,
        }]}
    }
    with patch("annotate_utils._client.get", return_value=_mock(payload)):
        results = au.annotate_dois_europmc(["10.1038/nature12373"])
    assert len(results) == 1
    assert results[0]["doi"] == "10.1038/nature12373"
    assert results[0]["title"] == "Test paper"


def test_europmc_empty_list():
    assert au.annotate_dois_europmc([]) == []


def test_europmc_http_error_skipped():
    with patch("annotate_utils._client.get", return_value=_mock({}, status=500)):
        results = au.annotate_dois_europmc(["10.1000/bad"])
    assert results == [{"doi": "10.1000/bad", "error": "HTTP 500"}]


def test_europmc_batches_by_25():
    """26 DOIs should trigger 2 HTTP calls."""
    payload = {"resultList": {"result": []}}
    call_count = 0

    def fake_get(*a, **kw):
        nonlocal call_count
        call_count += 1
        return _mock(payload)

    dois = [f"10.1234/doi{i}" for i in range(26)]
    with patch("annotate_utils._client.get", side_effect=fake_get):
        au.annotate_dois_europmc(dois)
    assert call_count == 2


# ---------------------------------------------------------------------------
# annotate_dois_crossref — unit
# ---------------------------------------------------------------------------

def test_crossref_returns_structured_dict():
    payload = {"message": {
        "DOI": "10.1038/nature12373",
        "title": ["Test paper"],
        "container-title": ["Nature"],
        "author": [{"given": "John", "family": "Smith"}],
        "published-print": {"date-parts": [[2020, 1, 1]]},
        "publisher": "Springer",
        "type": "journal-article",
        "is-referenced-by-count": 50,
        "URL": "https://doi.org/10.1038/nature12373",
    }}
    with patch("annotate_utils._client.get", return_value=_mock(payload)):
        results = au.annotate_dois_crossref(["10.1038/nature12373"])
    r = results[0]
    assert r["title"] == "Test paper"
    assert r["journal"] == "Nature"
    assert "John Smith" in r["authors"]
    assert r["year"] == 2020


def test_crossref_http_error_returned():
    with patch("annotate_utils._client.get", return_value=_mock({}, status=404)):
        results = au.annotate_dois_crossref(["10.0000/missing"])
    assert results[0]["error"] == "HTTP 404"


# ---------------------------------------------------------------------------
# annotate_dois_bibtex — unit
# ---------------------------------------------------------------------------

def test_bibtex_returns_text():
    bibtex_str = "@article{key, author={Smith}, title={Test}}"
    mock = MagicMock()
    mock.status_code = 200
    mock.text = bibtex_str
    with patch("annotate_utils._client.get", return_value=mock):
        result = au.annotate_dois_bibtex(["10.1038/nature12373"])
    assert result["bibtex_entries"][0] == bibtex_str


def test_bibtex_http_error_placeholder():
    mock = MagicMock()
    mock.status_code = 404
    mock.text = ""
    with patch("annotate_utils._client.get", return_value=mock):
        result = au.annotate_dois_bibtex(["10.0000/bad"])
    assert "HTTP 404" in result["bibtex_entries"][0]


# ---------------------------------------------------------------------------
# annotate_isbn_google — unit
# ---------------------------------------------------------------------------

def test_isbn_google_success():
    payload = {"items": [{"volumeInfo": {
        "title": "Circadian Biology",
        "authors": ["Jones A"],
        "publisher": "Academic",
        "publishedDate": "2019",
        "description": "A book about clocks.",
        "categories": ["Science"],
    }}]}
    with patch("annotate_utils._client.get", return_value=_mock(payload)):
        result = au.annotate_isbn_google("978-3-16-148410-0")
    assert result["title"] == "Circadian Biology"
    assert "Jones A" in result["authors"]


def test_isbn_google_not_found():
    with patch("annotate_utils._client.get", return_value=_mock({"items": []})):
        result = au.annotate_isbn_google("000-0-00-000000-0")
    assert result["error"] == "not found"


def test_isbn_google_http_error():
    with patch("annotate_utils._client.get", return_value=_mock({}, status=503)):
        result = au.annotate_isbn_google("xxx")
    assert "HTTP 503" in result["error"]


# ---------------------------------------------------------------------------
# annotate_isbn_openlib — unit
# ---------------------------------------------------------------------------

def test_isbn_openlib_success():
    isbn = "9783161484100"
    payload = {f"ISBN:{isbn}": {
        "title": "Circadian Biology",
        "authors": [{"name": "Jones A"}],
        "publishers": [{"name": "Academic"}],
        "publish_date": "2019",
        "number_of_pages": 300,
        "subjects": [{"name": "Chronobiology"}],
    }}
    with patch("annotate_utils._client.get", return_value=_mock(payload)):
        result = au.annotate_isbn_openlib("978-3-16-148410-0")
    assert result["title"] == "Circadian Biology"
    assert result["number_of_pages"] == 300


def test_isbn_openlib_not_found():
    with patch("annotate_utils._client.get", return_value=_mock({})):
        result = au.annotate_isbn_openlib("000-0-00-000000-0")
    assert result["error"] == "not found"


# ---------------------------------------------------------------------------
# Integration tests — require network
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_integration_europmc_known_doi():
    results = au.annotate_dois_europmc(["10.1038/nature12373"])
    assert len(results) >= 1
    r = results[0]
    assert r.get("doi", "").lower() == "10.1038/nature12373"
    assert r.get("title")
    assert int(r.get("citation_count", 0)) > 0


@pytest.mark.integration
def test_integration_crossref_known_doi():
    results = au.annotate_dois_crossref(["10.1038/nature12373"])
    r = results[0]
    assert r.get("title")
    assert r.get("journal")
    assert r.get("year") == 2013


@pytest.mark.integration
def test_integration_bibtex_known_doi():
    result = au.annotate_dois_bibtex(["10.1038/nature12373"])
    entry = result["bibtex_entries"][0]
    assert entry.startswith("@")
    assert "nature12373" in entry.lower() or "nature" in entry.lower()


@pytest.mark.integration
def test_integration_isbn_google():
    result = au.annotate_isbn_google("978-0-385-33348-1")
    if "HTTP 429" in result.get("error", ""):
        pytest.skip("Google Books keyless quota exhausted (set GOOGLE_BOOKS_API_KEY)")
    assert result.get("title")


@pytest.mark.integration
def test_integration_isbn_openlib():
    result = au.annotate_isbn_openlib("978-0-385-33348-1")
    assert result.get("title") or result.get("error")  # may not be in OL


# ---------------------------------------------------------------------------
# Google Books key / quota handling, DOI URL-encoding
# ---------------------------------------------------------------------------

def test_isbn_google_429_hint_mentions_key(monkeypatch):
    monkeypatch.setattr(au, "_GOOGLE_BOOKS_KEY", "")
    with patch("annotate_utils._client.get", return_value=_mock({}, status=429)):
        result = au.annotate_isbn_google("9780262033848")
    assert "HTTP 429" in result["error"]
    assert "GOOGLE_BOOKS_API_KEY" in result["error"]


def test_isbn_google_sends_key_when_configured(monkeypatch):
    monkeypatch.setattr(au, "_GOOGLE_BOOKS_KEY", "k123")
    with patch("annotate_utils._client.get", return_value=_mock({"items": []})) as m:
        au.annotate_isbn_google("9780262033848")
    assert m.call_args.kwargs["params"]["key"] == "k123"


def test_crossref_doi_is_url_encoded():
    with patch("annotate_utils._client.get", return_value=_mock({}, status=404)) as m:
        au.annotate_dois_crossref(["10.1002/(SICI)1097?x#y"])
    url = m.call_args.args[0]
    assert "?" not in url.split("works/")[1] and "#" not in url
