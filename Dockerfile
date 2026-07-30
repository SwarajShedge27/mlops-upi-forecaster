FROM python:3.11-slim

# Python runtime settings:
# - PYTHONUNBUFFERED=1: Sends Python stdout/stderr directly to the terminal
#   without buffering, allowing logs to appear immediately (useful for Docker logs).
# - PYTHONDONTWRITEBYTECODE=1: Prevents Python from generating .pyc bytecode
#   files, reducing unnecessary file creation inside the container.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY api.py app.py ./

EXPOSE 8000 8501

CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port 8000 & streamlit run app.py --server.port 8501 --server.address 0.0.0.0"]
