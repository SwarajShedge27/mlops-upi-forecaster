import os
import streamlit as st
import pandas as pd
import requests
import plotly.express as px

BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000/forecast/json")

st.set_page_config(page_title="Forecaster", layout="wide")

st.title("Generic Time Series Forecasting System")
st.write("Upload any historical time-series logs, map the columns, and project future volumes.")
st.markdown("---")

uploaded_file = st.file_uploader("Upload Time Series CSV", type=["csv"])

if "current_file" not in st.session_state:
    st.session_state["current_file"] = None

if uploaded_file is not None:
    if st.session_state["current_file"] != uploaded_file.name:
        st.session_state["current_file"] = uploaded_file.name
        if "payload" in st.session_state:
            del st.session_state["payload"]
    # above logic is used to remove cache from previous request 

    df_raw = pd.read_csv(uploaded_file)
    columns_list = list(df_raw.columns)
    
    st.subheader("Ingested Dataset Preview")
    st.dataframe(df_raw, use_container_width=True)
    st.markdown("---")

    st.subheader("Dataset Summary Statistics")
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    with col_stat1:
        st.metric("Total Row Records", f"{df_raw.shape[0]:,}")
    with col_stat2:
        st.metric("Total Columns", df_raw.shape[1])
    with col_stat3:
        null_vals = df_raw.isnull().sum().sum()
        st.metric("Missing (Null) Values", f"{null_vals:,}", delta="No missing values" if null_vals == 0 else f"{null_vals} nulls found", delta_color="off" if null_vals == 0 else "inverse")

    st.subheader("Schema Column Mapping Configuration")
    st.write("Help the pipeline understand your dataset columns:")
    
    col_mapping1, col_mapping2, col_mapping3 = st.columns(3)
    
    def find_default_idx(choices, substrings):
        for i, val in enumerate(choices):
            if any(sub in val.lower() for sub in substrings):
                return i
        return 0

    with col_mapping1:
        date_col = st.selectbox(
            "Select Timestamp Column (ds):", 
            columns_list,
            index=find_default_idx(columns_list, ["date", "ds", "time", "creation"])
        )
    with col_mapping2:
        id_choices = ["Single Series (No ID Column)"] + columns_list
        id_col = st.selectbox(
            "Select Series ID Column (unique_id):", 
            id_choices,
            index=find_default_idx(id_choices, ["id", "pg", "name", "gate", "series", "pg_name"])
        )
    with col_mapping3:
        val_col = st.selectbox(
            "Select Target Value Column (y):", 
            columns_list,
            index=find_default_idx(columns_list, ["y", "attempt", "volume", "value", "total"])
        )
        
    st.markdown("---")

    st.subheader("Ingested Historical Time-Series Preview")
    df_plot = df_raw.copy()
    if id_col == "Single Series (No ID Column)":
        df_plot["unique_id"] = "Series_1"
    else:
        df_plot.rename(columns={id_col: "unique_id"}, inplace=True)
        
    df_plot.rename(columns={date_col: "ds", val_col: "y"}, inplace=True)
    df_plot["unique_id"] = df_plot["unique_id"].astype(str)
    
    try:
        df_plot["ds"] = pd.to_datetime(df_plot["ds"], format='mixed', errors='coerce')
        
        plot_series_ids = sorted(df_plot["unique_id"].unique())
        
        preview_tabs = st.tabs([f"Preview: {sid}" for sid in plot_series_ids])
        preview_colors = ["#1f77b4", "#2ca02c", "#d62728", "#9467bd", "#ff7f0e", "#8c564b"]
        
        for idx, (tab, sid) in enumerate(zip(preview_tabs, plot_series_ids)):
            with tab:
                df_sid_plot = df_plot[df_plot["unique_id"] == sid]
                fig_preview = px.line(
                    df_sid_plot,
                    x="ds",
                    y="y",
                    title=f"Historical Values for {sid}",
                    labels={"y": "Value", "ds": "Timestamp"}
                )
               
                fig_preview.update_traces(line_color=preview_colors[idx % len(preview_colors)])
                st.plotly_chart(fig_preview, use_container_width=True)
                
    except Exception as e:
        st.warning(f"Unable to plot historical preview. Ensure timestamp column format is correct. Error: {str(e)}")

    st.markdown("---")

    col_param1, col_param2, col_param3 = st.columns(3)
    with col_param1:
        horizon = st.number_input("Forecast Horizon", min_value=1, max_value=500, value=100, step=1, format="%d")
    with col_param2:
        freq = st.selectbox("Interval Frequency", ["15min", "30min", "1H", "1D", "7D", "30D", "365D"])
        
        FREQ_SEASON_MAP = {
            "15min": 96,   
            "30min": 48,  
            "1H": 24,      
            "1D": 7,       
            "7D": 52,      
            "30D": 12,     
            "365D": 1      
        }
        season_length = FREQ_SEASON_MAP.get(freq, 24)

    with col_param3:
        
        # 1. Dictionary mapping raw codes to human-readable explanations
        ETS_MODEL_DESCRIPTIONS = {
            "ZZZ": "Auto-Select (Best Fit - Recommended)",
            "MMM": "Fully Multiplicative (Exponential Trends & Proportional Variance)",
            "AAA": "Fully Additive (Linear Trends & Constant Variance)",
            "MNN": "Multiplicative Error, No Trend, No Seasonality (Simple SES)",
            "ANN": "Additive Error, No Trend, No Seasonality (Simple SES)",
            "ZMN": "Auto Error with Multiplicative Trend, No Seasonality"
        }

        # 2. Selectbox using format_func to clean the dropdown options
        model_type = st.selectbox(
            "AutoETS Model Type",
            options=list(ETS_MODEL_DESCRIPTIONS.keys()),
            index=0,
            format_func=lambda x: f"{x} - {ETS_MODEL_DESCRIPTIONS[x]}",
            help="ETS models represent Error, Trend, and Seasonality configurations. 'A' stands for Additive, 'M' for Multiplicative, and 'Z' for Auto-Selection."
        )


    st.markdown("---")

    if st.button("Generate Forecasts", type="primary", use_container_width=True):
        with st.spinner("Processing forecasting pipeline..."):
            df_mapped = df_raw.copy()
            if id_col == "Single Series (No ID Column)":
                df_mapped["unique_id"] = "Series_1"
            else:
                df_mapped.rename(columns={id_col: "unique_id"}, inplace=True)
                
            df_mapped.rename(columns={date_col: "ds", val_col: "y"}, inplace=True)
            
            try:
                df_mapped = df_mapped[["unique_id", "ds", "y"]]
            except KeyError as ke:
                st.error(f"Column Mapping Error: {str(ke)}")
                st.write("**Columns in your CSV after rename step:**", list(df_mapped.columns))
                st.write(f"**Your mappings**: Date Column = `{date_col}`, ID Column = `{id_col}`, Value Column = `{val_col}`")
                st.stop()

            csv_buffer = df_mapped.to_csv(index=False).encode("utf-8")
            # converts the DataFrame directly into raw bytes in memory.
            files = {"file": (uploaded_file.name, csv_buffer, "text/csv")}
            
            params = {
                "horizon": horizon,
                "freq": freq,
                "season_length": season_length,
                "model_type": model_type
            }

            try:
                response = requests.post(BACKEND_URL, files=files, params=params)
                
                if response.status_code != 200:
                    st.error(f"API Error ({response.status_code}): {response.json().get('detail')}")
                    st.stop()

                st.session_state["payload"] = response.json()

            except Exception as e:
                st.error(f"Failed to connect to backend forecasting service. Error: {str(e)}")

    if "payload" in st.session_state:
        payload = st.session_state["payload"]

        if payload["warnings"]:
            st.warning("Data Quality Warnings:\n" + "\n".join([f"- {w}" for w in payload["warnings"]]))

        st.subheader("Model Evaluation Metrics")
        metrics = payload["metrics"]
        col_ets, col_base = st.columns(2)

        with col_ets:
            st.metric(
                label="AutoETS Model Accuracy",
                value=f"{metrics['auto_ets']['accuracy']:.2f}%",
                delta=f"MAE: {metrics['auto_ets']['mae']:.2f}"
            )
        with col_base:
            st.metric(
                label="Naive Baseline Accuracy",
                value=f"{metrics['baseline']['accuracy']:.2f}%",
                delta=f"MAE: {metrics['baseline']['mae']:.2f}",
                delta_color="inverse"
            )

        st.subheader("Gateway Performance & Forecast Analysis")
        forecast_df = pd.DataFrame(payload["forecasts"])
        val_df = pd.DataFrame(payload["val_predictions"])
        
        series_ids = sorted(forecast_df["unique_id"].unique())
        tabs = st.tabs([f"Series: {sid}" for sid in series_ids])
        colors = ["#1f77b4", "#2ca02c", "#d62728", "#9467bd", "#ff7f0e", "#8c564b"]

        for idx, (tab, sid) in enumerate(zip(tabs, series_ids)):
            with tab:
                col_val, col_fore = st.columns(2)
                
                with col_val:
                    st.write("**Validation Evaluation**")
                    df_val_sid = val_df[val_df["unique_id"] == sid]

                    fig_val = px.line(
                        df_val_sid,
                        x="ds",
                        y=["y", "AutoETS", "Naive"],
                        title=f"Validation Alignment for {sid}",
                        labels={"value": "Volume", "ds": "Timestamp", "variable": "Model"}
                    )
                    
                    color_discrete_map = {"y": "#F70C0C", "AutoETS": "#2ca02c", "Naive": "#1920e1"}
                    for trace in fig_val.data:
                        trace.line.color = color_discrete_map.get(trace.name, "#1f77b4")
                        if trace.name == "y":
                            trace.name = "Actual (y)"
                        elif trace.name == "AutoETS":
                            trace.line.dash = "dash"
                    
                    st.plotly_chart(fig_val, use_container_width=True)
                    
                with col_fore:
                    st.write("**Future Forecast (Horizon Projection)**")
                    df_sid = forecast_df[forecast_df["unique_id"] == sid]
                    
                    fig_fore = px.line(
                        df_sid,
                        x="datetime",
                        y="forecast",
                        title=f"Predicted Future Volume for {sid}",
                        labels={"datetime": "Timestamp", "forecast": "Attempts"}
                    )
                    
                    line_color = colors[idx % len(colors)]
                    fig_fore.update_traces(line_color=line_color)
                    st.plotly_chart(fig_fore, use_container_width=True)

        st.markdown("---")
        download_df = forecast_df.copy()
        download_df.rename(columns={
            "unique_id": id_col,
            "datetime": date_col,
            "forecast": val_col
        }, inplace=True)
        
        csv_data = download_df.to_csv(index=False)
        st.download_button(
            label="Download Predictions CSV",
            data=csv_data,
            file_name="time_series_predictions.csv",
            mime="text/csv",
            type="primary"
        )
else:
    st.info("Please upload a CSV file and map the columns to execute the forecasting pipeline.")
