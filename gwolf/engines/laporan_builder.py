"""Laporan Basis Data builder — template-clone A, stdlib+python-docx only."""
import io
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


def _set_run_text(p_elem, text, keep_two_runs=False):
    """Replace all <w:t> in <w:p> with text. keep_two_runs: 'Modul ' + label split biar style angka tetap."""
    ts = [t for t in p_elem.iter() if t.tag.endswith("}t")]
    if not ts:
        return
    if keep_two_runs and len(ts) >= 2 and text.startswith("Modul "):
        ts[0].text = "Modul "
        ts[1].text = text[len("Modul "):]
        for t in ts[2:]:
            t.text = ""
    else:
        ts[0].text = text
        ts[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        for t in ts[1:]:
            t.text = ""


def _set_cover_modul(doc, modul_label, matkul="Basis Data"):
    """Set shape cover: 'Laporan Praktikum <matkul>' + 'Modul <label>'.

    Shape = wp:anchor roundRect wps:txbx (primary) + v:roundrect fallback.
    modul_label: "5", "05", "VI", "1-3". Return True kalau kepasang.
    """
    label = str(modul_label or "").strip()
    matkul = str(matkul or "Basis Data").strip() or "Basis Data"
    if not label:
        return False
    title_txt = "Laporan Praktikum " + matkul  # shape punya judul sendiri, bukan cover['judul']
    changed = 0
    # Primary: SEMUA w:txbxContent — wps modern (wp:anchor) + vml fallback (v:roundrect).
    # Syarat: content punya >=2 <w:p> DAN p1 mengandung run "Modul" (biar TOC field "03 Modul 01" gak kena).
    try:
        for content in doc.element.iter():
            if not content.tag.endswith("}txbxContent"):
                continue
            ps = [c for c in content if c.tag.endswith("}p")]
            if len(ps) < 2:
                continue
            p1txt = "".join(t.text or "" for t in ps[1].iter() if t.tag.endswith("}t"))
            if "Modul" not in p1txt:
                continue
            _set_run_text(ps[0], title_txt)
            _set_run_text(ps[1], "Modul " + label, keep_two_runs=True)
            changed += 1
    except Exception:
        pass
    return changed > 0


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


def _add_script_table(doc, text):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.style = "Table Grid"
    cell = tbl.cell(0, 0)
    cell.text = text[:MAX_SCRIPT_LEN]
    _set_cell_shading(cell, "F2F2F2")
    _set_cell_monospace(cell, 9)
    for p in cell.paragraphs:
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.space_before = Pt(2)
    return tbl


def _add_image_table(doc, img_bytes):
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(img_bytes))
        im.verify()
        im = Image.open(io.BytesIO(img_bytes))
        max_w = 900
        if im.width > max_w:
            ratio = max_w / im.width
            im = im.resize((max_w, int(im.height * ratio)), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            fmt = "PNG" if im.mode in ("RGBA", "P") else "JPEG"
            if fmt == "JPEG" and im.mode in ("RGBA", "P"):
                im = im.convert("RGB")
            im.save(buf, format=fmt)
            img_bytes = buf.getvalue()
    except Exception:
        pass
    tbl = doc.add_table(rows=1, cols=1)
    tbl.style = "Table Grid"
    cell = tbl.cell(0, 0)
    cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    try:
        cell.paragraphs[0].add_run().add_picture(io.BytesIO(img_bytes), width=Inches(6))
    except Exception as e:
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
    """cover=dict(nama,nim,kelas,prodi,tahun,judul,modul,matkul) modules=list of {title, modul, blocks}.

    - cover['modul'] = label cover ("5","06","1-3") → shape cover "Modul <label>".
      Kosong → pakai modul pertama ("1-N" kalau >1 modul).
    - cover['matkul'] → judul shape "Laporan Praktikum <matkul>" (default "Basis Data").
      cover['judul'] TIDAK dipakai buat shape (legacy para 00, aman diabaikan).
    - Per modul: title default "Modul <label>" atau "Modul <ii:02d>".
      blocks: type="script" (text), type="screenshot" (file=bytes, alias image_bytes/file_bytes).
      caption OTOMATIS: "Script Modul: <label> <title>" / "Screenshot Modul: <label> <title>"
      + "Gambar <global-n> — <title>". Manual caption = override aja.
    Returns docx bytes. Raises ValueError on validation.
    """
    if not (1 <= len(modules) <= MAX_MODULES):
        raise ValueError(f"modul harus 1-{MAX_MODULES}")
    cover = {k: str(v or "").strip() for k, v in (cover or {}).items()}
    # normalisasi: tiap modul dapat label
    labels = []
    for i, m in enumerate(modules, start=1):
        if not isinstance(m, dict):
            raise ValueError("tiap modul harus object {title, blocks}")
        lbl = str(m.get("modul") or m.get("label") or "").strip()
        if not lbl:
            lbl = f"{i:02d}"
        labels.append(lbl)
        blks = m.get("blocks") or []
        if not (1 <= len(blks) <= MAX_BLOCKS_PER):
            raise ValueError(f"blok per modul 1-{MAX_BLOCKS_PER}")
        for b in blks:
            t = b.get("type")
            if t not in ("script", "screenshot"):
                raise ValueError("block type harus script|screenshot")
            if t == "script" and not str(b.get("text") or "").strip():
                raise ValueError("script kosong")

    doc = docx.Document(str(TEMPLATE))

    # 1) cover shape: modul label + matkul
    cover_modul = cover.get("modul") or (labels[0] if len(labels) == 1 else f"1-{len(labels)}")
    matkul = cover.get("matkul") or "Basis Data"
    _set_cover_modul(doc, cover_modul, matkul)

    # 1b) cover identitas paras 06-10 (06 Kelas, 07 Nama+NIM, 08 Prodi, 10 Tahun)
    try:
        if cover.get("kelas"):
            doc.paragraphs[6].text = f"Kelas : {cover['kelas']}"
        if cover.get("nama") or cover.get("nim"):
            doc.paragraphs[7].text = f"{cover.get('nama','')}\t{cover.get('nim','')}".strip()
        if cover.get("prodi"):
            doc.paragraphs[8].text = cover["prodi"]
        if cover.get("tahun"):
            doc.paragraphs[10].text = cover["tahun"]
    except Exception:
        pass

    # 2) strip isi modul lama (keep cover+TOC, drop dari Heading 1 pertama s/d sectPr)
    first_h1 = None
    for i, p in enumerate(doc.paragraphs):
        try:
            if p.style.name == "Heading 1":
                first_h1 = i
                break
        except Exception:
            continue
    if first_h1 is not None:
        body = doc.element.body
        target = doc.paragraphs[first_h1]._element
        to_remove, hit = [], False
        for ch in list(body.iterchildren()):
            if ch is target:
                hit = True
            if hit and not ch.tag.endswith("sectPr"):
                to_remove.append(ch)
        for ch in to_remove:
            body.remove(ch)

    # 3) append modules — caption OTOMATIS dari label, gak perlu ngetik
    gambar_no = 0
    for mi, (m, lbl) in enumerate(zip(modules, labels), start=1):
        title = str(m.get("title") or f"Modul {lbl}").strip() or f"Modul {lbl}"
        try:
            doc.add_heading(title, level=1)
        except Exception:
            h = doc.add_paragraph(title)
            try:
                h.style = doc.styles["Heading 1"]
            except Exception:
                pass
        for b in (m.get("blocks") or []):
            t = b.get("type")
            if t == "script":
                txt = str(b.get("text") or b.get("script") or "")
                _add_caption(doc, b.get("caption") or f"Script Modul: {lbl} {title}")
                _add_script_table(doc, txt)
            elif t == "screenshot":
                img = b.get("file") or b.get("file_bytes") or b.get("image_bytes") or b.get("bytes") or b.get("data")
                if img is None:
                    continue
                if isinstance(img, str):
                    img = img.encode()
                if len(img) > 10 * 1024 * 1024:
                    raise ValueError("screenshot >10MB")
                try:
                    from PIL import Image as _I
                    _I.open(io.BytesIO(img)).verify()
                except Exception:
                    raise ValueError("screenshot bukan gambar valid (png/jpg/webp)")
                _add_caption(doc, b.get("caption") or f"Screenshot Modul: {lbl} {title}")
                _add_image_table(doc, img)
                gambar_no += 1
                _add_caption(doc, f"Gambar {gambar_no} — {title}")

    out = io.BytesIO()
    doc.save(out)
    data = out.getvalue()
    if len(data) > 15 * 1024 * 1024:
        raise ValueError("output docx >15MB")
    return data
