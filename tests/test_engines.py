"""Unit test for Gwolf engines directly (no server needed)."""
import io
import sys
from pathlib import Path
from PIL import Image, ImageDraw
from docx import Document
import pypdf

# Add parent directory to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from gwolf.engines.pdf_compress import pypdf_compress
from gwolf.engines.pdf_render import render_pdf_pypdfium2
from gwolf.engines.docx_ops import word_to_pdf_docx_pillow, pdf_to_word_pypdf_docx
from gwolf.engines.img_ops import compress_img, convert_img, upscale_img, imgs_to_pdf

failures = []

def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name} {detail}")
    if not cond:
        failures.append(name)

def test_img_ops():
    im = Image.new("RGB", (200, 200), color="blue")
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    raw = buf.getvalue()
    
    # test convert
    jpg, _ = compress_img(raw, quality=80)
    check("img compress produces bytes", len(jpg) > 0)
    
    converted = convert_img(raw, "JPEG")
    check("img convert produces JPEG bytes", converted.startswith(b"\xff\xd8"))
    
    upscaled, _ = upscale_img(raw, scale=2)
    im_up = Image.open(io.BytesIO(upscaled))
    check("img upscale 2x width", im_up.size[0] == 400)
    
    pdf_data = imgs_to_pdf([("test.png", raw)])
    check("imgs_to_pdf valid PDF header", pdf_data is not None and pdf_data.startswith(b"%PDF"))

def test_docx_to_pdf_pillow():
    doc = Document()
    doc.add_heading("Judul Dokumen Uji", level=1)
    doc.add_paragraph("Paragraf pertama untuk pengujian engine.")
    tbl = doc.add_table(rows=2, cols=2)
    tbl.cell(0, 0).text = "A"
    tbl.cell(0, 1).text = "B"
    tbl.cell(1, 0).text = "C"
    tbl.cell(1, 1).text = "D"
    
    buf = io.BytesIO()
    doc.save(buf)
    docx_bytes = buf.getvalue()
    
    pdf_bytes = word_to_pdf_docx_pillow(docx_bytes)
    check("word_to_pdf_docx_pillow produces bytes", pdf_bytes is not None and len(pdf_bytes) > 0)
    if pdf_bytes:
        r = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        check("word_to_pdf_docx_pillow valid pages >= 1", len(r.pages) >= 1)

def test_pdf_to_word_pypdf_docx():
    # create sample PDF with text
    buf = io.BytesIO()
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=300, height=300)
    writer.add_blank_page(width=300, height=300)
    writer.write(buf)
    pdf_bytes = buf.getvalue()
    
    docx_bytes = pdf_to_word_pypdf_docx(pdf_bytes)
    check("pdf_to_word_pypdf_docx produces bytes", docx_bytes is not None and len(docx_bytes) > 0)
    if docx_bytes:
        doc = Document(io.BytesIO(docx_bytes))
        headings = [p.text for p in doc.paragraphs if p.text.startswith("Halaman")]
        check("pdf_to_word_pypdf_docx contains Halaman 1 & 2", "Halaman 1" in headings and "Halaman 2" in headings)

if __name__ == "__main__":
    print("=== RUNNING ENGINE UNIT TESTS ===")
    test_img_ops()
    test_docx_to_pdf_pillow()
    test_pdf_to_word_pypdf_docx()
    print(f"\nTOTAL FAILURES: {len(failures)}")
    if failures:
        sys.exit(1)
