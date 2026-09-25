def parse_multipart(handler):
    ctype = handler.headers.get("Content-Type", "")
    if not ctype.startswith("multipart/form-data"):
        return None, None, "Expected multipart/form-data"

    boundary = ctype.split("boundary=")[-1].encode("utf-8")
    content_length = int(handler.headers.get("Content-Length", 0))
    raw_body = handler.rfile.read(content_length)

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
        # strip exactly ONE trailing CRLF (the part delimiter) — rstrip would
        # eat real file bytes when uploads legitimately end in CR/LF
        # (e.g. PDFs ending in %%EOF newline -> corrupt X-Original-Size)
        if body_raw.endswith(b"\r\n"):
            body_raw = body_raw[:-2]
        elif body_raw.endswith(b"\n") or body_raw.endswith(b"\r"):
            body_raw = body_raw[:-1]
        header_str = header_raw.decode("utf-8", errors="replace")

        if 'filename="' in header_str:
            fn = header_str.split('filename="')[1].split('"')[0]
            if fn:
                files.append((fn, body_raw))
        elif 'name="' in header_str:
            field_name = header_str.split('name="')[1].split('"')[0]
            form_data[field_name] = body_raw.decode("utf-8", errors="replace")

    return files, form_data, None
