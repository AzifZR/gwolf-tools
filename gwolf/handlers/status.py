from gwolf.config import STATIC_DIR, PORT
from gwolf.responses import send_json

def handle_get(handler, path):
    if path == "/" or path == "/index.html":
        index_path = STATIC_DIR / "index.html"
        if index_path.exists():
            data = index_path.read_bytes()
            handler.send_response(200)
            handler.send_header("Content-Type", "text/html; charset=utf-8")
            handler.send_header("Content-Length", str(len(data)))
            handler.end_headers()
            handler.wfile.write(data)
        else:
            handler.send_response(404)
            handler.end_headers()
        return True

    if path == "/api/status":
        send_json(handler, {"status": "online", "port": PORT, "features": ["pdf_merge", "pdf_compress", "img_to_pdf", "img_compress", "img_upscale", "img_convert", "pdf_to_img", "word_to_pdf", "pdf_to_word"]})
        return True

    return False
