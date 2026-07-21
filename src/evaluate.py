import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error
from statsforecast import StatsForecast

def calculate_mae(y_true: pd.Series, y_pred: pd.Series) -> float:
    return float(mean_absolute_error(y_true, y_pred))

def calculate_wmape(y_true: pd.Series, y_pred: pd.Series) -> float:
    total_actual = np.sum(y_true)
    if total_actual == 0:
        return 0.0
    return float((np.sum(np.abs(y_true - y_pred)) / total_actual) * 100)

def evaluate_models_in_memory(val_df: pd.DataFrame, sf_ets: StatsForecast, sf_baseline: StatsForecast, h: int) -> dict:
    val_df = val_df.copy()

    # Predict validation steps and reset the index to convert unique_id to a column
    forecast_ets = sf_ets.predict(h=h).reset_index()
    forecast_baseline = sf_baseline.predict(h=h).reset_index()

    val_df["ds"] = pd.to_datetime(val_df["ds"])
    forecast_ets["ds"] = pd.to_datetime(forecast_ets["ds"])
    forecast_baseline["ds"] = pd.to_datetime(forecast_baseline["ds"])

    # Merge true validation target values and predictions
    merged = val_df.merge(forecast_ets, on=["unique_id", "ds"], how="left")
    merged = merged.merge(forecast_baseline, on=["unique_id", "ds"], how="left")

    merged.fillna(0.0, inplace=True)

    y_true = merged["y"]
    y_pred_ets = merged["AutoETS"]
    y_pred_baseline = merged["Naive"]

    wmape_ets = calculate_wmape(y_true, y_pred_ets)
    rmse_ets = float(np.sqrt(np.mean((y_true - y_pred_ets) ** 2)))
    
    wmape_baseline = calculate_wmape(y_true, y_pred_baseline)
    rmse_baseline = float(np.sqrt(np.mean((y_true - y_pred_baseline) ** 2)))

    # Map the short unique_id codes to their full gateway names (matching the frontend)
    inverse_mapping = {"A": "CITIBANKUPI", "B": "PAYTMPGUPI", "C": "YESBANKUPI"}
    merged["unique_id"] = merged["unique_id"].astype(str)
    merged["PG_NAME"] = merged["unique_id"].map(inverse_mapping)

    # Convert the prediction columns to string/float representations for JSON
    merged["ds"] = merged["ds"].dt.strftime("%Y-%m-%d %H:%M:%S")
    val_preds_list = merged[["PG_NAME", "ds", "y", "AutoETS", "Naive"]].to_dict(orient="records")

    return {
        "scores": {
            "auto_ets": {
                "mae": calculate_mae(y_true, y_pred_ets),
                "rmse": rmse_ets,
                "wmape": wmape_ets,
                "accuracy": max(0.0, 100.0 - wmape_ets)
            },
            "baseline": {
                "mae": calculate_mae(y_true, y_pred_baseline),
                "rmse": rmse_baseline,
                "wmape": wmape_baseline,
                "accuracy": max(0.0, 100.0 - wmape_baseline)
            }
        },
        "val_predictions": val_preds_list
    }
