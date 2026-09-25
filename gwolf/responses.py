import json

def send_json(handler, data, code=200):
    b = json.dumps(data).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(b)))
    handler.end_headers()
    handler.wfile.write(b)

def send_file_download(handler, data_bytes, filename, mime_type="application/octet-stream", original_size=None, page_count=None):
    if original_size is None:
        original_size = len(data_bytes)
    handler.send_response(200)
    handler.send_header("Content-Type", mime_type)
    handler.send_header("Content-Disposition", f'attachment; filename="{filename}"')
    handler.send_header("Content-Length", str(len(data_bytes)))
    handler.send_header("X-Original-Size", str(int(original_size)))
    handler.send_header("X-Result-Size", str(int(len(data_bytes))))
    if page_count is not None:
        handler.send_header("X-Page-Count", str(int(page_count)))
    handler.end_headers()
    handler.wfile.write(data_bytes)
