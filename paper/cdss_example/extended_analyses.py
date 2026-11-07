#!/usr/bin/env python
"""Extended CDSS analyses for the wikicitation-mcp paper.

Complements reproduce_case_study.py (which must have been run first: it writes
data/case_study.json and data/crossref_all.json) with analyses that exercise
other tools of the server:

  1. temporal    -- yearly snapshots of the 13-article corpus (date_limit)
  2. literature  -- publication years, journals and open-access status of the
                    cited papers (CrossRef + EuropePMC)
  3. categories  -- audit of every article of four Wikipedia categories
  4. languages   -- the same topics in the fr/de/es/it/pt Wikipedias

Every number comes from calls to the installed MCP server over stdio, except
the interlanguage titles of step 5, which are resolved with the MediaWiki
`langlinks` API (the server has no tool for that).

    python extended_analyses.py [--server /path/to/wikicitation-mcp] [--reuse]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path

import httpx
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from fastmcp import Client  # noqa: E402
from fastmcp.client.transports import StdioTransport  # noqa: E402

from reproduce_case_study import ARTICLES, TYPE_COLORS, clean_doi, tool  # noqa: E402

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
YEARS = list(range(2012, 2027))
CATEGORIES = ["Medical expert systems", "Electronic health records", "Telehealth",
              "Health informatics"]
MIN_TEMPLATES = 5            # SciScore is not meaningful below this
LANGS = ["en", "fr", "de", "es", "it", "pt"]
LANG_ARTICLES = ["Clinical decision support system", "Electronic health record",
                 "Telehealth", "Health informatics", "Artificial intelligence in healthcare",
                 "Computer-aided diagnosis"]
SEM = asyncio.Semaphore(4)


async def call(c: Client, name: str, args: dict):
    async with SEM:
        return await tool(c, name, args)


def summarise_citations(rows: list[dict]) -> dict:
    n = len(rows)
    journal = sum(1 for r in rows if r["cite_type"] == "journal")
    dois = sum(1 for r in rows if clean_doi(r.get("doi", "")))
    return {"n": n, "journal": journal, "doi": dois,
            "sci": (journal / n) if n else None}


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------

async def temporal(c: Client) -> dict:
    async def one(art: str, y: int):
        rows = await call(c, "parse_citations",
                          {"article_name": art, "date_limit": f"{y}-01-01"})
        return art, y, summarise_citations(rows)
    res = await asyncio.gather(*(one(a, y) for a in ARTICLES for y in YEARS))
    out: dict = defaultdict(dict)
    for art, y, s in res:
        out[art][str(y)] = s
    return out


async def literature(c: Client) -> dict:
    cr = json.loads((DATA / "crossref_all.json").read_text())
    dois = [r["doi"].lower() for r in cr if "error" not in r]
    epmc: list[dict] = []
    for i in range(0, len(dois), 150):
        epmc += await tool(c, "annotate_dois_europmc", {"doi_list": dois[i:i + 150]})
    oa = {}
    for r in epmc:
        if r.get("not_found") or "error" in r:
            oa[r["doi"].lower()] = None
        else:
            oa[r["doi"].lower()] = bool(r.get("is_open_access"))
    cs = json.loads((DATA / "case_study.json").read_text())
    by_art = {a: sorted(set(v["dois"])) for a, v in cs["articles"].items()}
    papers = [{"doi": r["doi"].lower(), "year": r.get("year"), "journal": r.get("journal"),
               "cited_by": r.get("is_referenced_by_count"), "oa": oa.get(r["doi"].lower())}
              for r in cr if "error" not in r]
    return {"papers": papers, "by_article": by_art,
            "epmc_found": sum(1 for v in oa.values() if v is not None), "n_dois": len(dois)}


async def categories(c: Client) -> dict:
    out: dict = {}
    for cat in CATEGORIES:
        pages = await call(c, "get_category_pages", {"category": cat})

        async def one(p: str):
            try:
                rows = await call(c, "parse_citations", {"article_name": p})
            except Exception as exc:  # noqa: BLE001 - report and continue
                return p, {"error": str(exc)[:80]}
            return p, summarise_citations(rows)
        res = await asyncio.gather(*(one(p) for p in pages))
        out[cat] = {"n_pages": len(pages), "pages": dict(res)}
        print(f"category {cat}: {len(pages)} pages", flush=True)
    return out


def langlinks(title: str) -> dict[str, str]:
    r = httpx.get("https://en.wikipedia.org/w/api.php",
                  params={"action": "query", "prop": "langlinks", "titles": title,
                          "lllimit": "max", "format": "json", "formatversion": 2},
                  headers={"User-Agent": "wikicitation-mcp-paper/0.5 (jsobel83@gmail.com)"},
                  timeout=30).json()
    return {x["lang"]: x["title"] for x in r["query"]["pages"][0].get("langlinks", [])}


async def languages(c: Client) -> dict:
    out: dict = {}
    for art in LANG_ARTICLES:
        ll = langlinks(art)
        out[art] = {}
        for lang in LANGS:
            title = art if lang == "en" else ll.get(lang)
            if not title:
                out[art][lang] = None
                continue
            rows = await call(c, "parse_citations",
                              {"article_name": title, "lang": lang})
            out[art][lang] = {"title": title, **summarise_citations(rows)}
    return out


async def collect(server: str) -> dict:
    async with Client(StdioTransport(command=server, args=[])) as c:
        d: dict = {}
        for name, fn in [("temporal", temporal), ("literature", literature), ("categories", categories),
                         ("languages", languages)]:
            d[name] = await fn(c)
            print("done:", name, flush=True)
    return d


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

def style() -> None:
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})


def fig_temporal(d: dict) -> None:
    t = d["temporal"]
    order = sorted(ARTICLES, key=lambda a: -(t[a][str(YEARS[-1])]["n"]))
    M = np.full((len(order), len(YEARS)), np.nan)
    for i, a in enumerate(order):
        for j, y in enumerate(YEARS):
            s = t[a][str(y)]
            if s["n"] >= 3:
                M[i, j] = s["sci"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.8), gridspec_kw={"width_ratios": [1.25, 1]})
    cmap = plt.get_cmap("RdYlGn").copy()
    cmap.set_bad("#e6e6e6")
    im = ax1.imshow(M, aspect="auto", cmap=cmap, vmin=0, vmax=1)
    ax1.set_xticks(range(len(YEARS)))
    ax1.set_xticklabels(YEARS, rotation=60)
    ax1.set_yticks(range(len(order)))
    ax1.set_yticklabels(order)
    ax1.set_title("SciScore on 1 January (grey: fewer than 3 templates)")
    fig.colorbar(im, ax=ax1, fraction=.04, pad=.02)
    tot = [sum(t[a][str(y)]["n"] for a in ARTICLES) for y in YEARS]
    jr = [sum(t[a][str(y)]["journal"] for a in ARTICLES) for y in YEARS]
    dd = [sum(t[a][str(y)]["doi"] for a in ARTICLES) for y in YEARS]
    ax2.bar(YEARS, jr, color=TYPE_COLORS["journal"], label="Journal templates")
    ax2.bar(YEARS, [x - j for x, j in zip(tot, jr)], bottom=jr, color=TYPE_COLORS["web"],
            label="Other templates")
    ax2.set_xticks(YEARS[::2])
    ax2.set_xticklabels(YEARS[::2], rotation=60)
    ax2.set_ylabel("Citation templates (13 articles)")
    ax2.set_title("Corpus growth and DOI coverage")
    ax3 = ax2.twinx()
    ax3.plot(YEARS, [100 * x / y if y else np.nan for x, y in zip(dd, tot)], "o-", color="#D7301F",
             label="% templates with DOI")
    ax3.set_ylim(0, 100)
    ax3.set_ylabel("% with DOI")
    ax3.spines["right"].set_visible(True)
    h1, l1 = ax2.get_legend_handles_labels()
    h2, l2 = ax3.get_legend_handles_labels()
    ax2.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(HERE / "fig_temporal.png", dpi=170)
    plt.close(fig)


def fig_literature(d: dict) -> None:
    L = d["literature"]
    papers = [p for p in L["papers"] if p.get("year")]
    years = np.array([int(p["year"]) for p in papers])
    oa = np.array([p["oa"] is True for p in papers])
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), gridspec_kw={"width_ratios": [1.1, 1.3, 1.1]})
    ax = axes[0]
    bins = np.arange(1960, 2031, 5)
    ax.hist([years[oa], years[~oa]], bins=bins, stacked=True,
            color=["#1B9641", "#4C78A8"], label=["Open access (EuropePMC)", "Closed or unknown"])
    ax.set_xlabel("Publication year")
    ax.set_ylabel("Cited papers")
    ax.set_title(f"Age of the cited literature (n = {len(papers)})")
    ax.legend(fontsize=8, loc="upper left")
    med = int(np.median(years))
    ax.axvline(med, ls="--", c="k", lw=1)
    ax.text(med - 1, ax.get_ylim()[1] * .55, f"median {med}", fontsize=8, ha="right")

    ax = axes[1]
    jc = Counter(p["journal"] for p in papers if p.get("journal"))
    top = jc.most_common(12)[::-1]
    ax.barh([(k if len(k) <= 40 else k[:39] + "\u2026") for k, _ in top], [v for _, v in top],
            color="#4C78A8", height=.65)
    ax.set_xlabel("Cited papers")
    ax.set_title("Most frequent journals")

    ax = axes[2]
    oa_map = {p["doi"]: p["oa"] for p in L["papers"]}
    rows = []
    for a, dois in L["by_article"].items():
        known = [oa_map[x] for x in dois if oa_map.get(x) is not None]
        if len(known) >= 5:
            rows.append((a, 100 * sum(known) / len(known), len(known)))
    rows.sort(key=lambda r: r[1])
    ax.barh([f"{a} (n={n})" for a, _, n in rows], [s for _, s, _ in rows], color="#1B9641", height=.65)
    ax.set_xlabel("% open access (EuropePMC)")
    ax.set_title("Open-access share by article")
    ax.set_xlim(0, 100)
    fig.tight_layout()
    fig.savefig(HERE / "fig_literature.png", dpi=170)
    plt.close(fig)


def fig_categories(d: dict) -> None:
    C = d["categories"]
    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    rng = np.random.default_rng(3)
    labels = []
    for i, cat in enumerate(CATEGORIES):
        pts = [(p, s) for p, s in C[cat]["pages"].items()
               if "error" not in s and s["n"] >= MIN_TEMPLATES]
        x = i + rng.uniform(-.28, .28, len(pts))
        ax.scatter(x, [s["sci"] for _, s in pts], s=[min(10 + s["n"], 160) for _, s in pts],
                   alpha=.55, color="#4C78A8", edgecolor="none")
        med = float(np.median([s["sci"] for _, s in pts])) if pts else np.nan
        ax.hlines(med, i - .35, i + .35, color="#D7301F", lw=2)
        ax.text(i + .38, med, f"median {med:.2f}", va="center", fontsize=8, color="#D7301F")
        labels.append(f"{cat}\n{len(pts)} of {C[cat]['n_pages']} articles\n(≥{MIN_TEMPLATES} templates)")
    ax.set_xticks(range(len(CATEGORIES)))
    ax.set_xticklabels(labels)
    ax.set_ylabel("SciScore")
    ax.set_ylim(-0.03, 1.03)
    ax.set_xlim(-.5, len(CATEGORIES) - .1)
    ax.set_title("SciScore of every article in four Wikipedia categories (dot size = number of templates)")
    fig.tight_layout()
    fig.savefig(HERE / "fig_categories.png", dpi=170)
    plt.close(fig)


def fig_languages(d: dict) -> None:
    Lg = d["languages"]
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    cols = dict(zip(LANGS, ["#4C78A8", "#F58518", "#54A24B", "#E45756", "#B279A2", "#72B7B2"]))
    for i, art in enumerate(LANG_ARTICLES):
        for j, lang in enumerate(LANGS):
            s = Lg[art].get(lang)
            if not s or s["n"] < 3:
                ax.scatter(j, i, marker="x", color="#999999", s=30)
                continue
            ax.scatter(j, i, s=min(30 + 2 * s["n"], 600), color=cols[lang], alpha=.8, edgecolor="k", lw=.4)
            ax.text(j, i + .33, f"{s['sci']:.2f} (n={s['n']})", ha="center", fontsize=7)
    ax.set_xticks(range(len(LANGS)))
    ax.set_xticklabels(LANGS)
    ax.set_yticks(range(len(LANG_ARTICLES)))
    ax.set_yticklabels(LANG_ARTICLES)
    ax.invert_yaxis()
    ax.set_xlim(-.5, len(LANGS) - .5)
    ax.set_ylim(len(LANG_ARTICLES) - .5 + .3, -.5)
    ax.set_title("SciScore across Wikipedia language editions\n(dot size = number of templates; × = no article or fewer than 3 templates)")
    fig.tight_layout()
    fig.savefig(HERE / "fig_languages.png", dpi=170)
    plt.close(fig)


def table_s1(d: dict) -> None:
    """Table S1: the 40 most-cited papers of the 13-article corpus.

    Ranked by Crossref cited-by count; open-access status from Europe PMC;
    "Cited in" lists the corpus articles whose citation templates contain the DOI.
    """
    import html
    import re

    import pandas as pd

    cs = json.loads((DATA / "case_study.json").read_text())
    oa = {p["doi"]: p["oa"] for p in d["literature"]["papers"]}
    rows = []
    for i, r in enumerate(cs["top"], 1):
        title = re.sub(r"<[^>]+>", "", html.unescape(r.get("title") or "")).strip()
        author = (r.get("authors") or [""])[0].strip()
        surname = author.split()[-1] if author else ""
        if surname.isupper():
            surname = surname.title()
        rows.append({
            "Rank": i,
            "First author": surname or "(no author)",
            "Year": r.get("year"),
            "Journal": html.unescape(r.get("journal") or "(book)"),
            "Title": title,
            "DOI": r["doi"],
            "Crossref citations": r["is_referenced_by_count"],
            "Open access": {True: "yes", False: "no"}.get(oa.get(r["doi"]), "unknown"),
            "Cited in (Wikipedia article)": "; ".join(
                a for a, v in cs["articles"].items() if r["doi"] in v["dois"]),
        })
    df = pd.DataFrame(rows)
    df.to_csv(HERE / "tableS1_top40.csv", index=False)
    df.to_excel(HERE / "tableS1_top40.xlsx", index=False)
    head = (f"# Table S1. The 40 most-cited papers in the CDSS corpus\n\n"
            f"Papers cited by 13 English Wikipedia articles on clinical decision support and "
            f"related topics, ranked by Crossref cited-by count. Data retrieved on "
            f"{cs['run_date'][:10]} with `wikicitation-mcp` (`parse_citations`, "
            f"`annotate_dois_crossref`, `annotate_dois_europmc`); open-access status from "
            f"Europe PMC (unknown: DOI not indexed). Produced by `extended_analyses.py`.\n\n")
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        cells = [str(r[c]).replace("|", "/") for c in cols]
        cells[cols.index("DOI")] = f"[{r['DOI']}](https://doi.org/{r['DOI']})"
        lines.append("| " + " | ".join(cells) + " |")
    (HERE / "tableS1_top40.md").write_text(head + "\n".join(lines) + "\n")


def summary(d: dict) -> dict:
    t, L, C, Lg = d["temporal"], d["literature"], d["categories"], d["languages"]
    pap = [p for p in L["papers"] if p.get("year")]
    yrs = [int(p["year"]) for p in pap]
    oa_known = [p["oa"] for p in L["papers"] if p["oa"] is not None]
    cat = {}
    for k, v in C.items():
        sc = [s["sci"] for s in v["pages"].values() if "error" not in s and s["n"] >= MIN_TEMPLATES]
        cat[k] = {"n_pages": v["n_pages"], "n_scored": len(sc),
                  "median_sci": float(np.median(sc)) if sc else None,
                  "q1": float(np.percentile(sc, 25)) if sc else None,
                  "q3": float(np.percentile(sc, 75)) if sc else None,
                  "errors": sum(1 for s in v["pages"].values() if "error" in s)}
    tot = {y: sum(t[a][str(y)]["n"] for a in ARTICLES) for y in YEARS}
    jr = {y: sum(t[a][str(y)]["journal"] for a in ARTICLES) for y in YEARS}
    dd = {y: sum(t[a][str(y)]["doi"] for a in ARTICLES) for y in YEARS}
    return {
        "temporal": {str(y): {"templates": tot[y], "journal_pct": round(100 * jr[y] / tot[y], 1) if tot[y] else None,
                              "doi_pct": round(100 * dd[y] / tot[y], 1) if tot[y] else None} for y in YEARS},
        "literature": {"n_papers": len(pap), "median_year": int(np.median(yrs)),
                       "share_since_2015_pct": round(100 * sum(1 for y in yrs if y >= 2015) / len(yrs), 1),
                       "share_before_2000_pct": round(100 * sum(1 for y in yrs if y < 2000) / len(yrs), 1),
                       "epmc_found": L["epmc_found"], "n_dois": L["n_dois"],
                       "oa_pct_among_found": round(100 * sum(oa_known) / len(oa_known), 1),
                       "top_journals": Counter(p["journal"] for p in pap if p.get("journal")).most_common(8)},
        "categories": cat,
        "categories_unique_scored": len({p for v in C.values() for p, s in v["pages"].items()
                                         if "error" not in s and s["n"] >= MIN_TEMPLATES}),
        "languages": {a: {lg: (None if not v else {"n": v["n"], "sci": v["sci"], "title": v["title"]})
                          for lg, v in Lg[a].items()} for a in LANG_ARTICLES},
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default=shutil.which("wikicitation-mcp"))
    ap.add_argument("--reuse", action="store_true", help="re-plot from data/extended.json")
    a = ap.parse_args()
    f = DATA / "extended.json"
    if a.reuse and f.exists():
        d = json.loads(f.read_text())
    else:
        d = asyncio.run(collect(a.server))
        f.write_text(json.dumps(d, ensure_ascii=False, indent=1))
    style()
    fig_temporal(d)
    fig_literature(d)
    fig_categories(d)
    fig_languages(d)
    table_s1(d)
    s = summary(d)
    (DATA / "extended_summary.json").write_text(json.dumps(s, ensure_ascii=False, indent=1))
    print(json.dumps(s, ensure_ascii=False, indent=1)[:6000])


if __name__ == "__main__":
    main()
