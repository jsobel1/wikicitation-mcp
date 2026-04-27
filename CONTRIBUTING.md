# Contributing to wikicitation-mcp

Thank you for your interest in contributing!  This document explains how to
report bugs, request features, and submit code changes.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Reporting Bugs](#reporting-bugs)
- [Requesting Features](#requesting-features)
- [Development Setup](#development-setup)
- [Running the Test Suite](#running-the-test-suite)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Code Style](#code-style)
- [Adding or Modifying Tools](#adding-or-modifying-tools)
- [Support and Questions](#support-and-questions)

---

## Code of Conduct

This project follows the
[Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/)
code of conduct.  By participating you agree to abide by its terms.  Please
report unacceptable behaviour to the repository maintainer via a private
GitHub message or the email address in `pyproject.toml`.

---

## Reporting Bugs

Before opening an issue, please:

1. Search [existing issues](https://github.com/jsobel1/wikicitation-mcp/issues)
   to avoid duplicates.
2. Reproduce the bug on the latest commit of `main`.

When opening a bug report, include:

- Your operating system and Python version (`python --version`).
- Your R version (`R --version`) and `wikilite` version
  (`packageVersion("wikilite")` inside R).
- The exact tool call or natural-language prompt that triggered the bug.
- The full error message and stack trace (Python side) or R traceback.
- Whether the bug is reproducible with a public Wikipedia article (preferred)
  or only with a private/restricted one.

---

## Requesting Features

Open an issue with the label **enhancement**.  Please describe:

- The Wikipedia citation analysis task you are trying to accomplish.
- Which existing `wikilite` R function, if any, would cover it (see the
  [wikilite documentation](https://github.com/jsobel1/wikilite)).
- Any relevant API endpoints or data sources involved.

---

## Development Setup

### Prerequisites

| Tool | Minimum version |
|------|----------------|
| Python | 3.10 |
| [uv](https://docs.astral.sh/uv/) | latest |
| R | 4.0 |
| wikilite R package | latest (`remotes::install_github("jsobel1/wikilite")`) |

### Clone and install

```bash
git clone https://github.com/jsobel1/wikicitation-mcp.git
cd wikicitation-mcp

# Create virtual environment and install dependencies
uv sync --dev
```

### Verify the R bridge

```bash
uv run python -c "
import asyncio, json
from r_bridge import call_r_tool
result = asyncio.run(call_r_tool('count_citations', {'article': 'Zeitgeber'}))
print(json.dumps(result, indent=2))
"
```

A successful response returns a JSON object with citation counts.  If you see
a `RuntimeError`, check that `Rscript` is on your `PATH` and that `wikilite`
is installed in R.

---

## Running the Test Suite

```bash
uv run pytest
```

The suite has three levels:

| Level | What it tests | Requires R? |
|-------|--------------|-------------|
| Unit | JSON serialisation, error propagation, timeout handling | No |
| Bridge | Real `Rscript` subprocess against known wikitext | Yes |
| Integration | Live MediaWiki API calls (skipped if `wikilite` absent) | Yes + network |

To run only unit tests (no R needed):

```bash
uv run pytest -k "not bridge and not integration"
```

To run the full suite including live API calls:

```bash
uv run pytest --run-integration
```

All tests must pass before a pull request will be merged.

---

## Submitting a Pull Request

1. **Fork** the repository and create a feature branch from `main`:

   ```bash
   git checkout -b feature/my-improvement
   ```

2. **Make your changes** following the code style guidelines below.

3. **Add or update tests** — new MCP tools should have at least a unit test
   (mocked subprocess) and a bridge test.

4. **Update documentation** — if you add a tool, document it in `README.md`
   under the appropriate category table.

5. **Commit with a descriptive message**:

   ```
   Add get_citation_network tool for co-citation graph export
   ```

6. **Push and open a PR** against `main`.  The PR description should explain
   *what* changed and *why*, and link to any relevant issue.

Pull requests are reviewed by the maintainer.  Please allow up to two weeks
for an initial response.  Large or complex changes may require discussion
before implementation — consider opening an issue first.

---

## Code Style

**Python**

- Follow [PEP 8](https://peps.python.org/pep-0008/).
- Use type annotations for all function signatures.
- Keep MCP tool docstrings concise — they appear in the LLM tool catalogue.
- Format with [ruff](https://docs.astral.sh/ruff/):

  ```bash
  uv run ruff format .
  uv run ruff check .
  ```

**R**

- Follow the [tidyverse style guide](https://style.tidyverse.org/) for any
  changes to `mcp_interface.R`.
- All R-level errors must be caught and returned as a JSON object with key
  `"error"` so the Python bridge can re-raise them as descriptive
  `RuntimeError` exceptions.

**Commits**

- Write commit messages in the imperative mood: *"Add …"*, *"Fix …"*, *"Remove …"*.
- Keep the subject line to 72 characters or fewer.
- Reference issue numbers where applicable: `Fix timeout on large articles (#12)`.

---

## Adding or Modifying Tools

`wikicitation-mcp` wraps functions from the `wikilite` R package.  To add a
new tool:

1. **Identify the `wikilite` function** you want to expose and its expected
   arguments and return structure.

2. **Add the R dispatch** in `mcp_interface.R` — add a case to the main
   `switch` statement that calls the function and returns
   `jsonlite::toJSON(result, auto_unbox = TRUE)`.

3. **Register the MCP tool** in `server.py` using the `@mcp.tool()` decorator.
   Provide a clear docstring and typed argument schema; the docstring text
   is shown to the LLM as the tool description.

4. **Write tests** — at minimum a unit test that mocks the subprocess and
   verifies JSON round-tripping, and a bridge test that exercises the R
   dispatch layer against known input.

5. **Update `README.md`** — add a row to the relevant category table.

---

## Support and Questions

For general questions about usage, open a
[GitHub Discussion](https://github.com/jsobel1/wikicitation-mcp/discussions).
For bug reports and feature requests, use
[GitHub Issues](https://github.com/jsobel1/wikicitation-mcp/issues).

This project is maintained by a single developer.  Response times may vary,
but all issues and PRs will receive a reply within two weeks.
