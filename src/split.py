import pandas as pd

def split_train_val_dynamic(df: pd.DataFrame, date_col: str = "ds") -> tuple[pd.DataFrame, pd.DataFrame]:
    
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])

    unique_timestamps = sorted(df[date_col].unique())
    total_timestamps = len(unique_timestamps)

    split_index = int(total_timestamps * 0.90)
    split_timestamp = unique_timestamps[split_index]

    train_data = df[df[date_col] <= split_timestamp]
    val_data = df[df[date_col] > split_timestamp]

    return train_data, val_data