import subprocess
import re
import json

def sanitize_namespace(namespace: str) -> str:
    if not namespace:
        return "default"
    sanitized = re.sub(r"[^a-z0-9-]", "", namespace.lower().strip())
    return sanitized if sanitized else "default"

def run_kubectl_command(args: list[str], timeout: int = 5) -> dict:
    try:
       
        result = subprocess.run(
            ["kubectl"] + args,
            capture_output=True,
            text=True,
            shell=False,
            timeout=timeout
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip()
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Error: Command timed out after {timeout} seconds. Is your Kubernetes cluster responsive?"
        }
    except FileNotFoundError:
        return {
            "success": False,
            "stdout": "",
            "stderr": "Error: 'kubectl' command-line tool not found in host PATH environment."
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"System error occurred: {str(e)}"
        }

def get_namespaces() -> list[str]:
   
    res = run_kubectl_command(["get", "namespaces", "-o", "jsonpath={.items[*].metadata.name}"])
    if res["success"] and res["stdout"]:
        return res["stdout"].split()
    return ["default", "my-prj", "project"]

def get_pod_names(namespace: str) -> list[str]:
    
    res = run_kubectl_command(["get", "pods", "-n", sanitize_namespace(namespace), "-o", "jsonpath={.items[*].metadata.name}"])
    if res["success"] and res["stdout"]:
        return res["stdout"].split()
    return []

def get_deployment_names(namespace: str) -> list[str]:
    res = run_kubectl_command(["get", "deployments", "-n", sanitize_namespace(namespace), "-o", "jsonpath={.items[*].metadata.name}"])
    return res["stdout"].split() if res["success"] and res["stdout"] else []

#JSONPath is a query language used to extract specific values from a JSON document.
# .items[*].metadata.name extracts the name of every deployment returned by kubectl.

def get_service_names(namespace: str) -> list[str]:
    res = run_kubectl_command(["get", "services", "-n", sanitize_namespace(namespace), "-o", "jsonpath={.items[*].metadata.name}"])
    return res["stdout"].split() if res["success"] and res["stdout"] else []

def check_cluster_connection() -> dict:
    
    res = run_kubectl_command(["cluster-info"], timeout=3)
    return res

