# wikilite MCP Server

MCP server exposing the R package
[wikilite](https://github.com/jsobel1/wikilite)
as tools usable from **Claude Code**, **Claude Desktop**, and
**claude.ai**.

~50 tools across 5 groups: Wikipedia history & metadata, citation
counting/extraction/quality, DOI/ISBN annotation, static PNG
visualisations, and interactive HTML visualisations.

---

## Prerequisites

| Tool | Minimum version |
|---|---|
| Python | 3.10 |
| R | 4.0 |
| uv | latest |
| wikilite | installed in R |

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify wikilite is installed
Rscript -e "library(wikilite); cat('OK\n')"

# If not installed:
Rscript -e "devtools::install_github('jsobel1/wikilite')"

# Optional: for static plots
Rscript -e "install.packages('base64enc')"

# Optional: for interactive HTML plots
Rscript -e "install.packages('htmlwidgets')"
```

---

## Installation

```bash
# Clone / copy the wikicitation-mcp folder
cd wikicitation-mcp

# Install Python dependencies
uv sync

# Test the R bridge directly
echo '{"tool":"get_doi_count","args":{"text":"see 10.1038/nature12373"}}' \
  | Rscript mcp_interface.R
# -> {"count":1}
```

---

## Connect to Claude Code

```bash
# From the wikicitation-mcp/ folder:
claude mcp add wikilite -- uv run python server.py

# Verify
claude mcp list
# wikilite    stdio    uv run python server.py

# Visual inspector
uv run fastmcp dev server.py
# -> opens http://localhost:5173
```

---

## Connect to Claude Desktop

Edit `~/.claude/claude_desktop_config.json`
(Windows: `%APPDATA%\Claude\claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "wikilite": {
      "command": "uv",
      "args": ["run", "python", "/PATH/TO/wikicitation-mcp/server.py"],
      "env": {
        "R_HOME": "/usr/lib/R"
      }
    }
  }
}
```

Restart Claude Desktop. The `wikilite` server appears in the toolbar.

> **Find your R_HOME:**
> ```bash
> Rscript -e "R.home()"
> ```

---

## Connect to claude.ai (HTTP mode)

```bash
# Start HTTP server
uv run fastmcp run server.py --transport streamable-http --port 8000

# In claude.ai -> Settings -> Connections -> Add MCP server
# URL: http://localhost:8000/mcp
```

For remote access use a tunnel:
```bash
ngrok http 8000
# Public URL: https://xxx.ngrok.io/mcp
```

---

## Available tools (~50 tools)

### Group 1 — Wikipedia history & metadata (14 tools)
| Tool | Description |
|---|---|
| `get_article_history` | Full edit history of an article (no wikitext) |
| `get_article_recent` | Most recent revision + wikitext |
| `get_article_initial` | First revision (creation) + wikitext |
| `get_article_info` | Current metadata (pageid, title, size) |
| `get_tables_all` | Initial + recent + full history + info in one call |
| `get_category_pages` | List pages in a category |
| `get_pages_in_cat_table` | Pages in category as a table |
| `get_subcat_table` | Direct subcategories of a category |
| `get_subcat_multiple` | Subcategories for multiple category names |
| `get_subcat_with_depth` | Recursive subcategories up to a given depth |
| `get_page_in_cat_multiple` | Pages for multiple categories |
| `get_category_history` | Edit history of multiple articles |
| `get_category_recent` | Most recent revision of multiple articles |
| `get_category_creation` | Creation revision of multiple articles |

### Group 2 — Citation counting, extraction & quality (18 tools)
| Tool | Description |
|---|---|
| `get_doi_count` | Count DOIs in text |
| `get_ref_count` | Count `<ref>` tags |
| `get_url_count` | Count URLs |
| `get_isbn_count` | Count ISBNs |
| `get_hyperlink_count` | Count `[[...]]` links |
| `get_any_count` | Count matches for a custom regex |
| `extract_citations` | Extract CS1 citation templates |
| `extract_wikihypelinks` | Extract Wikipedia hyperlinks |
| `replace_wikihypelinks` | Clean wikitext (remove `[[]]` syntax) |
| `parse_cite_type` | Parse a single CS1 template string |
| `extract_regex` | Extract citations by regex from an article |
| `extract_all_regex` | Apply all built-in regexes to an article |
| `parse_citations` | Structured parse of all CS1 citations |
| `parse_all_citations` | Full long-form table of all CS1 citations |
| `get_citation_types` | Count citations by type |
| `get_source_type_counts` | Source type counts directly from text |
| `get_sci_score` | SciScore and SciScore2 for an article |
| `get_top_cited_papers` | Top 40 most-cited DOIs in an article |
| `get_revert_counts` | Revert counts across a date range |

### Group 3 — DOI & ISBN annotation (7 tools)
| Tool | Description |
|---|---|
| `annotate_doi_europmc` | Annotate DOI list via EuropePMC |
| `annotate_doi_crossref` | Annotate DOI list via CrossRef |
| `annotate_doi_altmetric` | Altmetric scores for DOIs |
| `annotate_doi_bibtex` | Export DOIs as BibTeX via CrossRef |
| `annotate_isbn_google` | Book metadata via Google Books |
| `annotate_isbn_openlib` | Book metadata via Open Library |
| `annotate_isbn_altmetric` | Altmetric scores for ISBNs |

### Group 4 — Static visualisations (PNG base64, 6 tools)
| Tool | Description |
|---|---|
| `plot_article_creation` | Article creation timeline |
| `plot_static_timeline` | Labelled static timeline |
| `plot_citation_distribution` | Citation source type distribution |
| `plot_top_source` | Top 20 publishers/journals for an article |
| `plot_page_views` | Daily page views for an article |
| `plot_page_edits` | Weekly edit history for an article |

### Group 5 — Interactive visualisations (self-contained HTML, 4 tools)
| Tool | Description |
|---|---|
| `plot_interactive_timeline` | Interactive article timeline coloured by SciScore |
| `plot_publication_network` | Article-publication citation network |
| `plot_cocitation_network` | Co-citation network (articles sharing DOIs) |
| `plot_wikilink_network` | Wikilink network between articles |

Interactive tools return `{"html": "<self-contained HTML>", "format": "html", "description": "..."}`.

---

## Usage examples

Once connected, you can ask Claude:

```
"Give me the edit history of the article Zeitgeber since 2020"

"Count the DOIs in this wikitext: [paste text]"

"Calculate the SciScore of the article 'Sleep deprivation'"

"Annotate these DOIs with EuropePMC: 10.1038/nature12373, 10.1016/j.cell.2020.01.001"

"Generate a creation timeline for: Zeitgeber, Advanced sleep phase disorder, Sleep deprivation"

"Extract all citations from 'Circadian clock' and count how many are
 journal articles vs websites"

"Show me an interactive publication network for the articles in
 Category:Chronobiology"

"What are the revert counts for Wikipedia from 2023-01-01 to 2023-12-31?"
```

---

## Running tests

```bash
# Unit tests (no network, no R required)
uv run pytest tests/ -m "not integration" -v

# Integration tests (require R + wikilite + internet)
uv run pytest tests/ -m integration -v

# All tests
uv run pytest tests/ -v
```

---

## Troubleshooting

**`Rscript not found`**
```bash
# macOS with Homebrew
export PATH="/opt/homebrew/bin:$PATH"
# Linux
export PATH="/usr/bin:$PATH"
# Windows — ensure R bin directory is on PATH
```

**`wikilite not found in R`**
```r
install.packages("devtools")
devtools::install_github("jsobel1/wikilite")
```

**`htmlwidgets not found` (interactive plots)**
```r
install.packages("htmlwidgets")
```

**Timeout on large edit histories**
Increase `DEFAULT_TIMEOUT` in `r_bridge.py` (default: 120s).

**Server not appearing in Claude Code**
```bash
claude mcp list
claude mcp remove wikilite
claude mcp add wikilite -- uv run python server.py
```
