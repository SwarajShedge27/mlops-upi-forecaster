# MLOps UPI Time-Series Forecaster & Kubernetes GitOps Portal

A production-grade MLOps platform that combines a **Generic Time-Series Forecasting Pipeline** (powered by Nixtla's `StatsForecast`) with an **AI-driven Kubernetes GitOps Manifest Portal** (powered by a local Llama 3.2 engine).

---

## 📂 Project Architecture

```text
MLOps-Project/
├── api.py                      # FastAPI Backend Server (Hosts forecasting routes)
├── app.py                      # Streamlit Frontend Dashboard (Data Upload, Mapping, & Plotting)
├── Dockerfile                  # Docker unified container configurations
├── requirements.txt            # Python dependencies (StatsForecast, Streamlit, etc.)
│
├── src/                        # Machine Learning Pipeline Core Modules
│   ├── ingestion.py            # CSV schema checking and mixed date parsing
│   ├── preprocessing.py        # Fixed-frequency date spacing alignment
│   ├── ts_preprocessing.py     # Outlier cleanups using iterative rolling 3-sigma boundaries
│   ├── split.py                # Chronological train-validation splitter
│   ├── train.py                # AutoETS & Naive model fitting manager
│   ├── evaluate.py             # Performance evaluation (RMSE, MAE, WMAPE)
│   └── predict.py              # Dynamic future forecast projections
│
└── k8s/                        # Kubernetes Management Console & AI Portal
    ├── config.json             # Currently active deployment settings profile
    ├── k8s_config.py           # Pydantic schemas, validation rules, and LLM prompt
    ├── kubectl_helper.py       # Subprocess wrapper for local kubectl CLI executions
    ├── generate_k8s.py         # Compiles settings into Jinja2 Kubernetes templates
    ├── llm_frontend.py         # Streamlit chat portal, log streamer, & cluster status
    ├── templates/              # Jinja2 templates (deployment, service, ingress, configmap)
    └── build/                  # Final generated manifest YAMLs applied to the cluster
```

---

## 📊 Feature 1: Time-Series Forecasting Pipeline

The forecasting pipeline is fully generic and accepts any category-based sequential data (e.g. transaction counts, telemetry, volume indexes) mapping them dynamically in memory.

### **Technical Capabilities**
* **Rolling 3-Sigma Outlier Cleaning**: Computes rolling standard deviations ($\sigma$) and means ($\mu$) grouped by time buckets over 3 iterations to identify, remove, and interpolate telemetry spikes.
* **Frequency Rescaling & Alignment**: Automatically spaces irregular datetimes into rigid fixed gaps (like monthly boundaries) so StatsForecast matrix engines compile without errors.
* **Chronological Splits**: Isolates final 10% blocks for out-of-sample validation to prevent data leakage.
* **AutoETS & Naive fitting**: Trains error-trend-seasonal state-space models in parallel across multi-core systems, scoring performance via WMAPE, MAE, and RMSE.
* **Streamlit CSV Schema Mapping**: Users map local headers (e.g., `Date`, `Total_Amount`, `Series_ID`) to standard labels (`ds`, `y`, `unique_id`) on the client side, keeping database layouts unchanged.

---

## ☸️ Feature 2: Kubernetes GitOps AI Portal

An interactive terminal where users apply deployment configurations using conversational English prompts, compiled and executed on a local Kubernetes cluster.

### **Technical Capabilities**
* **Local LLM Extraction**: Routes prompt modifications to a local **Ollama** server running **Llama 3.2 (3B)** to translate text changes into configuration keys.
* **Double-Pass Validation Guards**:
  * **Pass 1 (Pre-LLM)**: Validates intent keywords and filters word-numbers (like `"three"` $\to$ `3`).
  * **Pass 2 (Post-LLM)**: Standardizes CPU cores, lowercase memory suffixes (e.g. `256mib` $\to$ `256Mi`), and trailing sentence punctuation.
* **End-State Pydantic Checks**: Validates configuration states using Pydantic, enforcing cross-field logic boundaries (e.g., CPU/Memory limit values cannot be less than requests).
* **Live Cluster Dashboard**: Streams container lifecycle statuses, restarts, pods metadata, live tail logs, and executes resource inspections (`kubectl describe`).

---

## 🚀 Getting Started

### **Prerequisites**
* Python 3.10+
* Docker Desktop (with Kubernetes enabled) or a local Minikube cluster
* [Ollama](https://ollama.com/) running locally with Llama 3.2:
  ```bash
  ollama pull llama3.2
  ```

### **1. Installation**
Clone this repository, create a virtual environment, and install dependencies:
```bash
python -m venv myenv
source myenv/bin/activate  # On Windows: myenv\Scripts\activate
pip install -r requirements.txt
```

### **2. Running the Forecasting Dashboard**
Start the FastAPI backend server:
```bash
python -m uvicorn api:app --reload --port 8000
```
In a new terminal window, start the Streamlit UI:
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

### **3. Running the Kubernetes GitOps Portal**
Start the Streamlit AI Dashboard:
```bash
streamlit run k8s/llm_frontend.py --server.port 8502
```
Open your browser at `http://localhost:8502`.
