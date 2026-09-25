import os
from pathlib import Path

PORT = 8083
BASE_DIR = Path.home() / "tools-web"
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = BASE_DIR / "tmp"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Processing presets & defaults
ALLOWED_DPI = (96, 150, 300)
DEFAULT_DPI = 150
DEFAULT_QUALITY = 70
DEFAULT_SCALE = 2

# Timeouts in seconds
TIMEOUT_GS = 30
TIMEOUT_GS_RENDER = 60
TIMEOUT_SOFFICE = 120

