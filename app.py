#!/usr/bin/env python3
"""
Gwolf Toolbox — Local Web Utilities (PDF & Image Tools)
Running on Termux Android (Port 8083)
"""

import os
import io
import json
import uuid
import zipfile
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

class ToolboxHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[tools] {self.client_address[0]} {fmt % args}", flush=True)

    def send_json(self, data, code=200):
        b = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def send_file_download(self, data_bytes, filename, mime_type="application/octet-stream"):
        self.send_response(200)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(data_bytes)))
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

        # Multipart form-data parser simple
        if not ctype.startswith("multipart/form-data"):
            self.send_json({"error": "Expected multipart/form-data"}, 400)
            return

        boundary = ctype.split("boundary=")[-1].encode("utf-8")
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length)

        # Parse multipart body
        parts = raw_body.split(b"--" + boundary)
        files = [] # list of (filename, file_bytes)
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
            # 1. PDF MERGE
            if path == "/api/pdf/merge":
                if not files:
                    self.send_json({"error": "No PDF files uploaded"}, 400); return
                merger = pypdf.PdfMerger()
                for fn, b in files:
                    merger.append(io.BytesIO(b))
                out_buf = io.BytesIO()
                merger.write(out_buf)
                merger.close()
                self.send_file_download(out_buf.getvalue(), "merged_document.pdf", "application/pdf")
                return

            # 2. PDF COMPRESS
            elif path == "/api/pdf/compress":
                if not files:
                    self.send_json({"error": "No PDF file uploaded"}, 400); return
                fn, b = files[0]
                reader = pypdf.PdfReader(io.BytesIO(b))
                writer = pypdf.PdfWriter()
                for page in reader.pages:
                    page.compress_content_streams()
                    writer.add_page(page)
                out_buf = io.BytesIO()
                writer.write(out_buf)
                out_bytes = out_buf.getvalue()
                self.send_file_download(out_bytes, f"compressed_{fn}", "application/pdf")
                return

            # 3. IMAGES TO PDF
            elif path == "/api/img/to-pdf":
                if not files:
                    self.send_json({"error": "No image files uploaded"}, 400); return
                pil_imgs = []
                for fn, b in files:
                    try:
                        im = Image.open(io.BytesIO(b))
                        if im.mode in ("RGBA", "P"):
                            im = im.convert("RGB")
                        pil_imgs.append(im)
                    except: pass
                if not pil_imgs:
                    self.send_json({"error": "Invalid image files"}, 400); return
                out_buf = io.BytesIO()
                pil_imgs[0].save(out_buf, "PDF", save_all=True, append_images=pil_imgs[1:], resolution=100.0)
                self.send_file_download(out_buf.getvalue(), "images_document.pdf", "application/pdf")
                return

            # 4. IMAGE COMPRESS (JPG/PNG/WEBP)
            elif path == "/api/img/compress":
                if not files:
                    self.send_json({"error": "No image uploaded"}, 400); return
                fn, b = files[0]
                quality = int(form_data.get("quality", 70))
                im = Image.open(io.BytesIO(b))
                out_buf = io.BytesIO()
                fmt = im.format if im.format in ("JPEG", "PNG", "WEBP") else "JPEG"
                if fmt == "JPEG" and im.mode in ("RGBA", "P"):
                    im = im.convert("RGB")
                im.save(out_buf, format=fmt, optimize=True, quality=quality)
                ext = "jpg" if fmt == "JPEG" else fmt.lower()
                self.send_file_download(out_buf.getvalue(), f"compressed_{Path(fn).stem}.{ext}", f"image/{ext}")
                return

            # 5. IMAGE UPSCALE (2x / 4x Super Resolution Interpolation)
            elif path == "/api/img/upscale":
                if not files:
                    self.send_json({"error": "No image uploaded"}, 400); return
                fn, b = files[0]
                scale = int(form_data.get("scale", 2)) # 2 or 4
                if scale not in (2, 4): scale = 2
                im = Image.open(io.BytesIO(b))
                new_w = im.width * scale
                new_h = im.height * scale
                # High-fidelity Lanczos resampling + sharpness touchup
                upscaled = im.resize((new_w, new_h), Image.Resampling.LANCZOS)
                # Unsharp enhancement
                enhancer = ImageEnhance.Sharpness(upscaled)
                upscaled = enhancer.enhance(1.25)
                out_buf = io.BytesIO()
                fmt = im.format if im.format in ("JPEG", "PNG", "WEBP") else "PNG"
                if fmt == "JPEG" and upscaled.mode in ("RGBA", "P"):
                    upscaled = upscaled.convert("RGB")
                upscaled.save(out_buf, format=fmt, quality=95, optimize=True)
                ext = "jpg" if fmt == "JPEG" else fmt.lower()
                self.send_file_download(out_buf.getvalue(), f"upscaled_{scale}x_{Path(fn).stem}.{ext}", f"image/{ext}")
                return

            # 6. IMAGE CONVERT
            elif path == "/api/img/convert":
                if not files:
                    self.send_json({"error": "No image uploaded"}, 400); return
                fn, b = files[0]
                target_fmt = form_data.get("format", "PNG").upper() # PNG, JPEG, WEBP
                im = Image.open(io.BytesIO(b))
                out_buf = io.BytesIO()
                if target_fmt == "JPEG" and im.mode in ("RGBA", "P"):
                    im = im.convert("RGB")
                im.save(out_buf, format=target_fmt, quality=90)
                ext = "jpg" if target_fmt == "JPEG" else target_fmt.lower()
                self.send_file_download(out_buf.getvalue(), f"converted_{Path(fn).stem}.{ext}", f"image/{ext}")
                return

            self.send_json({"error": "Unknown action"}, 404)
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

if __name__ == "__main__":
    print(f"Gwolf Toolbox listening on http://127.0.0.1:{PORT}")
    server = ThreadingHTTPServer(("127.0.0.1", PORT), ToolboxHandler)
    server.serve_forever()
