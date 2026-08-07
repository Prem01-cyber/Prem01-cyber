#!/usr/bin/env python3
"""Generate the daily animated banner SVGs (light + dark).

The banner spells the handle in contribution-graph cells, so it shares a visual
language with the snake below it in the README. Cell intensities and the noise
scatter are seeded by the UTC date: identical on re-runs (no empty commits),
new every day.
"""

from __future__ import annotations

import argparse
import datetime as dt
import random
from pathlib import Path

WORDMARK = "PREM01-CYBER"

PITCH = 10          # centre-to-centre distance between cells
CELL = 7            # drawn size of a cell
RADIUS = 2
GLYPH_W, GLYPH_H = 5, 7
GAP = 1             # blank columns between glyphs

WIDTH, HEIGHT = 840, 170

# 5x7 bitmap font, top row first.
FONT = {
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "R": ("####.", "#...#", "#...#", "####.", "#..#.", "#...#", "#...#"),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#...#", "#...#", "#...#", "#...#"),
    "C": (".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
}

THEMES = {
    "light": {
        "bg": "none",
        "empty": "#ebedf0",
        "levels": ["#9be9a8", "#40c463", "#30a14e", "#216e39"],
        "text": "#8b949e",
    },
    "dark": {
        "bg": "none",
        "empty": "#161b22",
        "levels": ["#0e4429", "#006d32", "#26a641", "#39d353"],
        "text": "#6e7681",
    },
}


def glyph_columns(text: str) -> tuple[set[tuple[int, int]], int]:
    """Map the wordmark onto grid coordinates; return lit cells and total width."""
    lit: set[tuple[int, int]] = set()
    col = 0
    for char in text:
        rows = FONT[char]
        for r, row in enumerate(rows):
            for c, pixel in enumerate(row):
                if pixel == "#":
                    lit.add((col + c, r))
        col += GLYPH_W + GAP
    return lit, col - GAP


def render(theme_name: str, day: dt.date) -> str:
    theme = THEMES[theme_name]
    rng = random.Random(f"{day.isoformat()}::prem01-cyber")

    lit, cols = glyph_columns(WORDMARK)
    grid_w = cols * PITCH - (PITCH - CELL)
    grid_h = GLYPH_H * PITCH - (PITCH - CELL)
    x0 = round((WIDTH - grid_w) / 2)
    y0 = round((HEIGHT - grid_h) / 2) - 6

    # A scatter of faint cells around the wordmark keeps it from floating.
    noise: dict[tuple[int, int], int] = {}
    for _ in range(90):
        spot = (rng.randrange(-5, cols + 5), rng.randrange(-3, GLYPH_H + 3))
        if spot not in lit and rng.random() < 0.5:
            noise[spot] = rng.choice([0, 0, 0, 1])

    cells: list[str] = []

    def emit(col: int, row: int, level: int, klass: str) -> None:
        x = x0 + col * PITCH
        y = y0 + row * PITCH
        # The wave sweeps left to right with a slight downward tilt.
        delay = round((col * 0.9 + row * 1.6) * 0.022, 2)
        cells.append(
            f'<rect class="{klass}" x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
            f'rx="{RADIUS}" fill="{theme["levels"][level]}" '
            f'style="animation-delay:{delay}s"/>'
        )

    for col, row in sorted(noise):
        emit(col, row, noise[(col, row)], "dim")

    for col, row in sorted(lit):
        # Only the top two levels, so the wordmark never breaks up.
        emit(col, row, rng.choice([2, 3, 3, 3]), "on")

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" \
viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="prem01-cyber, drawn in contribution cells ({day})">
  <style>
    .on {{ animation: on 3.4s ease-in-out infinite; }}
    .dim {{ opacity:.4; animation: dim 3.4s ease-in-out infinite; }}
    @keyframes on {{ 0%,100% {{ opacity:.62 }} 45% {{ opacity:1 }} }}
    @keyframes dim {{ 0%,100% {{ opacity:.18 }} 45% {{ opacity:.55 }} }}
    text {{ font-family:ui-monospace,SFMono-Regular,"SF Mono",Menlo,monospace;
            font-size:11px; letter-spacing:.14em; }}
    @media (prefers-reduced-motion: reduce) {{
      .on,.dim {{ animation:none }}
    }}
  </style>
  {"".join(cells)}
  <text x="{WIDTH // 2}" y="{HEIGHT - 16}" text-anchor="middle" fill="{theme["text"]}">{day.isoformat()}</text>
</svg>
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=Path("assets"), type=Path)
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
