from pathlib import Path
from gwolf.config import DEFAULT_QUALITY, DEFAULT_SCALE
from gwolf.responses import send_json, send_file_download
from gwolf.engines.img_ops import compress_img, convert_img, upscale_img, imgs_to_pdf

def handle_img_to_pdf(handler, files, form_data):
    if not files:
        send_json(handler, {"error": "No image files uploaded"}, 400); return True
    try:
        out_bytes = imgs_to_pdf(files)
        if not out_bytes:
            send_json(handler, {"error": "Invalid image files"}, 400); return True
        orig = sum(len(b) for _, b in files)
        send_file_download(handler, out_bytes, "images_document.pdf", "application/pdf", original_size=orig)
    except Exception as e:
        send_json(handler, {"error": str(e)}, 500)
    return True

def handle_img_compress(handler, files, form_data):
    if not files:
        send_json(handler, {"error": "No image uploaded"}, 400); return True
    try:
        fn, b = files[0]
        orig_len = len(b)
        quality = int(form_data.get("quality", DEFAULT_QUALITY))
        quality = max(1, min(95, quality))
        
        result, fmt = compress_img(b, quality)
        
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
            send_file_download(handler, result, f"compressed_{Path(fn).stem}.{ext2}", mime, original_size=orig_len)
        else:
            send_file_download(handler, result, f"compressed_{Path(fn).stem}.{ext}", mime, original_size=orig_len)
    except Exception as e:
        send_json(handler, {"error": str(e)}, 500)
    return True

def handle_img_upscale(handler, files, form_data):
    if not files:
        send_json(handler, {"error": "No image uploaded"}, 400); return True
    try:
        fn, b = files[0]
        orig_len = len(b)
        scale = int(form_data.get("scale", DEFAULT_SCALE))
        if scale not in (2, 4): scale = DEFAULT_SCALE
        
        result, fmt = upscale_img(b, scale)
        ext = "jpg" if fmt == "JPEG" else fmt.lower()
        send_file_download(handler, result, f"upscaled_{scale}x_{Path(fn).stem}.{ext}", f"image/{ext}", original_size=orig_len)
    except Exception as e:
        send_json(handler, {"error": str(e)}, 500)
    return True

def handle_img_convert(handler, files, form_data):
    if not files:
        send_json(handler, {"error": "No image uploaded"}, 400); return True
    try:
        fn, b = files[0]
        orig_len = len(b)
        target_fmt = form_data.get("format", "PNG").upper()
        if target_fmt not in ("PNG", "JPEG", "JPG", "WEBP"):
            target_fmt = "PNG"
        if target_fmt == "JPG":
            target_fmt = "JPEG"
            
        result = convert_img(b, target_fmt)
        ext = "jpg" if target_fmt == "JPEG" else target_fmt.lower()
        send_file_download(handler, result, f"converted_{Path(fn).stem}.{ext}", f"image/{ext}", original_size=orig_len)
    except Exception as e:
        send_json(handler, {"error": str(e)}, 500)
    return True
