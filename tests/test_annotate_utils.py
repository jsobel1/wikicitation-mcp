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
    with patch("annotate_utils.httpx.get", return_value=_mock(payload)):
        results = au.annotate_dois_europmc(["10.1038/nature12373"])
    assert len(results) == 1
    assert results[0]["doi"] == "10.1038/nature12373"
    assert results[0]["title"] == "Test paper"


def test_europmc_empty_list():
    assert au.annotate_dois_europmc([]) == []


def test_europmc_http_error_skipped():
    with patch("annotate_utils.httpx.get", return_value=_mock({}, status=500)):
        results = au.annotate_dois_europmc(["10.1000/bad"])
    assert results == []


def test_europmc_batches_by_10():
    """11 DOIs should trigger 2 HTTP calls."""
    payload = {"resultList": {"result": []}}
    call_count = 0

    def fake_get(*a, **kw):
        nonlocal call_count
        call_count += 1
        return _mock(payload)

    dois = [f"10.1234/doi{i}" for i in range(11)]
    with patch("annotate_utils.httpx.get", side_effect=fake_get):
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
    with patch("annotate_utils.httpx.get", return_value=_mock(payload)):
        results = au.annotate_dois_crossref(["10.1038/nature12373"])
    r = results[0]
    assert r["title"] == "Test paper"
    assert r["journal"] == "Nature"
    assert "John Smith" in r["authors"]
    assert r["year"] == 2020


def test_crossref_http_error_returned():
    with patch("annotate_utils.httpx.get", return_value=_mock({}, status=404)):
        results = au.annotate_dois_crossref(["10.0000/missing"])
    assert results[0]["error"] == "HTTP 404"


# ---------------------------------------------------------------------------
# annotate_dois_altmetric — unit
# ---------------------------------------------------------------------------

def test_altmetric_doi_success():
    payload = {
        "score": 42.5,
        "altmetric_id": 9999,
        "cited_by_tweeters_count": 10,
        "cited_by_accounts_count": 15,
        "cited_by_msm_count": 2,
        "cited_by_fbwalls_count": 3,
        "readers_count": 100,
        "details_url": "https://altmetric.com/details/9999",
    }
    with patch("annotate_utils.httpx.get", return_value=_mock(payload)):
        results = au.annotate_dois_altmetric(["10.1038/nature12373"])
    assert results[0]["altmetric_score"] == 42.5
    assert results[0]["cited_by_tweeters_count"] == 10


def test_altmetric_doi_not_found():
    with patch("annotate_utils.httpx.get", return_value=_mock({}, status=404)):
        results = au.annotate_dois_altmetric(["10.0000/x"])
    assert results[0]["altmetric_score"] is None


# ---------------------------------------------------------------------------
# annotate_dois_bibtex — unit
# ---------------------------------------------------------------------------

def test_bibtex_returns_text():
    bibtex_str = "@article{key, author={Smith}, title={Test}}"
    mock = MagicMock()
    mock.status_code = 200
    mock.text = bibtex_str
    with patch("annotate_utils.httpx.get", return_value=mock):
        result = au.annotate_dois_bibtex(["10.1038/nature12373"])
    assert result["bibtex_entries"][0] == bibtex_str


def test_bibtex_http_error_placeholder():
    mock = MagicMock()
    mock.status_code = 404
    mock.text = ""
    with patch("annotate_utils.httpx.get", return_value=mock):
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
    with patch("annotate_utils.httpx.get", return_value=_mock(payload)):
        result = au.annotate_isbn_google("978-3-16-148410-0")
    assert result["title"] == "Circadian Biology"
    assert "Jones A" in result["authors"]


def test_isbn_google_not_found():
    with patch("annotate_utils.httpx.get", return_value=_mock({"items": []})):
        result = au.annotate_isbn_google("000-0-00-000000-0")
    assert result["error"] == "not found"


def test_isbn_google_http_error():
    with patch("annotate_utils.httpx.get", return_value=_mock({}, status=503)):
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
    with patch("annotate_utils.httpx.get", return_value=_mock(payload)):
        result = au.annotate_isbn_openlib("978-3-16-148410-0")
    assert result["title"] == "Circadian Biology"
    assert result["number_of_pages"] == 300


def test_isbn_openlib_not_found():
    with patch("annotate_utils.httpx.get", return_value=_mock({})):
        result = au.annotate_isbn_openlib("000-0-00-000000-0")
    assert result["error"] == "not found"


# ---------------------------------------------------------------------------
# annotate_isbns_altmetric — unit
# ---------------------------------------------------------------------------

def test_isbns_altmetric_success():
    payload = {
        "score": 5.2,
        "cited_by_tweeters_count": 3,
        "cited_by_accounts_count": 4,
        "details_url": "https://altmetric.com/details/111",
    }
    with patch("annotate_utils.httpx.get", return_value=_mock(payload)):
        results = au.annotate_isbns_altmetric(["978-3-16-148410-0"])
    assert results[0]["altmetric_score"] == 5.2


def test_isbns_altmetric_not_found():
    with patch("annotate_utils.httpx.get", return_value=_mock({}, status=404)):
        results = au.annotate_isbns_altmetric(["000"])
    assert results[0]["altmetric_score"] is None


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
    assert int(r.get("citedByCount", 0)) > 0


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
    assert result.get("title")


@pytest.mark.integration
def test_integration_isbn_openlib():
    result = au.annotate_isbn_openlib("978-0-385-33348-1")
    assert result.get("title") or result.get("error")  # may not be in OL
