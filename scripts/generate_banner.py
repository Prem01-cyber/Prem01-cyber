#!/usr/bin/env python3
"""Generate the daily animated banner SVGs (light + dark).

The layout is deterministic for a given UTC date, so re-running on the same day
produces byte-identical output (no empty commits) while every new day yields a
brand new circuit.
"""

from __future__ import annotations

import argparse
import datetime as dt
import math
import random
from pathlib import Path

WIDTH, HEIGHT = 880, 220
MARGIN_X, MARGIN_Y = 28, 26
CELL = 40
COLS = (WIDTH - 2 * MARGIN_X) // CELL
ROWS = (HEIGHT - 2 * MARGIN_Y) // CELL
CORNER = 9

THEMES = {
    "light": {
        "bg": "#fbfcfe",
        "panel": "#f2f5fa",
        "grid": "#dde3ec",
        "trace": "#c2ccdb",
        "text": "#5b6675",
        "accents": ["#2f81f7", "#8957e5", "#1a7f37", "#bc4c00"],
    },
    "dark": {
        "bg": "#0d1117",
        "panel": "#111826",
        "grid": "#1c2432",
        "trace": "#263041",
        "text": "#7d8590",
        "accents": ["#58a6ff", "#bc8cff", "#3fb950", "#f0883e"],
    },
}


def node_xy(col: int, row: int) -> tuple[float, float]:
    return MARGIN_X + col * CELL, MARGIN_Y + row * CELL


def rounded_path(points: list[tuple[float, float]], radius: float = CORNER) -> str:
    """Orthogonal polyline rendered with rounded corners."""
    if len(points) < 2:
        return ""
    d = [f"M {points[0][0]:.1f} {points[0][1]:.1f}"]
    for i in range(1, len(points) - 1):
        prev, cur, nxt = points[i - 1], points[i], points[i + 1]
        r = min(radius, dist(prev, cur) / 2, dist(cur, nxt) / 2)
        a = toward(cur, prev, r)
        b = toward(cur, nxt, r)
        d.append(f"L {a[0]:.1f} {a[1]:.1f}")
        d.append(f"Q {cur[0]:.1f} {cur[1]:.1f} {b[0]:.1f} {b[1]:.1f}")
    d.append(f"L {points[-1][0]:.1f} {points[-1][1]:.1f}")
    return " ".join(d)


def dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def toward(origin, target, amount: float) -> tuple[float, float]:
    d = dist(origin, target) or 1.0
    return (
        origin[0] + (target[0] - origin[0]) * amount / d,
        origin[1] + (target[1] - origin[1]) * amount / d,
    )


def path_length(points: list[tuple[float, float]]) -> float:
    return sum(dist(points[i], points[i + 1]) for i in range(len(points) - 1))


def build_traces(rng: random.Random) -> list[list[tuple[int, int]]]:
    """Random orthogonal walks that always advance left to right."""
    traces: list[list[tuple[int, int]]] = []
    rows = list(range(ROWS + 1))
    rng.shuffle(rows)
    for row in rows[: rng.randint(4, 5)]:
        col, r = 0, row
        cells = [(col, r)]
        while col < COLS:
            step = rng.choice([1, 1, 2, 2, 3])
            col = min(COLS, col + step)
            cells.append((col, r))
            if col < COLS and rng.random() < 0.62:
                target = max(0, min(ROWS, r + rng.choice([-2, -1, 1, 2])))
                if target != r:
                    r = target
                    cells.append((col, r))
        traces.append(cells)
    return traces


def render(theme_name: str, day: dt.date) -> str:
    theme = THEMES[theme_name]
    rng = random.Random(f"{day.isoformat()}::prem01-cyber")

    traces = build_traces(rng)
    parts: list[str] = []
    css: list[str] = []
    junctions: set[tuple[int, int]] = set()

    for i, cells in enumerate(traces):
        pts = [node_xy(c, r) for c, r in cells]
        junctions.update(cells)
        accent = theme["accents"][i % len(theme["accents"])]
        d = rounded_path(pts)
        length = path_length(pts)
        dur = round(length / rng.uniform(70, 110), 2)
        delay = round(rng.uniform(0, 3), 2)

        parts.append(
            f'<path class="trace" d="{d}" stroke="{theme["trace"]}"/>'
            f'<path class="pkt p{i}" d="{d}" stroke="{accent}"/>'
        )
        css.append(
            f"@keyframes flow{i}{{from{{stroke-dashoffset:{length:.0f}}}"
            f"to{{stroke-dashoffset:0}}}}"
            f".p{i}{{stroke-dasharray:26 {length:.0f};"
            f"animation:flow{i} {dur}s linear {delay}s infinite}}"
        )

    for j, (c, r) in enumerate(sorted(junctions)):
        x, y = node_xy(c, r)
        accent = theme["accents"][(c + r) % len(theme["accents"])]
        lit = rng.random() < 0.30
        fill = accent if lit else theme["grid"]
        delay = round(rng.uniform(0, 4), 2)
        cls = "node pulse" if lit else "node"
        parts.append(
            f'<circle class="{cls}" cx="{x:.0f}" cy="{y:.0f}" r="3" '
            f'fill="{fill}" style="animation-delay:{delay}s"/>'
        )

    dots = "".join(
        f'<circle cx="{20 + k * 14}" cy="18" r="4" fill="{theme["accents"][k]}" '
        f'opacity="0.85"/>'
        for k in range(3)
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" \
viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="Generative circuit banner for {day}">
  <style>
    .trace {{ fill:none; stroke-width:1.6; stroke-linecap:round; stroke-linejoin:round; }}
    .pkt {{ fill:none; stroke-width:2.6; stroke-linecap:round; stroke-linejoin:round; }}
    .node {{ }}
    .pulse {{ animation:pulse 3.2s ease-in-out infinite; transform-origin:center; }}
    @keyframes pulse {{ 0%,100%{{opacity:.35;r:3}} 50%{{opacity:1;r:5}} }}
    text {{ font-family:ui-monospace,SFMono-Regular,"SF Mono",Menlo,monospace; }}
    @media (prefers-reduced-motion: reduce) {{
      .pkt,.pulse {{ animation:none }}
    }}
  </style>
  <rect width="{WIDTH}" height="{HEIGHT}" rx="14" fill="{theme["bg"]}"/>
  <rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{HEIGHT - 1}" rx="13.5"
        fill="none" stroke="{theme["grid"]}"/>
  <rect x="1" y="1" width="{WIDTH - 2}" height="36" rx="13" fill="{theme["panel"]}"/>
  {dots}
  <text x="66" y="23" font-size="12" fill="{theme["text"]}">~/prem01-cyber &#8212; build &amp; break</text>
  <text x="{WIDTH - 20}" y="23" font-size="12" text-anchor="end" fill="{theme["text"]}">{day.isoformat()}</text>
  <g transform="translate(0,20)">
    {"".join(parts)}
  </g>
</svg>
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="assets", type=Path)
    ap.add_argument("--date", default=None, help="YYYY-MM-DD (defaults to today, UTC)")
    args = ap.parse_args()

    day = (
        dt.date.fromisoformat(args.date)
        if args.date
        else dt.datetime.now(dt.timezone.utc).date()
    )
    args.out.mkdir(parents=True, exist_ok=True)
    for theme in THEMES:
        target = args.out / f"banner-{theme}.svg"
        target.write_text(render(theme, day), encoding="utf-8")
        print(f"wrote {target}")


if __name__ == "__main__":
    main()
