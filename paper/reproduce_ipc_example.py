#!/usr/bin/env python
"""Reproduce the infection prevention and control (IPC) example of the JOSS paper.

All data are obtained by calling the tools of the installed wikicitation-mcp
server over stdio, exactly as an AI assistant (MCP client) would:

    pip install wikicitation-mcp fastmcp matplotlib numpy
    python reproduce_ipc_example.py            # collect -> data/ipc_raw.json
    python make_ipc_figures.py                 # figures, table, summary

Snapshots are taken just before 00:00 UTC on each date in SNAP_DATES
(date_limit = previous day, 23:59:59Z).  The corpus is the current membership of
four English Wikipedia categories plus eight key IPC articles; earlier snapshots
therefore describe today's corpus at past dates.  Revision ids are stored so the
same wikitext can be re-fetched later; Crossref counts change over time.
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import re
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"

CATEGORIES = ["Infection-control measures", "Health care-associated infections",
              "Isolation (health care)", "Medical hygiene"]
SNAP_DATES = ["2010-01-01", "2012-01-01", "2014-01-01", "2016-01-01", "2018-01-01",
              "2020-01-01", "2021-01-01", "2022-01-01", "2024-01-01", "2026-11-01"]
KEY_ARTICLES = ["Hand washing", "Hospital-acquired infection", "Infection prevention and control",
                "Hand sanitizer", "Personal protective equipment", "Surgical mask",
                "Antimicrobial stewardship", "Universal precautions"]
# Interlanguage titles of the key articles (from the English pages' langlinks).
LANG_TITLES: dict[str, dict[str, str]] = json.loads((HERE / "data" / "ipc_lang_titles.json").read_text()) \
    if (HERE / "data" / "ipc_lang_titles.json").exists() else {}
DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+")


def bound(date: str) -> str:
    d = dt.date.fromisoformat(date) - dt.timedelta(days=1)
    return f"{d.isoformat()}T23:59:59Z"


async def tool(c: Client, name: str, args: dict):
    res = await c.call_tool(name, args)
    return json.loads(res.content[0].text) if res.content else []


async def snapshot(c: Client, art: str, date: str, lang: str = "en") -> dict:
    args = {"article_name": art, "date_limit": bound(date), "lang": lang}
    rec = {"article": art, "date": date, "revid": None}
    # An article that did not exist yet returns empty metadata; any API error
    # raises, so that failures are never mistaken for missing articles.
    recent = await tool(c, "get_article_recent", args)
    meta, text = recent.get("metadata", {}), recent.get("wikitext", "") or ""
    if not meta.get("revid"):
        return rec
    types = {t["cite_type"]: t["count"] for t in await tool(c, "get_citation_types", args)}
    cites = await tool(c, "parse_citations", args)
    sci = await tool(c, "get_sci_score", args)
    refs = await tool(c, "get_ref_count", {"text": text})
    rec.update(revid=meta["revid"], timestamp=meta.get("timestamp"), types=types,
               n_templates=sum(types.values()), sci_score=sci["sci_score"],
               templates_with_doi=sum(1 for r in cites if r.get("doi")),
               n_refs=refs["count"], bytes=len(text.encode()),
               dois=sorted({d.lower().rstrip(".,;") for d in DOI_RE.findall(text)}))
    return rec


async def collect(server: str) -> None:
    DATA.mkdir(exist_ok=True)
    out: dict = {"run_date": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                 "categories": {}, "snapshots": {}, "created": {}, "langs": {}}
    async with Client(StdioTransport(command=server, args=[])) as c:
        for cat in CATEGORIES:
            out["categories"][cat] = await tool(c, "get_category_pages", {"category": cat})
        corpus = sorted({a for v in out["categories"].values() for a in v} | set(KEY_ARTICLES))
        out["corpus"] = corpus
        for row in await tool(c, "get_category_creation", {"article_list": corpus}):
            out["created"][row.get("art")] = {"revid": row.get("revid"), "timestamp": row.get("timestamp")}
        for art in corpus:
            for d in SNAP_DATES:
                out["snapshots"][f"{art}|{d}"] = await snapshot(c, art, d)
            print(art, flush=True)
        shared: dict[str, int] = {}
        for k, s in out["snapshots"].items():
            if k.endswith("|" + SNAP_DATES[-1]):
                for doi in s.get("dois", []):
                    shared[doi] = shared.get(doi, 0) + 1
        top = sorted(shared, key=lambda x: (-shared[x], x))[:12]
        out["top_dois_crossref"] = await tool(c, "annotate_dois_crossref", {"doi_list": top})
        for art, titles in LANG_TITLES.items():
            out["langs"][art] = {}
            for lg, t in titles.items():
                s = await snapshot(c, t, SNAP_DATES[-1], lg)
                s.pop("dois", None)
                out["langs"][art][lg] = {"title": t, **s}
    (DATA / "ipc_raw.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default="wikicitation-mcp", help="command that starts the server")
    asyncio.run(collect(ap.parse_args().server))
