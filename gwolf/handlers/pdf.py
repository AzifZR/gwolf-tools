import io
import zipfile
from pathlib import Path
import pypdf
from PIL import Image
from gwolf.config import ALLOWED_DPI, DEFAULT_DPI
from gwolf.responses import send_json, send_file_download
from gwolf.engines.pdf_compress import gs_compress, pypdf_compress
from gwolf.engines.pdf_render import render_pdf_pypdfium2, render_pdf_gs
import shutil

def handle_pdf_merge(handler, files, form_data):
    if not files:
        send_json(handler, {"error": "No PDF files uploaded"}, 400); return True
    try:
        merger_cls = getattr(pypdf, "PdfMerger", None)
        if merger_cls is not None:
            merger = merger_cls()
            for fn, b in files:
                merger.append(io.BytesIO(b))
            out_buf = io.BytesIO()
            merger.write(out_buf)
            merger.close()
        else:
            writer = pypdf.PdfWriter()
            for fn, b in files:
                writer.append(io.BytesIO(b))
            out_buf = io.BytesIO()
            writer.write(out_buf)
            writer.close()
        out_bytes = out_buf.getvalue()
        orig = sum(len(b) for _, b in files)
        send_file_download(handler, out_bytes, "merged_document.pdf", "application/pdf", original_size=orig)
    except Exception as e:
        send_json(handler, {"error": str(e)}, 500)
    return True

def handle_pdf_compress(handler, files, form_data):
    if not files:
        send_json(handler, {"error": "No PDF file uploaded"}, 400); return True
    try:
        fn, b = files[0]
        orig_len = len(b)
        best = b
        gs_bytes = gs_compress(b)
        if gs_bytes and len(gs_bytes) < len(best):
            best = gs_bytes
        pypdf_bytes = pypdf_compress(b)
        if pypdf_bytes and len(pypdf_bytes) < len(best):
            best = pypdf_bytes
        if len(best) > orig_len:
            best = b
        send_file_download(handler, best, f"compressed_{fn}", "application/pdf", original_size=orig_len)
    except Exception as e:
        send_json(handler, {"error": str(e)}, 500)
    return True

def handle_pdf_to_img(handler, files, form_data):
    if not files:
        send_json(handler, {"error": "No PDF file uploaded"}, 400); return True
    try:
        fn, b = files[0]
        orig_len = len(b)
        fmt = form_data.get("format", "PNG").upper().strip()
        if fmt == "JPG":
            fmt = "JPEG"
        if fmt not in ("PNG", "JPEG"):
            fmt = "PNG"
        try:
            dpi = int(form_data.get("dpi", str(DEFAULT_DPI)))
        except Exception:
            dpi = DEFAULT_DPI
        if dpi not in ALLOWED_DPI:
            dpi = DEFAULT_DPI
        stem = Path(fn).stem if Path(fn).stem else "document"
        
        try:
            pypdf.PdfReader(io.BytesIO(b))
        except Exception:
            pass
            
        images = render_pdf_pypdfium2(b, dpi, fmt)
        if not images:
            images = render_pdf_gs(b, dpi, fmt)
            
        if not images or len(images) == 0 or any(not x for x in images):
            has_pdfium = False
            try:
                import pypdfium2
                has_pdfium = True
            except Exception:
                has_pdfium = False
            has_gs = shutil.which("gs") is not None
            if not has_gs:
                for cand in ("gswin64c", "gswin32c", "gsc"):
                    if shutil.which(cand):
                        has_gs = True
                        break
            if not has_pdfium and not has_gs:
                send_json(handler, {"error": "Render engine tidak tersedia. Install: pip install pypdfium2 (atau pkg install ghostscript di Termux)"}, 500); return True
            send_json(handler, {"error": "Failed to render PDF"}, 500); return True
            
        page_count = len(images)
        try:
            for data in images:
                im = Image.open(io.BytesIO(data))
                im.verify()
        except Exception:
            send_json(handler, {"error": "Failed to render PDF"}, 500); return True
            
        ext = "png" if fmt == "PNG" else "jpg"
        if page_count == 1:
            data = images[0]
            mime = "image/png" if fmt == "PNG" else "image/jpeg"
            filename = f"{stem}_page1.{ext}"
            send_file_download(handler, data, filename, mime, original_size=orig_len, page_count=page_count)
        else:
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for idx, data in enumerate(images, start=1):
                    arcname = f"{stem}_page{idx}.{ext}"
                    zf.writestr(arcname, data)
            zip_bytes = zip_buf.getvalue()
            filename = f"fotopdf_{stem}.zip"
            send_file_download(handler, zip_bytes, filename, "application/zip", original_size=orig_len, page_count=page_count)
    except Exception as e:
        send_json(handler, {"error": str(e)}, 500)
    return True
