#!/usr/bin/env python3
"""
Build a review page for one night's archived golden-hour frames.

The archive is written by BeachCamService._archive_golden_frame:

    data/golden_archive/<date>/<phase>/HHMMSS_score0.812.png
    data/golden_archive/<date>/<phase>/manifest.jsonl

This renders those into a single self-contained HTML page — frames in time
order, each with its score breakdown, and the algorithm's pick flagged. The
point is to answer one question by eye: *did it choose the best frame?*

Stdlib only, so it runs on the Pi or on a laptop after an scp.

Usage:
    python3 golden_review.py data/golden_archive/2026-08-21/sunset
    python3 golden_review.py <dir> -o /tmp/review.html
"""

import argparse
import json
from pathlib import Path

CSS = """
:root { --bg:#14161a; --card:#1e2127; --edge:#2c313a; --fg:#e6e8eb;
        --dim:#9aa3af; --win:#f0a83c; --accent:#5aa9e6; }
* { box-sizing:border-box; }
body { margin:0; padding:24px; background:var(--bg); color:var(--fg);
       font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
h1 { font-size:19px; margin:0 0 4px; }
.sub { color:var(--dim); margin-bottom:20px; font-size:13px; }
.sub b { color:var(--fg); font-weight:600; }
.grid { display:grid; gap:16px;
        grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); }
.card { background:var(--card); border:1px solid var(--edge);
        border-radius:10px; overflow:hidden; }
.card.win { border-color:var(--win); box-shadow:0 0 0 2px rgba(240,168,60,.22); }
.card img { width:100%; display:block; background:#000; }
.meta { padding:10px 12px; }
.row1 { display:flex; align-items:baseline; justify-content:space-between; gap:8px; }
.time { font-weight:600; font-variant-numeric:tabular-nums; }
.score { font-variant-numeric:tabular-nums; font-weight:700; color:var(--accent); }
.card.win .score { color:var(--win); }
.badge { display:inline-block; margin-top:6px; padding:1px 7px; border-radius:99px;
         background:var(--win); color:#1a1206; font-size:11px; font-weight:700; }
.rank { color:var(--dim); font-size:12px; }
table { width:100%; margin-top:8px; border-collapse:collapse; font-size:12px; }
td { padding:1px 0; color:var(--dim); }
td.v { text-align:right; color:var(--fg); font-variant-numeric:tabular-nums; }
.warn { margin-top:6px; font-size:12px; color:#e6a2a2; }
.empty { color:var(--dim); }
"""

FIELDS = [
    ("base", "base (composition)"),
    ("bonus", "warm-sky bonus"),
    ("bonus_weighted", "bonus x0.5"),
    ("vivid_pct", "vivid px"),
    ("pastel_pct", "pastel px"),
    ("p95_r_minus_b", "p95 R-B"),
    ("tail_score", "tail score"),
    ("warm_score", "warm score (pre-clamp)"),
    ("sky_mean_r", "sky mean R"),
    ("sky_mean_b", "sky mean B"),
]


def load(directory: Path) -> list:
    manifest = directory / "manifest.jsonl"
    if not manifest.exists():
        raise SystemExit(f"no manifest.jsonl in {directory}")
    rows = []
    for line in manifest.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    rows.sort(key=lambda r: r.get("time", ""))
    return rows


def fmt(key, val):
    if val is None:
        return "-"
    if key.endswith("_pct"):
        return f"{val * 100:.1f}%"
    if isinstance(val, float):
        return f"{val:.3f}"
    return str(val)


def render(rows: list, directory: Path) -> str:
    if not rows:
        return f"<!-- empty -->\n<h1>No frames archived</h1><p class=empty>{directory}</p>"

    best = max(rows, key=lambda r: r.get("score", 0))
    order = sorted(rows, key=lambda r: -r.get("score", 0))
    rank = {id(r): i + 1 for i, r in enumerate(order)}

    span = f"{rows[0]['time'][11:16]} - {rows[-1]['time'][11:16]}"
    day = rows[0].get("time", "")[:10]
    phase = rows[0].get("phase", "?")

    cards = []
    for r in rows:
        win = r is best
        tds = "".join(
            f"<tr><td>{label}</td><td class=v>{fmt(k, r.get(k))}</td></tr>"
            for k, label in FIELDS
            if r.get(k) is not None
        )
        warn = (
            f"<div class=warn>filter: {r['filter_reason']}</div>"
            if r.get("filter_reason")
            else ""
        )
        cls = "card win" if win else "card"
        cards.append(
            f"<div class='{cls}'>"
            f"<img src='{r['file']}' alt='{r['time']}' loading=lazy>"
            f"<div class=meta><div class=row1><span class=time>{r['time'][11:19]}</span>"
            f"<span class=score>{r.get('score', 0):.3f}</span></div>"
            f"<div class=rank>rank {rank[id(r)]} of {len(rows)}</div>"
            f"{'<div class=badge>ALGORITHM PICK</div>' if win else ''}"
            f"<table>{tds}</table>{warn}</div></div>"
        )

    return (
        f"<title>Golden hour {day} {phase}</title>\n<style>{CSS}</style>\n"
        f"<h1>Golden-hour review — {day} ({phase})</h1>\n"
        f"<div class=sub><b>{len(rows)}</b> frames over <b>{span}</b> &middot; "
        f"algorithm picked <b>{best['time'][11:19]}</b> at score "
        f"<b>{best.get('score', 0):.3f}</b><br>"
        f"Frames in time order. Pick the one you think is best, then compare "
        f"with the highlighted card.</div>\n"
        f"<div class=grid>{''.join(cards)}</div>\n"
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("directory", help="archive dir, e.g. data/golden_archive/2026-08-21/sunset")
    ap.add_argument("-o", "--out", help="output html (default: <directory>/review.html)")
    a = ap.parse_args()

    d = Path(a.directory)
    rows = load(d)
    out = Path(a.out) if a.out else d / "review.html"
    out.write_text(render(rows, d))
    print(f"{len(rows)} frames -> {out}")
    if rows:
        best = max(rows, key=lambda r: r.get("score", 0))
        print(f"pick: {best['file']} (score {best.get('score', 0):.3f})")


if __name__ == "__main__":
    main()
