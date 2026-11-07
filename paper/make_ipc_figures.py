#!/usr/bin/env python
"""Figures, Table 1 and summary numbers for the IPC example (reads data/ipc_raw.json).

    python make_ipc_figures.py [--no-crossref]

Writes fig_ipc_sciscore.png, fig_ipc_time.png, fig_ipc_languages.png,
table1_ipc_top_papers.md and data/ipc_summary.json next to this script.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import urllib.parse
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
FINAL = "2026-11-01"
MIN_T = 5  # minimum citation templates for a SciScore to be shown

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8.5, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.titlesize": 9.5, "axes.titleweight": "bold",
                     "axes.titlelocation": "left"})
CAT_SHORT = {"Infection-control measures": "Infection-\ncontrol meas.",
             "Health care-associated infections": "Health care-\nassoc. infect.",
             "Isolation (health care)": "Isolation\n(health care)",
             "Medical hygiene": "Medical\nhygiene"}
CAT_COL = {"Infection-control measures": "#4C78A8", "Health care-associated infections": "#E45756",
           "Isolation (health care)": "#54A24B", "Medical hygiene": "#B279A2"}
TYPE_ORDER = ["journal", "book", "web", "news", "report", "other"]
TYPE_COL = {"journal": "#4C78A8", "book": "#F58518", "web": "#9ECAE9", "news": "#E45756",
            "report": "#B279A2", "other": "#BAB0AC"}
KEY_COL = ["#4C78A8", "#E45756", "#54A24B", "#F58518", "#B279A2", "#72B7B2", "#9D755D", "#555555"]
LANGS = ["en", "fr", "de", "es", "it", "pt"]


def load() -> dict:
    return json.loads((DATA / "ipc_raw.json").read_text())


def snap(d: dict, art: str, date: str) -> dict | None:
    s = d["snapshots"].get(f"{art}|{date}")
    return s if s and s.get("revid") else None


def fig_sciscore(d: dict, summ: dict) -> None:
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.2, 3.8), gridspec_kw={"width_ratios": [1.15, 1]})
    cats = list(d["categories"])
    rng = np.random.default_rng(1)
    comp = {}
    for i, cat in enumerate(cats):
        vals, tc = [], Counter()
        for art in d["categories"][cat]:
            s = snap(d, art, FINAL)
            if not s:
                continue
            for t, n in s["types"].items():
                tc[t if t in TYPE_ORDER else "other"] += n
            if s["n_templates"] >= MIN_T:
                vals.append(s["sci_score"])
        comp[cat] = tc
        a1.boxplot(vals, positions=[i], widths=0.5, showfliers=False,
                   medianprops=dict(color="black"), boxprops=dict(color="#666"),
                   whiskerprops=dict(color="#666"), capprops=dict(color="#666"))
        a1.scatter(i + rng.uniform(-0.17, 0.17, len(vals)), vals, s=16, alpha=0.8,
                   color=CAT_COL[cat], edgecolor="white", linewidth=0.4, zorder=3)
        a1.text(i, 1.05, f"n={len(vals)}", ha="center", fontsize=7.5, color="#444")
        summ.setdefault("category", {})[cat] = {
            "n_articles": len(d["categories"][cat]), "n_scored": len(vals),
            "median_sci": round(median(vals), 3) if vals else None,
            "type_totals": dict(tc)}
    a1.set_xticks(range(len(cats)), [CAT_SHORT[c] for c in cats], fontsize=7.8)
    a1.set_ylim(-0.03, 1.1)
    a1.set_ylabel("SciScore (journal / all citation templates)")
    a1.set_title("A  SciScore per article, by category")
    # composition
    left = np.zeros(len(cats))
    for t in TYPE_ORDER:
        share = np.array([comp[c][t] / max(1, sum(comp[c].values())) for c in cats])
        a2.barh(range(len(cats)), share, left=left, color=TYPE_COL[t], label=t, height=0.6,
                edgecolor="white", linewidth=0.5)
        for j, v in enumerate(share):
            if v > 0.07:
                a2.text(left[j] + v / 2, j, f"{v:.0%}", ha="center", va="center", fontsize=7,
                        color="white" if t in ("journal", "news", "report") else "#222")
        left += share
    a2.set_yticks(range(len(cats)), [f"{CAT_SHORT[c]}\n({sum(comp[c].values())} templates)"
                                     for c in cats], fontsize=7.6)
    a2.invert_yaxis()
    a2.set_xlim(0, 1)
    a2.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    a2.set_title("B  Citation-template types")
    a2.legend(ncol=6, fontsize=7, frameon=False, loc="upper center", bbox_to_anchor=(0.45, -0.1),
              handlelength=1, columnspacing=0.8)
    fig.tight_layout()
    fig.savefig(HERE / "fig_ipc_sciscore.png", dpi=300, facecolor="white")
    plt.close(fig)


def fig_time(d: dict, summ: dict) -> None:
    dates = sorted({k.split("|")[1] for k in d["snapshots"]})
    x = [dt.date.fromisoformat(s) for s in dates]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.2, 3.6))
    keys = ["Hand washing", "Hospital-acquired infection", "Infection prevention and control",
            "Hand sanitizer", "Personal protective equipment", "Surgical mask",
            "Antimicrobial stewardship", "Universal precautions"]
    summ["key_series"] = {}
    for art, col in zip(keys, KEY_COL):
        ys, ns = [], []
        for s_ in dates:
            s = snap(d, art, s_)
            ok = s and s["n_templates"] >= MIN_T
            ys.append(s["sci_score"] if ok else np.nan)
            ns.append(s["n_templates"] if s else 0)
        summ["key_series"][art] = {"sci": dict(zip(dates, [None if np.isnan(v) else v for v in ys])),
                                   "n_templates": dict(zip(dates, ns))}
        a1.plot(x, ys, marker="o", ms=3, lw=1.4, color=col, label=art)
    a1.set_ylim(0, 1)
    a1.set_ylabel("SciScore")
    a1.set_title("A  Key IPC articles")
    a1.legend(fontsize=6.6, frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.12),
              handlelength=1.4, columnspacing=0.8)
    # corpus totals
    tot, doi, nart, journal = [], [], [], []
    for s_ in dates:
        T = D = J = A = 0
        for art in d["corpus"]:
            s = snap(d, art, s_)
            if s:
                A += 1
                T += s["n_templates"]
                D += s["templates_with_doi"]
                J += s["types"].get("journal", 0)
        tot.append(T); doi.append(D / T if T else 0); nart.append(A); journal.append(J)
    summ["corpus_series"] = {s_: {"articles": a, "templates": t, "with_doi": round(p, 3), "journal": j}
                             for s_, a, t, p, j in zip(dates, nart, tot, doi, journal)}
    w = [dt.timedelta(days=150)] * len(x)
    a2.bar(x, tot, width=w, color="#BFD3E6", label="citation templates")
    a2.bar(x, journal, width=w, color="#4C78A8", label="journal templates")
    a2.set_ylabel("Citation templates in corpus")
    a2.set_title("B  Whole corpus")
    b2 = a2.twinx()
    b2.spines["top"].set_visible(False)
    b2.plot(x, [100 * v for v in doi], color="#E45756", marker="o", ms=3, lw=1.5, label="% with DOI")
    b2.set_ylim(0, 100)
    b2.set_ylabel("% of templates with a DOI", color="#E45756")
    h1, l1 = a2.get_legend_handles_labels(); h2, l2 = b2.get_legend_handles_labels()
    a2.legend(h1 + h2, l1 + l2, fontsize=7, frameon=False, loc="upper left")
    for ax in (a1, a2):
        ax.axvline(dt.date(2020, 3, 11), color="#888", ls="--", lw=0.9)
        ax.text(dt.date(2020, 3, 11), ax.get_ylim()[1] * 0.98, " COVID-19\n pandemic", fontsize=6.6,
                color="#666", va="top")
        ax.xaxis.set_major_locator(mdates.YearLocator(2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.tight_layout()
    fig.savefig(HERE / "fig_ipc_time.png", dpi=300, facecolor="white")
    plt.close(fig)


def fig_langs(d: dict, summ: dict) -> None:
    arts = [a for a in d.get("langs", {})]
    if not arts:
        return
    M = np.full((len(arts), len(LANGS)), np.nan)
    N = np.zeros_like(M)
    summ["languages"] = {}
    for i, art in enumerate(arts):
        row = {"en": snap(d, art, FINAL)}
        row.update(d["langs"][art])
        summ["languages"][art] = {}
        for j, lg in enumerate(LANGS):
            s = row.get(lg)
            if s and s.get("revid"):
                N[i, j] = s["n_templates"]
                summ["languages"][art][lg] = {"title": s.get("title", art), "sci": s["sci_score"],
                                              "n": s["n_templates"], "refs": s.get("n_refs")}
                if s["n_templates"] >= MIN_T:
                    M[i, j] = s["sci_score"]
    fig, ax = plt.subplots(figsize=(6.6, 3.7))
    cmap = matplotlib.colormaps["Blues"].copy()
    cmap.set_bad("#EEEEEE")
    im = ax.imshow(np.ma.masked_invalid(M), cmap=cmap, vmin=0, vmax=1, aspect="auto")
    for i in range(len(arts)):
        for j in range(len(LANGS)):
            if np.isnan(M[i, j]):
                txt = "—" if N[i, j] == 0 else f"({int(N[i, j])})"
                ax.text(j, i, txt, ha="center", va="center", fontsize=7, color="#888")
            else:
                ax.text(j, i, f"{M[i, j]:.2f}\n({int(N[i, j])})", ha="center", va="center",
                        fontsize=6.8, color="white" if M[i, j] > 0.55 else "#222")
    ax.set_xticks(range(len(LANGS)), LANGS)
    ax.set_yticks(range(len(arts)), arts, fontsize=7.8)
    ax.xaxis.tick_top()
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
    cb.set_label("SciScore", fontsize=8)
    fig.tight_layout()
    fig.savefig(HERE / "fig_ipc_languages.png", dpi=300, facecolor="white")
    plt.close(fig)


def crossref(doi: str) -> dict:
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi)
    p = subprocess.run(["curl", "-sS", "-m", "30", "-A", "wikicitation-joss-example/0.1", url],
                       capture_output=True, text=True)
    try:
        return json.loads(p.stdout)["message"]
    except Exception:
        return {}


def table_top(d: dict, summ: dict, use_crossref: bool) -> None:
    by_doi = defaultdict(set)
    for art in d["corpus"]:
        s = snap(d, art, FINAL)
        for doi in (s or {}).get("dois", []):
            by_doi[doi].add(art)
    summ["unique_dois_final"] = len(by_doi)
    top = sorted(by_doi.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:12]
    lines = ["| Paper | Year | Crossref citations | Corpus articles citing it |",
             "|:--|--:|--:|:--|"]
    rows = []
    for doi, arts in top:
        m = crossref(doi) if use_crossref else {}
        au = m.get("author", [{}])
        first = au[0].get("family", au[0].get("name", "")) if au else ""
        etal = " et al." if len(au) > 2 else (f" & {au[1].get('family', '')}" if len(au) == 2 else "")
        title = (m.get("title") or [doi])[0]
        jn = (m.get("container-title") or [""])[0]
        yr = (m.get("issued", {}).get("date-parts") or [[None]])[0][0]
        rows.append({"doi": doi, "n_articles": len(arts), "articles": sorted(arts), "first_author": first,
                     "title": title, "journal": jn, "year": yr,
                     "crossref_citations": m.get("is-referenced-by-count")})
        lines.append(f"| {first}{etal}, *{title}*, {jn} | {yr or ''} | "
                     f"{m.get('is-referenced-by-count', '')} | {len(arts)}: {', '.join(sorted(arts))} |")
    summ["top_dois"] = rows
    (HERE / "table1_ipc_top_papers.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-crossref", action="store_true")
    a = ap.parse_args()
    d = load()
    summ: dict = {"n_corpus": len(d["corpus"]),
                  "n_categories": {c: len(v) for c, v in d["categories"].items()}}
    fin = [snap(d, art, FINAL) for art in d["corpus"]]
    fin = [s for s in fin if s]
    summ["final"] = {"articles": len(fin), "templates": sum(s["n_templates"] for s in fin),
                     "with_doi": sum(s["templates_with_doi"] for s in fin),
                     "refs": sum(s["n_refs"] for s in fin),
                     "scored": sum(1 for s in fin if s["n_templates"] >= MIN_T),
                     "zero_templates": sum(1 for s in fin if s["n_templates"] == 0),
                     "median_sci": median(s["sci_score"] for s in fin if s["n_templates"] >= MIN_T)}
    summ["final"]["sci_by_article"] = {s["article"]: [s["sci_score"], s["n_templates"]] for s in fin}
    summ["created"] = d.get("created", {})
    fig_sciscore(d, summ)
    fig_time(d, summ)
    fig_langs(d, summ)
    table_top(d, summ, not a.no_crossref)
    (DATA / "ipc_summary.json").write_text(json.dumps(summ, indent=1, default=str))
    print(json.dumps({k: summ[k] for k in ("n_corpus", "final")}, indent=1, default=str)[:3000])


if __name__ == "__main__":
    main()
