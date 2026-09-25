#!/usr/bin/env python3
"""
Gwolf Toolbox - Local Web Utilities (PDF & Image Tools)
Running on Termux Android (Port 8083)
"""

import os
import io
import json
import uuid
import zipfile
import shutil
import subprocess
import tempfile
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from PIL import Image, ImageOps, ImageEnhance
import pypdf

PORT = 8083
BASE_DIR = Path.home() / "tools-web"
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = BASE_DIR / "tmp"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)


def _gs_compress(input_bytes):
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
        subprocess.run(cmd, timeout=30, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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


def _pypdf_compress(input_bytes):
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


class ToolboxHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[tools] {self.client_address[0]} {format % args}", flush=True)

    def send_json(self, data, code=200):
        b = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def send_file_download(self, data_bytes, filename, mime_type="application/octet-stream", original_size=None):
        if original_size is None:
            original_size = len(data_bytes)
        self.send_response(200)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(data_bytes)))
        self.send_header("X-Original-Size", str(int(original_size)))
        self.send_header("X-Result-Size", str(int(len(data_bytes))))
        self.end_headers()
        self.wfile.write(data_bytes)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            index_path = STATIC_DIR / "index.html"
            if index_path.exists():
                data = index_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(404)
                self.end_headers()
            return

        if path == "/api/status":
            self.send_json({"status": "online", "port": PORT, "features": ["pdf_merge", "pdf_compress", "img_to_pdf", "img_compress", "img_upscale", "img_convert"]})
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        ctype = self.headers.get("Content-Type", "")

        if not ctype.startswith("multipart/form-data"):
            self.send_json({"error": "Expected multipart/form-data"}, 400)
            return

        boundary = ctype.split("boundary=")[-1].encode("utf-8")
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length)

        parts = raw_body.split(b"--" + boundary)
        files = []
        form_data = {}

        for part in parts:
            if not part or part == b"--\r\n" or part == b"--":
                continue
            head_and_body = part.split(b"\r\n\r\n", 1)
            if len(head_and_body) != 2:
                continue
            header_raw, body_raw = head_and_body
            body_raw = body_raw.rstrip(b"\r\n")
            header_str = header_raw.decode("utf-8", errors="replace")

            if 'filename="' in header_str:
                fn = header_str.split('filename="')[1].split('"')[0]
                if fn:
                    files.append((fn, body_raw))
            elif 'name="' in header_str:
                field_name = header_str.split('name="')[1].split('"')[0]
                form_data[field_name] = body_raw.decode("utf-8", errors="replace")

        try:
            if path == "/api/pdf/merge":
                if not files:
                    self.send_json({"error": "No PDF files uploaded"}, 400); return
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
                self.send_file_download(out_bytes, "merged_document.pdf", "application/pdf", original_size=orig)
                return

            elif path == "/api/pdf/compress":
                if not files:
                    self.send_json({"error": "No PDF file uploaded"}, 400); return
                fn, b = files[0]
                orig_len = len(b)
                best = b
                gs_bytes = None
                try:
                    gs_bytes = _gs_compress(b)
                except Exception:
                    gs_bytes = None
                if gs_bytes and len(gs_bytes) < len(best):
                    best = gs_bytes
                pypdf_bytes = None
                try:
                    pypdf_bytes = _pypdf_compress(b)
                except Exception:
                    pypdf_bytes = None
                if pypdf_bytes and len(pypdf_bytes) < len(best):
                    best = pypdf_bytes
                if len(best) > orig_len:
                    best = b
                self.send_file_download(best, f"compressed_{fn}", "application/pdf", original_size=orig_len)
                return

            elif path == "/api/img/to-pdf":
                if not files:
                    self.send_json({"error": "No image files uploaded"}, 400); return
                pil_imgs = []
                for fn, b in files:
                    try:
                        im = Image.open(io.BytesIO(b))
                        try:
                            im = ImageOps.exif_transpose(im)
                        except Exception:
                            pass
                        if im.mode in ("RGBA", "P"):
                            im = im.convert("RGB")
                        pil_imgs.append(im)
                    except Exception:
                        pass
                if not pil_imgs:
                    self.send_json({"error": "Invalid image files"}, 400); return
                out_buf = io.BytesIO()
                pil_imgs[0].save(out_buf, "PDF", save_all=True, append_images=pil_imgs[1:], resolution=100.0)
                out_bytes = out_buf.getvalue()
                orig = sum(len(b) for _, b in files)
                self.send_file_download(out_bytes, "images_document.pdf", "application/pdf", original_size=orig)
                return

            elif path == "/api/img/compress":
                if not files:
                    self.send_json({"error": "No image uploaded"}, 400); return
                fn, b = files[0]
                orig_len = len(b)
                quality = int(form_data.get("quality", 70))
                quality = max(1, min(95, quality))
                im = Image.open(io.BytesIO(b))
                # capture fmt/icc BEFORE exif_transpose: transpose returns a new
                # image object whose .format is None (would fall back to JPEG)
                fmt = im.format if im.format in ("JPEG", "PNG", "WEBP") else "JPEG"
                icc = im.info.get("icc_profile")
                try:
                    im = ImageOps.exif_transpose(im)
                except Exception:
                    pass
                if fmt == "JPEG" and im.mode in ("RGBA", "P"):
                    im = im.convert("RGB")
                if fmt == "WEBP" and im.mode == "P":
                    try:
                        im = im.convert("RGBA")
                    except Exception:
                        im = im.convert("RGB")
                out_buf = io.BytesIO()
                try:
                    if fmt == "JPEG":
                        if icc:
                            im.save(out_buf, format="JPEG", quality=quality, optimize=True, progressive=True, icc_profile=icc)
                        else:
                            im.save(out_buf, format="JPEG", quality=quality, optimize=True, progressive=True)
                    elif fmt == "PNG":
                        tmp1 = io.BytesIO()
                        if icc:
                            im.save(tmp1, format="PNG", optimize=True, compress_level=9, icc_profile=icc)
                        else:
                            im.save(tmp1, format="PNG", optimize=True, compress_level=9)
                        best_bytes = tmp1.getvalue()
                        best_len = len(best_bytes)
                        try:
                            has_alpha = ("A" in im.getbands()) if hasattr(im, "getbands") else (im.mode == "RGBA")
                            if has_alpha:
                                rgba = im.convert("RGBA") if im.mode != "RGBA" else im
                                q_im = rgba.quantize(colors=256, method=Image.Quantize.FASTOCTREE)
                            else:
                                rgb = im.convert("RGB") if im.mode != "RGB" else im
                                q_im = rgb.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
                            if q_im is not None:
                                tmp2 = io.BytesIO()
                                q_im.save(tmp2, format="PNG", optimize=True, compress_level=9)
                                q_bytes = tmp2.getvalue()
                                if len(q_bytes) < best_len:
                                    best_bytes = q_bytes
                        except Exception:
                            pass
                        out_buf = io.BytesIO(best_bytes)
                    elif fmt == "WEBP":
                        if icc:
                            im.save(out_buf, format="WEBP", quality=quality, method=6, icc_profile=icc)
                        else:
                            im.save(out_buf, format="WEBP", quality=quality, method=6)
                    else:
                        im.save(out_buf, format=fmt, quality=quality, optimize=True)
                except Exception:
                    out_buf = io.BytesIO()
                    try:
                        im.save(out_buf, format=fmt, quality=quality, optimize=True)
                    except Exception:
                        out_buf = io.BytesIO(b)
                result = out_buf.getvalue()
                if not result or len(result) > orig_len:
                    result = b
                ext = "jpg" if fmt == "JPEG" else fmt.lower()
                mime = "image/jpeg" if fmt == "JPEG" else f"image/{ext}"
                if result is b:
                    orig_ext = Path(fn).suffix.lstrip(".").lower() or ext
                    if orig_ext in ("jpg", "jpeg"):
                        ext2 = "jpg"
                        mime = "image/jpeg"
                    else:
                        ext2 = orig_ext
                        mime = f"image/{ext2}" if ext2 in ("png", "webp") else f"image/{ext}"
                    self.send_file_download(result, f"compressed_{Path(fn).stem}.{ext2}", mime, original_size=orig_len)
                else:
                    self.send_file_download(result, f"compressed_{Path(fn).stem}.{ext}", mime, original_size=orig_len)
                return

            elif path == "/api/img/upscale":
                if not files:
                    self.send_json({"error": "No image uploaded"}, 400); return
                fn, b = files[0]
                orig_len = len(b)
                scale = int(form_data.get("scale", 2))
                if scale not in (2, 4): scale = 2
                im = Image.open(io.BytesIO(b))
                # capture fmt/icc BEFORE exif_transpose (new object loses .format)
                fmt = im.format if im.format in ("JPEG", "PNG", "WEBP") else "PNG"
                icc = im.info.get("icc_profile")
                try:
                    im = ImageOps.exif_transpose(im)
                except Exception:
                    pass
                new_w = im.width * scale
                new_h = im.height * scale
                upscaled = im.resize((new_w, new_h), Image.Resampling.LANCZOS)
                enhancer = ImageEnhance.Sharpness(upscaled)
                upscaled = enhancer.enhance(1.25)
                out_buf = io.BytesIO()
                if fmt == "JPEG" and upscaled.mode in ("RGBA", "P"):
                    upscaled = upscaled.convert("RGB")
                try:
                    if fmt == "JPEG":
                        if icc:
                            upscaled.save(out_buf, format="JPEG", quality=95, optimize=True, progressive=True, icc_profile=icc)
                        else:
                            upscaled.save(out_buf, format="JPEG", quality=95, optimize=True, progressive=True)
                    elif fmt == "PNG":
                        if icc:
                            upscaled.save(out_buf, format="PNG", optimize=True, compress_level=9, icc_profile=icc)
                        else:
                            upscaled.save(out_buf, format="PNG", optimize=True, compress_level=9)
                    elif fmt == "WEBP":
                        if icc:
                            upscaled.save(out_buf, format="WEBP", quality=95, method=6, icc_profile=icc)
                        else:
                            upscaled.save(out_buf, format="WEBP", quality=95, method=6)
                    else:
                        upscaled.save(out_buf, format=fmt, quality=95, optimize=True)
                except Exception:
                    upscaled.save(out_buf, format=fmt, quality=95)
                ext = "jpg" if fmt == "JPEG" else fmt.lower()
                self.send_file_download(out_buf.getvalue(), f"upscaled_{scale}x_{Path(fn).stem}.{ext}", f"image/{ext}", original_size=orig_len)
                return

            elif path == "/api/img/convert":
                if not files:
                    self.send_json({"error": "No image uploaded"}, 400); return
                fn, b = files[0]
                orig_len = len(b)
                target_fmt = form_data.get("format", "PNG").upper()
                if target_fmt not in ("PNG", "JPEG", "JPG", "WEBP"):
                    target_fmt = "PNG"
                if target_fmt == "JPG":
                    target_fmt = "JPEG"
                im = Image.open(io.BytesIO(b))
                try:
                    im = ImageOps.exif_transpose(im)
                except Exception:
                    pass
                icc = im.info.get("icc_profile")
                out_buf = io.BytesIO()
                if target_fmt == "JPEG" and im.mode in ("RGBA", "P"):
                    im = im.convert("RGB")
                try:
                    if target_fmt == "JPEG":
                        if icc:
                            im.save(out_buf, format="JPEG", quality=90, optimize=True, progressive=True, icc_profile=icc)
                        else:
                            im.save(out_buf, format="JPEG", quality=90, optimize=True, progressive=True)
                    elif target_fmt == "PNG":
                        if icc:
                            im.save(out_buf, format="PNG", optimize=True, compress_level=9, icc_profile=icc)
                        else:
                            im.save(out_buf, format="PNG", optimize=True, compress_level=9)
                    elif target_fmt == "WEBP":
                        if icc:
                            im.save(out_buf, format="WEBP", quality=90, method=6, icc_profile=icc)
                        else:
                            im.save(out_buf, format="WEBP", quality=90, method=6)
                    else:
                        im.save(out_buf, format=target_fmt, quality=90)
                except Exception:
                    im.save(out_buf, format=target_fmt, quality=90)
                ext = "jpg" if target_fmt == "JPEG" else target_fmt.lower()
                self.send_file_download(out_buf.getvalue(), f"converted_{Path(fn).stem}.{ext}", f"image/{ext}", original_size=orig_len)
                return

            self.send_json({"error": "Unknown action"}, 404)
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

if __name__ == "__main__":
    print(f"Gwolf Toolbox listening on http://127.0.0.1:{PORT}")
    server = ThreadingHTTPServer(("127.0.0.1", PORT), ToolboxHandler)
    server.serve_forever()
