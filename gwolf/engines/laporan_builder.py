"""Laporan Basis Data builder — template-clone A, stdlib+python-docx only."""
import io
import copy
from pathlib import Path

import docx
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

TEMPLATE = Path.home() / "tools-web/templates/basis-data-2026.docx"
MAX_MODULES = 12
MAX_BLOCKS_PER = 10
MAX_SCRIPT_LEN = 20000


def _set_cell_shading(cell, color_hex="F2F2F2"):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), color_hex)
    shd.set(qn("w:val"), "clear")
    tcPr.append(shd)


def _set_cell_monospace(cell, fontsize=9):
    for p in cell.paragraphs:
        for r in p.runs:
            r.font.name = "Consolas"
            r.font.size = Pt(fontsize)
            # keep line breaks as-is


def _add_script_table(doc, text):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.style = "Table Grid"
    cell = tbl.cell(0, 0)
    cell.text = text[:MAX_SCRIPT_LEN]
    _set_cell_shading(cell, "F2F2F2")
    _set_cell_monospace(cell, 9)
    # compact spacing
    for p in cell.paragraphs:
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.space_before = Pt(2)
    return tbl


def _add_image_table(doc, img_bytes):
    # validate via Pillow, resize max 6in keep ratio
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(img_bytes))
        im.verify()  # check valid
        im = Image.open(io.BytesIO(img_bytes))  # reopen after verify
        # resize if wider than 6in at 150dpi ~900px
        max_w = 900
        if im.width > max_w:
            ratio = max_w / im.width
            nw = max_w
            nh = int(im.height * ratio)
            im = im.resize((nw, nh), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            fmt = "PNG" if im.mode in ("RGBA", "P") else "JPEG"
            if fmt == "JPEG" and im.mode in ("RGBA", "P"):
                im = im.convert("RGB")
            im.save(buf, format=fmt)
            img_bytes = buf.getvalue()
    except Exception:
        pass  # keep original, add anyway; docx may reject — caller handles
    tbl = doc.add_table(rows=1, cols=1)
    tbl.style = "Table Grid"
    cell = tbl.cell(0, 0)
    cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    try:
        cell.paragraphs[0].add_run().add_picture(io.BytesIO(img_bytes), width=Inches(6))
    except Exception as e:
        # fallback: text note instead of image
        cell.text = f"[gambar gagal dimuat: {e}]"
    return tbl


def _add_caption(doc, text, style="Caption"):
    try:
        p = doc.add_paragraph(style=style)
    except Exception:
        p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text)
    r.italic = True
    r.font.size = Pt(9)
    r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
    return p


def build(cover, modules):
    """cover=dict(nama,nim,kelas,prodi,tahun,judul) modules=list of {title, blocks:[{type,text}|{type,file}]}}.

    blocks: type="script" (text), type="screenshot" (file=bytes) — also accepts image_bytes/file_bytes aliases.
    Returns docx bytes. Raises ValueError on validation.
    """
    if not (1 <= len(modules) <= MAX_MODULES):
        raise ValueError(f"modul harus 1-{MAX_MODULES}")
    # normalize cover
    cover = {k: str(v or "").strip() for k, v in (cover or {}).items()}
    # validate modules
    for m in modules:
        if not isinstance(m, dict):
            raise ValueError("tiap modul harus object {title, blocks}")
        blks = m.get("blocks") or []
        if not (1 <= len(blks) <= MAX_BLOCKS_PER):
            raise ValueError(f"blok per modul 1-{MAX_BLOCKS_PER}")
        for b in blks:
            t = b.get("type")
            if t not in ("script", "screenshot"):
                raise ValueError("block type harus script|screenshot")
            if t == "script" and not str(b.get("text") or "").strip():
                raise ValueError("script kosong")

    # load template without CRC patch needed (clean copy)
    doc = docx.Document(str(TEMPLATE))

    # 1) patch cover paras 06-10 if cover provided
    # map: 06 Kelas, 07 Nama+NIM, 08 Prodi, 10 Tahun. 00 judul optional.
    try:
        if cover.get("kelas"):
            doc.paragraphs[6].text = f"Kelas : {cover['kelas']}"
        if cover.get("nama") or cover.get("nim"):
            nm = cover.get("nama", "")
            nim = cover.get("nim", "")
            doc.paragraphs[7].text = f"{nm}\t{nim}".strip()
        if cover.get("prodi"):
            doc.paragraphs[8].text = cover["prodi"]
        if cover.get("tahun"):
            doc.paragraphs[10].text = cover["tahun"]
        if cover.get("judul"):
            doc.paragraphs[0].text = cover["judul"]
    except Exception:
        pass

    # 2) strip old modul content (keep cover+TOC, drop from first Heading1 onward)
    # body children: find first Heading 1 index in paragraphs, then remove everything from there to sectPr
    first_h1 = None
    for i, p in enumerate(doc.paragraphs):
        try:
            if p.style.name == "Heading 1":
                first_h1 = i
                break
        except Exception:
            continue
    if first_h1 is not None:
        # remove via body iter: keep children up to before first H1 heading para
        body = doc.element.body
        # map para elements to indices
        para_elems = {p._element: idx for idx, p in enumerate(doc.paragraphs)}
        # find body child that is first_h1 para
        target = doc.paragraphs[first_h1]._element
        # collect children to remove: from target onward, keep last sectPr
        to_remove = []
        hit = False
        for ch in list(body.iterchildren()):
            if ch is target:
                hit = True
            if hit:
                # keep sectPr
                if ch.tag.endswith("sectPr"):
                    continue
                to_remove.append(ch)
        for ch in to_remove:
            body.remove(ch)
        # also remove orphan tables that were interleaved (they are body children too)
        # above already removed them because we removed from target onward.

    # 3) append modules flex
    for mi, m in enumerate(modules, start=1):
        title = str(m.get("title") or f"Modul {mi:02d}").strip() or f"Modul {mi:02d}"
        # Heading 1
        try:
            h = doc.add_heading(title, level=1)
        except Exception:
            h = doc.add_paragraph(title)
            try:
                h.style = doc.styles["Heading 1"]
            except Exception:
                pass
        # optional spacing para
        for b in (m.get("blocks") or []):
            t = b.get("type")
            if t == "script":
                txt = str(b.get("text") or b.get("script") or "")
                cap = b.get("caption") or f"Script: {title}"
                _add_caption(doc, cap)
                _add_script_table(doc, txt)
            elif t == "screenshot":
                img = b.get("file") or b.get("file_bytes") or b.get("image_bytes") or b.get("bytes") or b.get("data")
                if img is None:
                    # allow text path? skip
                    continue
                if isinstance(img, str):
                    img = img.encode()
                # PIL validation already in helper; still guard size
                if len(img) > 10 * 1024 * 1024:
                    raise ValueError("screenshot >10MB")
                try:
                    # quick magic check
                    from PIL import Image as _I
                    _I.open(io.BytesIO(img)).verify()
                except Exception:
                    raise ValueError("screenshot bukan gambar valid (png/jpg/webp)")
                cap = b.get("caption") or f"Screenshot: {title}"
                _add_caption(doc, cap)
                _add_image_table(doc, img)
                _add_caption(doc, f"Gambar {mi} — {title}", style="Caption")

    out = io.BytesIO()
    doc.save(out)
    data = out.getvalue()
    if len(data) > 15 * 1024 * 1024:
        raise ValueError("output docx >15MB")
    return data
