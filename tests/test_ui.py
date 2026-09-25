"""Playwright verification for UI."""
import sys
from pathlib import Path

# Add note about playwright in case it's not installed
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Please install playwright: pip install playwright && playwright install chromium")
    sys.exit(1)

HTML = Path(__file__).resolve().parent.parent / "static" / "index.html"
failures = []

def check(name, cond, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {detail}")
    if not cond:
        failures.append(name)

def no_hscroll(page):
    return page.evaluate(
        "() => ({sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth})")

with sync_playwright() as p:
    browser = p.chromium.launch()
    
    # overflow: phone + desktop
    for w, h in [(360, 740), (1440, 900)]:
        pg = browser.new_page(viewport={"width": w, "height": h})
        pg.goto(HTML.as_uri())
        r = no_hscroll(pg)
        check(f"[{w}px] page no h-scroll", r["sw"] <= r["cw"], str(r))
        pg.close()

    pg = browser.new_page(viewport={"width": 390, "height": 844})
    pg.goto(HTML.as_uri())

    cards = pg.evaluate(
        """() => [...document.querySelectorAll('#toolsGrid .card')].map(c => ({
            onclick: c.getAttribute('onclick'), tabindex: c.getAttribute('tabindex'),
            role: c.getAttribute('role'), cursor: getComputedStyle(c).cursor,
            hint: !!c.querySelector('.card-hint')}))"""
    )
    check("9 cards", len(cards) == 9, f"n={len(cards)}")
    if len(cards) == 9:
        check("all cards onclick", all(c["onclick"] and "openTool(" in c["onclick"] for c in cards))
        check("all cards tabindex=0", all(c["tabindex"] == "0" for c in cards))
        check("all cards role=button", all(c["role"] == "button" for c in cards))
    
    badges = pg.evaluate(
        """() => [...document.querySelectorAll('#tabBar button')].map(b => b.innerText.replace(/\\s+/g, ' '))""")
    check("badges contain 9", any("9" in b for b in badges), str(badges))
    
    pg.close()
    browser.close()

if failures:
    sys.exit(1)
