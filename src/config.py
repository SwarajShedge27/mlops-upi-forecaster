from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
RAW_DATA_PATH = DATA_DIR / "raw/tp_outage_data(in).csv"
PROCESSED_DATA_PATH = DATA_DIR / "processed"
MODELS_DIR = BASE_DIR / "models"

SPLIT_DATE = "2025-07-11 00:00:00"

TARGET_COL = "y"

FREQ = "15min"
SEASON_LENGTH = 96  
ETS_MODEL = "MMM"   

OUTPUTS_DIR = BASE_DIR / "outputs"
METRICS_PATH = OUTPUTS_DIR / "metrics.json"
FORECAST_PATH = OUTPUTS_DIR / "forecasts.csv"
AUTOETS_MODEL_PATH = MODELS_DIR / "autoets"

