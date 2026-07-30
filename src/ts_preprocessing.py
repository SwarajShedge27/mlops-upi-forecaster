import pandas as pd
import numpy as np

def _boundary_creation(df_count: pd.DataFrame, sdval: int = 2, mycol: str = "y", mydcol: str = "ds", bucket: str = "15min", aggtype="sum", iteration: int = 3, value_format: int = 2) -> pd.DataFrame:

    df_count = df_count.copy()
    df_count[mydcol] = pd.to_datetime(df_count[mydcol])
    df_count[mydcol] = df_count[mydcol].dt.floor(bucket) # keeps all date time in 15 min freq 
    
    # Group duplicate time observations
    df_count = df_count.groupby(["unique_id", mydcol], as_index=False).agg({mycol: aggtype})
    
    rolltype = 'dttime'
    df_count[rolltype] = df_count[mydcol].dt.time
    
    for k in range(0, iteration):
        # Calculate mean of y for each unique_id and time-of-day
        mean_map = df_count.groupby(["unique_id", rolltype])[mycol].transform("mean") # calculate the average for each unique time , ex- at time 12:30:00 what is the average value 
        df_count["AVG_" + mycol] = mean_map.fillna(0).round(value_format)
        
        # Calculate standard deviation of y for each unique_id and time-of-day
        std_map = df_count.groupby(["unique_id", rolltype])[mycol].transform("std") # calculate the std for each unique time , ex- at time 12:30:00 what is the std value 
        df_count["sdval"] = std_map.fillna(0).round()
        
        # Determine Lower Control Limit (LCL) and Upper Control Limit (UCL)
        df_count['LCL_' + mycol] = (df_count["AVG_" + mycol] - (sdval * df_count['sdval'])).round(value_format)
        df_count['UCL_' + mycol] = (df_count["AVG_" + mycol] + (sdval * df_count['sdval'])).round(value_format)
        df_count['LCL_' + mycol] = df_count['LCL_' + mycol].clip(lower=0)
        
        # Replace outliers with the mean
        df_count["outlier"] = np.where((df_count[mycol] < df_count['LCL_' + mycol]) | (df_count[mycol] > df_count['UCL_' + mycol]), 1, 0)
        df_count[mycol] = np.where(df_count["outlier"] == 1, df_count["AVG_" + mycol], df_count[mycol])
        
        # Clear calculation columns if not on the final iteration
        if k != iteration - 1:
            df_count = df_count.drop(columns=["AVG_" + mycol, "sdval", "LCL_" + mycol, "UCL_" + mycol, "outlier"])
            
    return df_count[["unique_id", mydcol, mycol]]

def clean_data(train_raw: pd.DataFrame, freq: str) -> pd.DataFrame:
    return _boundary_creation(train_raw, sdval=2, mycol="y", mydcol="ds", bucket=freq)
