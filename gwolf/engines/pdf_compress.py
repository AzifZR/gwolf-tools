import os
import io
import shutil
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageOps
import pypdf

from gwolf.config import TIMEOUT_GS

def gs_compress(input_bytes):
    gs = shutil.which("gs")
    if not gs:
        for cand in ("gswin64c", "gswin32c", "gsc"):
            gs = shutil.which(cand)
            if gs:
                break
    if not gs:
        return None
    tmp_in = tmp_out = None
    try:
        fd_in, p_in = tempfile.mkstemp(suffix=".pdf")
        os.close(fd_in)
        fd_out, p_out = tempfile.mkstemp(suffix=".pdf")
        os.close(fd_out)
        tmp_in, tmp_out = p_in, p_out
        Path(p_in).write_bytes(input_bytes)
        cmd = [gs, "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4", "-dPDFSETTINGS=/ebook", "-dNOPAUSE", "-dQUIET", "-dBATCH", f"-sOutputFile={p_out}", p_in]
        subprocess.run(cmd, timeout=TIMEOUT_GS, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not os.path.exists(p_out):
            return None
        out = Path(p_out).read_bytes()
        if not out or len(out) >= len(input_bytes):
            return None
        try:
            r = pypdf.PdfReader(io.BytesIO(out))
            if len(r.pages) == 0:
                return None
        except Exception:
            return None
        return out
    except Exception:
        return None
    finally:
        for p in (tmp_in, tmp_out):
            if p:
                try:
                    os.remove(p)
                except Exception:
                    pass

def pypdf_compress(input_bytes):
    try:
        reader = pypdf.PdfReader(io.BytesIO(input_bytes))
        writer = pypdf.PdfWriter()
        for page in reader.pages:
            try:
                page.compress_content_streams(level=9)
            except TypeError:
                try:
                    page.compress_content_streams()
                except Exception:
                    pass
            except Exception:
                pass
            try:
                writer.add_page(page)
            except Exception:
                continue
        # strip document info and XMP metadata
        try:
            if hasattr(writer, "_root_object") and writer._root_object is not None:
                if "/Metadata" in writer._root_object:
                    del writer._root_object["/Metadata"]
        except Exception:
            pass
        # re-encode embedded raster images
        for page in writer.pages:
            try:
                images = list(page.images)
            except Exception:
                continue
            for img_file in images:
                try:
                    orig_data = img_file.data
                    orig_len = len(orig_data) if orig_data else 0
                    pil = img_file.image
                    if pil is None:
                        continue
                    try:
                        pil = ImageOps.exif_transpose(pil)
                    except Exception:
                        pass
                    w, h = pil.size
                    longest = max(w, h)
                    if longest > 2500:
                        ratio = 2500.0 / longest
                        nw, nh = max(1, int(w * ratio)), max(1, int(h * ratio))
                        pil = pil.resize((nw, nh), Image.Resampling.LANCZOS)
                    has_alpha = ("A" in pil.getbands()) if hasattr(pil, "getbands") else (pil.mode in ("RGBA", "LA", "PA"))
                    buf = io.BytesIO()
                    if has_alpha:
                        if pil.mode not in ("RGBA", "LA"):
                            pil = pil.convert("RGBA")
                        pil.save(buf, format="PNG", optimize=True, compress_level=9)
                    else:
                        if pil.mode not in ("RGB", "L"):
                            pil = pil.convert("RGB")
                        pil.save(buf, format="JPEG", quality=75, optimize=True, progressive=True)
                    new_bytes = buf.getvalue()
                    if orig_len and len(new_bytes) >= orig_len:
                        continue
                    if has_alpha:
                        img_file.replace(pil, optimize=True, compress_level=9)
                    else:
                        img_file.replace(pil, quality=75, optimize=True, progressive=True)
                except Exception:
                    continue
        out_buf = io.BytesIO()
        writer.write(out_buf)
        out = out_buf.getvalue()
        if not out:
            return None
        try:
            r = pypdf.PdfReader(io.BytesIO(out))
            if len(r.pages) == 0:
                return None
        except Exception:
            return None
        return out
    except Exception:
        return None
