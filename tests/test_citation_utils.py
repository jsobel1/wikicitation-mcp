# tests/test_citation_utils.py
# Unit tests for citation_utils.py — no network, no R required.

from unittest.mock import patch

import citation_utils as cu

# ---------------------------------------------------------------------------
# Shared fixture wikitext
# ---------------------------------------------------------------------------

SAMPLE_WIKITEXT = """\
==Introduction==
The [[Zeitgeber]] is a cue that synchronises the [[circadian rhythm|biological clock]].<ref>\
{{cite journal |author=Smith J |year=2020 |title=Zeitgeber effects \
|doi=10.1038/nature12373 |journal=Nature |volume=123 |pages=1-10}}</ref>

==Sources==
{{cite web |url=https://example.com/zeitgeber |title=Zeitgeber Overview |accessdate=2021-01-01}}
{{cite book |author=Jones A |year=2019 |title=Circadian Biology \
|isbn=978-3-16-148410-0 |publisher=Academic Press}}

See also: [[Circadian clock]], [[Sleep|sleep science]].
<ref name="r2">Another reference http://bio.org/zeitgeber </ref>
"""

# Expected counts in SAMPLE_WIKITEXT:
#   DOI:       1  (10.1038/nature12373)
#   REF tags:  2  (<ref>…</ref> + <ref name="r2">)
#   URLs:      2  (https://example.com/… + http://bio.org/…)
#   ISBNs:     1  (978-3-16-148410-0)
#   Wikilinks: 4  ([[Zeitgeber]], [[circadian rhythm|biological clock]],
#                  [[Circadian clock]], [[Sleep|sleep science]])
#   CS1:       3  (journal + web + book)


# ---------------------------------------------------------------------------
# Counting functions
# ---------------------------------------------------------------------------

def test_doi_count():
    assert cu.get_doi_count(SAMPLE_WIKITEXT) == 1


def test_doi_count_multiple():
    text = "10.1038/nature12373 and 10.1016/j.cell.2020.01.001"
    assert cu.get_doi_count(text) == 2


def test_doi_count_empty():
    assert cu.get_doi_count("No DOIs here") == 0


def test_ref_count():
    assert cu.get_ref_count(SAMPLE_WIKITEXT) == 2


def test_ref_count_self_closing():
    text = "<ref name='foo'/> and <ref>bar</ref>"
    assert cu.get_ref_count(text) == 2


def test_url_count():
    assert cu.get_url_count(SAMPLE_WIKITEXT) == 2


def test_url_count_mixed():
    text = "See https://example.com and http://foo.org for details."
    assert cu.get_url_count(text) == 2


def test_isbn_count():
    assert cu.get_isbn_count(SAMPLE_WIKITEXT) == 1


def test_isbn_count_two():
    text = ("{{cite book|isbn=978-3-16-148410-0}} and "
            "{{cite book|isbn=0-306-40615-2}}")
    assert cu.get_isbn_count(text) == 2


def test_hyperlink_count():
    assert cu.get_hyperlink_count(SAMPLE_WIKITEXT) == 4


def test_any_count_case_sensitive():
    assert cu.get_any_count("abc ABC abc", "abc") == 2


def test_any_count_case_insensitive():
    assert cu.get_any_count("abc ABC abc", "(?i)abc") == 3


def test_any_count_no_match():
    assert cu.get_any_count("hello world", r"\d+") == 0


# ---------------------------------------------------------------------------
# Extraction functions
# ---------------------------------------------------------------------------

def test_extract_citations_count():
    citations = cu.extract_citations(SAMPLE_WIKITEXT)
    assert len(citations) == 3


def test_extract_citations_types():
    citations = cu.extract_citations(SAMPLE_WIKITEXT)
    joined = " ".join(citations).lower()
    assert "cite journal" in joined
    assert "cite web" in joined
    assert "cite book" in joined


def test_extract_citations_empty():
    assert cu.extract_citations("No templates here.") == []


def test_extract_wikihyperlinks_count():
    links = cu.extract_wikihyperlinks(SAMPLE_WIKITEXT)
    assert len(links) == 4


def test_extract_wikihyperlinks_piped():
    links = cu.extract_wikihyperlinks("See [[Sleep|sleep science]].")
    assert links == ["[[Sleep|sleep science]]"]


def test_replace_wikihyperlinks_simple():
    result = cu.replace_wikihyperlinks("See [[Circadian clock]].")
    assert "[[" not in result
    assert "Circadian clock" in result


def test_replace_wikihyperlinks_piped():
    result = cu.replace_wikihyperlinks("See [[Sleep|sleep science]].")
    assert "[[" not in result
    assert "sleep science" in result
    assert "Sleep" not in result


def test_replace_wikihyperlinks_multiple():
    text = "[[Zeitgeber]] and [[Sleep|sleeping]]"
    result = cu.replace_wikihyperlinks(text)
    assert result == "Zeitgeber and sleeping"


def test_parse_cite_type_journal():
    tmpl = "{{cite journal |author=Smith |doi=10.1234/foo |journal=Nature |year=2020}}"
    result = cu.parse_cite_type(tmpl)
    assert result["cite_type"] == "journal"
    assert result["fields"]["doi"] == "10.1234/foo"
    assert result["fields"]["author"] == "Smith"


def test_parse_cite_type_book():
    tmpl = "{{cite book |author=Jones |title=Biology |isbn=978-0-123456-78-9}}"
    result = cu.parse_cite_type(tmpl)
    assert result["cite_type"] == "book"
    assert result["fields"]["isbn"] == "978-0-123456-78-9"


def test_parse_cite_type_no_template():
    assert cu.parse_cite_type("plain text") == {}


def test_parse_cite_type_case_insensitive():
    tmpl = "{{Cite Journal |author=X |year=2021}}"
    result = cu.parse_cite_type(tmpl)
    assert result["cite_type"] == "journal"


# ---------------------------------------------------------------------------
# Source type counts
# ---------------------------------------------------------------------------

def test_get_source_type_counts():
    counts = cu.get_source_type_counts(SAMPLE_WIKITEXT)
    types = {r["cite_type"]: r["count"] for r in counts}
    assert types.get("journal", 0) == 1
    assert types.get("web", 0) == 1
    assert types.get("book", 0) == 1


def test_get_source_type_counts_empty():
    assert cu.get_source_type_counts("No citations.") == []


# ---------------------------------------------------------------------------
# SciScore (mocked wikitext fetch)
# ---------------------------------------------------------------------------

def test_get_sci_score_values():
    with patch("citation_utils._get_wikitext", return_value=(999, SAMPLE_WIKITEXT)):
        result = cu.get_sci_score("Zeitgeber", "2024-01-01T00:00:00Z")
    assert result["article"] == "Zeitgeber"
    # 1 journal / 3 total CS1
    assert abs(result["sci_score"] - round(1 / 3, 4)) < 1e-4
    # 1 DOI / 2 refs
    assert abs(result["sci_score2"] - 0.5) < 1e-4


def test_get_sci_score_no_citations():
    empty = "Plain text with no citations."
    with patch("citation_utils._get_wikitext", return_value=(1, empty)):
        result = cu.get_sci_score("Empty", "2024-01-01T00:00:00Z")
    assert result["sci_score"] == 0.0
    assert result["sci_score2"] == 0.0


# ---------------------------------------------------------------------------
# parse_all_citations (mocked)
# ---------------------------------------------------------------------------

def test_parse_all_citations_fields():
    with patch("citation_utils._get_wikitext", return_value=(42, SAMPLE_WIKITEXT)):
        rows = cu.parse_all_citations("Zeitgeber", "2024-01-01T00:00:00Z")
    assert len(rows) > 0
    # Every row must have required keys
    for row in rows:
        assert "art" in row
        assert "cite_type" in row
        assert "variable" in row
        assert "value" in row
    # Article name propagated
    assert all(r["art"] == "Zeitgeber" for r in rows)


def test_parse_citations_doi_extracted():
    with patch("citation_utils._get_wikitext", return_value=(42, SAMPLE_WIKITEXT)):
        rows = cu.parse_citations("Zeitgeber", "2024-01-01T00:00:00Z")
    dois = [r["doi"] for r in rows if r["doi"]]
    assert "10.1038/nature12373" in dois


# ---------------------------------------------------------------------------
# extract_with_regex (mocked)
# ---------------------------------------------------------------------------

def test_extract_with_regex_doi():
    with patch("citation_utils._get_wikitext", return_value=(7, SAMPLE_WIKITEXT)):
        rows = cu.extract_with_regex("Zeitgeber", r'10\.\d{4,9}/[\w./-]+')
    assert any("nature12373" in r["match"] for r in rows)


# ---------------------------------------------------------------------------
# extract_all_regex (mocked)
# ---------------------------------------------------------------------------

def test_extract_all_regex_has_doi_pattern():
    with patch("citation_utils._get_wikitext", return_value=(7, SAMPLE_WIKITEXT)):
        rows = cu.extract_all_regex("Zeitgeber")
    doi_rows = [r for r in rows if r["pattern_name"] == "doi"]
    assert len(doi_rows) >= 1
