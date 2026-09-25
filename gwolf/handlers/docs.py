import io
import zipfile
from pathlib import Path
from gwolf.responses import send_json, send_file_download
from gwolf.engines.docx_ops import (
    word_to_pdf_soffice,
    word_to_pdf_docx_pillow,
    pdf_to_word_pdf2docx,
    pdf_to_word_pypdf_docx,
)

def handle_word_to_pdf(handler, files, form_data):
    if not files:
        send_json(handler, {"error": "No file uploaded"}, 400); return True
    try:
        fn, b = files[0]
        orig_len = len(b)
        stem = Path(fn).stem or "document"
        pdf_bytes = word_to_pdf_soffice(b, fn)
        if not pdf_bytes:
            is_legacy = fn.lower().endswith(".doc") or b[:4] == b'\xd0\xcf\x11\xe0'
            if is_legacy and not zipfile.is_zipfile(io.BytesIO(b)):
                send_json(handler, {"error": ".doc butuh LibreOffice (pkg install libreoffice)"}, 400); return True
            pdf_bytes = word_to_pdf_docx_pillow(b)
            if not pdf_bytes:
                send_json(handler, {"error": "Konversi Word tidak tersedia. Install: pip install python-docx (atau libreoffice buat hasil penuh)"}, 500); return True
        send_file_download(handler, pdf_bytes, f"converted_{stem}.pdf", "application/pdf", original_size=orig_len)
    except Exception as e:
        send_json(handler, {"error": str(e)}, 500)
    return True

def handle_pdf_to_word(handler, files, form_data):
    if not files:
        send_json(handler, {"error": "No file uploaded"}, 400); return True
    try:
        fn, b = files[0]
        orig_len = len(b)
        stem = Path(fn).stem or "document"
        docx_bytes = pdf_to_word_pdf2docx(b)
        if not docx_bytes:
            docx_bytes = pdf_to_word_pypdf_docx(b)
            if not docx_bytes:
                send_json(handler, {"error": "Konversi PDF ke Word tidak tersedia. Install: pip install pdf2docx / python-docx"}, 500); return True
        send_file_download(handler, docx_bytes, f"converted_{stem}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", original_size=orig_len)
    except Exception as e:
        send_json(handler, {"error": str(e)}, 500)
    return True
