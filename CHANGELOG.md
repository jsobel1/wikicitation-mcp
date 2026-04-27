# Changelog

All notable changes to `wikicitation-mcp` are documented here.
This project adheres to [Semantic Versioning](https://semver.org/).

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
