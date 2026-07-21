import json
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional, Literal

K8S_DIR = Path(__file__).resolve().parent
CONFIG_PATH = K8S_DIR / "config.json"
OLLAMA_API_URL = "http://localhost:11434/api/chat"

DEFAULT_CONFIG = {
    "app_name": "upi-forecaster",
    "namespace": "my-prj",
    "replicas": 3,
    "image_name": "upi-dynamic-api:v1",
    "container_port": 8000,
    "service_port": 80,
    "service_type": "ClusterIP",
    "cpu_request": "250m",
    "memory_request": "256Mi",
    "cpu_limit": "500m",
    "memory_limit": "512Mi",
    "log_level": "INFO",
    "default_freq": "15min",
    "domain_name": "api.forecaster.local"
}

class K8sConfigUpdate(BaseModel):
    app_name: Optional[str] = None
    namespace: Optional[str] = None
    replicas: Optional[int] = Field(None, ge=1, lt=50, description="Must be >= 1")
    image_name: Optional[str] = None
    container_port: Optional[int] = Field(None, ge=1, le=65535)
    service_port: Optional[int] = Field(None, ge=1, le=65535)
    service_type: Optional[Literal["ClusterIP", "NodePort", "LoadBalancer"]] = None
    cpu_request: Optional[str] = Field(None, pattern=r"^\d+(\.\d+)?m?$")
    cpu_limit: Optional[str] = Field(None, pattern=r"^\d+(\.\d+)?m?$")
    memory_request: Optional[str] = Field(None, pattern=r"^\d+(Ki|Mi|Gi|Ti|K|M|G|T)?$")
    memory_limit: Optional[str] = Field(None, pattern=r"^\d+(Ki|Mi|Gi|Ti|K|M|G|T)?$")
    log_level: Optional[Literal["INFO", "DEBUG", "WARNING"]] = None
    default_freq: Optional[str] = Field(None, pattern=r"^\d+(min|H|D|W|M)$")
    domain_name: Optional[str] = Field(None, pattern=r"^[a-z0-9.-]+$")

KEY_ALIASES = {
    "app_name": ["app_name", "app", "name"],
    "namespace": ["namespace", "ns"],
    "replicas": ["replicas", "replica", "pods", "instances", "count"],
    "image_name": ["image_name", "image", "img"],
    "container_port": ["container_port", "port"],
    "service_port": ["service_port", "svc_port"],
    "service_type": ["service_type", "type"],
    "cpu_request": ["cpu_request", "cpu_req", "cpu"],
    "memory_request": ["memory_request", "memory_req", "mem_req", "memory"],
    "cpu_limit": ["cpu_limit", "cpu_lim"],
    "memory_limit": ["memory_limit", "mem_limit", "mem"],
    "log_level": ["log_level", "log"],
    "default_freq": ["default_freq", "freq", "frequency"],
    "domain_name": ["domain_name", "domain", "host"]
}

SYSTEM_INSTRUCTION = """
You are a Kubernetes deployment assistant. Read the user's change request.
Output a JSON dictionary containing ONLY the key-value pairs that the user explicitly wants to change.

Available Keys:
- app_name (string)
- namespace (string)
- replicas (integer)
- image_name (string)
- container_port (integer)
- service_port (integer)
- service_type (string: ClusterIP, NodePort, or LoadBalancer)
- cpu_request (string)
- memory_request (string)
- cpu_limit (string)
- memory_limit (string)
- log_level (string)
- default_freq (string)
- domain_name (string)

RULES FOR KEY MATCHING:
1. ALLOW COMMON ALIASES AND SHORTHAND:
   - "img", "image", "img name" -> "image_name"
   - "cpu", "cpu req" -> "cpu_request"
   - "mem", "memory limit" -> "memory_limit"
   - "port" -> "container_port"
   - "replica", "pods count" -> "replicas"

2. REJECT GIBBERISH:
   - If the input is completely unrecognized or cannot be confidently matched to an available key, output: {}
"""

def load_current_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()
