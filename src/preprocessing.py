import pandas as pd
from ts_preprocessing import clean_data

def preprocess_and_clean_data(df: pd.DataFrame, freq: str = "15min") -> pd.DataFrame:

    df = df.copy()

    rename_map = {}
    if "CREATION_DATE" in df.columns:
        rename_map["CREATION_DATE"] = "ds"
    if "TOTAL_ATTEMPTED" in df.columns:
        rename_map["TOTAL_ATTEMPTED"] = "y"
        
    df.rename(columns=rename_map, inplace=True)

    mapping = {"CITIBANKUPI": "A", "PAYTMPGUPI": "B", "YESBANKUPI": "C"}
    if "PG_NAME" in df.columns:
        df["unique_id"] = df["PG_NAME"].map(mapping).astype("string")
        df.drop(columns=["PG_NAME"], inplace=True)
    elif "unique_id" not in df.columns and "PG_NAME" not in df.columns:
        raise ValueError("DataFrame must contain 'PG_NAME' or 'unique_id' column.")

    # Drop records with invalid or unmapped gateway names
    df.dropna(subset=["unique_id"], inplace=True)

    df["ds"] = pd.to_datetime(df["ds"])

    clean_df = clean_data(df, freq=freq)

    return clean_df
