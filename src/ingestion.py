import io
import pandas as pd

REQUIRED_COLUMNS = ["unique_id", "ds", "y"]

def validate_and_ingest_data(file_bytes: bytes) -> tuple[pd.DataFrame, list[str]]:
    warnings = []
    
    try:
        df = pd.read_csv(io.BytesIO(file_bytes))
    except Exception as e:
        raise ValueError(f"Failed to parse CSV file: {str(e)}")

    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Invalid time-series schema. Missing required columns: {missing_cols}")

    try:
        df["ds"] = pd.to_datetime(df["ds"])
    except Exception:
        df["ds"] = pd.to_datetime(df["ds"], format='mixed', errors='coerce')
        warnings.append("Some timestamps in 'ds' could not be parsed and were set to NaT.")

    try:
        df["y"] = pd.to_numeric(df["y"])
    except ValueError:
        raise ValueError("Target column 'y' must contain numeric values.")

    null_count = df["y"].isnull().sum()
    if null_count > 0:
        warnings.append(f"Target column 'y' contains {null_count} missing values (NaN).")

    null_ids = df["unique_id"].isnull().sum()
    if null_ids > 0:
        warnings.append(f"Series identifier column 'unique_id' contains {null_ids} missing values.")

    return df, warnings
