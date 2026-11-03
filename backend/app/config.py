
"""
Application settings for the FinShield backend.

Values are read from environment variables (see .env.example) and fall back to
safe defaults so the project still runs on a teammate's laptop without setup.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Directory paths
# backend/app/config.py -> backend/ -> code/
BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent

# Load environment variables from backend/.env
load_dotenv(BACKEND_DIR / ".env")


def _path_setting(env_name: str, default_folder: str) -> Path:
    """Use the environment variable if set; otherwise use the default folder."""
    value = os.getenv(env_name)

    if value:
        return Path(value).expanduser().resolve()

    return REPO_ROOT / default_folder


# Database
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/finshield",
)

# Authentication
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "change-this-secret-key-in-production",
)
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120")
)

# Teammate code locations
ML_MODELS_DIR = _path_setting("ML_MODELS_DIR", "ml/models")
AML_PACKAGE_DIR = _path_setting("AML_PACKAGE_DIR", "member4_aml")

# ML model used by the API
# Supported options: xgboost, random_forest, logistic_regression
ML_MODEL_NAME = os.getenv("ML_MODEL_NAME", "xgboost")

# Hybrid risk scoring weights
ML_WEIGHT = float(os.getenv("ML_WEIGHT", "0.6"))
AML_WEIGHT = float(os.getenv("AML_WEIGHT", "0.4"))

# Risk thresholds
HIGH_RISK_THRESHOLD = float(
    os.getenv("HIGH_RISK_THRESHOLD", "0.70")
)
MEDIUM_RISK_THRESHOLD = float(
    os.getenv("MEDIUM_RISK_THRESHOLD", "0.40")
)

# Maximum number of previous transactions used for AML analysis
AML_HISTORY_LIMIT = int(os.getenv("AML_HISTORY_LIMIT", "50"))
