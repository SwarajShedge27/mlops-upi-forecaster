import sys
import os
from pathlib import Path
from typing import Annotated, Literal
from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.responses import Response  # Import Response to return files
import requests 

sys.path.append(str(Path(__file__).resolve().parent / "src"))

from ingestion import validate_and_ingest_data
from preprocessing import preprocess_and_clean_data
from split import split_train_val_dynamic
from train import train_models_in_memory
from evaluate import evaluate_models_in_memory
from predict import generate_future_forecast_dynamic

app = FastAPI(version="2.0.0")

@app.get("/health")
def health_check():
    
    try:
        response = requests.get("http://127.0.0.1:8501/", timeout=2)
        
        if response.status_code == 200:
            return {
                "status": "healthy",
                "services": {
                    "backend_api": "up",
                    "frontend_dashboard": "up"
                }
            }
    except Exception:
        pass
    
    raise HTTPException(status_code=503, detail="Frontend service is unreachable.")


@app.post("/forecast", status_code=200)
def run_forecasting_pipeline_json(
    file: UploadFile = File(...),
    horizon: Annotated[int,Query(ge=1,le=500,description="Forecast horizon")] = 96,
    freq: Literal["15min","30min","1H","1D","7D","30D","365D"] = Query("15min"),
    season_length: int = Query(default=96,ge=2,le=500,description="Supported seasonal cycle lengths are 24, 48, 96, 168"),
    model_type: str = Query(default="ZZZ", description="AutoETS Model configuration string (e.g. ZZZ, MMM, AAA)")
):

    allowed_values = {1, 7, 12, 24, 48, 52, 96, 168, 365}
    if season_length not in allowed_values:
        raise HTTPException(status_code=400,detail="season_length must be one of: 1, 7, 12, 24, 48, 52, 96, 168, or 365.")

    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted.")

    try:
        file_bytes = file.file.read()

        df_raw, warnings = validate_and_ingest_data(file_bytes)
        if df_raw.empty:
            raise HTTPException(status_code=400,detail="CSV contains no records.")

        df_clean = preprocess_and_clean_data(df_raw, freq=freq)

        train_df, val_df = split_train_val_dynamic(df_clean)

        if train_df.empty:
            raise HTTPException(status_code=400,detail="Training dataset is empty.")

        if val_df.empty:
            raise HTTPException(status_code=400,detail="Validation dataset is empty.")

        val_h = len(val_df["ds"].unique())

        sf_ets, sf_baseline = train_models_in_memory(train_df, freq=freq, season_length=season_length, model_type=model_type)

        if sf_ets is None:
            raise HTTPException(status_code=500,detail="AutoETS training failed.")

        if sf_baseline is None:
            raise HTTPException(status_code=500,detail="Baseline model training failed.")

        # Extract the scores sub-dictionary from the returned results
        evaluation_results = evaluate_models_in_memory(val_df, sf_ets, sf_baseline, h=val_h)
        metrics = evaluation_results["scores"]
        
        print("\n" + "="*30)
        print("EVALUATION METRICS")
        print("="*30)
        print(f"AutoETS Accuracy:   {metrics['auto_ets']['accuracy']:.2f}%")
        print(f"Baseline Accuracy:  {metrics['baseline']['accuracy']:.2f}%")
        print("="*30 + "\n")

        forecast_df = generate_future_forecast_dynamic(df_clean, h=horizon, freq=freq, season_length=season_length)
        if forecast_df.empty:
            raise HTTPException(status_code=500,detail="Forecast generation failed.")

        # Convert the forecast DataFrame into tabular CSV string
        csv_data = forecast_df.to_csv(index=False)

        return Response(
            content=csv_data,
            media_type="text/csv", # this tell browser the file is in csv format 
            headers={
                "Content-Disposition": 'attachment; filename="upi_future_forecasts.csv"' 
            }
            #The Content-Disposition HTTP header instructs the browser on how to handle an incoming file or response payload. It dictates whether the content should be displayed directly in the browser window (inline) or downloaded locally as a file (attachment)
        )

    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline execution error: {str(e)}")

@app.post("/forecast/json", status_code=200)
def run_forecasting_pipeline_json(
    file: UploadFile = File(...),
    horizon: Annotated[int,Query(ge=1,le=500,description="Forecast horizon")] = 96,
    freq: Literal["15min","30min","1H","1D","7D","30D","365D"] = Query("15min"),
    season_length: int = Query(default=96,ge=2,le=500,description="Supported seasonal cycle lengths are 24, 48, 96, 168"),
    model_type: str = Query(default="ZZZ", description="AutoETS Model configuration string (e.g. ZZZ, MMM, AAA)")
):

    allowed_values = {1, 7, 12, 24, 48, 52, 96, 168, 365}
    if season_length not in allowed_values:
        raise HTTPException(status_code=400,detail="season_length must be one of: 1, 7, 12, 24, 48, 52, 96, 168, or 365.")


    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted.")

    try:
        file_bytes = file.file.read()

        df_raw, warnings = validate_and_ingest_data(file_bytes)
        if df_raw.empty:
            raise HTTPException(status_code=400,detail="CSV contains no records.")

        df_clean = preprocess_and_clean_data(df_raw, freq=freq)

        train_df, val_df = split_train_val_dynamic(df_clean)
        if train_df.empty:
            raise HTTPException(status_code=400,detail="Training dataset is empty.")

        if val_df.empty:
            raise HTTPException(status_code=400,detail="Validation dataset is empty.")

        val_h = len(val_df["ds"].unique())

        sf_ets, sf_baseline = train_models_in_memory(train_df, freq=freq, season_length=season_length, model_type=model_type)
        if sf_ets is None:
            raise HTTPException(status_code=500,detail="AutoETS training failed.")

        if sf_baseline is None:
            raise HTTPException(status_code=500,detail="Baseline model training failed.")

        evaluation_results = evaluate_models_in_memory(val_df, sf_ets, sf_baseline, h=val_h)
        metrics = evaluation_results["scores"]
        val_predictions = evaluation_results["val_predictions"]

        forecast_df = generate_future_forecast_dynamic(df_clean, h=horizon, freq=freq, season_length=season_length)

        if forecast_df.empty:
            raise HTTPException(status_code=500,detail="Forecast generation failed.")

        forecasts_list = forecast_df.to_dict(orient="records")

        return {
            "metrics": metrics,
            "warnings": warnings,
            "val_predictions": val_predictions,
            "forecasts": forecasts_list
        }

    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline execution error: {str(e)}")
