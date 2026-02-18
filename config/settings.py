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
NOWCERTS_API_BASE_URL = os.getenv(
    "NOWCERTS_API_BASE_URL", "https://api.nowcerts.com/api")

# --------------------------------------------------
# AUTH
# --------------------------------------------------
NOWCERTS_USERNAME = os.getenv("NOWCERTS_USERNAME")
NOWCERTS_PASSWORD = os.getenv("NOWCERTS_PASSWORD")
NOWCERTS_AGENCY_ID = os.getenv("NOWCERTS_AGENCY_ID")

# --------------------------------------------------
# REQUEST SETTINGS
# --------------------------------------------------
REQUEST_TIMEOUT = 60

# --------------------------------------------------
# PAGINACIÓN DEFAULT
# --------------------------------------------------
DEFAULT_TOP = 2000
