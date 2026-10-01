# Laporan Basis Data Builder — Design

Tanggal: 2026-10-01 · Status: approved sections 1-4, siap implementasi
Pendekatan: **A template-clone** (copy `bdl05_2a_089.docx` bersih + isi dinamis)
Scope: modul fleksibel 1–12, block dinamis 1–10/modul, form reusable siapa aja

## 1. Arsitektur & file map

Reuse 1 service `tools-web :8083` (tunnel `tools.gwolfdev.my.id` existing).
No service baru, no DB, no auth tambahan, no deps baru (`python-docx 1.2.0` + `Pillow` installed).

| File | Peran |
|---|---|
| `tools-web/templates/basis-data-2026.docx` | Master bersih dari `bdl05_2a_089.docx` (61 para, cover 00-10, TOC, 9×Heading1, 18 tabel script+SS, 13 img, 1 section, footer `JessieTugasBasis Data Lanjut`; buang `image10.png` CRC bad) |
| `tools-web/gwolf/engines/laporan_builder.py` | ~90 baris stdlib+docx. `build(cover, modules) -> bytes` |
| `tools-web/gwolf/handlers/laporan.py` | 1 endpoint `POST /api/laporan/basis-data`, reuse `multipart.py` + `responses.py` |
| `tools-web/static/laporan.html` | Form vanilla JS, `/laporan` static |
| `tools-web/gwolf/handlers/__init__.py` | +1 route |

`ponytail: no TOC auto-update (Word F9), no soffice — pdf image-fallback.`

## 2. Data flow & block model

`multipart/form-data`: `cover_nama/nim/kelas/prodi/tahun`, `judul`,
`modules_json: [{title, blocks:[{type:"script",text}|{type:"screenshot",file}]}]`,
files `ss*.png/jpg/webp` (0..N).

- Cover: ganti para 06/07/08/10; kosong → keep template.
- Per modul: clone pola Heading1 + blocks:
  - `script` → Table 1x1, `Normal`, `Consolas 9pt`, shading `#F2F2F2`, border tipis.
  - `screenshot` → Table 1x1 + image resize max `6in` keep ratio (Pillow) + Caption `Gambar N — <title>`.
  - Block dinamis 2..N per modul (bukan fixed script+SS).
- TOC keep placeholder (Word F9). Footer/pagination keep template.
- Response `200` docx download + log `{"modules":n,"blocks":n}`.

## 3. Error & constraints

- `modules_json` must parse; modul 1–12, blok/modul 1–10 → else `400`.
- `script` ≤20k char raw `\n`.
- `screenshot`: `png/jpg/jpeg/webp` + `PIL verify`; `>10MB`/invalid → `400`.
- Total upload ≤40MB, output docx ≤15MB guard.
- Template open `except BadZipFile → 500 "template rusak, rebuild"`.
- Resize fail → fallback original bytes, no crash.
- PDF via `/api/word/to-pdf` existing (image-PDF, `soffice` absent HP).
- Stateless. `ponytail: no AI ringkas, no TOC render, no pagination auto — Word handle.`

## 4. Testing & deploy

- `tests/test_laporan_builder.py` stdlib assert:
  1. build 1 modul script+SS dummy → `PK`, re-open OK, cover match, H1=1.
  2. 3-block modul → Table+3, Caption match.
  3. 13 modul → `ValueError`; `.txt` sbg SS → `ValueError`.
- E2E manual: `curl POST /api/laporan/basis-data` → `200` docx (WPS cek) + `/api/word/to-pdf` → `%PDF`.
- Deploy: `sv restart hermes-tools`; rollback `git checkout` 1 route.
- RAM guard: peak resize 6in + docx mem, test 12 modul avail 1.2GB.
