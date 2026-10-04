"""Shared helpers for the static mockup generator. Not shipped in the app."""
from __future__ import annotations

import html
import json
import math
from pathlib import Path

HERE = Path(__file__).parent
DATA = json.loads((HERE / "data" / "detail.json").read_text())
RUNS = json.loads((HERE / "data" / "runs_v2.json").read_text())
LEGACY = json.loads((HERE / "data" / "legacy_expected.json").read_text())

POS, NEG, NEG_T, ACC, INFO = "#3ddc97", "#e5484d", "#ff7a7e", "#f5a524", "#5ab0ff"
MARKET_COLOR = {("NIFTY", 0): "#7cc4ff", ("NIFTY", 1): "#2f6fd6", ("SENSEX", 0): "#ffb35c", ("SENSEX", 1): "#c4561b"}
SERIES = ["#f5a524", "#5ab0ff", "#3ddc97", "#c792ff"]


def esc(s) -> str:
    return html.escape(str(s))


def inr(v, signed=False, dec=0) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    neg = v < 0
    x = abs(v)
    s = f"{x:,.{dec}f}"
    # Indian grouping: 12,34,567
    ip, _, fp = s.partition(".")
    ip = ip.replace(",", "")
    if len(ip) > 3:
        head, tail = ip[:-3], ip[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        ip = ",".join(parts + [tail])
    s = ip + ("." + fp if fp else "")
    sign = "−" if neg else ("+" if signed and v > 0 else "")
    return f"{sign}₹{s}"


def pct(v, dec=1, signed=True) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    sign = "−" if v < 0 else ("+" if signed and v > 0 else "")
    return f"{sign}{abs(v) * 100:.{dec}f}%"


def num(v, dec=2) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    if abs(v) < 0.5 * 10 ** (-dec):
        v = 0.0
    return ("−" if v < 0 else "") + f"{abs(v):.{dec}f}"


ICONS = {
    "library": '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    "run": '<polyline points="3 17 9 11 13 15 21 7"/><polyline points="15 7 21 7 21 13"/>',
    "compare": '<line x1="8" y1="4" x2="8" y2="20"/><line x1="16" y1="4" x2="16" y2="20"/><polyline points="4 8 8 4 12 8"/><polyline points="12 16 16 20 20 16"/>',
    "groups": '<circle cx="6" cy="6" r="2"/><circle cx="18" cy="6" r="2"/><circle cx="6" cy="18" r="2"/><circle cx="18" cy="18" r="2"/><circle cx="12" cy="12" r="2"/>',
    "new": '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
    "help": '<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .8-1 1.5V14"/><line x1="12" y1="17" x2="12" y2="17.01"/>',
    "search": '<circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.5" y2="16.5"/>',
    "download": '<path d="M12 4v11"/><polyline points="7 10 12 15 17 10"/><line x1="5" y1="20" x2="19" y2="20"/>',
    "external": '<path d="M14 4h6v6"/><line x1="20" y1="4" x2="11" y2="13"/><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
    "expand": '<polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/>',
    "copy": '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a1 1 0 0 1 1-1h10"/>',
    "chev": '<polyline points="9 6 15 12 9 18"/>',
    "chevdown": '<polyline points="6 9 12 15 18 9"/>',
    "info": '<circle cx="12" cy="12" r="9"/><line x1="12" y1="11" x2="12" y2="16"/><line x1="12" y1="8" x2="12" y2="8.01"/>',
    "warn": '<path d="M12 3 2 20h20L12 3z"/><line x1="12" y1="10" x2="12" y2="14"/><line x1="12" y1="17" x2="12" y2="17.01"/>',
    "x": '<line x1="6" y1="6" x2="18" y2="18"/><line x1="18" y1="6" x2="6" y2="18"/>',
    "filter": '<polygon points="3 4 21 4 14 12 14 19 10 21 10 12 3 4"/>',
}


def icon(name, size=16, stroke=1.8) -> str:
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg>')


def shell(title: str, active: str, crumbs: str, body: str, *, topbar_actions: str = "", width=1440, height=None) -> str:
    rail = []
    for key, label in [("library", "Library"), ("run", "Run"), ("compare", "Compare"), ("groups", "Groups"), ("new", "New run")]:
        cur = ' aria-current="page"' if key == active else ""
        rail.append(f'<button class="rail__btn"{cur} aria-label="{label}" title="{label}">{icon(key, 20, 1.7)}</button>')
    h = f"height:{height}px;" if height else ""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} — Stolgo mockup</title>
<link rel="stylesheet" href="fonts/fonts.css"><link rel="stylesheet" href="../tokens.css"><link rel="stylesheet" href="../components.css">
<style>body{{width:{width}px;{h}}} .rail{{position:relative;height:auto;min-height:100%}}</style></head>
<body><div class="app" style="{h}">
<nav class="rail" aria-label="Primary"><div class="rail__logo">S</div>{''.join(rail)}<div class="rail__spacer"></div>
<button class="rail__btn" aria-label="Help">{icon('help', 20, 1.7)}</button></nav>
<div class="main"><header class="topbar"><div class="crumbs">{crumbs}</div>
<label class="cmdk">{icon('search', 15, 2)}<input aria-label="Command bar" placeholder="Jump to run, trade #, date, metric…"><span class="kbd">⌘K</span></label>{topbar_actions}</header>
<main class="page">{body}</main></div></div></body></html>"""


# ---------------------------------------------------------------- SVG helpers
def scale(lo, hi, a, b):
    span = (hi - lo) or 1.0
    return lambda v: a + (v - lo) / span * (b - a)


def polyline(pts, color, w=1.6, extra=""):
    p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    return f'<polyline points="{p}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linejoin="round" {extra}/>'


def candles_svg(rows, W, H, *, pad_r=52, pad_b=18, markers=None, sel=None, grid_step=500, dec=0, label_every=None):
    """rows: [label, o, h, l, c]. markers: {index: pnl}. Returns an svg string."""
    n = len(rows)
    lo = min(r[3] for r in rows)
    hi = max(r[2] for r in rows)
    if markers:
        lo -= (hi - lo) * 0.08
    padv = (hi - lo) * 0.06
    lo -= padv
    hi += padv
    X = lambda i: (i + 0.5) * (W - pad_r) / n
    Y = scale(lo, hi, H - pad_b, 4)
    bw = max(1.5, (W - pad_r) / n * 0.6)
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" height="{H}" role="img" aria-label="Candlestick chart">']
    g = math.ceil(lo / grid_step) * grid_step
    while g < hi:
        y = Y(g)
        out.append(f'<line x1="0" x2="{W - pad_r}" y1="{y:.1f}" y2="{y:.1f}" stroke="#14181c"/>')
        out.append(f'<text x="{W - 4}" y="{y + 3:.1f}" text-anchor="end" fill="#6b737c" font-size="10" font-family="IBM Plex Mono">{g:,.{dec}f}</text>')
        g += grid_step
    last_lab = None
    for i, r in enumerate(rows):
        lab = r[0][:7] if label_every is None else None
        if label_every is None and lab != last_lab and i > 0:
            x = X(i) - (W - pad_r) / n / 2
            import datetime as _d
            mname = _d.date(int(lab[:4]), int(lab[5:7]), 1).strftime("%b")
            out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="0" y2="{H - pad_b}" stroke="#14181c"/>'
                       f'<text x="{x + 4:.1f}" y="{H - 4}" fill="#6b737c" font-size="10" font-family="IBM Plex Mono">{mname}</text>')
        last_lab = lab
        if label_every and i % label_every == 0:
            out.append(f'<text x="{X(i):.1f}" y="{H - 4}" fill="#6b737c" font-size="10" text-anchor="middle" font-family="IBM Plex Mono">{r[0]}</text>')
        o, h, l, c = r[1:5]
        col = POS if c >= o else NEG
        x = X(i)
        top, bot = Y(max(o, c)), Y(min(o, c))
        out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{Y(h):.1f}" y2="{Y(l):.1f}" stroke="{col}"/>'
                   f'<rect x="{x - bw / 2:.1f}" y="{top:.1f}" width="{bw:.1f}" height="{max(1, bot - top):.1f}" fill="{col}"/>')
    if markers:
        for i, p in markers.items():
            x = X(i)
            y = Y(rows[i][3]) + 12
            ring = ACC if i == sel else "#0d1013"
            r_ = 6 if i == sel else 4.5
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r_}" fill="{POS if p >= 0 else NEG}" stroke="{ring}" stroke-width="2"/>')
    lc = rows[-1][4]
    y = Y(lc)
    out.append(f'<line x1="0" x2="{W - pad_r}" y1="{y:.1f}" y2="{y:.1f}" stroke="{NEG if lc < rows[-1][1] else POS}" stroke-dasharray="2 3" stroke-opacity=".6"/>'
               f'<rect x="{W - pad_r + 2}" y="{y - 8:.1f}" width="{pad_r - 4}" height="16" rx="3" fill="{NEG if lc < rows[-1][1] else POS}"/>'
               f'<text x="{W - pad_r / 2:.1f}" y="{y + 4:.1f}" text-anchor="middle" fill="#0a0c0e" font-size="10" font-weight="600" font-family="IBM Plex Mono">{lc:,.{dec}f}</text>')
    out.append("</svg>")
    return "".join(out)


def area_svg(values, W, H, color, *, zero=None, fill_opacity=0.08, lo=None, hi=None, invert=False, extra=""):
    lo = min(values) if lo is None else lo
    hi = max(values) if hi is None else hi
    n = len(values)
    X = lambda i: i / (n - 1) * W
    Y = scale(lo, hi, H - 2, 2)
    pts = [(X(i), Y(v)) for i, v in enumerate(values)]
    base = Y(zero if zero is not None else lo) if not invert else 0
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    s = f'<svg viewBox="0 0 {W} {H}" width="100%" height="{H}" preserveAspectRatio="none">'
    if zero is not None:
        s += f'<line x1="0" x2="{W}" y1="{Y(zero):.1f}" y2="{Y(zero):.1f}" stroke="#2a3037" stroke-dasharray="3 4"/>'
    s += f'<polygon points="0,{base:.1f} {poly} {W},{base:.1f}" fill="{color}" fill-opacity="{fill_opacity}"/>'
    s += polyline(pts, color, 1.6) + extra + "</svg>"
    return s, X, Y
