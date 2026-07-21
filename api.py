import sys
import os
from pathlib import Path
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
def run_forecasting_pipeline(
    file: UploadFile = File(...),
    horizon: int = Query(96, description="Forecast horizon h (number of intervals)"),
    freq: str = Query("15min", description="Time series step frequency"),
    season_length: int = Query(96, description="Seasonal cycle length")
):
   
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted.")

    try:
        file_bytes = file.file.read()

        df_raw, warnings = validate_and_ingest_data(file_bytes)

        df_clean = preprocess_and_clean_data(df_raw, freq=freq)

        train_df, val_df = split_train_val_dynamic(df_clean)

        val_h = len(val_df["ds"].unique())

        sf_ets, sf_baseline = train_models_in_memory(train_df, freq=freq, season_length=season_length)

        # Extract the scores sub-dictionary from the returned results
        evaluation_results = evaluate_models_in_memory(val_df, sf_ets, sf_baseline, h=val_h)
        metrics = evaluation_results["scores"]

        # metrics = evaluate_models_in_memory(val_df, sf_ets, sf_baseline, h=val_h)
        
        print("\n" + "="*30)
        print("EVALUATION METRICS")
        print("="*30)
        print(f"AutoETS Accuracy:   {metrics['auto_ets']['accuracy']:.2f}%")
        print(f"Baseline Accuracy:  {metrics['baseline']['accuracy']:.2f}%")
        print("="*30 + "\n")

        forecast_df = generate_future_forecast_dynamic(df_clean, h=horizon, freq=freq, season_length=season_length)

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
    horizon: int = Query(96, description="Forecast horizon h (number of intervals)"),
    freq: str = Query("15min", description="Time series step frequency"),
    season_length: int = Query(96, description="Seasonal cycle length")
):
    
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted.")

    try:
        file_bytes = file.file.read()

        df_raw, warnings = validate_and_ingest_data(file_bytes)

        df_clean = preprocess_and_clean_data(df_raw, freq=freq)

        train_df, val_df = split_train_val_dynamic(df_clean)

        val_h = len(val_df["ds"].unique())

        sf_ets, sf_baseline = train_models_in_memory(train_df, freq=freq, season_length=season_length)

        evaluation_results = evaluate_models_in_memory(val_df, sf_ets, sf_baseline, h=val_h)
        metrics = evaluation_results["scores"]
        val_predictions = evaluation_results["val_predictions"]

        forecast_df = generate_future_forecast_dynamic(df_clean, h=horizon, freq=freq, season_length=season_length)
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
