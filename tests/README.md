# Tests

## Cara menjalankan

1. Jalankan server (terminal 1):
   ```
   python app.py
   # server di http://127.0.0.1:8083
   ```

2. Jalankan test (terminal 2):
   ```
   python tests/test_contract.py
   python tests/test_engines.py
   python tests/e2e_backend.py
   python tests/test_ui.py   # butuh playwright+chromium
   ```

- `test_contract.py` — cek struktur package, endpoint, header, tanpa server.
- `test_engines.py` — unit test engine langsung, tanpa server.
- `e2e_backend.py` — butuh server hidup di 127.0.0.1:8083, pakai fixtures di tests/fixtures.
- `test_ui.py` — buka static/index.html via file://, butuh `pip install playwright && playwright install chromium`.
