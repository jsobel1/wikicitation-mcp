# wikicitation-mcp — Usage Guide

Worked examples for the 38 tools and the research workflows they combine into.
Tool arguments are listed in the [README](README.md#tool-reference).

---

## Quick reference

| Goal | Tool |
|------|------|
| Fetch article revision history | `get_article_history` |
| Get the current (or a dated) wikitext | `get_article_recent` |
| Count DOIs / refs / ISBNs in text | `get_doi_count`, `get_ref_count`, `get_isbn_count` |
| Compute SciScore for an article | `get_sci_score` |
| Break down citation types | `get_citation_types` (article), `get_source_type_counts` (raw text) |
| Parse all citation templates | `parse_citations`, `parse_all_citations` |
| Annotate DOIs with metadata | `annotate_dois_europmc`, `annotate_dois_crossref`, `annotate_dois_bibtex` |
| Find top-cited papers | `get_top_cited_papers` |
| Browse a category tree | `get_category_pages`, `get_subcat_table`, `get_subcat_with_depth` |
| Track reverts | `get_revert_counts` |
| Look up a book | `annotate_isbn_openlib`, `annotate_isbn_google` |

Article-level tools default to the **current revision**; pass `date_limit`
(ISO 8601, an upper bound) for a historical snapshot, and `lang` for another
Wikipedia edition.

---

## Workflow 1 — Quick article quality check

```
Compute the SciScore of "Zeitgeber", and count its references and DOIs.
Summarise in a table.
```

Claude calls `get_sci_score("Zeitgeber")`, then `get_article_recent` followed by
`get_ref_count` and `get_doi_count` on the returned wikitext.

## Workflow 2 — Citation type breakdown

```
Extract all citations from "CRISPR" — how many are journals vs websites vs books?
```

`get_citation_types("CRISPR")` returns `[{"cite_type": "journal", "count": N}, …]`.
Use `parse_citations` for one row per citation (doi, isbn, pmid, url, title,
author, year, journal, publisher, accessdate).

## Workflow 3 — Top cited papers

```
Find the 10 most-cited papers in "mRNA vaccine" with journal, year and EuropePMC
citation count.
```

`get_top_cited_papers` returns up to 40 DOIs ranked by `wiki_count` (how many
times the article cites each one), annotated through EuropePMC.

## Workflow 4 — Historical evolution

```
Compare the SciScore of "COVID-19" at 1 January of each year from 2020 to 2024.
```

Claude calls `get_sci_score("COVID-19", date_limit="2020-01-01")` once per date.
`date_limit` is the *newest* revision allowed, so each call returns the article
as it stood on that day.

## Workflow 5 — Category-wide analysis

```
List the articles in Category:Circadian rhythm and give me the SciScore of each.
```

`get_category_pages` → article titles; then `get_sci_score` per title, or
`get_category_recent` for all wikitext in one call (up to 100 articles). Use
`get_subcat_with_depth(catname, depth=2)` to descend the tree.

## Workflow 6 — DOI annotation and BibTeX

```
Parse the citations of "Zeitgeber", take their DOIs, and give me title, journal,
year and open-access status, plus BibTeX.
```

`parse_citations` → `doi` column → `annotate_dois_europmc` (fields: `doi`, `pmid`,
`pmcid`, `title`, `authors`, `journal`, `year`, `citation_count`,
`is_open_access`) and `annotate_dois_bibtex`. DOIs missing from EuropePMC still
come back, flagged `not_found`.

## Workflow 7 — Edit-war monitoring

```
Which articles had the most reverts in the last week?
```

`get_revert_counts()` defaults to the last 7 days. Wikipedia keeps recent changes
for about 30 days, so older windows return partial or empty results, and the scan
can take a minute or more.

## Workflow 8 — Multilingual analysis

```
Compare the SciScore of the French and English "COVID-19" articles.
```

`get_sci_score("COVID-19", lang="en")` and `get_sci_score("COVID-19", lang="fr")`.
French (`Article`, `Ouvrage`, …), German (`Literatur`, `Internetquelle`, …),
Spanish, Italian and Portuguese templates are mapped to the same canonical types,
so scores are comparable. Other language codes work for history and category
tools; their citation templates are treated as English unless supported.

---

## Notes

* **Books:** `annotate_isbn_google` shares a small keyless quota and often answers
  HTTP 429. Set `GOOGLE_BOOKS_API_KEY` or use `annotate_isbn_openlib`.
* **Altmetric** tools were removed in 0.5.0: the public API now returns HTTP 403
  without a paid key.
* **Limits:** 100 articles, 20 categories, 200 DOIs per call; regular expressions
  up to 500 characters. Violations return a descriptive error.

---

## Running the test suite

```bash
uv sync --dev
uv run pytest                          # unit tests, no network
uv run pytest --run-integration        # also hit the live public APIs
uv run pytest tests/test_server.py -v  # a single file
```

## Adding a new tool

1. Implement the logic in `wiki_api.py`, `citation_utils.py` or `annotate_utils.py`
   (plain functions, no MCP imports).
2. Register it in `server.py` with `@mcp.tool()`. Validate every argument with the
   `_name` / `_names` / `_lang` / `_date` / `_regex` / `_dois` helpers; the
   docstring is shown to the LLM as the tool description.
3. Add the name to `EXPECTED_TOOLS` in `tests/test_server.py` and unit tests for
   the new logic (mock `wiki_api._client.get` / `annotate_utils._client.get`).
4. Add a row to the README tool table.
