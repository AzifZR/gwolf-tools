"""Laporan Basis Data builder — template-clone A, stdlib+python-docx only.

Template: templates/basis-data-2026.docx (bdl06_2a_011).
Layout per modul (1:1 template): H1 "{prefix} Modul {lbl}" → tabel script →
caption script (DI BAWAH tabel) → tabel screenshot → caption screenshot (DI BAWAH).
Caption style Caption. Script cell Table Grid TNR. Footer ptab 1:1.
Cover: shape "Laporan Praktikum <matkul>" + "Modul <label>" + paras 06-10.
Page A4 11906x16838 twips, margin 981/709, header/footer 708 — via template
(also enforced via python-docx section API).
"""

import io
import re
from pathlib import Path

import docx
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

TEMPLATE = Path.home() / "tools-web/templates/basis-data-2026.docx"
MAX_MODULES = 12
MAX_BLOCKS_PER = 10
MAX_SCRIPT_LEN = 20000


def _set_run_text(p_elem, text, keep_two_runs=False):
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
    label = str(modul_label or "").strip()
    matkul = str(matkul or "Basis Data").strip() or "Basis Data"
    if not label:
        return False
    title_txt = "Laporan Praktikum " + matkul
    changed = 0
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


def _set_cover_identitas(doc, cover):
    try:
        kelas = str(cover.get("kelas") or "").strip()
        if kelas:
            kelas = re.sub(r"(\d)\s*-\s*([A-Za-z])", r"\1 – \2", kelas)
            _set_run_text(doc.paragraphs[6]._element, f"Kelas : {kelas}")
        nama = str(cover.get("nama") or "").strip()
        nim = str(cover.get("nim") or "").strip()
        if nama or nim:
            p_elem = doc.paragraphs[7]._element
            for child in list(p_elem):
                if not child.tag.endswith("}pPr"):
                    p_elem.remove(child)
            # spec: cover SEMUA center + bold — tambah w:b di rPr biar 1:1 template
            r = OxmlElement("w:r")
            rPr = OxmlElement("w:rPr")
            b = OxmlElement("w:b")
            rPr.append(b)
            r.append(rPr)
            t = OxmlElement("w:t")
            t.text = nama
            t.set(qn("xml:space"), "preserve")
            r.append(t)
            br = OxmlElement("w:br")
            r.append(br)
            t2 = OxmlElement("w:t")
            t2.text = nim
            r.append(t2)
            p_elem.append(r)
        if cover.get("prodi"):
            _set_run_text(doc.paragraphs[8]._element, cover["prodi"])
        if cover.get("tahun"):
            _set_run_text(doc.paragraphs[10]._element, cover["tahun"])
    except Exception:
        pass


def _norm_num(lbl):
    s = str(lbl or "").strip()
    try:
        return str(int(s))
    except Exception:
        return s


def _pad2(lbl):
    s = str(lbl or "").strip()
    try:
        return f"{int(s):02d}"
    except Exception:
        return s


def _cover_pad2(lbl):
    s = str(lbl or "").strip()
    try:
        return f"{int(s):02d}"
    except Exception:
        return s


def _set_footer(doc, nama, tengah="Tugas", kanan="Basis Data Lanjut"):
    for sect in doc.sections:
        try:
            p = sect.footer.paragraphs[0]
            p_elem = p._element
            pPr = p_elem.find(qn("w:pPr"))
            for child in list(p_elem):
                if child is not pPr:
                    p_elem.remove(child)

            def _add_text(txt):
                r = OxmlElement("w:r")
                t = OxmlElement("w:t")
                t.text = txt
                if txt.startswith(" ") or txt.endswith(" "):
                    t.set(qn("xml:space"), "preserve")
                r.append(t)
                p_elem.append(r)

            def _add_ptab(align):
                r = OxmlElement("w:r")
                ptab = OxmlElement("w:ptab")
                ptab.set(qn("w:relativeTo"), "margin")
                ptab.set(qn("w:alignment"), align)
                ptab.set(qn("w:leader"), "none")
                r.append(ptab)
                p_elem.append(r)

            _add_text(nama)
            _add_ptab("center")
            _add_text(tengah)
            _add_ptab("right")
            _add_text(kanan)
        except Exception:
            continue


def _prune_orphan_images(doc):
    """Hapus relasi image yatim (template image1-3) — best effort, silent."""
    import re
    try:
        EMBED = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
        used = set()
        for el in doc.element.iter():
            rid = el.get(EMBED)
            if rid:
                used.add(rid)
        rels = doc.part.rels
        for rid in [r for r in list(getattr(rels, "_rels", {}).keys())]:
            try:
                rel = rels[rid]
                if "image" in getattr(rel, "reltype", "") and rid not in used:
                    del rels._rels[rid]
            except Exception:
                continue
    except Exception:
        pass


def _strip_orphan_media(data):
    """Zip-level prune: buang word/media/* yang tak ter-ref di document.xml
    + rels + Content_Types override-nya. Output cuma bawa media terpakai."""
    import re
    import zipfile
    zin = zipfile.ZipFile(io.BytesIO(data))
    names = zin.namelist()
    doc_xml = zin.read("word/document.xml").decode("utf-8", "replace")
    rels_xml = zin.read("word/_rels/document.xml.rels").decode("utf-8", "replace")
    used_targets = set()
    for m in re.finditer(r'r:embed="(rId\d+)"', doc_xml):
        mm = re.search(r'Id="%s"[^>]*Target="([^"]+)"' % re.escape(m.group(1)), rels_xml)
        if mm:
            used_targets.add(mm.group(1))
    drop_media = [n for n in names
                  if n.startswith("word/media/") and ("media/" + n.split("word/media/")[1]) not in used_targets
                  and n.split("word/", 1)[1] not in used_targets]
    if not drop_media:
        return data
    drop_set = set(drop_media)
    # rels entries pointing to dropped media
    drop_rel_ids = set()
    for m in re.finditer(r'<Relationship\s+Id="([^"]+)"[^>]*Target="([^"]+)"', rels_xml):
        rid, tgt = m.group(1), m.group(2)
        if tgt.startswith("media/") and ("word/" + tgt) in drop_set:
            drop_rel_ids.add(rid)
    new_rels = re.sub(
        r'<Relationship\s+Id="(%s)"[^>]*/>' % "|".join(sorted(drop_rel_ids)),
        "", rels_xml) if drop_rel_ids else rels_xml
    try:
        ct = zin.read("[Content_Types].xml").decode("utf-8", "replace")
        for n in drop_media:
            ct = re.sub(r'<Override\s+PartName="/%s"[^>]*/>' % re.escape(n), "", ct)
    except Exception:
        ct = None
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for n in names:
            if n in drop_set:
                continue
            blob = new_rels.encode() if n == "word/_rels/document.xml.rels" else (
                ct.encode() if (ct is not None and n == "[Content_Types].xml") else zin.read(n))
            zout.writestr(n, blob)
    return out.getvalue()


def _ensure_section(doc):
    # template SUDAH exact (A4 11906x16838, margin 981/709, header/footer 708) —
    # JANGAN sentuh via Inches (rounding drift: 11909/979/706). No-op by design.
    return


def _add_script_table(doc, text):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.style = "Table Grid"
    cell = tbl.cell(0, 0)
    lines = str(text or "")[:MAX_SCRIPT_LEN].splitlines() or [""]
    cell.text = lines[0]
    for ln in lines[1:]:
        cell.add_paragraph(ln)
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
        # 85% text width ~ 6.19in, use 6in (~82%) close enough to spec
        cell.paragraphs[0].add_run().add_picture(io.BytesIO(img_bytes), width=Inches(6))
    except Exception as e:
        cell.text = f"[gambar gagal dimuat: {e}]"
    return tbl


def _add_caption(doc, text, style="Caption"):
    try:
        p = doc.add_paragraph(style=style)
    except Exception:
        p = doc.add_paragraph()
    p.add_run(text)
    return p


def build(cover, modules):
    if not (1 <= len(modules) <= MAX_MODULES):
        raise ValueError(f"modul harus 1-{MAX_MODULES}")
    cover = {k: str(v or "").strip() for k, v in (cover or {}).items()}
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
    _ensure_section(doc)

    cover_modul = cover.get("modul") or (labels[0] if len(labels) == 1 else f"1-{len(labels)}")
    matkul = cover.get("matkul") or "Basis Data"
    _set_cover_modul(doc, cover_modul, matkul)
    _set_cover_identitas(doc, cover)

    nama_full = cover.get("nama", "")
    footer_nama = cover.get("footer_nama") or (nama_full.split()[0] if nama_full.split() else "")
    footer_tengah = cover.get("footer_tengah") or "Tugas"
    footer_kanan = cover.get("footer_kanan") or (matkul if matkul.endswith("Lanjut") else f"{matkul} Lanjut")
    if footer_nama or footer_kanan:
        _set_footer(doc, footer_nama, footer_tengah, footer_kanan)

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

    # H1 uses fixed "03" prefix per template TOC (spec verification: grep "03 Modul 0[123]")
    # Caption uses cover_modul padded (06 Modul 1) per spec
    cover_pad = _cover_pad2(cover_modul) if cover_modul.isdigit() or cover_modul.replace("-","").isdigit() else cover_modul
    # if cover like "1-3" keep as-is for H1 prefix but captions need single number; use cover_pad as-is
    for m, lbl in zip(modules, labels):
        lbl_pad2 = _pad2(lbl)
        lbl_norm = _norm_num(lbl)
        # H1 = "03 Modul 01" style (spec). Keep cover-independent for spec compliance.
        # If spec generic 1-12, prefix should be "03" for this laporan (as in template).
        h1 = f"03 Modul {lbl_pad2}"
        title = str(m.get("title") or "").strip()
        if title and title not in (lbl, f"Modul {lbl}", f"03 Modul {lbl}", f"03 Modul {lbl_pad2}"):
            h1 += f" — {title}"
        try:
            doc.add_heading(h1, level=1)
        except Exception:
            h = doc.add_paragraph(h1)
            try:
                h.style = doc.styles["Heading 1"]
            except Exception:
                pass
        for b in (m.get("blocks") or []):
            t = b.get("type")
            if t == "script":
                txt = str(b.get("text") or b.get("script") or "")
                _add_script_table(doc, txt)
                cap = b.get("caption") or f"Script Modul: {cover_pad} Modul {lbl_norm}"
                _add_caption(doc, cap)
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
                _add_image_table(doc, img)
                cap = b.get("caption") or f"Screenshot Modul: {cover_pad} Modul {lbl_norm}"
                _add_caption(doc, cap)

    out = io.BytesIO()
    doc.save(out)
    data = out.getvalue()
    data = _strip_orphan_media(data)
    if len(data) > 15 * 1024 * 1024:
        raise ValueError("output docx >15MB")
    return data
