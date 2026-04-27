# wikicitation-mcp — Usage Guide

Comprehensive examples for every tool group, common research workflows,
and tips for getting the most out of the MCP server in Claude.

---

## Quick reference

| Goal | Tool to ask Claude to use |
|------|--------------------------|
| Fetch article revision history | `get_article_history` |
| Get current wikitext | `get_article_most_recent` |
| Count DOIs / refs / ISBNs | `get_doi_count`, `get_ref_count`, `get_isbn_count` |
| Compute SciScore | `get_sci_score` |
| Break down citation types | `get_citation_type_counts` |
| Parse all CS1 templates | `parse_all_citations` |
| Annotate DOIs with metadata | `annotate_dois` |
| Find top-cited papers | `get_top_cited_papers` |
| Browse category tree | `get_category_pages`, `get_subcat_table` |
| Track edit wars / reverts | `get_revert_counts` |
| Probe article over time | `probe_article_over_time` |

---

## Workflow 1 — Quick article quality check

**Goal:** Understand how scientifically sourced an article is in 30 seconds.

**Prompt:**
```
Fetch the most recent version of "Zeitgeber" and compute its SciScore,
total reference count, and DOI count. Summarise in a table.
```

**What Claude will do:**
1. Call `get_article_most_recent("Zeitgeber")`
2. Call `get_sci_score` with the wikitext
3. Call `get_ref_count` and `get_doi_count`
4. Present results as a summary table

**Expected output shape:**
| Metric | Value |
|--------|-------|
| SciScore (journal%) | 0.78 |
| SciScore2 (DOI/ref ratio) | 0.65 |
| Total `<ref>` tags | 84 |
| DOI count | 55 |

---

## Workflow 2 — Citation type breakdown

**Goal:** See what kinds of sources an article relies on.

**Prompt:**
```
For the Wikipedia article "mRNA vaccine", count citations by type
(journal articles, books, websites, news, preprints, etc.).
Show the result as a sorted table with percentages.
```

**What Claude will do:**
1. Call `get_citation_type_counts("mRNA vaccine")`
2. Compute percentages from the count column
3. Present a sorted table

**Return format from `get_citation_type_counts`:**
```json
[
  {"category": "Journal",      "count": 142},
  {"category": "Web",          "count": 38},
  {"category": "Book",         "count": 12},
  {"category": "News/Magazine","count": 7},
  {"category": "Preprint",     "count": 4},
  {"category": "Report",       "count": 3}
]
```

**Categories returned:**
- `Journal` — `{{cite journal}}`, `{{cite article}}`
- `Book` — `{{cite book}}`, `{{cite encyclopaedia}}`
- `Web` — `{{cite web}}`
- `News/Magazine` — `{{cite news}}`, `{{cite magazine}}`
- `Preprint` — `{{cite arxiv}}`, `{{cite ssrn}}`, `{{cite biorxiv}}`
- `Thesis` — `{{cite thesis}}`
- `Conference` — `{{cite conference}}`
- `Report` — `{{cite report}}`, `{{cite press release}}`
- `Multimedia` — `{{cite AV media}}`, `{{cite podcast}}`, `{{cite episode}}`
- `Legal/Patent` — `{{cite patent}}`, `{{cite court}}`
- `Social Media` — `{{cite tweet}}`, `{{cite reddit}}`
- `Other` — unrecognised templates

---

## Workflow 3 — Top cited papers

**Goal:** Find which scientific papers are most influential in an article.

**Prompt:**
```
Find the top 10 most-cited papers in the Wikipedia article "CRISPR".
Include journal name, publication year, and how many Wikipedia articles
cite each one.
```

**What Claude will do:**
1. Call `get_top_cited_papers("CRISPR")`
2. Format the result, highlighting journal, year, and wiki_count

**Useful follow-up prompts:**
```
Now annotate those DOIs with their open-access status and citation counts.
```
→ Claude calls `annotate_dois(doi_list)` with the DOIs from step 1.

---

## Workflow 4 — Historical citation evolution

**Goal:** Track how an article's citations changed over time.

**Prompt:**
```
Probe the "COVID-19" Wikipedia article at the start of each year from
2020 to 2024. Show how SciScore, DOI count, and total ref count changed.
Plot the trend.
```

**What Claude will do:**
1. Call `probe_article_over_time("COVID-19", dates_to_probe=[...], metrics=[...])`
2. Present a time-series table
3. Optionally generate a plotly chart if running in a code environment

**`probe_article_over_time` parameters:**
- `article_name` — article title
- `dates_to_probe` — list of ISO 8601 timestamps
- `metrics` — any subset of `["sci_score", "doi_count", "ref_count", "size"]`
- `lang` — Wikipedia language edition (default `"en"`)

---

## Workflow 5 — Category-wide analysis

**Goal:** Compare citation quality across all articles in a Wikipedia category.

**Prompt:**
```
List all articles in the Wikipedia category "Circadian rhythm".
For each one, compute the SciScore and DOI count.
Rank them from most to least scientifically sourced.
```

**What Claude will do:**
1. Call `get_category_pages("Circadian rhythm")` → list of article titles
2. For each article, call `get_article_most_recent(article)` and `get_sci_score(wikitext)`
3. Sort and present results

> **Tip:** For categories with many articles, ask Claude to work through the
> list in batches of 10 to stay within a reasonable time window.

**Subcategory browsing:**
```
What subcategories does the "Chronobiology" category have?
```
→ Claude calls `get_subcat_table("Chronobiology")` and lists them.

```
Drill into "Sleep disorders" and list its articles.
```
→ Claude calls `get_category_pages("Sleep disorders")`.

---

## Workflow 6 — DOI annotation and BibTeX

**Goal:** Extract DOIs from an article and get their metadata.

**Prompt:**
```
Parse all CS1 citations in "Zeitgeber" and extract the DOIs.
Annotate them with EuropePMC — I want title, journal, year, and
open-access status.
```

**What Claude will do:**
1. Call `parse_all_citations("Zeitgeber")` → structured citation fields
2. Extract `doi` values from the results
3. Call `annotate_dois(doi_list)` for EuropePMC metadata

**Annotation columns from `annotate_dois`:**
| Column | Description |
|--------|-------------|
| `doi` | DOI string |
| `title` | Paper title |
| `authorString` | Author list |
| `journalTitle` | Journal name |
| `pubYear` | Publication year |
| `isOpenAccess` | `"Y"` or `"N"` |
| `citedByCount` | EuropePMC citation count |
| `firstPublicationDate` | ISO date of first publication |
| `pmid` | PubMed ID (if indexed) |
| `pmcid` | PubMed Central ID (if OA) |

---

## Workflow 7 — Edit-war monitoring

**Goal:** Identify heavily contested articles in a time window.

**Prompt:**
```
Find all Wikipedia articles with the most revert-tagged edits between
1 January 2024 00:00:00 and 1 January 2024 01:00:00 UTC.
```

**What Claude will do:**
1. Call `get_revert_counts("20240101000000", "20240101010000")`
2. Rank articles by number of reverts

> **Note:** The Wikipedia `recentchanges` API retains approximately 30 days
> of history. For older periods the result will be empty.

---

## Workflow 8 — Multilingual analysis

All tools accept a `lang` parameter for any Wikipedia edition.

**Prompt:**
```
Compare the SciScore of the French and English versions of
the "COVID-19" article as of 1 January 2022.
```

**What Claude will do:**
1. `get_article_most_recent("COVID-19", lang="en", date_an="2022-01-01T00:00:00Z")`
2. `get_article_most_recent("COVID-19", lang="fr", date_an="2022-01-01T00:00:00Z")`
3. `get_sci_score(wikitext_en)` and `get_sci_score(wikitext_fr)`
4. Present comparison

**Supported languages:** any Wikipedia language code — `en`, `fr`, `de`, `es`,
`it`, `pt`, `nl`, `ru`, `ja`, `zh`, `ar`, `pl`, `sv`, …

---

## Tool signatures

### `get_citation_type_counts`

```
get_citation_type_counts(article_name, lang="en", date_an=None)
```

Returns citation counts grouped by display category for a Wikipedia article.
`date_an` restricts to a historical snapshot (ISO 8601 timestamp or `None`
for the current revision).

### `probe_article_over_time`

```
probe_article_over_time(article_name, dates_to_probe, lang="en", metrics=None)
```

Fetches the article at each timestamp in `dates_to_probe` and computes the
requested quality metrics.  Default metrics: `["sci_score", "doi_count",
"ref_count", "size"]`.

### `annotate_dois`

```
annotate_dois(doi_list)
```

Accepts a list of DOI strings and queries EuropePMC for each one.
Returns a list of metadata records (one per DOI found).  DOIs not indexed
by EuropePMC are silently omitted from the result.

---

## Running the test suite

```bash
cd wikicitation-mcp

# Fast unit tests (no network, no R)
uv run pytest tests/ -m "not integration" -v

# Integration tests (require network + wikilite in R)
uv run pytest tests/ -m integration -v

# Single test file
uv run pytest tests/test_server.py -v

# Coverage report
uv run pytest tests/ -m "not integration" --cov=. --cov-report=term-missing
```

---

## Adding a new tool

1. **R side** — add a new `switch` case in `mcp_interface.R`.
2. **Python side** — add an `@mcp.tool()` decorated async function in `server.py`
   that calls `await call_r_async("new_tool_name", {...})`.
3. **Tests** — add a mocked unit test in `tests/test_server.py` and an
   optional integration test in `tests/test_bridge.py`.

Example skeleton:

```python
# server.py
@mcp.tool()
async def my_new_tool(article_name: str, lang: str = "en") -> dict:
    """One-line description shown in Claude's tool list."""
    return await call_r_async("my_new_tool", {
        "article_name": article_name,
        "lang": lang,
    })
```

```r
# mcp_interface.R — inside switch(tool, ...)
"my_new_tool" = {
  wikilite::my_r_function(args$article_name, lang = args$lang %||% "en")
},
```

```python
# tests/test_server.py
@pytest.mark.asyncio
async def test_my_new_tool_calls_r():
    with patch("server.call_r_async", new_callable=AsyncMock,
               return_value={"result": "ok"}) as mock_r:
        from server import my_new_tool
        result = await my_new_tool("Zeitgeber")
        mock_r.assert_called_once()
        assert result["result"] == "ok"
```
