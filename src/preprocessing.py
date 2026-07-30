import pandas as pd
from ts_preprocessing import clean_data

def preprocess_and_clean_data(df: pd.DataFrame, freq: str = "15min") -> pd.DataFrame:
    df = df.copy()

    if "unique_id" not in df.columns or "ds" not in df.columns or "y" not in df.columns:
        raise ValueError("DataFrame must contain 'unique_id', 'ds', and 'y' columns.")

    df["unique_id"] = df["unique_id"].astype(str).astype("string")
    df.dropna(subset=["unique_id"], inplace=True)
    df["ds"] = pd.to_datetime(df["ds"])

    #It assumes that the dataset is sorted and that rows represent consecutive, chronological observations without missing intervals. If there are missing intervals
    aligned_dfs = []
    for unique_id, group in df.groupby("unique_id"):
        group = group.sort_values("ds").copy()
        
        # Generate a perfectly regular date range starting from the first date using the target frequency
        n_rows = len(group)
        regular_dates = pd.date_range(start=group["ds"].iloc[0], periods=n_rows, freq=freq)
        
        group["ds"] = regular_dates
        aligned_dfs.append(group)
        
    df = pd.concat(aligned_dfs, ignore_index=True)

    clean_df = clean_data(df, freq=freq)

    return clean_df
