"""Generate docs/design/mockups/*.html from the data snapshot in _build/data.

    python docs/design/_build/build_mockups.py      # writes HTML
    node docs/design/_build/render_png.mjs          # writes docs/design/png/*.png (needs playwright)
"""
from pathlib import Path
import page_run as R
import page_other as O

OUT = Path(__file__).resolve().parent.parent / "mockups"
PAGES = {
    "01-library.html": O.library,
    "02-run-overview.html": R.overview,
    "03-run-overview-equity.html": R.overview_equity,
    "04-run-trades.html": R.trades_tab,
    "05-run-diagnostics.html": R.diagnostics_tab,
    "06-run-chart-fullscreen.html": R.fullscreen_chart,
    "07-compare.html": O.compare,
    "08-group-heatmap.html": O.groups,
    "09-new-run.html": O.new_run,
    "10-components-states.html": O.components,
}
if __name__ == "__main__":
    for name, fn in PAGES.items():
        (OUT / name).write_text(fn(), encoding="utf-8")
        print("wrote", name)
