# Gwolf Toolbox

Aplikasi utilitas web lokal ringan untuk pemrosesan file PDF, Gambar, dan Dokumen Word. Dirancang khusus untuk efisiensi tinggi pada lingkungan Android Termux dan Desktop tanpa ketergantungan framework web berat.

## Cara Menjalankan

1. Pastikan dependensi terpasang:
   ```bash
   pip install -r requirements.txt
   ```

2. Jalankan server:
   ```bash
   python app.py
   ```

3. Buka peramban di `http://127.0.0.1:8083`.

> **Catatan Termux**: Direktori kerja default berada di `~/tools-web/` (`STATIC_DIR` dan `UPLOAD_DIR`). File statis diletakkan pada folder `static/`.

---

## Daftar Fitur dan Endpoint API

| Fitur | Endpoint | Method | Input | Output / Format |
|---|---|---|---|---|
| Gabung PDF | `/api/pdf/merge` | POST | Beberapa file PDF | PDF gabungan (`merged_document.pdf`) |
| Kompres PDF | `/api/pdf/compress` | POST | 1 file PDF | PDF terkompresi (`compressed_<nama>.pdf`) |
| PDF ke Gambar | `/api/pdf/to-img` | POST | 1 file PDF, `dpi`, `format` | Gambar tunggal / ZIP multi-halaman |
| Gambar ke PDF | `/api/img/to-pdf` | POST | Beberapa file gambar | PDF (`images_document.pdf`) |
| Kompres Gambar | `/api/img/compress` | POST | 1 file gambar, `quality` | Gambar terkompresi |
| Perbesar Gambar | `/api/img/upscale` | POST | 1 file gambar, `scale` | Gambar resolusi lebih tinggi (2x/4x) |
| Konversi Format | `/api/img/convert` | POST | 1 file gambar, `format` | Gambar dengan format baru (PNG/JPG/WEBP) |
| Word ke PDF | `/api/word/to-pdf` | POST | 1 file Word (.docx/.doc) | Dokumen PDF (`converted_<nama>.pdf`) |
| PDF ke Word | `/api/pdf/to-word` | POST | 1 file PDF | Dokumen DOCX (`converted_<nama>.docx`) |
| Status Server | `/api/status` | GET | - | JSON status fitur aktif |

---

## Engine Opsional dan Dependensi Tambahan

Untuk hasil konversi maksimal:

- **pdf2docx** (Layout-preserving PDF ke Word):
  ```bash
  pip install pdf2docx
  ```
- **Ghostscript** (Kompresi PDF lanjutan dan render PDF):
  - Termux: `pkg install ghostscript`
  - Linux/Ubuntu: `sudo apt install ghostscript`
- **LibreOffice / soffice** (Fidelitas penuh konversi Word ke PDF dan dukungan legacy .doc):
  - Termux: `pkg install libreoffice`
  - Linux/Ubuntu: `sudo apt install libreoffice`

---

## Menjalankan Pengujian (Tests)

1. Jalankan unit test engine (tanpa perlu server):
   ```bash
   python tests/test_engines.py
   ```

2. Jalankan pemeriksaan kontrak dan struktur:
   ```bash
   python tests/test_contract.py
   ```

3. Jalankan end-to-end testing (saat server menyala di port 8083):
   ```bash
   python tests/e2e_backend.py
   ```

4. Jalankan UI visual test (opsional, butuh Playwright):
   ```bash
   pip install -r requirements-test.txt
   playwright install chromium
   python tests/test_ui.py
   ```

---

## Struktur Direktori

```
gwolf-tools/
|-- app.py                   # Entry point server HTTP (thin wrapper)
|-- requirements.txt         # Ketergantungan inti
|-- requirements-optional.txt# Ketergantungan opsional
|-- requirements-test.txt    # Ketergantungan testing
|-- README.md                # Dokumentasi proyek
|-- gwolf/                   # Paket modul utama
|   |-- __init__.py
|   |-- config.py            # Konfigurasi port, path, dan default
|   |-- multipart.py         # Parser multipart form data
|   |-- responses.py         # Helper pengiriman JSON dan file download
|   |-- handlers/            # Routing dan handler HTTP request
|   |   |-- __init__.py
|   |   |-- status.py        # Handler halaman utama dan status API
|   |   |-- pdf.py           # Handler pemrosesan PDF
|   |   |-- image.py         # Handler pemrosesan gambar
|   |   |-- docs.py          # Handler dokumen Word & konversi PDF
|   `-- engines/             # Engine pemrosesan inti
|       |-- __init__.py
|       |-- pdf_compress.py  # Kompresi PDF via Ghostscript / pypdf
|       |-- pdf_render.py    # Render halaman PDF ke gambar
|       |-- img_ops.py       # Manipulasi, upscale, konversi gambar
|       `-- docx_ops.py      # Konversi Word <-> PDF
|-- static/
|   `-- index.html           # Tampilan antarmuka pengguna
`-- tests/
    |-- test_contract.py     # Validasi kontrak API & UI
    |-- test_engines.py      # Unit test fungsi engine
    |-- e2e_backend.py       # Pengujian end-to-end backend
    |-- test_ui.py           # Validasi UI berbasis Playwright
    `-- fixtures/            # Direktori file uji
```
