"""Render every mockup to docs/design/png/<name>.png (1440px wide, full page).

    pip install playwright && playwright install chromium
    python docs/design/_build/render_png.py
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
MOCK, OUT = HERE.parent / "mockups", HERE.parent / "png"
OUT.mkdir(exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    for f in sorted(MOCK.glob("*.html")):
        pg.goto(f.as_uri())
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(150)
        pg.screenshot(path=str(OUT / (f.stem + ".png")), full_page=True)
        print("png", f.stem)
    b.close()
