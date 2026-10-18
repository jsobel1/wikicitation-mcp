# Changelog

All notable changes to `wikicitation-mcp` are documented here.
This project adheres to [Semantic Versioning](https://semver.org/).

---

## [0.5.2] — 2026-10-18

### Added
- `server.json` and an `mcp-name` marker in the README, for listing in the
  official MCP Registry.

No change to the server code or its 38 tools.

---

## [0.5.1] — 2026-10-18

### Added
- `paper/`: JOSS paper, reproducible worked example (scripts, raw data,
  figures) and Table S1 (40 most-cited papers of the CDSS corpus).
- `CITATION.cff` and `.zenodo.json` for citation and archiving metadata.

No change to the server code or its 38 tools.

---

## [0.5.0] — 2026-10-18

The server is again the pure-Python implementation (no R, no `Rscript`
subprocess). `server.py` had been replaced by an R-bridge version with 20 tools
while the hardened pure-Python modules (retries, multilingual parsing, progress
reporting) sat unused; they are wired back in.

### Fixed
- **Pagination bug**: "latest/first revision" calls (`rvlimit=1`) walked the
  article's entire history one revision at a time, downloading full wikitext
  for each. `get_article_recent` / `get_article_initial` took ~40 s and
  triggered Wikipedia HTTP 429, which cascaded into most other tools. They now
  stop after one request (~0.3 s).
- `annotate_*` helpers report the last HTTP status after exhausted retries
  ("HTTP 429") instead of "HTTP transport".
- DOIs are URL-encoded before being placed in CrossRef / doi.org paths.
- `CROSSREF_MAILTO` is now actually read from the environment.
- Unit tests mocked `httpx.get` while the modules use a shared client, so they
  silently hit the network; they now mock the client and never sleep.
- `get_revert_counts` defaults to the last 7 days instead of fixed 2024 dates.
- Redirects are followed (e.g. `fr:Aspirine` used to return the `#REDIRECT` stub, so
  every citation metric silently read 0).

### Added
- 38 tools, all article-level ones with `lang` and `date_limit` (default: now).
- Input validation: list sizes, regex length, text size, DOI/ISBN/date/language
  shape.
- `GOOGLE_BOOKS_API_KEY` support; HTTP 429 hint on `annotate_isbn_google`.
- `wikicitation-mcp --transport streamable-http --port 8000` (stdio by default).
- `--run-integration` pytest flag; regression tests for the pagination bug.
- CI on Python 3.10–3.13 (unit, lint) plus a non-blocking live-API job.

### Removed
- `annotate_dois_altmetric`, `annotate_isbns_altmetric` (Altmetric's public API
  now answers HTTP 403).
- `sci_score2` (DOI/ref-tag ratio; also removed from the `wikilite` R package).
- `r_bridge.py`, `mcp_interface.R`, `tests/test_bridge.py`.

### Packaging
- Wheel now includes `citation_templates.py` and `progress.py` (the 0.3.1 wheel
  omitted them and could not be imported); console entry point is `server:main`.

---

## [0.2.0] — 2026-04-25

### Added
- Streamable-HTTP transport mode for registration with the claude.ai web interface
- `uvx wikicitation-mcp` entry point for pip-installable deployment
- `annotate_doi_list_cross_ref` batch annotation with CrossRef polite-pool support
- `get_sci_score` corpus-wide quality scoring (proportion of templates with a DOI)
- Static and interactive visualisation tools (PNG base64 + self-contained HTML)
- pytest suite: unit tests (mocked subprocess), bridge tests (real Rscript),
  and integration tests (live MediaWiki API, auto-skipped when wikilite absent)

### Changed
- Migrated R backend from `WikiCitationHistoRy` to `wikilite`
- Renamed server from `WikiCitationHistoRy-mcp` to `wikicitation-mcp`
- R bridge now uses a fresh `Rscript` subprocess per call (eliminates shared
  session state and memory leaks; adds ~0.3 s per-call overhead)
- Error boundaries: R-level exceptions are now propagated as descriptive
  Python `RuntimeError` rather than raw stderr output

### Fixed
- `get_top_cited_papers`: resolved `pkg.env not found` error on Windows
- Auto-detection of `Rscript` on Windows when not in `PATH`

---

## [0.1.0] — 2026-01-10

### Added
- Initial public release
- 43 MCP tools wrapping the wikilite R package
- stdio transport (Claude Desktop / Claude Code)
- JSON-over-stdio R bridge (`r_bridge.py` + `mcp_interface.R`)
- Configuration for Claude Desktop (`config/mcp_config.json`)
- Windows installer script (`install.cmd`)
