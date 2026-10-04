"""Library, Compare, Groups, New run, Components & states mockups."""
from common import *  # noqa

STATUS_BADGE = {"ok": ("OK", "ok"), "low_sample": ("Low sample", "low"), "short_window": ("Short window", "low"),
                "data_issues": ("Data issues", "warn"), "superseded": ("Superseded", "muted"), "empty": ("Empty", "muted")}


def badge(status):
    lab, cls = STATUS_BADGE[status]
    return f'<span class="badge badge--{cls}">{lab}</span>'


def mkey(r):
    d = r["dte"][0] if r["dte"] else 0
    return (r["markets"][0], d) if len(r["markets"]) == 1 else ("MIX", 0)


def color_of(r):
    return MARKET_COLOR.get(mkey(r), "#9aa3b2")


def visible_runs():
    return [r for r in RUNS if r["status"] not in ("empty", "superseded")]


def library():
    runs = visible_runs()
    # scatter
    W, H = 720, 330
    X = scale(0, 55, 44, W - 10)
    Y = scale(20, -55, 12, H - 26)
    pts = []
    for r in runs:
        m = r["metrics"]
        if m["max_drawdown"] is None or m["total_return"] is None:
            continue
        low = r["trades"] < 100
        rad = 2.2 + math.sqrt(r["trades"]) * 0.36
        col = color_of(r)
        pts.append(f'<circle cx="{X(-m["max_drawdown"]*100):.1f}" cy="{Y(m["total_return"]*100):.1f}" r="{rad:.1f}" fill="{"none" if low else col}" fill-opacity=".8" stroke="{col}" stroke-width="1.4"/>')
    ticks = "".join(f'<text x="{X(v):.1f}" y="{H-8}" text-anchor="middle" fill="#6b737c" font-size="10" font-family="IBM Plex Mono">−{v}%</text>' for v in range(0, 56, 10))
    ticks += "".join(f'<text x="36" y="{Y(v)+3:.1f}" text-anchor="end" fill="#6b737c" font-size="10" font-family="IBM Plex Mono">{v:+d}%</text>' for v in range(20, -56, -15))
    lab = [("NIFTY 0-DTE benchmark", 9.6, 18.2, "start"), ("SENSEX 1-DTE timing cluster", 31, -28, "start"), ("SENSEX 0-DTE iron condor", 51.7, -52, "end"), ("NIFTY 1-DTE IC", 32, -32.5, "start")]
    labs = "".join(f'<text x="{X(dx)+(10 if a=="start" else -10):.1f}" y="{Y(dy)+4:.1f}" fill="#e6e8ea" font-size="11" text-anchor="{a}">{t}</text>' for t, dx, dy, a in lab)
    scatter = f"""<svg viewBox="0 0 {W} {H}" width="100%" height="{H}">
<rect x="{X(0):.1f}" y="12" width="{X(10)-X(0):.1f}" height="{Y(0)-12:.1f}" fill="#7cc4ff" fill-opacity=".05" stroke="#7cc4ff" stroke-opacity=".25" stroke-dasharray="3 4"/>

<line x1="44" x2="{W-10}" y1="{Y(0):.1f}" y2="{Y(0):.1f}" stroke="#2a3650"/>{ticks}{''.join(pts)}{labs}</svg>"""
    legend = "".join(f'<span class="chip"><span class="dot" style="background:{c}"></span>{l}</span>' for l, c in [("NIFTY 0-DTE", "#7cc4ff"), ("NIFTY 1-DTE", "#2f6fd6"), ("SENSEX 0-DTE", "#ffb35c"), ("SENSEX 1-DTE", "#c4561b"), ("Other / mixed", "#9aa3b2")])
    leaders = sorted([r for r in runs if r["trades"] >= 100 and r["metrics"]["sharpe"] is not None], key=lambda r: -r["metrics"]["sharpe"])[:6]
    lead_rows = "".join(f'<div style="display:grid;grid-template-columns:18px minmax(0,1fr) 54px 64px;gap:8px;align-items:center;height:34px;border-bottom:1px solid var(--line-faint);font-size:12.5px"><span class="mono faint">{i+1}</span><span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap"><span class="dot" style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{color_of(r)};margin-right:6px"></span>{esc(r["name"].replace(" — corrected timing / conditional data",""))}</span><span class="num">{r["metrics"]["sharpe"]:.2f}</span><span class="num pos">{pct(r["metrics"]["total_return"])}</span></div>' for i, r in enumerate(leaders))
    # table
    rows_sorted = sorted(runs, key=lambda r: -(r["metrics"]["sharpe"] or -99))[:14]
    trs = []
    for i, r in enumerate(rows_sorted):
        m = r["metrics"]
        low = r["trades"] < 100
        mk = mkey(r)
        mlabel = "+".join(r["markets"]) + " · " + ",".join(str(d) for d in r["dte"]) + "D"
        sel = ' aria-selected="true"' if i in (4,) else ""
        chk = "checked" if i in (4,) else ""
        grp = '<span class="chip" style="height:18px;font-size:10.5px;margin-left:6px">timing sweep</span>' if r["group"] else ""
        cagr_warn = ' <span class="accent" title="Annualised from a window under 252 sessions">⚠</span>' if (m.get("sessions") or 999) < 252 else ""
        trs.append(f"""<tr{sel} style="{'opacity:.78' if low else ''}"><td><input type="checkbox" aria-label="Select" {chk} style="accent-color:var(--accent)"></td>
<td><div style="max-width:300px;overflow:hidden"><div class="name" style="display:flex;align-items:center;max-width:300px"><span style="overflow:hidden;text-overflow:ellipsis">{esc(r['name'].replace(' — corrected timing / conditional data',''))}</span>{grp}</div><span class="sub" style="overflow:hidden;text-overflow:ellipsis">{r['id']}</span></div></td>
<td><span style="display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--text-2)"><span style="width:8px;height:8px;border-radius:50%;background:{color_of(r)}"></span>{mlabel}</span></td>
<td>{badge(r['status'])}</td><td class="num">{r['trades']}</td>
<td class="num {'pos' if m['total_return']>=0 else 'neg'}">{pct(m['total_return'])}</td><td class="num">{pct(m['cagr'])}{cagr_warn}</td>
<td class="num" style="color:var(--text-1);font-weight:500">{num(m['sharpe'])}</td><td class="num neg">{pct(m['max_drawdown'])}</td><td class="num">{num(m['profit_factor'])}</td><td class="num">{pct(r['p_net_positive'], 0, False)}</td></tr>""")
    head = '<thead><tr><th style="width:34px"></th><th>Run</th><th>Market · DTE</th><th>Status</th><th class="num">Trades</th><th class="num">Return</th><th class="num">CAGR</th><th class="num" aria-sort="descending">Sharpe</th><th class="num">Max DD</th><th class="num">PF</th><th class="num" title="Bootstrap probability that net P&amp;L is positive">P(&gt;0)</th></tr></thead>'
    filt = f"""<aside class="panel" style="display:flex;flex-direction:column;gap:18px;align-self:start">
<div><div class="eyebrow" style="margin-bottom:8px">Market</div><div style="display:flex;gap:6px;flex-wrap:wrap"><button class="chip chip--button chip--on">All</button><button class="chip chip--button">NIFTY</button><button class="chip chip--button">SENSEX</button></div></div>
<div><div class="eyebrow" style="margin-bottom:8px">DTE</div><div style="display:flex;gap:6px"><button class="chip chip--button chip--on">Any</button><button class="chip chip--button">0</button><button class="chip chip--button">1</button><button class="chip chip--button">2</button></div></div>
<div><div class="eyebrow" style="margin-bottom:8px">Structure</div><select class="select" style="width:100%"><option>All structures (4)</option></select></div>
<div><div class="eyebrow" style="margin-bottom:4px">Status</div>
<label class="check"><input type="checkbox" checked>{badge('ok')}<span class="mono faint" style="margin-left:auto">8</span></label>
<label class="check"><input type="checkbox" checked>{badge('low_sample')}<span class="mono faint" style="margin-left:auto">15</span></label>
<label class="check"><input type="checkbox" checked>{badge('data_issues')}<span class="mono faint" style="margin-left:auto">99</span></label>
<label class="check"><input type="checkbox">{badge('superseded')}<span class="mono faint" style="margin-left:auto">2</span></label>
<label class="check"><input type="checkbox">{badge('empty')}<span class="mono faint" style="margin-left:auto">4</span></label></div>
<div><div class="eyebrow" style="margin-bottom:8px">Group</div><select class="select" style="width:100%"><option>Any group</option><option>3-year timing sweep (99)</option></select></div>
<label class="field">Min. trades <span class="mono accent" style="float:right">0</span><input type="range" class="range" min="0" max="160" value="0"></label>
<div class="callout">Hollow dots and dimmed rows have fewer than 100 trades. <b>Data issues</b> means more than 5% of trades were forced out by missing market data.</div></aside>"""
    body = f"""<section style="display:flex;align-items:flex-end;gap:16px"><div style="flex:1"><div class="eyebrow">Library</div>
<h1 style="margin:4px 0 0;font-size:28px;font-weight:600">122 runs</h1><div class="muted" style="font-size:13px">4 empty and 2 superseded runs hidden · 99 belong to the 3-year timing sweep · all 99 have more than 5% forced data exits</div></div>
<button class="btn">{icon('compare',15)}Compare selected (1)</button><button class="btn btn--primary">{icon('new',15)}New run</button></section>
<div class="banner" style="border-color:rgba(90,176,255,.35);background:var(--info-bg);color:#b9dcff">{icon('info',16)}<span>All metrics use the <b>calendar_daily</b> basis: every exchange session, idle days included. 23 older runs were recomputed on 29 Sep 2026.</span><a href="#" style="margin-left:auto">Migration report →</a></div>
<div class="grid" style="grid-template-columns:240px minmax(0,1fr)">{filt}
<div class="grid">
<div class="grid" style="grid-template-columns:minmax(0,1fr) 380px">
<section class="panel"><div class="panel__head"><span class="eyebrow">Return vs max drawdown · size = trades</span></div>{scatter}<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:6px">{legend}<span class="chip" style="border-style:dashed;border-color:#7cc4ff55">Dashed box = sweet spot · DD &lt; 10%, return &gt; 0</span><span class="chip">○ hollow = &lt; 100 trades</span></div></section>
<section class="panel"><div class="panel__head"><span class="eyebrow">Leaders · ≥ 100 trades · by Sharpe</span></div>{lead_rows}
<div class="panel__foot">The highest-Sharpe runs overall (Top 1–3, combined) have 14–54 trades, so they are excluded here.</div></section></div>
<div class="table-wrap"><table class="table table--dense">{head}<tbody>{''.join(trs)}</tbody></table></div>
<div style="display:flex;justify-content:space-between" class="muted"><span style="font-size:12px">Showing 1–14 of 122 · sorted by Sharpe ↓</span><div style="display:flex;gap:6px"><button class="btn btn--sm" disabled>Prev</button><button class="btn btn--sm">Next</button></div></div>
</div></div>"""
    return shell("Library", "library", "<b>Library</b>", body)


def compare():
    ids = ["nifty-0dte-strangle-benchmark", "sensex-0dte-strangle-benchmark", "validated-timing-3y-sensex-0dte-static", "top1-sensex-1dte-strangle"]
    names = ["NIFTY 0-DTE Strangle Benchmark", "SENSEX 0-DTE Strangle Benchmark", "SENSEX 0DTE STATIC (timing)", "Top 1: SENSEX Thu 1-DTE Strangle"]
    cmp = DATA["cmp"]
    import datetime as dt
    d0, d1 = dt.date(2023, 9, 1), dt.date(2026, 9, 15)
    W, H = 1000, 260
    X = lambda s: 50 + (dt.date.fromisoformat(s) - d0).days / (d1 - d0).days * (W - 60)
    Y = scale(-12, 20, H - 20, 8)
    lines = []
    for k, i in enumerate(ids):
        pts = [(X(r[0]), Y((r[1] / 180000 - 1) * 100)) for r in cmp[i]]
        lines.append(polyline(pts, SERIES[k], 1.8))
    grid = "".join(f'<line x1="50" x2="{W-10}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="#14181c"/><text x="44" y="{Y(v)+3:.1f}" text-anchor="end" fill="#6b737c" font-size="10" font-family="IBM Plex Mono">{v:+d}%</text>' for v in range(-10, 21, 5))
    years = "".join(f'<text x="{X(f"{y}-01-01"):.1f}" y="{H-4}" fill="#6b737c" font-size="10" font-family="IBM Plex Mono">{y}</text><line x1="{X(f"{y}-01-01"):.1f}" x2="{X(f"{y}-01-01"):.1f}" y1="0" y2="{H-18}" stroke="#14181c"/>' for y in (2024, 2025, 2026))
    eq_svg = f'<svg viewBox="0 0 {W} {H}" width="100%" height="{H}">{grid}{years}<line x1="50" x2="{W-10}" y1="{Y(0):.1f}" y2="{Y(0):.1f}" stroke="#2a3037"/>{"".join(lines)}</svg>'
    Hd = 90
    Yd = scale(-15, 0, Hd - 4, 4)
    dl = []
    for k, i in enumerate(ids):
        dl.append(polyline([(X(r[0]), Yd(r[2] * 100)) for r in cmp[i]], SERIES[k], 1.2))
    dd_svg = f'<svg viewBox="0 0 {W} {Hd}" width="100%" height="{Hd}"><line x1="50" x2="{W-10}" y1="{Yd(0):.1f}" y2="{Yd(0):.1f}" stroke="#2a3037"/><text x="44" y="{Yd(-10)+3:.1f}" text-anchor="end" fill="#6b737c" font-size="10" font-family="IBM Plex Mono">−10%</text>{"".join(dl)}</svg>'
    L = LEGACY
    s0 = DATA["s0"]["metrics"]
    S0R = next(r for r in RUNS if r["id"] == ids[2])
    cols = [
        dict(net=30330.69, ret=L[ids[0]]["new"]["total_return"], cagr=L[ids[0]]["new"]["cagr"], sharpe=L[ids[0]]["new"]["sharpe"], sortino=L[ids[0]]["new"]["sortino"], dd=L[ids[0]]["new"]["max_drawdown"], pf=1.31, hit=.350, n=157, p=L[ids[0]]["robust"]["p_net_positive"], w5=L[ids[0]]["robust"]["net_without_top5"], ses=740, status="ok"),
        dict(net=L[ids[1]]["net"], ret=L[ids[1]]["new"]["total_return"], cagr=L[ids[1]]["new"]["cagr"], sharpe=L[ids[1]]["new"]["sharpe"], sortino=L[ids[1]]["new"]["sortino"], dd=L[ids[1]]["new"]["max_drawdown"], pf=1.28, hit=.401, n=157, p=L[ids[1]]["robust"]["p_net_positive"], w5=L[ids[1]]["robust"]["net_without_top5"], ses=741, status="ok"),
        dict(net=s0["net_pnl"], ret=s0["total_return"], cagr=s0["cagr"], sharpe=s0["sharpe"], sortino=s0["sortino"], dd=s0["max_drawdown"], pf=s0["profit_factor"], hit=s0["hit_rate"], n=157, p=S0R["p_net_positive"], w5=S0R["without_top5"], ses=741, status="data_issues"),
        dict(net=L[ids[3]]["net"], ret=L[ids[3]]["new"]["total_return"], cagr=L[ids[3]]["new"]["cagr"], sharpe=L[ids[3]]["new"]["sharpe"], sortino=L[ids[3]]["new"]["sortino"], dd=L[ids[3]]["new"]["max_drawdown"], pf=8.57, hit=.786, n=14, p=L[ids[3]]["robust"]["p_net_positive"], w5=L[ids[3]]["robust"]["net_without_top5"], ses=65, status="low_sample"),
    ]
    rows = [("Status", "status", None), ("Trades", "n", "count"), ("Sessions in window", "ses", "count"), ("Net P&L", "net", "inr"), ("Total return", "ret", "pct"), ("CAGR", "cagr", "pct"),
            ("Sharpe", "sharpe", "num"), ("Sortino", "sortino", "num"), ("Max drawdown", "dd", "pct"), ("Profit factor", "pf", "num"), ("Hit rate", "hit", "pct0"),
            ("P(net > 0) · bootstrap", "p", "pct0"), ("Net without best 5", "w5", "inr")]
    trs = []
    for lab, k, f in rows:
        vals = [c[k] for c in cols]
        cells = []
        eligible = [j for j, c in enumerate(cols) if c["n"] >= 100 and c["ses"] >= 252]
        numeric = [vals[j] for j in eligible if isinstance(vals[j], (int, float)) and vals[j] is not None]
        best = None
        if f in ("inr", "pct", "num", "pct0") and numeric:
            best = max(numeric)
        for j, v in enumerate(vals):
            if f is None:
                cells.append(f"<td>{badge(v)}</td>")
                continue
            txt = {"inr": lambda x: inr(x, True), "pct": lambda x: pct(x), "num": lambda x: num(x), "pct0": lambda x: pct(x, 0, False), "count": lambda x: f"{x}"}[f](v) if v is not None else "—"
            warn = ""
            if k == "cagr" and cols[j]["ses"] < 252:
                warn = ' <span class="accent" title="Annualised from 65 sessions">⚠</span>'
            if k == "n" and v < 100:
                warn = ' <span class="accent">⚠</span>'
            style = "color:var(--text-1);font-weight:600;background:rgba(245,165,36,.07)" if (best is not None and v == best and j in eligible) else ""
            cells.append(f'<td class="num" style="{style}">{txt}{warn}</td>')
        trs.append(f'<tr><td style="color:var(--text-2)">{lab}</td>{"".join(cells)}</tr>')
    ths = "".join(f'<th class="num" style="text-transform:none;letter-spacing:0;font-family:var(--font-sans);font-size:12px;color:var(--text-1)"><span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:{SERIES[k]};margin-right:6px"></span>{esc(n)}</th>' for k, n in enumerate(names))
    chips = "".join(f'<span class="chip chip--on" style="height:30px"><span class="dot" style="background:{SERIES[k]}"></span>{esc(n)}<button class="btn btn--ghost icon-btn" style="width:18px;height:18px" aria-label="Remove">{icon("x",12)}</button></span>' for k, n in enumerate(names))
    body = f"""<section style="display:flex;align-items:flex-end;gap:16px"><div style="flex:1"><div class="eyebrow">Compare</div><h1 style="margin:4px 0 0;font-size:28px;font-weight:600">4 runs, one calendar</h1></div>
<button class="btn">{icon('copy',15)}Copy link</button></section>
<section style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">{chips}<button class="btn btn--sm">+ Add run</button><span class="muted" style="font-size:12px;margin-left:auto">Max 4 · colours are fixed by slot</span></section>
<div class="banner">{icon('warn',16)}<span><b>Top 1</b> covers 65 sessions (Jun–Sep 2026) and 14 trades. Its CAGR and Sharpe are annualised from a short window and are not comparable to the 3-year runs.</span></div>
<section class="panel"><div class="panel__head"><span class="eyebrow">Cumulative return on capital · daily, aligned by date</span><div class="seg seg--mono"><button class="seg__item" aria-selected="true">% return</button><button class="seg__item">₹ P&amp;L</button></div></div>{eq_svg}
<div class="mono faint" style="font-size:11px;margin:8px 0 4px">DRAWDOWN</div>{dd_svg}</section>
<div class="table-wrap"><table class="table"><thead><tr><th>Metric</th>{ths}</tr></thead><tbody>{''.join(trs)}</tbody></table></div>
<div class="muted" style="font-size:12px">The best value in each row is highlighted, counting only runs with ≥ 100 trades and ≥ 252 sessions. Values from runs below those limits are marked ⚠ and never highlighted. — means the metric is not recorded for that run.</div>"""
    return shell("Compare", "compare", "<span>Library</span><span class='sep'>/</span><b>Compare</b>", body)


def groups():
    g = [r for r in RUNS if r["group"] == "validated-timing-3y"]
    fams = ["STATIC", "LEG100", "A", "B", "C", "D", "CUT", "EXIT_TOUCH", "ONE_CONV"]
    cols = [("NIFTY", 0), ("NIFTY", 1), ("SENSEX", 0), ("SENSEX", 1)]
    cells = ['<span></span>'] + [f'<span class="mono" style="text-align:center;color:var(--text-2);padding-bottom:4px">{m} {d}-DTE</span>' for m, d in cols]
    for f in fams:
        cells.append(f'<span class="mono" style="color:var(--text-2);align-self:center">{f}</span>')
        for m, d in cols:
            xs = [r["metrics"]["total_return"] for r in g if r["axes"]["family"] == f and r["axes"]["market"] == m and r["axes"]["dte"] == d]
            if not xs:
                cells.append('<div class="heat__cell heat__cell--empty">—</div>')
                continue
            v = sum(xs) / len(xs) * 100
            a = min(0.95, 0.12 + abs(v) / 18)
            bg = f"rgba(90,176,255,{a:.2f})" if v >= 0 else f"rgba(224,122,69,{a:.2f})"
            fg = "#0a0c0e" if abs(v) > 9 else "#e6e8ea"
            sel = "outline:2px solid var(--accent);outline-offset:1px;" if (f == "A" and m == "SENSEX" and d == 0) else ""
            cells.append(f'<div class="heat__cell" style="height:38px;background:{bg};color:{fg};{sel}"><span>{v:+.1f}%<span style="opacity:.7;font-size:10px"> ·{len(xs)}</span></span></div>')
    # knob effects
    s0 = [r for r in g if r["axes"]["market"] == "SENSEX" and r["axes"]["dte"] == 0 and r["axes"]["family"] in ("A", "B", "C")]
    d2 = [r for r in s0 if r["axes"]["d"] == "2"]
    d3 = [r for r in s0 if r["axes"]["d"] == "3"]
    pos = lambda xs: sum(1 for r in xs if r["metrics"]["total_return"] > 0)
    def cnt(market, dte):
        xs = [r for r in g if r["axes"]["market"] == market and r["axes"]["dte"] == dte]
        return pos(xs), len(xs)
    s0p, s0n = cnt("SENSEX", 0)
    s1p, s1n = cnt("SENSEX", 1)
    n0p, n0n = cnt("NIFTY", 0)
    n1p, n1n = cnt("NIFTY", 1)
    capeff = []
    for c in ("2", "99"):
        xs = [r["metrics"]["total_return"] for r in g if r["axes"]["cap"] == c]
        capeff.append(sum(xs) / len(xs) * 100)
    sel = sorted([r for r in g if r["axes"]["family"] == "A" and r["axes"]["market"] == "SENSEX" and r["axes"]["dte"] == 0], key=lambda r: -r["metrics"]["total_return"])
    vrows = "".join(f'<tr><td class="mono">{r["id"].replace("validated-timing-3y-","")}</td><td class="num">{r["axes"]["cap"]}</td><td class="num">{r["axes"]["d"]}</td><td class="num">{r["axes"]["w"] or "—"}</td><td class="num {"pos" if r["metrics"]["total_return"]>=0 else "neg"}">{pct(r["metrics"]["total_return"])}</td><td class="num">{num(r["metrics"]["sharpe"])}</td><td class="num neg">{pct(r["metrics"]["max_drawdown"])}</td><td class="num">{num(r["metrics"]["profit_factor"])}</td><td><a href="#">Open →</a></td></tr>' for r in sel)
    knobs = f"""<div class="kv kv--divided"><span>SENSEX 0-DTE · variants positive</span><span class="accent">{s0p} / {s0n}</span></div>
<div class="kv kv--divided"><span>SENSEX 1-DTE · variants positive</span><span class="neg">{s1p} / {s1n}</span></div>
<div class="kv kv--divided"><span>NIFTY 0-DTE · variants positive</span><span>{n0p} / {n0n}</span></div>
<div class="kv kv--divided"><span>NIFTY 1-DTE · variants positive</span><span class="neg">{n1p} / {n1n}</span></div>
<div class="kv kv--divided"><span>SENSEX 0-DTE A/B/C · d=2 positive</span><span class="pos">{pos(d2)} / {len(d2)}</span></div>
<div class="kv kv--divided"><span>SENSEX 0-DTE A/B/C · d=3 positive</span><span class="neg">{pos(d3)} / {len(d3)}</span></div>
<div class="kv"><span>cap 2 vs cap 99 · mean return</span><span>{capeff[0]:+.1f}% vs {capeff[1]:+.1f}%</span></div>
<div class="callout" style="margin-top:10px">The market/DTE regime matters more than any knob: SENSEX 1-DTE loses in every variant. Within SENSEX 0-DTE, <span class="mono">d</span> decides the result for families A/B/C.</div>"""
    body = f"""<section style="display:flex;align-items:flex-end;gap:16px"><div style="flex:1"><div class="eyebrow">Group</div><h1 style="margin:4px 0 0;font-size:28px;font-weight:600">3-year timing sweep</h1>
<div class="muted">99 runs · 2023-09-13 → 2026-09-11 · axes: market, dte, family, cap, d, w</div></div>
<button class="btn">{icon('compare',15)}Compare top 4</button></section>
<section style="display:flex;gap:10px;align-items:center;flex-wrap:wrap"><span class="eyebrow">Rows</span><select class="select"><option>family</option></select>
<span class="eyebrow">Columns</span><select class="select"><option>market × dte</option></select>
<span class="eyebrow">Cell</span><div class="seg"><button class="seg__item" aria-selected="true">Mean return</button><button class="seg__item">Mean Sharpe</button><button class="seg__item">Max DD</button><button class="seg__item">% positive</button></div></section>
<div class="grid" style="grid-template-columns:minmax(0,1fr) 400px">
<section class="panel"><div class="panel__head"><span class="eyebrow">Mean total return · cell label = mean · count</span></div>
<div class="heat" style="grid-template-columns:110px repeat(4,minmax(0,1fr));gap:4px;font-size:12px">{''.join(cells)}</div>
<div class="panel__foot" style="display:flex;gap:10px;align-items:center"><span style="width:44px;height:8px;border-radius:2px;background:linear-gradient(90deg,#e07a45,#1a2233,#5ab0ff)"></span>−23% … +16% · diverging blue/orange (colour-blind safe) · click a cell to list its variants</div></section>
<section class="panel"><div class="panel__head"><span class="eyebrow">Knob effects</span></div>{knobs}</section></div>
<section class="panel panel--flush"><div style="padding:12px 16px" class="panel__head"><span class="eyebrow">Selected cell · family A × SENSEX 0-DTE · 4 variants</span></div>
<table class="table"><thead><tr><th>Variant</th><th class="num">cap</th><th class="num">d</th><th class="num">w</th><th class="num" aria-sort="descending">Return</th><th class="num">Sharpe</th><th class="num">Max DD</th><th class="num">PF</th><th></th></tr></thead><tbody>{vrows}</tbody></table></section>"""
    return shell("Group", "groups", "<span>Groups</span><span class='sep'>/</span><b>validated-timing-3y</b>", body)


def new_run():
    body = f"""<section><div class="eyebrow">New run</div><h1 style="margin:4px 0 0;font-size:28px;font-weight:600">Build a backtest command</h1>
<div class="muted" style="max-width:760px">The UI cannot start runs yet. Fill the form, copy the command, run it in a terminal, then refresh the Library. Only the flags the <span class="mono">stolgo</span> CLI supports today are shown.</div></section>
<div class="grid" style="grid-template-columns:minmax(0,1fr) 420px">
<section class="panel"><div class="panel__head"><span class="panel__title">Parameters</span></div>
<div class="grid" style="grid-template-columns:repeat(2,minmax(0,1fr));gap:16px">
<label class="field">Strategy file (.py) <input class="input mono" value="examples/trend_breakout_backtest.py"></label>
<label class="field">Strategy class <input class="input mono" value="TrendBreakout"></label>
<label class="field">Data CSV (OHLCV) <input class="input mono" value="data/NIFTY_15m.csv"></label>
<label class="field">Run id (folder name under runs/) <input class="input mono" value="nifty-trend-breakout-15m"><span class="faint">Lowercase, digits and dashes only. Must not already exist.</span></label>
<label class="field">Starting cash (₹) <input class="input mono" value="180000"></label>
<label class="field">Commission (fraction per fill) <input class="input mono" value="0.0003"><span class="faint">0.0003 = 3 bps. Statutory F&amp;O charges are not modelled by this CLI.</span></label></div>
<div class="eyebrow" style="margin:18px 0 8px">Command</div>
<div class="code">stolgo examples/trend_breakout_backtest.py \\
  --class TrendBreakout \\
  --data data/NIFTY_15m.csv \\
  --cash 180000 \\
  --commission 0.0003 \\
  --output runs/nifty-trend-breakout-15m</div>
<div style="display:flex;gap:8px;margin-top:12px"><button class="btn btn--primary">{icon('copy',15)}Copy command</button><button class="btn">Reset</button></div></section>
<aside class="grid" style="align-content:start">
<section class="panel"><div class="panel__head"><span class="panel__title">After it finishes</span></div>
<ol style="margin:0;padding-left:18px;color:var(--text-2);line-height:1.8"><li>The run folder appears in <span class="mono">runs/</span> with a v2 manifest.</li><li>The server re-indexes on the next Library load.</li><li>Open it from the Library. It is sorted by creation time when you choose “Newest”.</li></ol></section>
<section class="panel"><div class="panel__head"><span class="panel__title">Options research runs</span></div>
<div style="color:var(--text-2);font-size:13px">Options replays (strangles, iron condors, timing sweeps) come from the research generators. They must call <span class="mono">export_run_v2()</span> to appear here with full diagnostics.</div>
<div class="callout" style="margin-top:10px">Runner API (queue from UI) is <b>not built</b>. This page will gain a “Run” button when <span class="mono">POST /api/runs</span> exists.</div></section></aside></div>"""
    return shell("New run", "new", "<b>New run</b>", body)


def components():
    def sw(name, var):
        return f'<div style="display:flex;flex-direction:column;gap:6px"><div style="height:44px;border-radius:6px;border:1px solid var(--line);background:var({var})"></div><span class="mono" style="font-size:11px;color:var(--text-2)">{var}</span><span class="faint" style="font-size:11px">{name}</span></div>'
    colors = "".join(sw(n, v) for n, v in [("app bg", "--bg-app"), ("panel", "--bg-panel"), ("raised", "--bg-raised"), ("active", "--bg-active"), ("line", "--line"), ("text-1", "--text-1"), ("text-muted", "--text-muted"), ("accent", "--accent"), ("pos", "--pos"), ("neg", "--neg"), ("neg-text", "--neg-text"), ("info", "--info")])
    body = f"""<section><div class="eyebrow">Design system</div><h1 style="margin:4px 0 0;font-size:28px;font-weight:600">Components &amp; states</h1><div class="muted">Class names match <span class="mono">docs/design/components.css</span>. Build React components with the same names (UI plan §5).</div></section>
<section class="panel"><div class="panel__head"><span class="eyebrow">Colour tokens</span></div><div style="display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:12px">{colors}</div></section>
<div class="grid" style="grid-template-columns:repeat(3,minmax(0,1fr))">
<section class="panel"><div class="panel__head"><span class="eyebrow">Buttons · Button</span></div><div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
<button class="btn btn--primary">Primary</button><button class="btn">Default</button><button class="btn btn--ghost">Ghost</button><button class="btn btn--sm">Small</button><button class="btn" disabled>Disabled</button><button class="btn icon-btn" aria-label="Expand">{icon('expand',15)}</button></div>
<div class="eyebrow" style="margin:16px 0 8px">Segmented · Tabs</div><div class="seg"><button class="seg__item" aria-selected="true">Price</button><button class="seg__item">Equity</button></div>
<div class="tabs" style="margin-top:10px"><button class="tab" aria-selected="true">Overview</button><button class="tab">Trades<span class="count">157</span></button><button class="tab">Diagnostics</button></div></section>
<section class="panel"><div class="panel__head"><span class="eyebrow">StatusBadge · all values</span></div><div style="display:flex;gap:8px;flex-wrap:wrap">{''.join(badge(s) for s in STATUS_BADGE)}<span class="badge badge--info">calendar_daily</span></div>
<div class="eyebrow" style="margin:16px 0 8px">Chips</div><div style="display:flex;gap:8px;flex-wrap:wrap"><span class="chip">NIFTY</span><span class="chip chip--button chip--on">Selected</span><span class="chip"><span class="dot" style="background:#7cc4ff"></span>NIFTY 0-DTE</span></div>
<div class="eyebrow" style="margin:16px 0 8px">Money &amp; numbers</div><div class="mono" style="display:flex;gap:16px"><span class="pos">+₹30,331</span><span class="neg">−₹6,014</span><span>0.73</span><span class="neg">−9.5%</span><span class="muted">—</span></div></section>
<section class="panel"><div class="panel__head"><span class="eyebrow">VerdictPill · 5 states</span></div><div class="grid" style="gap:8px">
<div class="verdict verdict--ok"><span class="verdict__dot"></span><div><div class="verdict__label">EDGE · ROBUST</div><div class="verdict__text">Survives bootstrap and top-5 removal</div></div></div>
<div class="verdict"><span class="verdict__dot"></span><div><div class="verdict__label">EDGE · FRAGILE</div><div class="verdict__text">Profitable, but the best 5 trades carry it</div></div></div>
<div class="verdict"><span class="verdict__dot"></span><div><div class="verdict__label">EDGE · UNPROVEN</div><div class="verdict__text">Fewer than 30 trades</div></div></div>
<div class="verdict verdict--bad"><span class="verdict__dot"></span><div><div class="verdict__label">NO EDGE</div><div class="verdict__text">P(net &gt; 0) below 80%</div></div></div>
<div class="verdict" style="border-color:var(--line-strong);background:transparent"><span class="verdict__dot" style="background:var(--text-muted)"></span><div><div class="verdict__label" style="color:var(--text-muted)">NO TRADES</div><div class="verdict__text" style="color:var(--text-muted)">Nothing to evaluate</div></div></div></div></section>
</div>
<section class="kpis"><div class="kpi"><div class="kpi__label">Net P&amp;L</div><div class="kpi__value pos">+₹30,331</div><div class="kpi__sub">+16.9% on capital</div></div>
<div class="kpi"><div class="kpi__label">CAGR <span class="accent" title="Annualised from a short window">⚠</span></div><div class="kpi__value">+44.4%</div><div class="kpi__sub kpi__warn">from 65 sessions · not comparable</div></div>
<div class="kpi"><div class="kpi__label">Sharpe</div><div class="kpi__value">0.73</div><div class="kpi__sub">daily, √252</div></div>
<div class="kpi"><div class="kpi__label">Avg R</div><div class="kpi__value muted">—</div><div class="kpi__sub">R not recorded for this run</div></div>
<div class="kpi"><div class="kpi__label">Loading</div><div class="skeleton" style="height:28px;margin-top:6px;width:80%"></div><div class="skeleton" style="height:12px;margin-top:8px;width:50%"></div></div>
<div class="kpi"><div class="kpi__label">Max drawdown</div><div class="kpi__value neg">−9.5%</div><div class="kpi__sub">347 sessions</div></div></section>
<div class="grid" style="grid-template-columns:repeat(4,minmax(0,1fr))">
<div class="empty-state"><div class="empty-state__title">No price data for this run</div><div>The generator did not export <span class="mono">ohlcv.parquet</span>. Equity and trades are still available.</div><button class="btn btn--sm">Show equity instead</button></div>
<div class="empty-state"><div class="empty-state__title">Run not migrated</div><div>This run still uses the v1 manifest. Run<br><span class="mono">python scripts/migrate_runs_v2.py</span></div></div>
<div class="empty-state"><div class="empty-state__title">No trades</div><div>The strategy never entered. Check the signal funnel in Diagnostics.</div></div>
<div class="empty-state" style="border-color:rgba(229,72,77,.4)"><div class="empty-state__title">Can’t reach the API</div><div class="mono" style="font-size:12px">GET /api/runs → 502</div><button class="btn btn--sm">Retry</button></div></div>
<div class="grid" style="grid-template-columns:repeat(3,minmax(0,1fr))">
<div class="banner">{icon('warn',16)}<span>Warning banner: amber, for data issues and short windows.</span></div>
<div class="banner banner--bad">{icon('warn',16)}<span>Error banner: red, for failed loads.</span></div>
<div style="position:relative;height:120px"><div class="tooltip" style="left:0;top:0;position:absolute"><div class="mono" style="color:var(--text-1)">08 Sep 2026 · #157</div><div class="kv"><span>Net</span><span class="pos">+₹1,155</span></div><div class="kv"><span>R</span><span>+0.64</span></div><div class="kv"><span>Exit</span><span>TIME_EXIT</span></div></div></div></div>
<div class="table-wrap"><table class="table"><thead><tr><th>Row states</th><th class="num">Net</th><th>Note</th></tr></thead><tbody>
<tr><td>Default</td><td class="num pos">+₹1,155</td><td class="muted">36px height</td></tr><tr style="background:#11151a"><td>Hover</td><td class="num neg">−₹902</td><td class="muted">#11151a</td></tr>
<tr aria-selected="true"><td>Selected</td><td class="num pos">+₹3,043</td><td class="muted">bg-active + 2px amber inset</td></tr><tr style="opacity:.78"><td>Low sample (dimmed)</td><td class="num pos">+₹17,307</td><td class="muted">opacity .78</td></tr></tbody></table></div>"""
    return shell("Components", "library", "<b>Design system</b>", body)
