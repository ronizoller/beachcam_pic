"""
Guest beach report: how each guest camera behaved the times it was actually
shown. No extra fetching — every number comes from a real guest run (the ~6
frames taken between the two ESP pulls a guest is on the panel for).

A run ends with one status:
  ok      at least one usable frame
  fog     frames arrived but every one was grey (fog / static / dark)
  frozen  frames arrived but did not change between snapshots
  dead    every fetch failed

Stored in data/guest_report.json; served at /guests (page) and /guests.json.
"""

import html
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger("beachcam")

# Mean absolute change between consecutive snapshots (0-255, 64x48 grey) below
# which a run counts as frozen. Measured 2026-10-08: live cams 1.2 (Ilia, calm
# sea) to 20 (Baleal); the frozen Niagara feed exactly 0.0 every time.
FROZEN_MAX_CHANGE = 0.3
KEEP_RUNS = 30


class GuestRun:
    """Accumulates one guest run; `finish()` turns it into a status record."""

    def __init__(self, camera: str):
        self.camera = camera
        self.started = datetime.now()
        self.frames = 0
        self.usable = 0
        self.failed = 0
        self.best: Optional[float] = None
        self.error: Optional[str] = None
        self.max_change = 0.0
        self._last: Optional[np.ndarray] = None

    def fail(self, error: str):
        self.failed += 1
        self.error = self.error or str(error)[:120]

    def frame(self, image, usable: bool, score: float):
        self.frames += 1
        if usable:
            self.usable += 1
            self.best = score if self.best is None else max(self.best, score)
        small = np.asarray(image.convert("L").resize((64, 48)), dtype=float)
        if self._last is not None:
            self.max_change = max(self.max_change, float(np.abs(small - self._last).mean()))
        self._last = small

    def status(self) -> str:
        if self.frames == 0:
            return "dead"
        if self.frames >= 2 and self.max_change < FROZEN_MAX_CHANGE:
            return "frozen"
        if self.usable == 0:
            return "fog"
        return "ok"

    def finish(self) -> dict:
        return {
            "date": self.started.strftime("%Y-%m-%d %H:%M"),
            "camera": self.camera,
            "status": self.status(),
            "frames": self.frames,
            "usable": self.usable,
            "failed": self.failed,
            "best": round(self.best, 3) if self.best is not None else None,
            "note": self.error if self.frames == 0 else None,
        }


def record(path: Path, run: GuestRun) -> Optional[dict]:
    """Fold a finished run into the report file. Best-effort."""
    try:
        rec = run.finish()
        report = load(path)
        cam = report["cameras"].setdefault(rec["camera"], {"picked": 0, "ok": 0})
        cam["picked"] += 1
        cam["ok"] += rec["status"] == "ok"
        cam["latest"] = rec
        report["runs"] = ([rec] + report["runs"])[:KEEP_RUNS]
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(report, indent=1))
        tmp.replace(path)
        logger.info(f"Guest report: {rec['camera']} -> {rec['status']} "
                    f"({rec['usable']}/{rec['frames']} usable, {rec['failed']} failed)")
        return rec
    except Exception as e:
        logger.warning(f"Failed to record guest run: {e}")
        return None


def load(path: Path) -> dict:
    try:
        report = json.loads(path.read_text())
        report.setdefault("cameras", {})
        report.setdefault("runs", [])
        return report
    except (OSError, ValueError):
        return {"cameras": {}, "runs": []}


_DOT = {"ok": "#2e9e5b", "fog": "#c9a227", "frozen": "#3d7fc1", "dead": "#c0392b"}


def render_html(report: dict, camera_names: list) -> str:
    """One small page: a row per camera, then the recent runs."""
    def badge(status):
        if not status:
            return '<span class="muted">not picked yet</span>'
        return f'<span class="dot" style="background:{_DOT.get(status, "#888")}"></span>{status}'

    rows = []
    for name in camera_names:
        cam = report["cameras"].get(name, {})
        latest = cam.get("latest") or {}
        rows.append(
            f"<tr><td>{html.escape(name)}</td><td>{badge(latest.get('status'))}</td>"
            f"<td class=n>{cam.get('ok', 0)}/{cam.get('picked', 0)}</td>"
            f"<td class=muted>{latest.get('date', '')}</td></tr>"
        )
    runs = []
    for r in report["runs"][:14]:
        detail = (f"{r['usable']}/{r['frames']} usable"
                  + (f", best {r['best']:.2f}" if r.get("best") is not None else "")
                  + (f" — {html.escape(r['note'])}" if r.get("note") else ""))
        runs.append(
            f"<tr><td class=muted>{r['date']}</td><td>{html.escape(r['camera'])}</td>"
            f"<td>{badge(r['status'])}</td><td class=muted>{detail}</td></tr>"
        )
    return f"""<!doctype html><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Guest beaches</title>
<style>
body{{font:15px/1.5 -apple-system,system-ui,sans-serif;margin:24px auto;max-width:720px;padding:0 16px;color:#1d2b36;background:#fff}}
h1{{font-size:20px;margin:0 0 4px}} h2{{font-size:15px;margin:28px 0 6px;color:#555}}
table{{border-collapse:collapse;width:100%}} td,th{{padding:6px 8px;border-bottom:1px solid #eee;text-align:left}}
th{{font-weight:600;color:#666;font-size:13px}} .n{{text-align:right}} .muted{{color:#888;font-size:13px}}
.dot{{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px}}
@media (prefers-color-scheme:dark){{body{{background:#14181c;color:#e3e7ea}} td,th{{border-color:#2a3036}}}}
</style>
<h1>Guest beaches</h1>
<div class=muted>Updated each time a guest beach is shown. ok = a usable frame; fog = only grey frames; frozen = image never changed; dead = no image.</div>
<table><tr><th>Camera</th><th>Last run</th><th class=n>OK / picked</th><th>When</th></tr>{''.join(rows)}</table>
<h2>Recent runs</h2>
<table>{''.join(runs) or '<tr><td class=muted>No guest runs yet.</td></tr>'}</table>
"""
