import pandas as pd
from statsforecast import StatsForecast
from models.auto_ets import fit_auto_ets_dynamic
from config import FREQ, SEASON_LENGTH

def generate_future_forecast_dynamic(full_df: pd.DataFrame, h: int, freq: str = FREQ, season_length: int = SEASON_LENGTH) -> pd.DataFrame:
    
    sf = fit_auto_ets_dynamic(full_df, freq=freq, season_length=season_length)

    forecast_df = sf.predict(h=h)
    forecast_df = forecast_df.reset_index()

    inverse_mapping = {"A": "CITIBANKUPI", "B": "PAYTMPGUPI", "C": "YESBANKUPI"}
    forecast_df["unique_id"] = forecast_df["unique_id"].astype(str) # Ensure string conversion
    forecast_df["PG_NAME"] = forecast_df["unique_id"].map(inverse_mapping)

    forecast_df["ds"] = pd.to_datetime(forecast_df["ds"])
    forecast_df["datetime"] = forecast_df["ds"].dt.strftime("%Y-%m-%d %H:%M:%S") #Formats Pandas Datetime objects to standard ISO strings

    forecast_df.rename(columns={"AutoETS": "forecast"}, inplace=True)

    return forecast_df[["PG_NAME", "datetime", "forecast"]]
