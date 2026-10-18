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
2. Reproduce the bug on the latest commit of `master`.

When opening a bug report, include:

- Your operating system and Python version (`python --version`).
- Your Python version and `wikicitation-mcp` version (`wikicitation-mcp --version`).
- The exact tool call or natural-language prompt that triggered the bug.
- The full error message and stack trace.
- Whether the bug is reproducible with a public Wikipedia article (preferred)
  or only with a private/restricted one.

---

## Requesting Features

Open an issue with the label **enhancement**.  Please describe:

- The Wikipedia citation analysis task you are trying to accomplish.
- Whether the R package [wikilite](https://github.com/jsobel1/wikilite) already has an equivalent function (useful as a reference implementation).
- Any relevant API endpoints or data sources involved.

---

## Development Setup

### Prerequisites

| Tool | Minimum version |
|------|----------------|
| Python | 3.10 |
| [uv](https://docs.astral.sh/uv/) | latest |

### Clone and install

```bash
git clone https://github.com/jsobel1/wikicitation-mcp.git
cd wikicitation-mcp

# Create virtual environment and install dependencies
uv sync --dev
```

### Verify the install

```bash
uv run python -c "import wiki_api; print(wiki_api.get_article_info('Zeitgeber'))"
```

A successful response prints the page metadata. R is **not** required.

---

## Running the Test Suite

```bash
uv run pytest
```

The suite has two levels:

| Level | What it tests | Needs network? |
|-------|--------------|----------------|
| Unit | Parsing, validation, tool registry, mocked HTTP layers | No |
| Integration (`--run-integration`) | Live Wikipedia, EuropePMC, CrossRef, Open Library, Google Books | Yes |

Integration tests are skipped unless you pass the flag:

```bash
uv run pytest --run-integration
```

All tests must pass before a pull request will be merged.

---

## Submitting a Pull Request

1. **Fork** the repository and create a feature branch from `master`:

   ```bash
   git checkout -b feature/my-improvement
   ```

2. **Make your changes** following the code style guidelines below.

3. **Add or update tests** — new MCP tools should have at least a unit test
   (mock `wiki_api._client.get` or `annotate_utils._client.get`) and, if it
   calls a public API, an integration test.

4. **Update documentation** — if you add a tool, document it in `README.md`
   under the appropriate category table.

5. **Commit with a descriptive message**:

   ```
   Add get_citation_network tool for co-citation graph export
   ```

6. **Push and open a PR** against `master`.  The PR description should explain
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

**Commits**

- Write commit messages in the imperative mood: *"Add …"*, *"Fix …"*, *"Remove …"*.
- Keep the subject line to 72 characters or fewer.
- Reference issue numbers where applicable: `Fix timeout on large articles (#12)`.

---

## Adding or Modifying Tools

`wikicitation-mcp` is pure Python. To add a new tool:

1. **Implement the logic** as a plain function in `wiki_api.py`,
   `citation_utils.py` or `annotate_utils.py`.

2. **Register the MCP tool** in `server.py` using `@mcp.tool()`. Validate every
   argument with the `_name` / `_lang` / `_date` / `_regex` / `_dois` helpers and
   write a clear docstring: it is shown to the LLM as the tool description.

3. **Write tests** — a unit test for the logic with mocked HTTP, and add the tool
   name to `EXPECTED_TOOLS` in `tests/test_server.py`.

5. **Update `README.md`** — add a row to the relevant category table.

---

## Support and Questions

For general questions about usage, open a
[GitHub Discussion](https://github.com/jsobel1/wikicitation-mcp/discussions).
For bug reports and feature requests, use
[GitHub Issues](https://github.com/jsobel1/wikicitation-mcp/issues).

This project is maintained by a single developer.  Response times may vary,
but all issues and PRs will receive a reply within two weeks.
