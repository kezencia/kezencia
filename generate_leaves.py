#!/usr/bin/env python3
"""
generate_leaves.py

Fetches a GitHub user's REAL public contribution calendar
and renders it as an SVG where active days fall like leaves.
"""

import sys
import re
import random
import urllib.request

LEVEL_COLORS = {
    0: "#161b22",
    1: "#0e4429",
    2: "#006d32",
    3: "#26a641",
    4: "#39d353",
}
BG = "#0d1117"
BORDER = "#21262d"
TEXT = "#7d8590"

CELL = 10
GAP = 3
STEP = CELL + GAP
LEFT_MARGIN = 34
TOP_MARGIN = 42

MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
DAY_LABELS = {1: "Mon", 3: "Wed", 5: "Fri"}


def fetch_contributions(username: str) -> str:
    url = f"https://github.com/users/{username}/contributions"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        if resp.status != 200:
            raise RuntimeError(f"GitHub returned status {resp.status} for user '{username}'")
        return resp.read().decode("utf-8")


def parse_cells(html: str):
    """Parses cells reliably from GitHub contribution grid."""
    cells = []
    pattern = r'data-date="([^"]+)".*?data-level="(\d+)"'
    matches = list(re.finditer(pattern, html))

    if not matches:
        pattern = r'data-level="(\d+)".*?data-date="([^"]+)"'
        for i, m in enumerate(re.finditer(pattern, html)):
            level, date = int(m.group(1)), m.group(2)
            col, row = divmod(i, 7)
            cells.append({"row": row, "col": col, "date": date, "level": level})
    else:
        for i, m in enumerate(matches):
            date, level = m.group(1), int(m.group(2))
            col, row = divmod(i, 7)
            cells.append({"row": row, "col": col, "date": date, "level": level})

    return cells


def month_label_positions(cells):
    labels = {}
    seen_months = set()
    for c in sorted(cells, key=lambda x: x["col"]):
        month = c["date"][5:7]
        if month not in seen_months:
            seen_months.add(month)
            labels[c["col"]] = MONTH_NAMES[int(month) - 1]
    return labels


def build_svg(cells, total_contributions: str, interval: float = 3.0) -> str:
    if not cells:
        raise RuntimeError("No contribution cells parsed.")

    cols = max(c["col"] for c in cells) + 1
    rows = max(c["row"] for c in cells) + 1

    width = LEFT_MARGIN + cols * STEP + 10
    height = TOP_MARGIN + rows * STEP + 20

    svg = [
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">',
        f'<rect width="{width}" height="{height}" rx="10" fill="{BG}" stroke="{BORDER}" stroke-width="1"/>',
        f'<text x="{LEFT_MARGIN}" y="14" font-family="Helvetica, Arial, sans-serif" font-size="12" fill="{TEXT}">{total_contributions} contributions &#183; falling as leaves</text>'
    ]

    for col, name in month_label_positions(cells).items():
        x = LEFT_MARGIN + col * STEP
        svg.append(
            f'<text x="{x:.1f}" y="{TOP_MARGIN - 14}" font-family="Helvetica, Arial, sans-serif" font-size="10" fill="{TEXT}">{name}</text>'
        )

    for row, label in DAY_LABELS.items():
        y = TOP_MARGIN + row * STEP + CELL
        svg.append(
            f'<text x="4" y="{y}" font-family="Helvetica, Arial, sans-serif" font-size="10" fill="{TEXT}">{label}</text>'
        )

    # Base grid
    for c in cells:
        x = LEFT_MARGIN + c["col"] * STEP
        y = TOP_MARGIN + c["row"] * STEP
        svg.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" fill="{LEVEL_COLORS[0]}"/>')

    # Falling leaves animation
    active_cells = [c for c in cells if c["level"] > 0]
    active_cells.sort(key=lambda c: (c["level"], c["date"]))

    if not active_cells:
        svg.append('</svg>')
        return "\n".join(svg)

    total_cycle = round(interval * len(active_cells), 2)
    fall_dur = min(interval * 0.6, 1.8)

    for i, c in enumerate(active_cells):
        x = LEFT_MARGIN + c["col"] * STEP
        y = TOP_MARGIN + c["row"] * STEP
        color = LEVEL_COLORS[c["level"]]

        start = i * interval
        start_frac = round(start / total_cycle, 6)
        gone_frac = round((start + fall_dur) / total_cycle, 6)
        fall_distance = round((height - y) + 24, 1)
        tilt = random.choice([-1, 1]) * random.randint(30, 70)

        svg.append(
            f'<g transform="translate({x} {y})">'
            f'<rect x="0" y="0" width="{CELL}" height="{CELL}" rx="2.5" fill="{color}" opacity="1">'
            f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;{start_frac};{gone_frac};1" dur="{total_cycle}s" begin="0s" repeatCount="indefinite"/>'
            f'</rect>'
            f'<animateTransform attributeName="transform" type="translate" additive="sum" values="0 0;0 0;0 {fall_distance};0 {fall_distance}" keyTimes="0;{start_frac};{gone_frac};1" dur="{total_cycle}s" begin="0s" repeatCount="indefinite"/>'
            f'<animateTransform attributeName="transform" type="rotate" additive="sum" values="0 {CELL/2} {CELL/2};0 {CELL/2} {CELL/2};{tilt} {CELL/2} {CELL/2};{tilt} {CELL/2} {CELL/2}" keyTimes="0;{start_frac};{gone_frac};1" dur="{total_cycle}s" begin="0s" repeatCount="indefinite"/>'
            f'</g>'
        )

    svg.append('</svg>')
    return "\n".join(svg)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 generate_leaves.py <github-username> [output.svg] [interval-seconds]", file=sys.stderr)
        sys.exit(1)

    username = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else "activity-leaves.svg"
    interval = float(sys.argv[3]) if len(sys.argv) > 3 else 3.0

    html = fetch_contributions(username)
    cells = parse_cells(html)

    total_m = re.search(r'([\d,]+)\s*\n?\s*contributions', html)
    total = total_m.group(1) if total_m else "Recent"

    svg = build_svg(cells, total, interval)

    with open(out_path, "w") as f:
        f.write(svg)

    active = sum(1 for c in cells if c["level"] > 0)
    print(f"OK — {username}: {total} contributions, {active} active days parsed -> {out_path}")


if __name__ == "__main__":
    main()
