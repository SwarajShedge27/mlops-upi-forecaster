import io
import pandas as pd

REQUIRED_COLUMNS = ["PG_NAME", "CREATION_DATE","TOTAL_ATTEMPTED"]

def validate_and_ingest_data(file_bytes: bytes) -> tuple[pd.DataFrame, list[str]]:
    warnings = []
    #The uploaded CSV is held in RAM rather than saved to disk
    # Parse raw bytes into a Pandas DataFrame in-memory
    try:
        df = pd.read_csv(io.BytesIO(file_bytes)) #This converts those bytes into a file-like object. BytesIO acts as temporary file in memory.
    except Exception as e:
        raise ValueError(f"Failed to parse CSV file: {str(e)}")

    # Check for basic required columns
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Invalid schema. Missing required columns: {missing_cols}")

    # Rename 'TOTAL_ATTEMPTED' to 'y' if present
    if "TOTAL_ATTEMPTED" in df.columns:
        df.rename(columns={"TOTAL_ATTEMPTED": "y"}, inplace=True)
    
    # If after renaming, we still don't have 'y', raise an error
    if "y" not in df.columns:
        raise ValueError("Invalid schema. Dataset must contain a target column named 'y' or 'TOTAL_ATTEMPTED'.")

    # Data Type Conversions & Checks
    # Validate and convert timestamps
    try:
        df["CREATION_DATE"] = pd.to_datetime(df["CREATION_DATE"])
    except Exception:
        df["CREATION_DATE"] = pd.to_datetime(df["CREATION_DATE"], errors="coerce")  # errors="coerce" replace invalide dates with NaT(not a time)
        warnings.append("Some timestamps in 'CREATION_DATE' could not be parsed and were set to NaT.")

    # Validate target column types
    try:
        df["y"] = pd.to_numeric(df["y"])
    except ValueError:
        raise ValueError("Target column 'y' (or 'TOTAL_ATTEMPTED') must contain numeric values.")

    # Check for missing values in target column
    null_count = df["y"].isnull().sum()
    if null_count > 0:
        warnings.append(f"Target column 'y' contains {null_count} missing values (NaN).")

    # Check for invalid/missing gateway names
    null_gateways = df["PG_NAME"].isnull().sum()
    if null_gateways > 0:
        warnings.append(f"Gateway column 'PG_NAME' contains {null_gateways} missing values.")

    # Ensure gateways match expected names in training
    valid_gateways = {"CITIBANKUPI", "PAYTMPGUPI", "YESBANKUPI"}
    unique_gateways = set(df["PG_NAME"].dropna().unique())
    invalid_gateways = unique_gateways - valid_gateways
    if invalid_gateways:
        warnings.append(f"Found unexpected gateway names: {invalid_gateways}. The model will only forecast for: {list(valid_gateways)}.")

    return df, warnings
