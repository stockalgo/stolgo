"""Run detail mockups: Overview, Trades, Diagnostics, Full-screen chart."""
from common import *  # noqa

B = DATA["bench"]
BL = LEGACY["nifty-0dte-strangle-benchmark"]
NEW, ROB = BL["new"], BL["robust"]
CAP = 180000.0


def run_header(name, chips, verdict_cls, verdict_label, verdict_text, status_badge):
    ch = "".join(f'<span class="chip">{c}</span>' for c in chips)
    return f"""<section class="run-head"><div style="flex:1;min-width:0">
<div style="display:flex;align-items:center;gap:10px">{status_badge}<span class="eyebrow">Run · nifty-0dte-strangle-benchmark</span></div>
<h1 class="run-head__title" style="margin-top:6px">{esc(name)}</h1><div class="run-head__chips">{ch}</div></div>
<div class="verdict {verdict_cls}"><span class="verdict__dot"></span><div><div class="verdict__label">{verdict_label}</div><div class="verdict__text">{verdict_text}</div></div></div></section>"""


def run_tabs(active):
    t = [("overview", "Overview", ""), ("trades", "Trades", "157"), ("diagnostics", "Diagnostics", "")]
    out = []
    for k, label, c in t:
        sel = "true" if k == active else "false"
        cnt = f'<span class="count">{c}</span>' if c else ""
        out.append(f'<button class="tab" role="tab" aria-selected="{sel}">{label}{cnt}</button>')
    return f'<div class="tabs" role="tablist" style="display:flex;align-items:flex-end"><div style="display:flex;gap:4px;flex:1">{"".join(out)}</div>' \
           f'<div style="display:flex;gap:8px;padding-bottom:6px"><button class="btn btn--sm">{icon("compare",14)}Add to compare</button>' \
           f'<button class="btn btn--sm">{icon("external",14)}Audit report</button><button class="btn btn--sm">{icon("download",14)}Trades CSV</button></div></div>'


TOP_ACTIONS = f'<button class="btn">{icon("compare",15)}Compare (2)</button>'
CRUMBS = '<span>Library</span><span class="sep">/</span><span>NIFTY · short strangle</span><span class="sep">/</span><b>nifty-0dte-strangle-benchmark</b>'
CHIPS = ["NIFTY", "Short strangle · 0 DTE", "157 trades", "14 Sep 2023 → 08 Sep 2026 · 740 sessions", "Capital ₹1,80,000", "Entry 09:30 · Exit 14:45 IST"]
HEADER = run_header("NIFTY 0-DTE Strangle Benchmark", CHIPS, "", "EDGE · FRAGILE",
                    "Profitable, but the best 5 trades carry it", '<span class="badge badge--ok">OK</span>')


def kpis():
    items = [
        ("Net P&L", inr(30330.69, True), "+16.9% on capital", "pos"),
        ("CAGR", pct(NEW["cagr"]), "calendar · 3.0 yrs", ""),
        ("Sharpe", num(NEW["sharpe"]), f"Sortino {num(NEW['sortino'])} · daily, √252", ""),
        ("Max drawdown", pct(NEW["max_drawdown"]), f"{NEW['max_drawdown_duration']:.0f} sessions underwater", "neg"),
        ("Profit factor", "1.31", "payoff 2.43×", ""),
        ("Hit rate", "35.0%", "55 W · 102 L · ₹193 / trade", ""),
    ]
    cells = "".join(f'<div class="kpi"><div class="kpi__label">{l}</div><div class="kpi__value {c}">{v}</div><div class="kpi__sub">{s}</div></div>' for l, v, s, c in items)
    return f'<section class="kpis" aria-label="Key metrics">{cells}</section>'


def price_panel(W=940):
    rows = [r for r in B["candles"] if r[0] >= "2026-03-23"]
    idx = {r[0]: i for i, r in enumerate(rows)}
    marks = {idx[t["session"]]: t["net"] for t in B["trades"] if t["session"] in idx}
    sel = idx["2026-09-08"]
    svg = candles_svg(rows, W, 262, markers=marks, sel=sel)
    # strategy P&L step line for the same window
    run = 0.0
    pts = [(0, 0.0)]
    n = len(rows)
    X = lambda i: (i + 0.5) * (W - 52) / n
    for t in B["trades"]:
        if t["session"] in idx:
            run += t["net"]
            pts.append((X(idx[t["session"]]), run))
    lo, hi = min(0, min(p[1] for p in pts)), max(p[1] for p in pts)
    Y = scale(lo, hi, 50, 4)
    step = []
    prev = Y(0)
    for x, v in pts:
        step += [(x, prev), (x, Y(v))]
        prev = Y(v)
    step.append((W - 52, prev))
    sub = (f'<svg viewBox="0 0 {W} 54" width="100%" height="54"><line x1="0" x2="{W-52}" y1="{Y(0):.1f}" y2="{Y(0):.1f}" stroke="#22272d"/>'
           + polyline(step, POS, 1.6) + f'<text x="{W-4}" y="{prev+3:.1f}" text-anchor="end" fill="{POS}" font-size="10" font-family="IBM Plex Mono">{inr(run, True)}</text></svg>')
    last = rows[-1]
    return f"""<section class="panel" style="padding:12px 16px 10px">
<div class="panel__head" style="margin-bottom:8px">
<div class="seg" role="tablist"><button class="seg__item" aria-selected="true">Price · candles</button><button class="seg__item" aria-selected="false">Equity · drawdown</button></div>
<span style="width:1px;height:18px;background:var(--line-strong);margin:0 6px"></span>
<span class="mono" style="font-size:12px;color:var(--text-2)">NIFTY 50</span>
<div class="seg seg--mono"><button class="seg__item">15m</button><button class="seg__item">1H</button><button class="seg__item" aria-selected="true">1D</button></div>
<button class="btn btn--sm" style="margin-left:4px">Indicators</button>
<div style="flex:1"></div>
<span class="mono" style="font-size:12px;color:var(--text-3)">08 Sep · O <b style="color:var(--text-1);font-weight:500">{last[1]:,}</b> H <b style="color:var(--text-1);font-weight:500">{last[2]:,}</b> L <b style="color:var(--text-1);font-weight:500">{last[3]:,}</b> C <b style="color:var(--neg-text);font-weight:500">{last[4]:,}</b></span>
<button class="btn btn--sm icon-btn" aria-label="Full screen">{icon('expand',14)}</button></div>
{svg}
<div class="mono" style="display:flex;gap:14px;font-size:11px;color:var(--text-faint);margin:4px 0 2px"><span>STRATEGY P&amp;L · SAME WINDOW</span>
<span style="display:flex;align-items:center;gap:5px"><span style="width:8px;height:8px;border-radius:50%;background:{POS}"></span>winning expiry</span>
<span style="display:flex;align-items:center;gap:5px"><span style="width:8px;height:8px;border-radius:50%;background:{NEG}"></span>losing expiry · click to inspect</span></div>
{sub}</section>"""


def edge_panel():
    pf_lo, pf_hi = ROB["pf_p05"], ROB["pf_p95"]
    # log-free linear scale 0..3 for the band
    Xs = scale(0, 3, 0, 290)
    return f"""<aside class="panel" style="display:flex;flex-direction:column;gap:14px">
<div><div class="eyebrow">Edge integrity</div><div class="faint" style="font-size:12px;margin-top:4px">Bootstrap of trade P&amp;L · 4,000 resamples · seed 7</div></div>
<div><div class="kv" style="padding:0"><span>P(net P&amp;L &gt; 0)</span><span class="pos">{ROB['p_net_positive']*100:.1f}%</span></div>
<div class="meter" style="margin-top:8px"><span style="width:{ROB['p_net_positive']*100:.1f}%"></span></div></div>
<div><div class="kv" style="padding:0"><span>Profit factor, 90% band</span><span>{pf_lo:.2f} – {pf_hi:.2f}</span></div>
<svg viewBox="0 0 290 26" width="100%" height="26" style="margin-top:4px"><line x1="0" x2="290" y1="13" y2="13" stroke="#1c2127" stroke-width="6" stroke-linecap="round"/>
<line x1="{Xs(pf_lo):.1f}" x2="{Xs(pf_hi):.1f}" y1="13" y2="13" stroke="#a7aeb5" stroke-width="6" stroke-linecap="round"/>
<line x1="{Xs(1):.1f}" x2="{Xs(1):.1f}" y1="2" y2="24" stroke="{NEG}" stroke-width="1.5"/><circle cx="{Xs(1.31):.1f}" cy="13" r="5" fill="#e6e8ea"/></svg>
<div style="display:flex;justify-content:space-between;font-size:11px" class="faint"><span>break-even 1.0 inside band</span><span class="mono">point 1.31</span></div></div>
<div style="border-top:1px solid var(--line);padding-top:10px">
<div class="kv"><span>Without best 5 trades</span><span class="neg">{inr(ROB['net_without_top5'], True)}</span></div>
<div class="kv"><span>Without best 10 trades</span><span class="neg">{inr(ROB['net_without_top10'], True)}</span></div>
<div class="kv"><span>Longest losing streak</span><span>{ROB['longest_losing_streak']} trades</span></div>
<div class="kv"><span>Fees ÷ gross profit</span><span class="accent">43.6%</span></div>
<div class="kv"><span>Worst day</span><span class="neg">{inr(-4282.4)}</span></div></div>
<div class="callout" style="margin-top:auto">Right-tail strategy: 35% hit rate, payoff 2.4×. Cutting costs by ₹50 per trade adds ₹7,850.</div></aside>"""


def hist_panel():
    vals = [t["net"] for t in B["trades"]]
    edges = list(range(-5000, 11001, 1000))
    counts = [0] * (len(edges) - 1)
    for v in vals:
        k = min(len(counts) - 1, max(0, int((v + 5000) // 1000)))
        counts[k] += 1
    mx = max(counts)
    bars = "".join(f'<div title="{edges[i]}…{edges[i+1]}: {c}" style="flex:1;height:{max(2 if c else 0, c / mx * 110):.0f}px;border-radius:2px 2px 0 0;background:{NEG if edges[i] < 0 else POS}"></div>' for i, c in enumerate(counts))
    return f"""<section class="panel"><div class="panel__head"><span class="eyebrow">Trade P&amp;L distribution</span>
<div class="seg seg--mono"><button class="seg__item" aria-selected="true">₹</button><button class="seg__item">R</button></div></div>
<div style="display:flex;align-items:flex-end;gap:3px;height:116px;border-bottom:1px solid var(--line-strong)">{bars}</div>
<div class="mono faint" style="display:flex;justify-content:space-between;font-size:10px;margin-top:6px"><span>−₹5k</span><span>0</span><span>+₹5k</span><span>+₹11k</span></div>
<div class="panel__foot">Median trade <span class="mono neg">{inr(sorted(vals)[len(vals)//2], True)}</span> · mean <span class="mono pos">{inr(sum(vals)/len(vals), True)}</span></div></section>"""


def monthly_panel():
    mon = B["monthly"]
    cells = ['<span></span>'] + [f'<span class="mono faint" style="text-align:center">{m}</span>' for m in "JFMAMJJASOND"]
    green = sum(1 for v in mon.values() if v > 0)
    for y in ["2023", "2024", "2025", "2026"]:
        cells.append(f'<span class="mono muted" style="align-self:center">{y}</span>')
        for m in range(1, 13):
            k = f"{y}-{m:02d}"
            v = mon.get(k)
            if v is None:
                cells.append('<div class="heat__cell heat__cell--empty"></div>')
            else:
                a = min(1, 0.15 + abs(v) / 8000)
                bg = f"rgba(61,220,151,{a:.2f})" if v >= 0 else f"rgba(229,72,77,{a:.2f})"
                cells.append(f'<div class="heat__cell" title="{k}: {inr(v, True)}" style="background:{bg}"></div>')
    return f"""<section class="panel"><div class="panel__head"><span class="eyebrow">Monthly P&amp;L</span><span class="faint" style="font-size:11px">{green} of {len(mon)} months green</span></div>
<div class="heat" style="grid-template-columns:38px repeat(12,minmax(0,1fr))">{''.join(cells)}</div>
<div class="panel__foot" style="display:flex;gap:10px;align-items:center"><span style="width:36px;height:8px;border-radius:2px;background:linear-gradient(90deg,{NEG},#111418,{POS})"></span>−₹8k … +₹8k per month</div></section>"""


def inspector_panel(sel_id=157, W=520):
    t = next(x for x in B["trades"] if x["id"] == sel_id)
    bars = B["intraday"][str(sel_id)]
    ce = next(l for l in t["legs"] if l[1] == "CE")
    pe = next(l for l in t["legs"] if l[1] == "PE")
    lo = min(pe[2], min(b[3] for b in bars)) - 15
    hi = max(ce[2], max(b[2] for b in bars)) + 15
    Y = scale(lo, hi, 156, 4)
    n = len(bars)
    step = 470 / n
    X = lambda i: step * i + step / 2
    s = [f'<svg viewBox="0 0 {W} 176" width="100%" height="176">']
    ei = next(i for i, b in enumerate(bars) if b[0] == t["entry"])
    xi = next(i for i, b in enumerate(bars) if b[0] == t["exit"])
    s.append(f'<rect x="{X(ei):.1f}" y="0" width="{X(xi)-X(ei):.1f}" height="160" fill="{ACC}" fill-opacity=".05"/>')
    for lab, strike, col in [("CE", ce[2], NEG_T), ("PE", pe[2], INFO)]:
        s.append(f'<line x1="0" x2="470" y1="{Y(strike):.1f}" y2="{Y(strike):.1f}" stroke="{col}" stroke-dasharray="4 3"/>'
                 f'<text x="{W-2}" y="{Y(strike)+3:.1f}" text-anchor="end" fill="{col}" font-size="10" font-family="IBM Plex Mono">{lab} {strike:,}</text>')
    for i, b in enumerate(bars):
        o, h, l, c = b[1:5]
        col = POS if c >= o else NEG
        top, bot = Y(max(o, c)), Y(min(o, c))
        s.append(f'<line x1="{X(i):.1f}" x2="{X(i):.1f}" y1="{Y(h):.1f}" y2="{Y(l):.1f}" stroke="{col}"/><rect x="{X(i)-5:.1f}" y="{top:.1f}" width="10" height="{max(1,bot-top):.1f}" fill="{col}"/>')
    for i, lab in [(ei, f"SELL {t['entry']}"), (xi, f"BUY {t['exit']}")]:
        s.append(f'<line x1="{X(i):.1f}" x2="{X(i):.1f}" y1="0" y2="160" stroke="{ACC}" stroke-width="1.2"/><text x="{X(i):.1f}" y="173" text-anchor="middle" fill="{ACC}" font-size="10" font-family="IBM Plex Mono">{lab}</text>')
    s.append("</svg>")
    tabs = []
    for x in B["trades"][-6:]:
        on = x["id"] == sel_id
        d = x["session"][8:10] + " " + ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][int(x["session"][5:7])]
        tabs.append(f'<button class="btn btn--sm mono" style="flex:1;height:40px;flex-direction:column;gap:0;justify-content:center;{"background:var(--bg-active);border-color:#3a424b" if on else "background:transparent;border-color:var(--line)"}">'
                    f'<span style="font-size:11px;color:var(--text-2)">{d}</span><span style="font-size:11px" class="{"pos" if x["net"]>=0 else "neg"}">{inr(x["net"], True)}</span></button>')
    return f"""<section class="panel" style="display:flex;flex-direction:column;gap:8px">
<div class="panel__head" style="margin:0"><span class="eyebrow">Trade inspector · #{sel_id} · 15m</span><a href="#" style="font-size:11px">Open in Trades →</a></div>
<div style="display:flex;gap:4px">{''.join(tabs)}</div>{''.join(s)}
<div class="mono" style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;font-size:11px;border-top:1px solid var(--line);padding-top:8px">
<div><div class="faint">SHORT CE</div><div style="margin-top:2px">{ce[2]:,} · {ce[3]}→{ce[4]}</div></div>
<div><div class="faint">SHORT PE</div><div style="margin-top:2px">{pe[2]:,} · {pe[3]}→{pe[4]}</div></div>
<div><div class="faint">FEES · SLIPPAGE</div><div style="margin-top:2px">₹{t['fees']:.0f} · —</div></div>
<div><div class="faint">NET</div><div class="pos" style="margin-top:2px">{inr(t['net'], True)} · +{t['r']:.2f}R</div></div></div></section>"""


def overview():
    body = HEADER + run_tabs("overview") + kpis() + f"""
<div class="grid" style="grid-template-columns:minmax(0,1fr) 330px">{price_panel()}{edge_panel()}</div>
<div class="grid" style="grid-template-columns:300px minmax(0,1fr) 560px">{hist_panel()}{monthly_panel()}{inspector_panel()}</div>"""
    return shell("Run · Overview", "run", CRUMBS, body, topbar_actions=TOP_ACTIONS)


def overview_equity():
    """Same page with the Equity · drawdown segment selected (second chart state)."""
    d = B["daily"]
    eq = [r[2] - CAP for r in d]
    dd = [r[3] * 100 for r in d]
    W = 940
    svg, X, Y = area_svg(eq, W, 230, POS, zero=0)
    top_ids = sorted(B["trades"], key=lambda t: -t["net"])[:5]
    sess = [r[0] for r in d]
    rings = "".join(f'<circle cx="{X(sess.index(t["session"])):.1f}" cy="{Y(eq[sess.index(t["session"])]):.1f}" r="5.5" fill="#0d1013" stroke="{ACC}" stroke-width="2"/>' for t in top_ids)
    svg = svg.replace("</svg>", rings + "</svg>")
    ddsvg, _, _ = area_svg(dd, W, 64, NEG, lo=min(dd), hi=0, invert=True, fill_opacity=0.28)
    panel = f"""<section class="panel" style="padding:12px 16px 10px"><div class="panel__head" style="margin-bottom:8px">
<div class="seg"><button class="seg__item" aria-selected="false">Price · candles</button><button class="seg__item" aria-selected="true">Equity · drawdown</button></div>
<div style="flex:1"></div><span style="display:flex;align-items:center;gap:6px;font-size:12px;color:var(--text-3)"><span style="width:9px;height:9px;border-radius:50%;border:2px solid {ACC}"></span>Top 5 trades</span>
<div class="seg seg--mono"><button class="seg__item">1Y</button><button class="seg__item" aria-selected="true">ALL</button></div></div>
<div class="mono faint" style="font-size:11px;margin-bottom:4px">EQUITY − CAPITAL (₹) · DAILY, EVERY SESSION</div>{svg}
<div class="mono faint" style="font-size:11px;margin:8px 0 4px">DRAWDOWN · max −9.5% · 347 sessions · Apr-2025 peak not yet reclaimed</div>{ddsvg}</section>"""
    body = HEADER + run_tabs("overview") + kpis() + f"""
<div class="grid" style="grid-template-columns:minmax(0,1fr) 330px">{panel}{edge_panel()}</div>"""
    return shell("Run · Overview (equity)", "run", CRUMBS, body, topbar_actions=TOP_ACTIONS)


def trades_tab():
    rows = []
    trades = list(reversed(B["trades"]))[:14]
    for i, t in enumerate(trades):
        exp = t["id"] == 156
        sel = ' aria-selected="true"' if exp else ""
        legs = " ".join(f'{"−" if l[0]=="-" else "+"}{l[1]} {l[2]:,}' for l in t["legs"])
        prem_in = sum(l[3] or 0 for l in t["legs"] if l[0] == "-")
        prem_out = sum(l[4] or 0 for l in t["legs"] if l[0] == "-")
        d = t["session"]
        rows.append(f"""<tr{sel}><td><button class="btn btn--ghost icon-btn" aria-label="Expand" style="height:24px;width:24px">{icon('chevdown' if exp else 'chev',14)}</button></td>
<td class="num" style="text-align:left">{t['id']}</td><td class="mono">{d}<span class="sub">{t['entry']} → {t['exit']} IST</span></td>
<td><span class="chip">Short strangle</span><span class="sub" style="margin-top:2px">{legs}</span></td>
<td class="num">{t['u_in']:,.1f}<span class="sub">→ {t['u_out']:,.1f}</span></td><td class="num">{prem_in:.1f}<span class="sub">→ {prem_out:.1f}</span></td>
<td class="num">{t['qty']:.0f}<span class="sub">1 lot</span></td><td class="num">{inr(t['gross'], True)}</td><td class="num muted">{inr(t['fees'])}</td><td class="num faint">—</td>
<td class="num {'pos' if t['net']>=0 else 'neg'}">{inr(t['net'], True)}</td><td class="num">{t['r']:+.2f}</td><td><span class="badge badge--muted">TIME_EXIT</span></td><td></td></tr>""")
        if exp:
            leg_rows = "".join(f'<tr><td>{l[1]}</td><td class="num">{l[2]:,}</td><td>{"SELL" if l[0]=="-" else "BUY"}</td><td class="num">{l[3]}</td><td class="num">{l[4]}</td><td class="num {"neg" if (l[4]-l[3])>0 else "pos"}">{inr(-(l[4]-l[3])*t["qty"], True)}</td></tr>' for l in t["legs"])
            rows.append(f"""<tr class="row-expanded"><td></td><td colspan="13"><div style="display:grid;grid-template-columns:420px minmax(0,1fr);gap:16px">
<div><div class="eyebrow" style="margin-bottom:6px">Legs</div><table class="table" style="font-size:12px"><thead><tr><th>Type</th><th class="num">Strike</th><th>Action</th><th class="num">Entry ₹</th><th class="num">Exit ₹</th><th class="num">Leg P&amp;L</th></tr></thead><tbody>{leg_rows}</tbody></table>
<div class="callout" style="margin-top:10px">Spot rallied to ~24,140 by 11:30, taking the 24,150 call from 17.1 to 34.1. The put decayed 8.9→4.2 and did not offset it.</div></div>
<div><div class="eyebrow" style="margin-bottom:6px">Session · 15m · entry/exit and strikes</div>{mini_session(156)}</div></div></td></tr>""")
    head = """<thead><tr><th style="width:36px"></th><th>#</th><th aria-sort="descending">Session</th><th>Structure · legs</th><th class="num">Underlying</th><th class="num">Premium</th><th class="num">Qty</th><th class="num">Gross</th><th class="num">Fees</th><th class="num">Slippage</th><th class="num">Net</th><th class="num">R</th><th>Exit</th><th>Flag</th></tr></thead>"""
    foot = f"""<tfoot><tr><td></td><td colspan="6">157 trades · 55 W / 102 L · filtered: all</td><td class="num pos">+₹53,787</td><td class="num">−₹23,456</td><td class="num">—</td><td class="num pos">+₹30,331</td><td class="num">{sum(x["r"] for x in B["trades"])/len(B["trades"]):+.2f}</td><td colspan="2" class="muted" style="font-family:var(--font-sans)">Gross − fees − slippage = net ✓</td></tr></tfoot>"""
    filters = f"""<section style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
<div class="seg"><button class="seg__item" aria-selected="true">All 157</button><button class="seg__item">Winners 55</button><button class="seg__item">Losers 102</button></div>
<select class="select" style="width:170px"><option>Exit reason: any</option></select><select class="select" style="width:170px"><option>Data flag: any</option></select>
<label class="field" style="flex-direction:row;align-items:center;gap:8px"><input class="input mono" style="width:120px" value="2023-09-14"><span>→</span><input class="input mono" style="width:120px" value="2026-09-08"></label>
<div style="flex:1"></div><span class="muted" style="font-size:12px">Times in IST · amounts in ₹ · premium per unit</span><button class="btn btn--sm">{icon('download',14)}CSV (v2 columns)</button></section>"""
    body = HEADER + run_tabs("trades") + filters + f'<div class="table-wrap"><table class="table">{head}<tbody>{"".join(rows)}</tbody>{foot}</table></div>'
    body += '<div style="display:flex;justify-content:space-between;align-items:center" class="muted"><span style="font-size:12px">Showing 1–14 of 157 · newest first</span><div style="display:flex;gap:6px"><button class="btn btn--sm" disabled>Prev</button><button class="btn btn--sm">Next</button></div></div>'
    return shell("Run · Trades", "run", CRUMBS, body, topbar_actions=TOP_ACTIONS)


def mini_session(tid, W=760, H=200):
    t = next(x for x in B["trades"] if x["id"] == tid)
    bars = B["intraday"][str(tid)]
    ce = next(l for l in t["legs"] if l[1] == "CE")
    pe = next(l for l in t["legs"] if l[1] == "PE")
    lo = min(pe[2], min(b[3] for b in bars)) - 15
    hi = max(ce[2], max(b[2] for b in bars)) + 15
    Y = scale(lo, hi, H - 20, 4)
    n = len(bars)
    step = (W - 70) / n
    X = lambda i: step * i + step / 2
    s = [f'<svg viewBox="0 0 {W} {H}" width="100%" height="{H}" style="background:#0d1013;border:1px solid var(--line);border-radius:8px">']
    for lab, strike, col in [("CE", ce[2], NEG_T), ("PE", pe[2], INFO)]:
        s.append(f'<line x1="0" x2="{W-70}" y1="{Y(strike):.1f}" y2="{Y(strike):.1f}" stroke="{col}" stroke-dasharray="4 3"/><text x="{W-6}" y="{Y(strike)+3:.1f}" text-anchor="end" fill="{col}" font-size="10" font-family="IBM Plex Mono">{lab} {strike:,}</text>')
    for i, b in enumerate(bars):
        o, h, l, c = b[1:5]
        col = POS if c >= o else NEG
        top, bot = Y(max(o, c)), Y(min(o, c))
        s.append(f'<line x1="{X(i):.1f}" x2="{X(i):.1f}" y1="{Y(h):.1f}" y2="{Y(l):.1f}" stroke="{col}"/><rect x="{X(i)-6:.1f}" y="{top:.1f}" width="12" height="{max(1,bot-top):.1f}" fill="{col}"/>')
        if i % 4 == 0:
            s.append(f'<text x="{X(i):.1f}" y="{H-5}" text-anchor="middle" fill="#6b737c" font-size="10" font-family="IBM Plex Mono">{b[0]}</text>')
    for i in (1, 22):
        s.append(f'<line x1="{X(i):.1f}" x2="{X(i):.1f}" y1="0" y2="{H-18}" stroke="{ACC}"/>')
    s.append("</svg>")
    return "".join(s)


S0 = DATA["s0"]


def diagnostics_tab():
    m = S0["metrics"]
    er = S0["exit_reasons"]
    total = sum(er.values())
    order = [("PORTFOLIO_TARGET", "TARGET", "#a7aeb5"), ("DAILY_STOP", "STOP", "#a7aeb5"), ("TIME_EXIT", "TIME_EXIT", "#a7aeb5"),
             ("MISSING_SPOT", "DATA · SPOT", ACC), ("MISSING_HELD_QUOTE", "DATA · QUOTE", ACC)]
    ex_rows = "".join(f'<div class="hbar" style="grid-template-columns:96px minmax(0,1fr) 64px"><span class="mono" style="color:var(--text-2);font-size:11px">{lab}</span><div class="hbar__track"><div class="hbar__fill" style="width:{er[k]/total*100:.1f}%;background:{col}"></div></div><span class="num">{er[k]} · {er[k]/total*100:.0f}%</span></div>' for k, lab, col in order)
    # net per exit reason
    net_by = {}
    for t in S0["trades"]:
        net_by[t["tag"]] = net_by.get(t["tag"], 0) + t["net"]
    reason_tbl = "".join(f'<tr><td class="mono" style="font-size:12px">{lab}</td><td class="num">{er[k]}</td><td class="num {"pos" if net_by[k]>=0 else "neg"}">{inr(net_by[k], True)}</td><td class="num">{inr(net_by[k]/er[k], True)}</td></tr>' for k, lab, _ in order)
    gross, fees, slip, net = S0["gross"], S0["fees"], S0["slip"], S0["net"]
    def wrow(label, start, width, color, value, bold=False):
        return (f'<div style="display:grid;grid-template-columns:78px minmax(0,1fr) 86px;gap:10px;align-items:center;height:30px;font-size:12px">'
                f'<span style="color:var(--text-2);{"font-weight:600;color:var(--text-1)" if bold else ""}">{label}</span>'
                f'<div style="position:relative;height:20px;background:var(--bg-raised);border-radius:3px"><div style="position:absolute;left:{start:.1f}%;width:{width:.1f}%;top:0;bottom:0;border-radius:3px;background:{color}"></div></div>'
                f'<span class="num" style="{"font-weight:600" if bold else ""}">{value}</span></div>')
    g = gross
    wf = (wrow("Gross P&amp;L", 0, 100, POS, inr(gross, True))
          + wrow("Fees", (gross - fees) / g * 100, fees / g * 100, NEG, '<span class="neg">' + inr(-fees) + '</span>')
          + wrow("Slippage", net / g * 100, slip / g * 100, ACC, '<span class="accent">' + inr(-slip) + '</span>')
          + wrow("Net P&amp;L", 0, net / g * 100, "#e6e8ea", inr(net, True), True))
    stab = f"""<div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px">
<div style="padding:12px;border-radius:8px;background:var(--bg-raised)"><div class="eyebrow">Early half · 79 trades</div><div class="mono pos" style="font-size:20px;margin-top:6px">{inr(m['early_net'], True)}</div><div class="muted" style="font-size:12px">hit {m['early_win_rate']*100:.1f}% · {S0['trades'][0]['session']} → {S0['trades'][78]['session']}</div></div>
<div style="padding:12px;border-radius:8px;background:var(--bg-raised)"><div class="eyebrow">Recent half · 78 trades</div><div class="mono pos" style="font-size:20px;margin-top:6px">{inr(m['recent_net'], True)}</div><div class="muted" style="font-size:12px">hit {m['recent_win_rate']*100:.1f}% · {S0['trades'][79]['session']} → {S0['trades'][-1]['session']}</div></div></div>
<div class="callout" style="margin-top:10px">Both halves are profitable with similar hit rates, so the edge is not concentrated in one period.</div>"""
    dq = f"""<div class="banner" style="margin-bottom:12px">{icon('warn',16)}<span><b>24 of 157 trades (15.3%)</b> exited because market data went missing. Their P&amp;L is known but was forced. Status: <b>DATA ISSUES</b>.</span></div>
<div class="kv kv--divided"><span>Eligible sessions</span><span>{m['eligible']}</span></div><div class="kv kv--divided"><span>Traded</span><span>{m['traded']}</span></div>
<div class="kv kv--divided"><span>Skipped</span><span>{m['skipped']}</span></div><div class="kv kv--divided"><span>Unresolved P&amp;L</span><span class="pos">{m['unresolved']}</span></div>
<div class="kv kv--divided"><span>Forced exit · MISSING_SPOT</span><span class="accent">19</span></div><div class="kv"><span>Forced exit · MISSING_HELD_QUOTE</span><span class="accent">5</span></div>"""
    extremes = f"""<div class="kv kv--divided"><span>Best expiry</span><span class="pos">{inr(m['best_expiry'], True)}</span></div>
<div class="kv kv--divided"><span>Worst expiry</span><span class="neg">{inr(m['worst_expiry'], True)}</span></div>
<div class="kv kv--divided"><span>Worst intraday MTM</span><span class="neg">{inr(m['worst_mtm'], True)}</span></div>
<div class="kv kv--divided"><span>Max stop overshoot</span><span class="accent">{inr(m['max_stop_overshoot'])}</span></div>
<div class="kv kv--divided"><span>Expected shortfall 95%</span><span class="neg">{inr(m['expected_shortfall_95'], True)}</span></div>
<div class="kv"><span>Intraday max drawdown</span><span class="neg">{pct(m['intraday_max_drawdown'])}</span></div>"""
    monthly = f"""<div class="kv kv--divided"><span>Profitable months</span><span>{m['profitable_months']} / {m['months']}</span></div>
<div class="kv kv--divided"><span>Mean month</span><span class="pos">+{m['mean_monthly_pct']:.2f}%</span></div><div class="kv"><span>Median month</span><span>{m['median_monthly_pct']:+.2f}%</span></div>"""
    val = f"""<div class="kv kv--divided"><span>Execution model</span><span style="font-family:var(--font-sans);text-align:right;max-width:340px">{esc(S0['params']['execution'])}</span></div>
<div class="kv kv--divided"><span>Window</span><span>{esc(S0['params']['window'])}</span></div>
<div class="kv kv--divided"><span>Metric basis</span><span><span class="badge badge--info">calendar_daily</span></span></div>
<div class="kv kv--divided"><span>Orders</span><span>{m['orders']}</span></div>
<div class="callout callout--warn" style="margin-top:10px"><b>Caveat from the run:</b> {esc(S0['params']['caveat'])}</div>"""
    hdr = run_header("SENSEX 0DTE STATIC — corrected timing", ["SENSEX", "Short strangle · 0 DTE", "Group: 3-year timing sweep · family STATIC", "157 trades", "13 Sep 2023 → 11 Sep 2026 · 741 sessions", "Capital ₹1,80,000"],
                     "", "EDGE · FRAGILE", "Profitable in both halves; 15% forced data exits",
                     '<span class="badge badge--warn">Data issues</span>').replace("nifty-0dte-strangle-benchmark", "validated-timing-3y-sensex-0dte-static")
    body = hdr + run_tabs("diagnostics") + f"""
<div class="grid" style="grid-template-columns:repeat(3,minmax(0,1fr))">
<section class="panel"><div class="panel__head"><span class="eyebrow">Data coverage</span></div>{dq}</section>
<section class="panel"><div class="panel__head"><span class="eyebrow">Exit reasons</span><span class="faint" style="font-size:11px">DATA · SPOT = MISSING_SPOT, DATA · QUOTE = MISSING_HELD_QUOTE</span></div>{ex_rows}
<table class="table table--dense" style="margin-top:10px"><thead><tr><th>Reason</th><th class="num">Trades</th><th class="num">Net</th><th class="num">Per trade</th></tr></thead><tbody>{reason_tbl}</tbody></table></section>
<section class="panel"><div class="panel__head"><span class="eyebrow">Where the money went</span></div>{wf}<div class="panel__foot">Costs take {((fees+slip)/gross)*100:.0f}% of gross. Slippage alone is {inr(slip)} (₹{slip/157:.0f} per trade). STOP exits lose more than TARGET exits earn back per trade. See the Exit reasons table.</div></section>
<section class="panel"><div class="panel__head"><span class="eyebrow">Stability · early vs recent</span></div>{stab}</section>
<section class="panel"><div class="panel__head"><span class="eyebrow">Tail risk &amp; extremes</span></div>{extremes}</section>
<section class="panel"><div class="panel__head"><span class="eyebrow">Monthly consistency</span></div>{monthly}
<div class="eyebrow" style="margin-top:14px;margin-bottom:6px">Signal funnel (S/R runs only)</div><div class="muted" style="font-size:12px">Not recorded for this run. Shown when <span class="mono">diagnostics.decision_counts</span> exists.</div></section>
</div>
<section class="panel"><div class="panel__head"><span class="eyebrow">Validation, execution &amp; configuration</span><button class="btn btn--sm">{icon('copy',14)}Copy manifest JSON</button></div>
<div class="grid" style="grid-template-columns:minmax(0,1.2fr) minmax(0,1fr)"><div>{val}</div>
<div class="code">instrument: SENSEX · BSE · short_strangle · dte [0]
group:      validated-timing-3y · family STATIC
capital:    ₹1,80,000
window:     2023-09-13 → 2026-09-11 (741 sessions)
cost_model: null   ← not recorded by generator
data_source: null  ← not recorded by generator
code_version: null</div></div></section>"""
    crumbs = '<span>Library</span><span class="sep">/</span><span>3-year timing sweep</span><span class="sep">/</span><b>validated-timing-3y-sensex-0dte-static</b>'
    return shell("Run · Diagnostics", "run", crumbs, body, topbar_actions=TOP_ACTIONS)


def fullscreen_chart():
    rows = [r for r in B["candles"] if r[0] >= "2025-09-01"]
    idx = {r[0]: i for i, r in enumerate(rows)}
    marks = {idx[t["session"]]: t["net"] for t in B["trades"] if t["session"] in idx}
    svg = candles_svg(rows, 1070, 820, markers=marks, sel=idx["2026-09-08"])
    SEL = ' aria-selected="true"'
    lst = "".join(f'<tr{SEL if t["id"]==157 else ""}><td class="mono">{t["session"][5:]}</td><td class="num {"pos" if t["net"]>=0 else "neg"}">{inr(t["net"], True)}</td><td class="num">{t["r"]:+.2f}</td></tr>' for t in list(reversed(B["trades"]))[:24])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Full-screen chart — Stolgo mockup</title>
<link rel="stylesheet" href="fonts/fonts.css"><link rel="stylesheet" href="../tokens.css"><link rel="stylesheet" href="../components.css"><style>body{{width:1440px;height:900px}}</style></head>
<body><div style="height:900px;display:flex;flex-direction:column;overflow:hidden">
<header class="topbar"><button class="btn btn--sm">← Back to run</button><span class="mono" style="font-size:13px">NIFTY 50 · nifty-0dte-strangle-benchmark</span>
<div class="seg seg--mono"><button class="seg__item">15m</button><button class="seg__item">1H</button><button class="seg__item" aria-selected="true">1D</button></div>
<button class="btn btn--sm">Indicators</button><button class="btn btn--sm">Go to date</button><div class="crumbs"></div>
<div class="seg seg--mono"><button class="seg__item">1M</button><button class="seg__item">3M</button><button class="seg__item" aria-selected="true">1Y</button><button class="seg__item">ALL</button></div></header>
<div style="flex:1;min-height:0;display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:0">
<div style="padding:12px 16px">{svg}</div>
<aside style="border-left:1px solid var(--line);background:var(--bg-panel);display:flex;flex-direction:column;min-height:0;overflow:hidden"><div style="padding:12px 16px" class="eyebrow">Trades in view · 53</div>
<div style="overflow:auto;flex:1"><table class="table"><thead><tr><th>Session</th><th class="num">Net</th><th class="num">R</th></tr></thead><tbody>{lst}</tbody></table></div></aside></div></div></body></html>"""
