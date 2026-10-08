#!/usr/bin/env python3
"""
Chart every charge cycle's discharge against the projection frozen on 2026-09-14.

The point is to grade the estimate honestly. The projection below is stored as
data, not recomputed on each run — a forecast you regenerate from the latest
data every time is not a forecast, it is a curve fit, and it can never be wrong.
Whatever the pack actually does gets drawn straight over the line we committed
to, so drift is visible at a glance.

Each charge cycle is its own curve on a shared "days since charge" axis, so
cycles can be compared directly. A new cycle starts after a gap of more than
GAP_HOURS (the ESP was dead; overnight gaps are ~11.5 h) or a jump of JUMP_V or
more (charged before it died). Readings taken while the voltage is still
climbing are the charge itself and are skipped; day 0 is the first reading
after it stops rising.

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
# battery.json keeps only the last 200 readings (~7.7 days), so the oldest cycle
# in the file usually has its start cut off. Full charges logged by hand let
# that cycle keep its true day 0 instead of starting from mid-discharge.
KNOWN_CHARGES = [CHARGE_START]
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
GAP_HOURS = 18               # longer than any overnight sleep -> the ESP was dead
JUMP_V = 0.30                # a rise this big between wakes is a recharge

W, H = 1180, 560
PAD_L, PAD_R, PAD_T, PAD_B = 62, 30, 46, 52
V_LO, V_HI = 3.00, 4.30
CURRENT_COLOR, PAST_COLOR = "#16324f", "#9aaec4"


def load(path: Path):
    """Readings as (local_datetime, volts), oldest first."""
    with open(path) as f:
        state = json.load(f)
    out = []
    for stamp, volts in state.get("history", []):
        try:
            t = datetime.fromisoformat(stamp.rstrip("Z")) + timedelta(hours=TZ_OFFSET_HOURS)
        except ValueError:
            continue
        out.append((t, float(volts)))
    return sorted(out)


def split_cycles(readings):
    """
    Group readings into charge cycles: [{"start": datetime, "points": [(day, V)],
    "ended": bool}], oldest first. Points are days since that cycle's start.
    """
    groups, cur, charging = [], [], False
    for i, (t, v) in enumerate(readings):
        if cur:
            pt, pv = readings[i - 1]
            if charging and v > pv:
                pass  # still climbing: same charge, however big the step
            elif (t - pt).total_seconds() > GAP_HOURS * 3600 or v - pv >= JUMP_V:
                groups.append(cur)
                cur, charging = [], True
            else:
                charging = False
        cur.append((t, v))
    if cur:
        groups.append(cur)

    cycles = []
    for gi, g in enumerate(groups):
        if gi > 0:
            # Drop the still-rising run: that is the pack charging, not draining.
            k = 0
            while k + 1 < len(g) and g[k + 1][1] > g[k][1]:
                k += 1
            g = g[k:]
        else:
            # The oldest cycle may have lost its start to the 200-reading cap.
            # Use the latest hand-logged charge before its first reading.
            known = [c for c in KNOWN_CHARGES if c <= g[0][0]]
            if known:
                g = [(known[-1], None)] + g
        start = g[0][0]
        pts = [((t - start).total_seconds() / 86400.0, v) for t, v in g if v is not None]
        cycles.append({"start": start, "points": pts, "ended": gi < len(groups) - 1})
    # A trailing group that only ever rose (charging right now) is not a cycle yet.
    return [c for c in cycles if c["points"]]


def crossing(series, target):
    """First x where the series drops to `target`, linearly interpolated."""
    for i in range(1, len(series)):
        (x0, y0), (x1, y1) = series[i - 1], series[i]
        if y0 > target >= y1:
            span = (y0 - y1) or 1e-9
            return x0 + (y0 - target) / span * (x1 - x0)
    return None


def predicted_at(d):
    """Frozen projection at day `d`, or None outside its range."""
    for i in range(1, len(FROZEN)):
        if FROZEN[i - 1][0] <= d <= FROZEN[i][0]:
            (x0, y0), (x1, y1) = FROZEN[i - 1], FROZEN[i]
            return y0 + (d - x0) / ((x1 - x0) or 1e-9) * (y1 - y0)
    return None


def render(cycles, out_path: Path):
    last_day = max(c["points"][-1][0] for c in cycles)
    x_max = max(FROZEN[-1][0], last_day) + 1
    def sx(d): return PAD_L + (d / x_max) * (W - PAD_L - PAD_R)
    def sy(v): return PAD_T + (V_HI - v) / (V_HI - V_LO) * (H - PAD_T - PAD_B)

    def path(pts):
        return " ".join(("M" if i == 0 else "L") + f"{sx(d):.1f},{sy(v):.1f}"
                        for i, (d, v) in enumerate(pts))

    parts = []
    # day gridlines every 5 days — days since charge, since cycles start on
    # different dates
    day = 0
    while day <= x_max:
        x = sx(day)
        parts.append(f'<line x1="{x:.1f}" y1="{PAD_T}" x2="{x:.1f}" y2="{H-PAD_B}" '
                     f'stroke="#e5e7eb" stroke-width="1"/>')
        parts.append(f'<text x="{x:.1f}" y="{H-PAD_B+18}" font-size="11" fill="#6b7280" '
                     f'text-anchor="middle">day {day}</text>')
        day += 5
    parts.append(f'<text x="{(W + PAD_L) / 2:.1f}" y="{H-8}" font-size="11" fill="#9ca3af" '
                 f'text-anchor="middle">days since full charge</text>')
    # voltage axis
    v = 3.0
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
    # predicted, then past cycles muted, then the current cycle on top
    parts.append(f'<path d="{path(FROZEN)}" fill="none" stroke="#3d6ea8" '
                 f'stroke-width="2" stroke-dasharray="7 5"/>')
    for i, c in enumerate(cycles):
        current = i == len(cycles) - 1
        col = CURRENT_COLOR if current else PAST_COLOR
        parts.append(f'<path d="{path(c["points"])}" fill="none" stroke="{col}" '
                     f'stroke-width="{2.6 if current else 2}"/>')
        d, vv = c["points"][-1]
        label = (f'now {vv:.2f} V · day {d:.1f}' if current else
                 f'last wake {vv:.2f} V · day {d:.1f}')
        parts.append(f'<circle cx="{sx(d):.1f}" cy="{sy(vv):.1f}" r="{5 if current else 4}" '
                     f'fill="{col}"/>')
        # Labels on the right half go left of the point, or they clip.
        right = sx(d) > W / 2
        parts.append(f'<text x="{sx(d) + (-10 if right else 10):.1f}" y="{sy(vv)-10:.1f}" '
                     f'font-size="12" text-anchor="{"end" if right else "start"}" '
                     f'font-weight="{"bold" if current else "normal"}" fill="{col}">'
                     f'{c["start"]:%d %b}: {label}</text>')
    # legend
    lx = W - 380
    for dx, dash, col, lab in ((0, "", CURRENT_COLOR, "current charge"),
                               (130, "", PAST_COLOR, "past charges"),
                               (250, "7 5", "#3d6ea8", "predicted 14 Sep")):
        parts.append(f'<line x1="{lx+dx}" y1="{PAD_T-16}" x2="{lx+dx+28}" y2="{PAD_T-16}" '
                     f'stroke="{col}" stroke-width="2.4" stroke-dasharray="{dash}"/>')
        parts.append(f'<text x="{lx+dx+34}" y="{PAD_T-12}" font-size="11" '
                     f'fill="#374151">{lab}</text>')

    # --- verdict, one row per cycle ---------------------------------------
    rows = []
    for i, c in enumerate(cycles):
        pts = c["points"]
        d, vv = pts[-1]
        bits = [f"<b>full {c['start']:%a %d %b %H:%M}</b>"]
        if pts[0][0] < 0.5:
            bits.append(f"first reading {pts[0][1]:.2f} V")
        if c["ended"]:
            bits.append(f"<b>lasted {d:.1f} days</b> (last wake {vv:.2f} V)")
        else:
            bits.append(f"now <b>{vv:.2f} V</b> at day {d:.1f}")
            pred = predicted_at(d)
            if pred is not None:
                bits.append(f"projection {pred:.2f} V ({vv - pred:+.2f} V)")
        warn = crossing(pts, WARN_V)
        if warn is not None:
            bits.append(f"3.60 V warning at day {warn:.1f}")
        rows.append(" · ".join(bits))

    html = f"""<title>Battery review</title>
<style>
body{{margin:0;padding:26px;background:#fff;color:#16324f;
 font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
h1{{font-size:18px;margin:0 0 2px}} p.sub{{color:#6b7280;margin:0 0 18px;font-size:13px}}
ul{{margin:16px 0 0;padding-left:18px;color:#374151}} li{{margin:3px 0}}
svg{{border:1px solid #e5e7eb;border-radius:8px;max-width:100%}}
</style>
<h1>Surf frame battery — every charge vs. the 14 Sep projection</h1>
<p class=sub>{len(cycles)} charge cycle{"s" if len(cycles) != 1 else ""} &middot; predicted drain
{PREDICTED_RATE_PCT_PER_DAY:.2f} %/day &middot; {sum(len(c["points"]) for c in cycles)} readings</p>
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
    cycles = split_cycles(load(src))
    if not cycles:
        raise SystemExit("battery.json has no usable history yet")
    out = Path(a.out)
    for row in render(cycles, out):
        print(row.replace("<b>", "").replace("</b>", ""))
    print(f"\n{len(cycles)} cycles -> {out}")


if __name__ == "__main__":
    main()
