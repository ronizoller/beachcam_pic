#!/usr/bin/env python3
"""
Chart the battery discharge against the projection frozen on 2026-09-14.

The point is to grade the estimate honestly. The projection below is stored as
data, not recomputed on each run — a forecast you regenerate from the latest
data every time is not a forecast, it is a curve fit, and it can never be wrong.
Whatever the pack actually does gets drawn straight over the line we committed
to, so drift is visible at a glance.

Reads data/battery.json, written by the /log handler when the ESP's serial dump
contains a "BATTERY: x.xx V" line.

Stdlib only — no matplotlib, no numpy — so it runs on the Pi as well as on a
laptop, same as golden_review.py. Output is an HTML page with an inline SVG.

Usage:
    python3 battery_review.py                       # writes battery_review.html
    python3 battery_review.py -o /tmp/bat.html
    python3 battery_review.py --json path/to/battery.json
"""

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

# --- the prediction being graded -------------------------------------------
# Frozen 2026-09-14 from 3.76 days of readings: settled drain 3.99 %/day off a
# full charge, giving a ~25-day cycle. Points are (days_since_charge, volts).
# DO NOT regenerate these from newer data — that would defeat the comparison.
CHARGE_START = datetime(2026, 9, 10, 16, 57)
PREDICTED_RATE_PCT_PER_DAY = 3.99
FROZEN = [
    (3.76, 4.05), (4.26, 4.03), (4.76, 4.01), (5.26, 3.99), (5.76, 3.97),
    (6.26, 3.95), (6.76, 3.936), (7.26, 3.922), (7.76, 3.907), (8.26, 3.894),
    (8.76, 3.882), (9.26, 3.869), (9.76, 3.857), (10.26, 3.845), (10.76, 3.835),
    (11.26, 3.825), (11.76, 3.815), (12.26, 3.805), (12.76, 3.795),
    (13.26, 3.785), (13.76, 3.775), (14.26, 3.766), (14.76, 3.756),
    (15.26, 3.746), (15.76, 3.736), (16.26, 3.726), (16.76, 3.716),
    (17.26, 3.706), (17.76, 3.696), (18.26, 3.686), (18.76, 3.676),
    (19.26, 3.666), (19.76, 3.656), (20.26, 3.642), (20.76, 3.622),
    (21.26, 3.602), (21.76, 3.574), (22.26, 3.545), (22.76, 3.517),
    (23.26, 3.48), (23.76, 3.43), (24.26, 3.36), (24.76, 3.26), (25.26, 3.2),
]
WARN_V, EMPTY_V = 3.60, 3.20
TZ_OFFSET_HOURS = 3          # battery.json stamps are utcnow(); Israel is UTC+3

W, H = 1180, 560
PAD_L, PAD_R, PAD_T, PAD_B = 62, 30, 46, 52
V_LO, V_HI = 3.10, 4.30


def load(path: Path):
    """Measured points as (days_since_charge, volts), oldest first."""
    with open(path) as f:
        state = json.load(f)
    out = []
    for stamp, volts in state.get("history", []):
        try:
            t = datetime.fromisoformat(stamp.rstrip("Z")) + timedelta(hours=TZ_OFFSET_HOURS)
        except ValueError:
            continue
        out.append(((t - CHARGE_START).total_seconds() / 86400.0, float(volts)))
    return sorted(p for p in out if p[0] >= 0)


def crossing(series, target):
    """First x where the series drops to `target`, linearly interpolated."""
    for i in range(1, len(series)):
        (x0, y0), (x1, y1) = series[i - 1], series[i]
        if y0 > target >= y1:
            span = (y0 - y1) or 1e-9
            return x0 + (y0 - target) / span * (x1 - x0)
    return None


def render(measured, out_path: Path):
    x_max = max(FROZEN[-1][0], measured[-1][0] if measured else 0) + 1
    def sx(d): return PAD_L + (d / x_max) * (W - PAD_L - PAD_R)
    def sy(v): return PAD_T + (V_HI - v) / (V_HI - V_LO) * (H - PAD_T - PAD_B)

    def path(pts):
        return " ".join(("M" if i == 0 else "L") + f"{sx(d):.1f},{sy(v):.1f}"
                        for i, (d, v) in enumerate(pts))

    parts = []
    # day gridlines every 5 days
    day = 0
    while day <= x_max:
        x = sx(day)
        parts.append(f'<line x1="{x:.1f}" y1="{PAD_T}" x2="{x:.1f}" y2="{H-PAD_B}" '
                     f'stroke="#e5e7eb" stroke-width="1"/>')
        label = (CHARGE_START + timedelta(days=day)).strftime("%d %b")
        parts.append(f'<text x="{x:.1f}" y="{H-PAD_B+18}" font-size="11" fill="#6b7280" '
                     f'text-anchor="middle">{label}</text>')
        parts.append(f'<text x="{x:.1f}" y="{H-PAD_B+33}" font-size="10" fill="#9ca3af" '
                     f'text-anchor="middle">d{day}</text>')
        day += 5
    # voltage axis
    v = 3.2
    while v <= 4.3001:
        y = sy(v)
        parts.append(f'<line x1="{PAD_L}" y1="{y:.1f}" x2="{W-PAD_R}" y2="{y:.1f}" '
                     f'stroke="#e5e7eb" stroke-width="1"/>')
        parts.append(f'<text x="{PAD_L-10}" y="{y+4:.1f}" font-size="11" fill="#6b7280" '
                     f'text-anchor="end">{v:.1f}</text>')
        v += 0.2
    # thresholds
    for tv, lab, col in ((WARN_V, "3.60 V  low-battery icon", "#c1121f"),
                         (EMPTY_V, "3.20 V  empty", "#6b7280")):
        y = sy(tv)
        parts.append(f'<line x1="{PAD_L}" y1="{y:.1f}" x2="{W-PAD_R}" y2="{y:.1f}" '
                     f'stroke="{col}" stroke-width="1.2" stroke-dasharray="3 3"/>')
        parts.append(f'<text x="{PAD_L+6}" y="{y-6:.1f}" font-size="10" fill="{col}">{lab}</text>')
    # predicted, then measured on top
    parts.append(f'<path d="{path(FROZEN)}" fill="none" stroke="#3d6ea8" '
                 f'stroke-width="2" stroke-dasharray="7 5"/>')
    if measured:
        parts.append(f'<path d="{path(measured)}" fill="none" stroke="#16324f" stroke-width="2.6"/>')
        d, vv = measured[-1]
        parts.append(f'<circle cx="{sx(d):.1f}" cy="{sy(vv):.1f}" r="5" fill="#16324f"/>')
        parts.append(f'<text x="{sx(d)-10:.1f}" y="{sy(vv)-12:.1f}" font-size="12" '
                     f'font-weight="bold" fill="#16324f" text-anchor="end">'
                     f'now {vv:.2f} V · day {d:.1f}</text>')
    # legend
    parts.append(f'<line x1="{W-250}" y1="{PAD_T-16}" x2="{W-222}" y2="{PAD_T-16}" '
                 f'stroke="#16324f" stroke-width="2.6"/>')
    parts.append(f'<text x="{W-216}" y="{PAD_T-12}" font-size="11" fill="#374151">measured</text>')
    parts.append(f'<line x1="{W-140}" y1="{PAD_T-16}" x2="{W-112}" y2="{PAD_T-16}" '
                 f'stroke="#3d6ea8" stroke-width="2" stroke-dasharray="7 5"/>')
    parts.append(f'<text x="{W-106}" y="{PAD_T-12}" font-size="11" fill="#374151">'
                 f'predicted 14 Sep</text>')

    # --- verdict ---------------------------------------------------------
    rows = []
    if measured:
        d, vv = measured[-1]
        pred_now = None
        for i in range(1, len(FROZEN)):
            if FROZEN[i - 1][0] <= d <= FROZEN[i][0]:
                (x0, y0), (x1, y1) = FROZEN[i - 1], FROZEN[i]
                pred_now = y0 + (d - x0) / ((x1 - x0) or 1e-9) * (y1 - y0)
                break
        if pred_now is not None:
            delta = vv - pred_now
            verdict = ("ahead of prediction — draining slower" if delta > 0.01 else
                       "behind prediction — draining faster" if delta < -0.01 else
                       "on prediction")
            rows.append(f"day {d:.1f}: measured <b>{vv:.2f} V</b> vs predicted "
                        f"<b>{pred_now:.2f} V</b> ({delta:+.2f} V) — {verdict}")
        for tv, lab in ((WARN_V, "3.60 V"), (EMPTY_V, "3.20 V")):
            pc = crossing(FROZEN, tv)
            ac = crossing(measured, tv)
            when = CHARGE_START + timedelta(days=pc) if pc else None
            line = f"{lab}: predicted {when:%a %d %b}" if when else f"{lab}: predicted —"
            if ac:
                line += f" · <b>actual {CHARGE_START + timedelta(days=ac):%a %d %b}</b>"
            rows.append(line)

    html = f"""<title>Battery review</title>
<style>
body{{margin:0;padding:26px;background:#fff;color:#16324f;
 font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
h1{{font-size:18px;margin:0 0 2px}} p.sub{{color:#6b7280;margin:0 0 18px;font-size:13px}}
ul{{margin:16px 0 0;padding-left:18px;color:#374151}} li{{margin:3px 0}}
svg{{border:1px solid #e5e7eb;border-radius:8px;max-width:100%}}
</style>
<h1>Surf frame battery — measured vs. the 14 Sep projection</h1>
<p class=sub>Full charge {CHARGE_START:%d %b %H:%M} &middot; predicted drain
{PREDICTED_RATE_PCT_PER_DAY:.2f} %/day &middot; {len(measured)} readings</p>
<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}">{''.join(parts)}</svg>
<ul>{''.join(f'<li>{r}</li>' for r in rows)}</ul>
"""
    out_path.write_text(html)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", default=str(Path(__file__).parent / "data" / "battery.json"))
    ap.add_argument("-o", "--out", default="battery_review.html")
    a = ap.parse_args()

    src = Path(a.json)
    if not src.exists():
        raise SystemExit(f"no battery history at {src}")
    measured = load(src)
    if not measured:
        raise SystemExit("battery.json has no usable history yet")
    out = Path(a.out)
    for row in render(measured, out):
        print(row.replace("<b>", "").replace("</b>", ""))
    print(f"\n{len(measured)} readings -> {out}")


if __name__ == "__main__":
    main()
