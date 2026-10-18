"""Shared pytest configuration.

* Tests marked ``integration`` call live public APIs (Wikipedia, EuropePMC,
  CrossRef, Open Library, Google Books). They are skipped unless pytest is run
  with ``--run-integration``.
* Unit tests never sleep: the per-host throttles and retry backoffs are zeroed
  so a mocked 429 does not stall the suite.
"""
import pytest

import annotate_utils
import wiki_api


def pytest_addoption(parser):
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="run tests that call live public APIs",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-integration"):
        return
    skip = pytest.mark.skip(reason="needs network; pass --run-integration")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch, request):
    if "integration" in request.keywords:
        return
    monkeypatch.setattr(wiki_api, "_MIN_INTERVAL_S", 0.0)
    monkeypatch.setattr(wiki_api.time, "sleep", lambda s: None)
    monkeypatch.setattr(annotate_utils, "_MIN_INTERVAL_S", {})
    monkeypatch.setattr(annotate_utils, "_DEFAULT_MIN_INTERVAL", 0.0)
    monkeypatch.setattr(annotate_utils.time, "sleep", lambda s: None)
