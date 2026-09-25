#!/usr/bin/env python3
"""Gwolf Toolbox - Local Web Utilities (PDF & Image Tools)"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from gwolf.config import PORT
from gwolf.responses import send_json as _send_json, send_file_download as _send_file
from gwolf.multipart import parse_multipart
from gwolf.handlers import POST_ROUTES, handle_get

class ToolboxHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[tools] {self.client_address[0]} {format % args}", flush=True)
    def send_json(self, data, code=200):
        return _send_json(self, data, code)
    def send_file_download(self, data_bytes, filename, mime_type="application/octet-stream", original_size=None, page_count=None):
        return _send_file(self, data_bytes, filename, mime_type, original_size, page_count)
    def do_GET(self):
        path = urlparse(self.path).path
        if handle_get(self, path):
            return
        self.send_response(404); self.end_headers()
    def do_POST(self):
        path = urlparse(self.path).path
        files, form_data, err = parse_multipart(self)
        if err:
            self.send_json({"error": err}, 400); return
        h = POST_ROUTES.get(path)
        if h:
            try:
                h(self, files, form_data)
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
            return
        self.send_json({"error": "Unknown action"}, 404)

if __name__ == "__main__":
    print(f"Gwolf Toolbox listening on http://127.0.0.1:{PORT}")
    server = ThreadingHTTPServer(("127.0.0.1", PORT), ToolboxHandler)
    server.serve_forever()
