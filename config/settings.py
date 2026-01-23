import os
from pathlib import Path
from dotenv import load_dotenv

# --------------------------------------------------
# BASE DIR DEL PROYECTO
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BASE_DIR / ".env"

# --------------------------------------------------
# LOAD ENV
# --------------------------------------------------
load_dotenv(dotenv_path=ENV_PATH)

# --------------------------------------------------
# API BASE
# --------------------------------------------------
NOWCERTS_API_BASE_URL = "https://api.nowcerts.com/api"

# --------------------------------------------------
# AUTH
# --------------------------------------------------
NOWCERTS_ACCESS_TOKEN = os.getenv("NOWCERTS_ACCESS_TOKEN")

if not NOWCERTS_ACCESS_TOKEN:
    raise RuntimeError(
        f"❌ Falta NOWCERTS_ACCESS_TOKEN en el .env ({ENV_PATH})"
    )

# --------------------------------------------------
# REQUEST SETTINGS
# --------------------------------------------------
REQUEST_TIMEOUT = 60

# --------------------------------------------------
# PAGINACIÓN DEFAULT
# --------------------------------------------------
DEFAULT_TOP = 500
