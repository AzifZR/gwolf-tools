import os
import io
import shutil
import subprocess
import tempfile
from pathlib import Path
from PIL import Image

from gwolf.config import TIMEOUT_GS_RENDER

def render_pdf_pypdfium2(pdf_bytes, dpi, fmt):
    try:
        import pypdfium2
    except Exception:
        return None
    try:
        pdf = pypdfium2.PdfDocument(pdf_bytes)
    except Exception:
        return None
    try:
        n = len(pdf)
        if n == 0:
            return None
        scale = dpi / 72.0
        out = []
        for i in range(n):
            try:
                page = pdf[i]
                pil = page.render(scale=scale).to_pil()
                buf = io.BytesIO()
                if fmt == "JPEG":
                    if pil.mode in ("RGBA", "LA", "P", "PA"):
                        pil = pil.convert("RGB")
                    elif pil.mode != "RGB":
                        try:
                            pil = pil.convert("RGB")
                        except Exception:
                            pil = pil.convert("RGB")
                    pil.save(buf, format="JPEG", quality=85, optimize=True, progressive=True)
                else:
                    pil.save(buf, format="PNG", optimize=True, compress_level=9)
                data = buf.getvalue()
                if not data:
                    return None
                out.append(data)
            except Exception:
                return None
        if not out:
            return None
        return out
    except Exception:
        return None
    finally:
        try:
            pdf.close()
        except Exception:
            pass

def render_pdf_gs(pdf_bytes, dpi, fmt):
    gs = shutil.which("gs")
    if not gs:
        for cand in ("gswin64c", "gswin32c", "gsc"):
            gs = shutil.which(cand)
            if gs:
                break
    if not gs:
        return None
    tmpdir = None
    tmp_in = None
    try:
        tmpdir = tempfile.mkdtemp()
        fd, tmp_in = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        Path(tmp_in).write_bytes(pdf_bytes)
        ext = "png" if fmt == "PNG" else "jpg"
        device = "png16m" if fmt == "PNG" else "jpeg"
        pattern = os.path.join(tmpdir, f"page%d.{ext}")
        if fmt == "PNG":
            cmd = [gs, "-dNOPAUSE", "-dBATCH", f"-sDEVICE={device}", f"-r{dpi}", f"-o{pattern}", tmp_in]
        else:
            cmd = [gs, "-dNOPAUSE", "-dBATCH", f"-sDEVICE={device}", "-dJPEGQ=85", f"-r{dpi}", f"-o{pattern}", tmp_in]
        subprocess.run(cmd, timeout=TIMEOUT_GS_RENDER, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        files = []
        for p in Path(tmpdir).glob(f"page*.{ext}"):
            name = p.name
            try:
                num = name[len("page"):-len("."+ext)]
                files.append((int(num), p))
            except Exception:
                continue
        if not files:
            return None
        files.sort(key=lambda x: x[0])
        out = []
        for _, p in files:
            try:
                data = p.read_bytes()
                if not data:
                    return None
                out.append(data)
            except Exception:
                return None
        if not out:
            return None
        return out
    except Exception:
        return None
    finally:
        if tmp_in:
            try:
                os.remove(tmp_in)
            except Exception:
                pass
        if tmpdir:
            try:
                shutil.rmtree(tmpdir)
            except Exception:
                pass
