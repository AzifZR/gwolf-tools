import io
from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance

def convert_img(b, target_fmt):
    im = Image.open(io.BytesIO(b))
    icc = im.info.get("icc_profile")
    try:
        im = ImageOps.exif_transpose(im)
    except Exception:
        pass
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
    return out_buf.getvalue()

def upscale_img(b, scale):
    im = Image.open(io.BytesIO(b))
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
    return out_buf.getvalue(), fmt

def compress_img(b, quality):
    orig_len = len(b)
    im = Image.open(io.BytesIO(b))
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
    return result, fmt

def imgs_to_pdf(files):
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
        return None
    out_buf = io.BytesIO()
    pil_imgs[0].save(out_buf, "PDF", save_all=True, append_images=pil_imgs[1:], resolution=100.0)
    return out_buf.getvalue()
