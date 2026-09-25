"""Contract check for Gwolf Toolbox: package structure, endpoints, headers, and UI contract."""
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "static" / "index.html"
README = ROOT / "README.md"
REQ_CORE = ROOT / "requirements.txt"
REQ_OPT = ROOT / "requirements-optional.txt"
REQ_TEST = ROOT / "requirements-test.txt"

failures = []

def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name} {detail}")
    if not cond:
        failures.append(name)

def test_files_exist():
    check("index.html exists", HTML.exists())
    check("README.md exists", README.exists())
    check("requirements.txt exists", REQ_CORE.exists())
    check("requirements-optional.txt exists", REQ_OPT.exists())
    check("requirements-test.txt exists", REQ_TEST.exists())
    check("gwolf package exists", (ROOT / "gwolf" / "__init__.py").exists())
    check("gwolf.config exists", (ROOT / "gwolf" / "config.py").exists())
    check("gwolf.handlers exists", (ROOT / "gwolf" / "handlers" / "__init__.py").exists())
    check("gwolf.engines exists", (ROOT / "gwolf" / "engines" / "__init__.py").exists())

def test_no_emoji():
    emoji_pattern = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F]")
    for p in ROOT.rglob("*.py"):
        if ".git" in p.parts or "__pycache__" in p.parts:
            continue
        txt = p.read_text(encoding="utf-8")
        hits = set(c for c in txt if emoji_pattern.match(c))
        check(f"no emoji in {p.name}", not hits, f"hits: {hits}" if hits else "")
    if README.exists():
        txt = README.read_text(encoding="utf-8")
        hits = set(c for c in txt if emoji_pattern.match(c))
        check("no emoji in README.md", not hits, f"hits: {hits}" if hits else "")

def test_endpoints_and_ui():
    if not HTML.exists():
        return
    html = HTML.read_text(encoding="utf-8")
    
    eps = [
        "/api/pdf/merge",
        "/api/pdf/compress",
        "/api/img/to-pdf",
        "/api/img/compress",
        "/api/img/upscale",
        "/api/img/convert",
        "/api/pdf/to-img",
        "/api/word/to-pdf",
        "/api/pdf/to-word",
        "/api/status",
    ]
    for ep in eps:
        check(f"endpoint {ep} in index.html", ep in html)
        
    for h in ["X-Original-Size", "X-Result-Size", "X-Page-Count"]:
        check(f"header {h} handled in html", h in html)
        
    for key in [
        "merge", "pdf-compress", "img-to-pdf", "img-compress",
        "img-upscale", "img-convert", "pdf-to-img", "word-to-pdf", "pdf-to-word"
    ]:
        check(f"openTool('{key}') in html", f"openTool('{key}')" in html)

if __name__ == "__main__":
    print("=== RUNNING CONTRACT TESTS ===")
    test_files_exist()
    test_no_emoji()
    test_endpoints_and_ui()
    print(f"\nTOTAL FAILURES: {len(failures)}")
    if failures:
        exit(1)
