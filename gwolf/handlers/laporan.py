import json
from pathlib import Path
from gwolf.responses import send_json, send_file_download
from gwolf.engines.laporan_builder import build

MAX_TOTAL = 40 * 1024 * 1024

def handle_laporan_basis_data(handler, files, form_data):
    try:
        total = sum(len(b) for _, b in files)
        if total > MAX_TOTAL:
            send_json(handler, {"error": "total upload >40MB"}, 400); return True
        # modules_json required
        mj = form_data.get("modules_json", "")
        if not mj:
            send_json(handler, {"error": "modules_json kosong — isi modul dulu"}, 400); return True
        try:
            modules = json.loads(mj)
        except Exception:
            send_json(handler, {"error": "modules_json bukan JSON valid"}, 400); return True
        # map files by name for screenshot blocks: {"file":"ss1.png"} lookup
        fmap = {}
        for fn, b in files:
            fmap[fn] = b
            fmap[Path(fn).name] = b
        # resolve screenshot refs
        for m in (modules if isinstance(modules, list) else []):
            for b in ((m.get("blocks") or []) if isinstance(m, dict) else []):
                if isinstance(b, dict) and b.get("type") == "screenshot" and not b.get("file"):
                    ref = b.get("file_name") or b.get("filename") or b.get("name") or ""
                    if ref and ref in fmap:
                        b["file"] = fmap[ref]
                    elif len(files) == 1 and len([x for x in sum([mm.get("blocks", []) for mm in modules if isinstance(mm, dict)], []) if isinstance(x, dict) and x.get("type")=="screenshot" and not x.get("file")]) == 1:
                        # single SS convenience: auto-attach
                        b["file"] = files[0][1]
        cover = {
            "nama": form_data.get("cover_nama", ""),
            "nim": form_data.get("cover_nim", ""),
            "kelas": form_data.get("cover_kelas", ""),
            "prodi": form_data.get("cover_prodi", ""),
            "tahun": form_data.get("cover_tahun", ""),
            "modul": form_data.get("cover_modul", ""),
            "matkul": form_data.get("matkul", "") or "Basis Data",
        }
        try:
            data = build(cover, modules)
        except ValueError as e:
            send_json(handler, {"error": str(e)}, 400); return True
        except Exception as e:
            send_json(handler, {"error": f"builder gagal: {e}"}, 500); return True
        nmod = len(modules) if isinstance(modules, list) else 0
        nblk = sum(len(m.get("blocks", [])) for m in modules) if isinstance(modules, list) else 0
        stem = (cover.get("nama") or "laporan").strip().replace(" ", "_")[:30] or "laporan"
        print(f"[laporan] modules={nmod} blocks={nblk} bytes={len(data)}", flush=True)
        send_file_download(handler, data, f"laporan_{stem}.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            original_size=total)
    except Exception as e:
        send_json(handler, {"error": str(e)}, 500)
    return True
