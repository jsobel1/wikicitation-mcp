# wikilite MCP Server

> Bring Wikipedia citation science into your Claude conversations.

An [MCP](https://modelcontextprotocol.io) server that wraps the
[**wikilite**](https://github.com/jsobel1/wikilite) R package and exposes
~50 tools to Claude Code, Claude Desktop, and claude.ai.  
Ask Claude to fetch Wikipedia edit histories, analyse citations, score
scientific quality, annotate DOIs, and generate interactive visualisations
— all without leaving the chat.

---

## What you can do

| Category | Examples |
|---|---|
| **Edit history** | Full revision history, first/latest wikitext, category-wide sweeps |
| **Citation analysis** | Count DOIs/refs/ISBNs, extract CS1 templates, compute SciScore |
| **DOI & ISBN annotation** | Enrich DOIs via CrossRef / EuropePMC / Altmetric; books via Google Books |
| **Static plots** | Article creation timeline, citation distribution, page views/edits (PNG) |
| **Interactive plots** | Publication network, co-citation network, wikilink network (HTML) |

---

## Prerequisites

| Tool | Minimum version | Notes |
|---|---|---|
| Python | 3.10 | |
| [uv](https://docs.astral.sh/uv/) | latest | replaces pip/venv |
| R | 4.0 | |
| wikilite | latest | installed in R |

---

## Setup

### 1 — Install uv

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2 — Install wikilite in R

```r
# In an R console
install.packages("devtools")
devtools::install_github("jsobel1/wikilite")

# Required for CrossRef DOI annotation (annotate_dois_crossref, annotate_dois_bibtex)
install.packages("bibtex")

# Optional: for static PNG plots
install.packages("base64enc")

# Optional: for interactive HTML plots
install.packages("htmlwidgets")
```

### 3 — Clone and install Python dependencies

```bash
git clone https://github.com/jsobel1/wikicitation-mcp.git
cd wikicitation-mcp
uv sync
```

### 4 — Verify the bridge works

**macOS / Linux (bash):**
```bash
echo '{"tool":"get_doi_count","args":{"text":"doi:10.1038/nature12373"}}' | Rscript mcp_interface.R
# -> {"count":1}
```

**Windows (PowerShell):**
```powershell
'{"tool":"get_doi_count","args":{"text":"doi:10.1038/nature12373"}}' | Rscript mcp_interface.R
# -> {"count":1}
```

---

## Connect to Claude

### Claude Code (CLI)

```bash
# Run this from inside the wikicitation-mcp/ directory — uv needs to find pyproject.toml
cd /path/to/wikicitation-mcp
claude mcp add wikilite -- uv run python server.py

# Confirm
claude mcp list
# wikilite    stdio    uv run python server.py
```

### Claude Desktop

Edit `~/.claude/claude_desktop_config.json`
(Windows: `%APPDATA%\Claude\claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "wikilite": {
      "command": "uv",
      "args": [
        "run", "python",
        "/ABSOLUTE/PATH/TO/wikicitation-mcp/server.py"
      ],
      "env": {
        "R_HOME": "/usr/lib/R"
      }
    }
  }
}
```

> Find `R_HOME` with: `Rscript -e "R.home()"`

Restart Claude Desktop — the **wikilite** server appears in the toolbar.

### claude.ai (web, HTTP)

```bash
# Start HTTP server
uv run fastmcp run server.py --transport streamable-http --port 8000

# Then in claude.ai -> Settings -> Connections -> Add MCP server
# URL: http://localhost:8000/mcp
```

For remote access expose with a tunnel:
```bash
ngrok http 8000
# Use the https://xxx.ngrok.io/mcp URL in claude.ai
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
Calculate the SciScore for the Wikipedia article "Sleep deprivation".
```

```
Extract all citations from "CRISPR" and tell me how many are journal
articles vs websites vs books.
```

```
Show me the top 20 most-cited papers in the Wikipedia article "mRNA vaccine".
```

```
Annotate these DOIs with CrossRef metadata:
10.1038/nature12373, 10.1016/j.cell.2020.01.001
```

```
Generate a creation timeline chart for these articles:
Zeitgeber, Advanced sleep phase disorder, Delayed sleep phase disorder,
Non-24-hour sleep-wake disorder
```

```
Build an interactive publication network for all articles in
Category:Chronobiology using the top 50 DOIs.
```

---

## Usage examples

### Get article edit history

```
Get the edit history of "Alzheimer's disease" up to 2024-01-01.
```
→ Returns a table of revisions: timestamp, editor, edit size, comment.

> **Note:** `date_limit` is the **upper** (newest) date bound — it controls how recent the results go, not how far back. To retrieve edits "since 2023", pass today's date as the limit and filter the results by timestamp.

### Score citation quality (SciScore)

```
What is the SciScore of "Long COVID"?
```
→ Returns `sci_score` (fraction of DOI citations) and `sci_score2`
(fraction of peer-reviewed citations).

### Annotate DOIs from an article

```
1. Get the most recent wikitext of "Parkinson's disease"
2. Extract all DOIs
3. Annotate them with EuropePMC to get titles, journals, and citation counts
```

### Interactive co-citation network

```
Build a co-citation network for:
COVID-19, COVID-19 pandemic, COVID-19 vaccine
Show pairs that share at least 3 DOIs.
```
→ Returns a self-contained interactive HTML network you can open in a browser.

### Revert trend analysis

```
How many edits were reverted on Wikipedia between 2023-01-01 and 2023-12-31?
```

---

## Tool reference

### Group 1 — History & metadata (14 tools)

| Tool | Key arguments | Returns |
|---|---|---|
| `get_article_history` | `article_name`, `date_limit` | revision table |
| `get_article_recent` | `article_name`, `date_limit` | metadata + wikitext |
| `get_article_initial` | `article_name` | metadata + wikitext |
| `get_article_info` | `article_name` | pageid, size, title |
| `get_tables_all` | `article_name`, `date_limit` | all tables in one call |
| `get_category_pages` | `category` | page name list |
| `get_pages_in_cat_table` | `category` | page table |
| `get_subcat_table` | `catname` | direct subcategories |
| `get_subcat_multiple` | `catname_list` | subcategories for N categories |
| `get_subcat_with_depth` | `catname`, `depth` | recursive subcategories |
| `get_page_in_cat_multiple` | `catname_list` | pages for N categories |
| `get_category_history` | `article_list`, `date_limit` | revision table |
| `get_category_recent` | `article_list`, `date_limit` | metadata + wikitext list |
| `get_category_creation` | `article_list` | creation revision table |

### Group 2 — Citation counting, extraction & quality (19 tools)

| Tool | Key arguments | Returns |
|---|---|---|
| `get_doi_count` | `text` | `{count}` |
| `get_ref_count` | `text` | `{count}` |
| `get_url_count` | `text` | `{count}` |
| `get_isbn_count` | `text` | `{count}` |
| `get_hyperlink_count` | `text` | `{count}` |
| `get_any_count` | `text`, `regexp` | `{count}` |
| `extract_citations` | `text` | list of CS1 templates |
| `extract_wikihypelinks` | `text` | list of `[[...]]` links |
| `replace_wikihypelinks` | `text` | cleaned text |
| `parse_cite_type` | `text` | parsed CS1 fields |
| `extract_with_regex` | `article_name`, `regexp`, `date_limit` | matches table |
| `extract_all_regex` | `article_name`, `date_limit` | all regex matches |
| `parse_citations` | `article_name`, `date_limit` | structured citation table |
| `parse_all_citations` | `article_name`, `date_limit` | full long-form table |
| `get_citation_types` | `article_name`, `date_limit` | counts by type |
| `get_source_type_counts` | `text` | counts from raw text |
| `get_sci_score` | `article_name`, `date_limit` | `sci_score`, `sci_score2` |
| `get_top_cited_papers` | `article_name`, `date_limit` | top 40 DOIs |
| `get_revert_counts` | `start`, `end` | revert statistics |

### Group 3 — DOI & ISBN annotation (7 tools)

| Tool | Key arguments | Returns |
|---|---|---|
| `annotate_dois_europmc` | `doi_list` | EuropePMC metadata |
| `annotate_dois_crossref` | `doi_list` | CrossRef metadata (requires `bibtex` R package) |
| `annotate_dois_altmetric` | `doi_list` | Altmetric scores (requires `rAltmetric`) |
| `annotate_dois_bibtex` | `doi_list` | BibTeX entries (requires `bibtex` R package) |
| `annotate_isbn_google` | `isbn` | Google Books metadata |
| `annotate_isbn_openlib` | `isbn` | Open Library metadata |
| `annotate_isbns_altmetric` | `isbn_list` | Altmetric scores (requires `rAltmetric`) |

### Group 4 — Static PNG plots (6 tools)

| Tool | Key arguments |
|---|---|
| `plot_article_creation` | `article_list`, `title`, `cumsum` |
| `plot_static_timeline` | `article_list` |
| `plot_citation_distribution` | `article_list` |
| `plot_top_source` | `article_name`, `source_type`, `date_limit` |
| `plot_page_views` | `article_name`, `start`, `end` |
| `plot_page_edits` | `article_name`, `start`, `end` |

### Group 5 — Interactive HTML plots (4 tools)

| Tool | Key arguments |
|---|---|
| `plot_interactive_timeline` | `article_list`, `date_limit`, `color_by` |
| `plot_publication_network` | `article_list`, `top_n_dois`, `min_wiki_count`, `annotate` |
| `plot_cocitation_network` | `article_list`, `min_shared_dois` |
| `plot_wikilink_network` | `article_list`, `only_internal`, `top_n_links` |

Interactive tools return `{"html": "<self-contained HTML>", "format": "html", "description": "..."}`.

---

## Running tests

```bash
# Unit tests — no R, no network required
uv run pytest tests/ -m "not integration" -v

# Integration tests — require R + wikilite + internet
uv run pytest tests/ -m integration -v

# All tests
uv run pytest tests/ -v
```

---

## Troubleshooting

**`Rscript not found`**

macOS / Linux — add R to your shell profile:
```bash
export PATH="/usr/bin:$PATH"          # or /opt/homebrew/bin on macOS
```

Windows — add R to your user PATH permanently (PowerShell, run once, then reopen PowerShell):
```powershell
[Environment]::SetEnvironmentVariable(
  "Path",
  $env:Path + ";C:\Program Files\R\R-4.2.3\bin",
  "User"
)
```

Or use the full path without modifying PATH at all:
```powershell
'{"tool":"get_doi_count","args":{"text":"test"}}' | & "C:\Program Files\R\R-4.2.3\bin\Rscript.exe" mcp_interface.R
```

> Find your installed R version with: `Get-ChildItem "C:\Program Files\R"`

**`wikilite not found in R`**
```r
install.packages("devtools")
devtools::install_github("jsobel1/wikilite")
```

**`htmlwidgets not found` (interactive plot tools)**
```r
install.packages("htmlwidgets")
```

**`Please install bibtex` (CrossRef annotation tools)**
```r
install.packages("bibtex")
```

**Timeout on large edit histories**  
Increase `DEFAULT_TIMEOUT` in `r_bridge.py` (default: 120 s).

**Server not appearing in Claude Code**
```bash
claude mcp remove wikilite
claude mcp add wikilite -- uv run python server.py
claude mcp list
```

---

## Related

- [wikilite R package](https://github.com/jsobel1/wikilite) — the underlying R package
- [Model Context Protocol](https://modelcontextprotocol.io) — MCP specification
- [FastMCP](https://github.com/jlowin/fastmcp) — Python MCP framework used here
