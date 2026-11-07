#!/usr/bin/env python
"""Reproduce the CDSS case study of the wikicitation-mcp paper.

Every number and figure in the "Case Study" section is produced here by calling
the tools of the installed MCP server (stdio), exactly as an MCP client would.

    pip install wikicitation-mcp==0.5.0 fastmcp pandas matplotlib openpyxl
    python reproduce_case_study.py [--server /path/to/wikicitation-mcp]

Outputs (next to this script): data/case_study.json, data/crossref_all.json
and the SciScore figure (Table S1 is written by extended_analyses.py). Results depend on the date of
the run, because Wikipedia and CrossRef citation counts keep changing; the run
date and the revision id of each article are stored in data/case_study.json.
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import re
import shutil
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from fastmcp import Client  # noqa: E402
from fastmcp.client.transports import StdioTransport  # noqa: E402

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"

ARTICLES = [
    "Computer-aided diagnosis", "Drug interaction", "Imaging informatics",
    "Artificial intelligence in healthcare", "Clinical decision support system",
    "Telehealth", "Electronic health record", "Medical diagnosis",
    "Computerized physician order entry", "Health informatics",
    "Clinical pharmacy", "Pharmacy automation", "OpenEvidence",
]
TOP_N_FIGURE = 15
TOP_N_TABLE = 40
DOI_RE = re.compile(r"10\.\d{4,9}/\S+")

TYPE_COLORS = {"journal": "#4C78A8", "web": "#9ECAE9", "book": "#F58518",
               "news": "#E45756", "conference": "#54A24B", "report": "#B279A2",
               "magazine": "#72B7B2", "other": "#BAB0AC"}


async def tool(client: Client, name: str, args: dict):
    res = await client.call_tool(name, args)
    # An empty list result (e.g. no citations in an early revision) has no content block.
    return json.loads(res.content[0].text) if res.content else []


def clean_doi(raw: str) -> str | None:
    m = DOI_RE.search(raw or "")
    if not m:
        return None
    doi = m.group(0).rstrip(".,;")
    # Old SICI-style DOIs contain parentheses and '<...>'; only drop a trailing
    # ')' when it is unbalanced (e.g. "(doi:10.1000/x)").
    while doi.endswith(")") and doi.count(")") > doi.count("("):
        doi = doi[:-1]
    return doi.lower()


async def collect(server: str) -> dict:
    out: dict = {"run_date": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                 "articles": {}}
    async with Client(StdioTransport(command=server, args=[])) as c:
        tools = await c.list_tools()
        out["server_tools"] = len(tools)
        for art in ARTICLES:
            info = await tool(c, "get_article_info", {"article_name": art})
            rec = await tool(c, "get_article_recent", {"article_name": art})
            score = await tool(c, "get_sci_score", {"article_name": art})
            types = await tool(c, "get_citation_types", {"article_name": art})
            cites = await tool(c, "parse_citations", {"article_name": art})
            hist = await tool(c, "get_article_history", {"article_name": art})
            dois = [d for d in (clean_doi(r.get("doi", "")) for r in cites) if d]
            out["articles"][art] = {
                "resolved_title": info.get("title", art),
                "revid": rec["metadata"].get("revid"),
                "revision_timestamp": rec["metadata"].get("timestamp"),
                "n_revisions": len(hist),
                "sci_score": score["sci_score"],
                "types": {t["cite_type"]: t["count"] for t in types},
                "n_templates": len(cites),
                "n_templates_with_doi": len(dois),
                "dois": dois,
            }
            print(f"{art:40s} templates={len(cites):4d} doi={len(dois):4d} "
                  f"sci={score['sci_score']:.2f}", flush=True)

        all_dois = sorted({d for a in out["articles"].values() for d in a["dois"]})
        out["n_unique_dois"] = len(all_dois)
        cr: list[dict] = []
        for i in range(0, len(all_dois), 150):
            cr += await tool(c, "annotate_dois_crossref", {"doi_list": all_dois[i:i + 150]})
        DATA.mkdir(exist_ok=True)
        (DATA / "crossref_all.json").write_text(json.dumps(cr, ensure_ascii=False, indent=1))
        ok = [r for r in cr if "error" not in r]
        out["crossref_ok"] = len(ok)
        out["crossref_failed"] = len(cr) - len(ok)
        ranked = sorted(ok, key=lambda r: r.get("is_referenced_by_count") or 0, reverse=True)
        top = ranked[:TOP_N_TABLE]
        # wiki_count = number of articles of the corpus citing the DOI (any template)
        by_doi_articles = Counter(d for a in out["articles"].values() for d in set(a["dois"]))
        epmc = await tool(c, "annotate_dois_europmc",
                          {"doi_list": [r["doi"] for r in top[:TOP_N_FIGURE]]})
        oa = {(r.get("doi") or "").lower(): bool(r.get("is_open_access")) for r in epmc}
        out["top"] = [{**r, "doi": r["doi"].lower(),
                       "n_corpus_articles": by_doi_articles[r["doi"].lower()],
                       "open_access": oa.get(r["doi"].lower())} for r in top]

    return out


def bucket(types: dict[str, int]) -> dict[str, int]:
    known = ["journal", "web", "book", "news", "report", "magazine", "conference"]
    b = {k: types.get(k, 0) for k in known}
    b["other"] = sum(v for k, v in types.items() if k not in known)
    return b


def make_figures(d: dict) -> None:
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
    arts = d["articles"]
    run = d["run_date"][:10]

    # Fig: SciScore per article
    s = sorted(arts.items(), key=lambda kv: kv[1]["sci_score"])
    fig, ax = plt.subplots(figsize=(8, 5.2))
    cols = ["#1B9641" if v["sci_score"] >= .7 else "#F57F00" if v["sci_score"] >= .4 else "#D7301F"
            for _, v in s]
    ax.barh([k for k, _ in s], [v["sci_score"] for _, v in s], color=cols, height=.62)
    for i, (_, v) in enumerate(s):
        ax.text(v["sci_score"] + .01, i, f"{v['sci_score']:.2f}", va="center", fontsize=8)
    ax.axvline(.4, ls="--", c="#F57F00", alpha=.6, lw=1)
    ax.axvline(.7, ls="--", c="#1B9641", alpha=.6, lw=1)
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("SciScore (proportion of citation templates that cite journal articles)")
    ax.set_title(f"SciScore: CDSS Wikipedia corpus ({run})")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color="#1B9641", label="High (≥ 0.70)"),
                       Patch(color="#F57F00", label="Mid (0.40–0.69)"),
                       Patch(color="#D7301F", label="Low (< 0.40)")], loc="lower right")
    fig.tight_layout()
    fig.savefig(HERE / "cdss_fig1_sciscore.png", dpi=170)
    plt.close(fig)


def summarise(d: dict) -> dict:
    arts = d["articles"]
    tot = sum(a["n_templates"] for a in arts.values())
    with_doi = sum(a["n_templates_with_doi"] for a in arts.values())
    types: Counter = Counter()
    for a in arts.values():
        types.update(a["types"])
    return {"run_date": d["run_date"], "n_articles": len(arts), "n_templates": tot,
            "n_templates_with_doi": with_doi, "pct_with_doi": round(100 * with_doi / tot, 1),
            "n_unique_dois": d["n_unique_dois"], "crossref_ok": d["crossref_ok"],
            "crossref_failed": d["crossref_failed"],
            "type_share_pct": {k: round(100 * v / tot, 1) for k, v in types.most_common(8)}}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default=shutil.which("wikicitation-mcp"),
                    help="path of the wikicitation-mcp executable")
    ap.add_argument("--reuse", action="store_true", help="re-plot from data/case_study.json")
    a = ap.parse_args()
    DATA.mkdir(exist_ok=True)
    f = DATA / "case_study.json"
    if a.reuse and f.exists():
        d = json.loads(f.read_text())
    else:
        d = asyncio.run(collect(a.server))
        f.write_text(json.dumps(d, ensure_ascii=False, indent=1))
    make_figures(d)
    summ = summarise(d)
    (DATA / "summary.json").write_text(json.dumps(summ, indent=1))
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
