import os
import streamlit as st
import pandas as pd
import requests
import plotly.express as px

BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000/forecast/json")

st.set_page_config(page_title="Forecaster", layout="wide")

st.title("UPI Transaction Outage & Forecasting System")
st.write("Upload historical gateway logs to evaluate model accuracy and generate future forecasts.")
st.markdown("---")

col_upload, col_param1, col_param2 = st.columns([2, 1, 1])

with col_upload:
    uploaded_file = st.file_uploader("Upload Historical Transaction CSV", type=["csv"])

with col_param1:
    horizon = st.number_input(
        "Forecast Horizon", 
        min_value=1, 
        max_value=500,  
        format="%d"
    )

with col_param2:
    freq = st.selectbox("Interval Frequency", ["15min", "30min", "1H"])
    season_length = 96 if freq == "15min" else (48 if freq == "30min" else 24)
# using this because seasonal length depends on freq .

if uploaded_file is not None:
    st.markdown("---")
    
    st.subheader("Ingested Dataset Preview")
    df_raw = pd.read_csv(uploaded_file)
    st.dataframe(df_raw.head(5), use_container_width=True)

    if st.button("Generate Forecasts", type="primary"):
        with st.spinner("Processing pipeline..."):
            uploaded_file.seek(0)
            files = {"file": (uploaded_file.name, uploaded_file.read(), "text/csv")}
            params = {
                "horizon": horizon,
                "freq": freq,
                "season_length": season_length
            }

            try:
                response = requests.post(BACKEND_URL, files=files, params=params)
                
                if response.status_code != 200:
                    st.error(f"API Error ({response.status_code}): {response.json().get('detail')}")
                    st.stop()

                # Save payload to persistent session_state memory
                st.session_state["payload"] = response.json()

            except Exception as e:
                st.error(f"Failed to connect to backend forecasting service. Error: {str(e)}")

    # Render results whenever payload is present in session_state
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
        
        gateways = sorted(forecast_df["PG_NAME"].unique())
        tabs = st.tabs([f"Gateway: {gw}" for gw in gateways])

        for tab, gw in zip(tabs, gateways):
            with tab:
                col_val, col_fore = st.columns(2)
                
                with col_val:
                    st.write("**Validation Evaluation (Hold-out Fit)**")
                    df_val_gw = val_df[val_df["PG_NAME"] == gw]

                    fig_val = px.line(
                        df_val_gw,
                        x="ds",
                        y=["y", "AutoETS", "Naive"],
                        title=f"Validation Alignment for {gw}",
                        labels={"value": "Attempts", "ds": "Timestamp", "variable": "Model"}
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
                    df_gw = forecast_df[forecast_df["PG_NAME"] == gw]
                    
                    fig_fore = px.line(
                        df_gw,
                        x="datetime",
                        y="forecast",
                        title=f"Predicted Future Volume for {gw}",
                        labels={"datetime": "Timestamp", "forecast": "Attempts"}
                    )
                    color_map = {"CITIBANKUPI": "#1f77b4", "PAYTMPGUPI": "#2ca02c", "YESBANKUPI": "#d62728"}
                    fig_fore.update_traces(line_color=color_map.get(gw, "#1f77b4"))
                    st.plotly_chart(fig_fore, use_container_width=True)

        st.markdown("---")
        csv_data = forecast_df.to_csv(index=False)
        st.download_button(
            label="Download Predictions CSV",
            data=csv_data,
            file_name="upi_future_forecasts.csv",
            mime="text/csv",
            type="primary"
        )

else:
    st.info("Please upload a CSV file to execute the forecasting pipeline.")
