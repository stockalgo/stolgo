# Stolgo "Cockpit" design

A dark, dense research-terminal look: IBM Plex Sans/Mono, one amber accent, and green/red only for P&L.
Every screen **states a conclusion** (verdict, data-quality banner, knob effects) instead of only listing numbers.

```
design/
  tokens.css          ← SOURCE OF TRUTH: colours, type, spacing, radii, layout sizes
  components.css      ← SOURCE OF TRUTH: class names used by the mockups and the app
  png/                ← 1440 px screenshots (the visual contract)
  mockups/            ← static HTML for each screen (open it in a browser, inspect it with devtools)
    fonts/            ← offline IBM Plex subset used by the mockups only
  _build/             ← generator: real run data → mockups → PNGs
```

| # | Screen | PNG |
|---|---|---|
| 01 | Library: filters, return-vs-drawdown scatter, comparable leaders, runs table | `png/01-library.png` |
| 02 | Run · Overview: KPIs, candles with trade markers, P&L sub-pane, edge integrity, distribution, monthly heatmap, trade inspector | `png/02-run-overview.png` |
| 03 | Run · Overview with the Equity · drawdown segment | `png/03-run-overview-equity.png` |
| 04 | Run · Trades: v2 columns, expanded legs + session chart, reconciling footer | `png/04-run-trades.png` |
| 05 | Run · Diagnostics: data coverage, exit reasons, cost waterfall, stability, extremes, validation/config | `png/05-run-diagnostics.png` |
| 06 | Full-screen chart | `png/06-run-chart-fullscreen.png` |
| 07 | Compare: aligned equity/drawdown, comparability-aware table | `png/07-compare.png` |
| 08 | Group heatmap (3-year timing sweep): family × market/DTE, knob effects, variants | `png/08-group-heatmap.png` |
| 09 | New run: honest CLI command builder | `png/09-new-run.png` |
| 10 | Components & states: tokens, buttons, badges, verdicts, KPIs, empty/error/loading states | `png/10-components-states.png` |

All numbers in the mockups come from the real `runs/` folder, **recomputed on the corrected basis of Plan 01**
(e.g. benchmark Sharpe 0.73, not 1.66).

## Regenerate

```bash
python docs/design/_build/build_mockups.py      # HTML from _build/data/*.json
pip install playwright && playwright install chromium
python docs/design/_build/render_png.py         # PNGs
```

`_build/data/` is a snapshot taken on 2026-09-28. After Plan 01's migration you can regenerate it from `/api/*`,
but that is not required.

## Rules of the look

- Surfaces: `--bg-app` < `--bg-panel` < `--bg-raised` < `--bg-active`. Panels have a 1 px `--line` border, 10 px radius and no shadows.
- Numbers use **mono with tabular figures**. Labels use sans. Eyebrows use mono, 11 px, uppercase, +0.08em tracking, `--text-muted`.
- Colour carries meaning only: green = gain / OK, red = loss, amber = accent, warning or selection, blue = information and PE strike.
  Sample size is shown by **hollow vs filled** marks and by row dimming, never by colour alone.
- One primary (amber) button per screen at most.
- Unknown values are an em dash `—`, never `0`.
