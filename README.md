# wikicitation-mcp

> Wikipedia citation-science tools for Claude — pure Python, no R required.

An [MCP](https://modelcontextprotocol.io) server that exposes **40 tools** to
Claude Code, Claude Desktop, and claude.ai.  
Ask Claude to fetch Wikipedia edit histories, analyse citations, score
scientific quality, and annotate DOIs and ISBNs — all without leaving the chat.

---

## What you can do

| Category | Examples |
|---|---|
| **Edit history** | Full revision history, first/latest wikitext, category-wide sweeps |
| **Citation analysis** | Count DOIs/refs/ISBNs, extract CS1 templates, compute SciScore |
| **DOI & ISBN annotation** | Enrich DOIs via CrossRef / EuropePMC / Altmetric; books via Google Books / Open Library |

---

## Installation

### Option A — PyPI (recommended)

No clone needed. `uvx` downloads and runs the package in one step:

```bash
# Requires uv (https://docs.astral.sh/uv/)
uvx wikicitation-mcp
```

Or install permanently with pip:

```bash
pip install wikicitation-mcp
wikicitation-mcp          # starts the stdio server
```

### Option B — From source

```bash
git clone https://github.com/jsobel1/wikicitation-mcp.git
cd wikicitation-mcp
uv sync
uv run python server.py
```

---

## Connect to Claude

### Claude Code (CLI) — PyPI

```bash
claude mcp add wikilite -- uvx wikicitation-mcp
claude mcp list
```

### Claude Code (CLI) — from source

```bash
# Run from inside the cloned directory
claude mcp add wikilite -- uv run python server.py
```

### Claude Desktop — PyPI

Edit `~/.claude/claude_desktop_config.json`
(Windows: `%APPDATA%\Claude\claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "wikilite": {
      "command": "uvx",
      "args": ["wikicitation-mcp"]
    }
  }
}
```

### Claude Desktop — from source

```json
{
  "mcpServers": {
    "wikilite": {
      "command": "uv",
      "args": [
        "run", "python",
        "/ABSOLUTE/PATH/TO/wikicitation-mcp/server.py"
      ],
      "cwd": "/ABSOLUTE/PATH/TO/wikicitation-mcp"
    }
  }
}
```

Restart Claude Desktop — the **wikilite** server appears in the toolbar.

### claude.ai (web, HTTP transport)

```bash
uvx wikicitation-mcp --transport streamable-http --port 8000
# Then in claude.ai → Settings → Connections → Add MCP server
# URL: http://localhost:8000/mcp
```

---

## Quick start

Once connected, try these prompts in Claude:

```
Fetch all edits to the Wikipedia article "Circadian clock" up to today.
```

```
Count all DOIs, references, and ISBNs in this wikitext: [paste wikitext]
```

```
Calculate the SciScore for "Sleep deprivation".
```

```
Extract all citations from "CRISPR" — how many are journals vs websites vs books?
```

```
Show me the top 20 most-cited papers in the Wikipedia article "mRNA vaccine".
```

```
Annotate these DOIs with CrossRef metadata:
10.1038/nature12373, 10.1016/j.cell.2020.01.001
```

---

## Usage notes

### `date_limit` is an upper bound

`date_limit` controls the **newest** revision returned, not the oldest.
To retrieve edits "since 2023", pass today's date as the limit and filter
the returned rows by timestamp.

### SciScore

`get_sci_score` returns two metrics:

| Field | Formula | Meaning |
|---|---|---|
| `sci_score` | journal citations ÷ total CS1 citations | Proportion of references that are peer-reviewed journal articles |
| `sci_score2` | DOI count ÷ `<ref>` tag count | Proportion of footnotes that have a resolvable DOI |

Both range from 0 to 1; higher = more scientifically sourced.

### Altmetric

Altmetric returns attention scores without an API key for most DOIs and ISBNs.
If a DOI or ISBN is not indexed, `altmetric_score` will be `null`.
For production use, set the `ALTMETRIC_KEY` environment variable.

---

## Tool reference

### Group 1 — History & metadata (14 tools)

| Tool | Key arguments | Returns |
|---|---|---|
| `get_article_history` | `article_name`, `date_limit` | revision table (revid, user, timestamp, size, comment) |
| `get_article_recent` | `article_name`, `date_limit` | metadata + full wikitext |
| `get_article_initial` | `article_name` | first-ever revision metadata + wikitext |
| `get_article_info` | `article_name` | pageid, title, byte length |
| `get_tables_all` | `article_name`, `date_limit` | initial + recent + history + info in one call |
| `get_category_pages` | `category` | list of article titles |
| `get_pages_in_cat_table` | `category` | structured page table (pageid, title, type) |
| `get_subcat_table` | `catname`, `replacement` | direct subcategories |
| `get_subcat_multiple` | `catname_list` | subcategories for N categories |
| `get_subcat_with_depth` | `catname`, `depth`, `replacement` | recursive subcategories |
| `get_page_in_cat_multiple` | `catname_list` | pages for N categories |
| `get_category_history` | `article_list` | revision table for a list of articles |
| `get_category_recent` | `article_list`, `date_limit` | metadata + wikitext for a list of articles |
| `get_category_creation` | `article_list` | creation-revision metadata for a list of articles |

### Group 2 — Citation counting, extraction & quality (19 tools)

| Tool | Key arguments | Returns |
|---|---|---|
| `get_doi_count` | `text` | `{"count": N}` |
| `get_ref_count` | `text` | `{"count": N}` |
| `get_url_count` | `text` | `{"count": N}` |
| `get_isbn_count` | `text` | `{"count": N}` |
| `get_hyperlink_count` | `text` | `{"count": N}` |
| `get_any_count` | `text`, `regexp` | `{"count": N}` |
| `extract_citations` | `text` | list of CS1 template strings |
| `extract_wikihypelinks` | `text` | list of `[[...]]` wikilink strings |
| `replace_wikihypelinks` | `text` | `{"cleaned_text": ...}` with links replaced by display text |
| `parse_cite_type` | `text` | `{"cite_type": ..., "fields": {...}}` |
| `extract_with_regex` | `article_name`, `regexp`, `date_limit` | list of regex matches from live article |
| `extract_all_regex` | `article_name`, `date_limit` | all built-in pattern matches (doi, url, isbn, pmid, …) |
| `parse_citations` | `article_name`, `date_limit` | structured citation rows (cite_type, doi, author, year, title) |
| `parse_all_citations` | `article_name`, `date_limit` | long-form table: one row per citation field |
| `get_citation_types` | `article_name`, `date_limit` | citation counts by CS1 type |
| `get_source_type_counts` | `text` | citation counts by CS1 type from raw wikitext |
| `get_sci_score` | `article_name`, `date_limit` | `sci_score` and `sci_score2` (see above) |
| `get_top_cited_papers` | `article_name`, `date_limit` | top 40 DOIs annotated via EuropePMC |
| `get_revert_counts` | `start`, `end` | revert-tagged edit counts by article (≤30-day window) |

### Group 3 — DOI & ISBN annotation (7 tools)

| Tool | Key arguments | Returns |
|---|---|---|
| `annotate_dois_europmc` | `doi_list` | title, journal, pubYear, citedByCount, isOpenAccess, … |
| `annotate_dois_crossref` | `doi_list` | title, authors, journal, year, publisher, citation count |
| `annotate_dois_altmetric` | `doi_list` | Altmetric score, tweet count, news mentions, … |
| `annotate_dois_bibtex` | `doi_list` | `{"bibtex_entries": [...]}` |
| `annotate_isbn_google` | `isbn` | title, authors, publisher, publishedDate, description |
| `annotate_isbn_openlib` | `isbn` | title, authors, publishers, publish_date, page count |
| `annotate_isbns_altmetric` | `isbn_list` | Altmetric score per ISBN |

---

## Running tests

```bash
# Unit tests — no network required
uv run pytest tests/ -m "not integration" -v

# Integration tests — require internet
uv run pytest tests/ -m integration -v

# Full suite
uv run pytest tests/ -v
```

---

## Troubleshooting

**`uvx: command not found`**

Install uv first:
```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Server not appearing in Claude Code**

```bash
claude mcp remove wikilite
claude mcp add wikilite -- uvx wikicitation-mcp
claude mcp list
```

**`ModuleNotFoundError: No module named 'mwparserfromhell'`**

The venv is missing a dependency. Run `uv sync` inside the cloned repo, or
reinstall via `pip install wikicitation-mcp`.

**`get_revert_counts` returns no results**

The Wikipedia `recentchanges` API only retains ~30 days of history. Requests
for date ranges older than that will return empty results.

---

## Related

- [Model Context Protocol](https://modelcontextprotocol.io) — MCP specification
- [FastMCP](https://gofastmcp.com) — Python MCP framework used here
- [mwparserfromhell](https://github.com/earwig/mwparserfromhell) — wikitext parser
