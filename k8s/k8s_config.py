import json
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional, Literal
import re

K8S_DIR = Path(__file__).resolve().parent
CONFIG_PATH = K8S_DIR / "config.json"
OLLAMA_API_URL = "http://localhost:11434/api/chat"

DEFAULT_CONFIG = {
    "app_name": "upi-forecaster",
    "namespace": "project",
    "replicas": 3,
    "image_name": "upi-forecaster:v4",
    "container_port": 8000,
    "service_port": 80,
    "service_type": "ClusterIP",
    "cpu_request": "250m",
    "memory_request": "256Mi",
    "cpu_limit": "500m",
    "memory_limit": "512Mi",
    "log_level": "INFO",
    "default_freq": "15min",
    "domain_name": "127.0.0.1.nip.io"
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
    "app_name": ["app_name", "app", "name","app name"],
    "namespace": ["namespace", "ns","name space"],
    "replicas": ["replicas", "replica", "pods", "instances", "count"],
    "image_name": ["image_name", "image", "img","image name"],
    "container_port": ["container_port", "port","container port"],
    "service_port": ["service_port", "svc_port","service port"],
    "service_type": ["service_type", "type","service type"],
    "cpu_request": ["cpu_request", "cpu_req", "cpu","cpu request"],
    "memory_request": ["memory_request", "memory_req", "mem_req", "memory","memory request"],
    "cpu_limit": ["cpu_limit", "cpu_lim","cpu limit"],
    "memory_limit": ["memory_limit", "mem_limit", "mem","memory limit"],
    "log_level": ["log_level", "log","log level"],
    "default_freq": ["default_freq", "freq", "frequency","default freq"],
    "domain_name": ["domain_name", "domain", "host","domain name"]
}


SYSTEM_INSTRUCTION = """You are a strict Kubernetes configuration extractor.

Extract the requested updates from the user prompt and format them as a JSON object matching this schema:
- app_name: string
- namespace: string
- replicas: integer
- image_name: string
- container_port: integer
- service_port: integer
- service_type: "ClusterIP" | "NodePort" | "LoadBalancer"
- cpu_request: string
- cpu_limit: string
- memory_request: string
- memory_limit: string
- log_level: "INFO" | "DEBUG" | "WARNING"
- default_freq: string
- domain_name: string

Rules:
1. Return ONLY the JSON object. Do not include markdown code blocks or explanations.
2. Extract ONLY the fields explicitly mentioned in the user prompt. Do not invent or include other fields.

Examples:
User: "scale deployment to 5 replicas"
Output: {"replicas": 5}

User: "change log_level to warning"
Output: {"log_level": "WARNING"}
"""

def load_current_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def has_modification_intent(prompt: str) -> bool:
    
    prompt_lower = prompt.lower().strip()
    
    intent_verbs = {
        "scale", "change", "update", "set", "modify", "increase", 
        "decrease", "reset", "make", "put", "use", "deploy", "apply"
    }
    
    transition_words = {"to", "is", "=", "become", "value","as"}
    words = set(prompt_lower.split())
    
    has_verb = not words.isdisjoint(intent_verbs)
    has_transition = not words.isdisjoint(transition_words)
    
    return has_verb or has_transition

def has_valid_parameters(prompt: str) -> bool:
   
    prompt_lower = prompt.lower().strip()
    
    matched_keys = []
    for key, aliases in KEY_ALIASES.items():
        if any(alias in prompt_lower for alias in aliases):
            matched_keys.append(key)
            
    if not matched_keys:
        return False
        
    for key in matched_keys:
        if key in ["replicas", "container_port", "service_port"]:
            if not any(word.isdigit() for word in prompt_lower.split() if re.search(r'\d+', word)):
                return False
        elif key in ["cpu_request", "cpu_limit"]:
            if not re.search(r'\d+m?', prompt_lower):
                return False
        elif key in ["memory_request", "memory_limit"]:
            if not re.search(r'\d+(mi|gi|ki|m|g|k)?', prompt_lower):
                return False
                
    return True
