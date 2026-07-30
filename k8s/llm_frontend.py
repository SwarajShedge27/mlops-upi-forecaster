import json
import sys
from pathlib import Path
import streamlit as st
import requests
import re

from k8s_config import (
    K8S_DIR, CONFIG_PATH, OLLAMA_API_URL, DEFAULT_CONFIG, 
    K8sConfigUpdate, KEY_ALIASES, SYSTEM_INSTRUCTION, load_current_config,
    has_modification_intent, has_valid_parameters
)
from kubectl_helper import (
    run_kubectl_command, sanitize_namespace, get_namespaces, 
    get_pod_names, get_deployment_names, get_service_names, check_cluster_connection
)

sys.path.append(str(K8S_DIR))
from generate_k8s import generate_manifests

st.set_page_config(page_title="K8s AI Configurator", layout="wide")

st.sidebar.title("Navigation")
page = st.sidebar.radio("Select Workspace:", ["AI Manifest Configurator", "Cluster Management Console"])
st.sidebar.markdown("---")
if st.sidebar.button("Refresh Dashboard", type="secondary", use_container_width=True):
    st.rerun()

if page == "AI Manifest Configurator":
    st.title("Local Kubernetes AI Configuration UI")
    st.write("Submit deployment updates in English. The local Llama 3.2 model will modify configurations and compile manifests.")
    st.markdown("---")

    current_config = load_current_config()
    col_config, col_chat = st.columns([1, 2])

    with col_config:
        st.write("**Current Active Config Profile**")
        st.json(current_config)
        
        if st.button("Reset to Baseline Defaults", type="secondary", use_container_width=True):
            with open(CONFIG_PATH, "w") as f:
                json.dump(DEFAULT_CONFIG, f, indent=2)
            generate_manifests()
            st.success("Config reset to defaults!")
            st.rerun()

    with col_chat:
        st.write("**Describe Manifest Changes**")
        user_prompt = st.text_input("Enter deployment modifications:", placeholder="e.g. scale deployment to 5 replicas and change namespace to testing", key="user_prompt_input")

        if st.button("Apply Changes", type="primary", use_container_width=True):
            if not user_prompt:
                st.warning("Please describe your changes first.")
            else:
                
                if not has_modification_intent(user_prompt):
                    st.error("Invalid Command: No modification intent detected.")
                    st.warning("Please specify an action (e.g. 'scale replicas to 3', 'change namespace to dev').")
                    st.stop()
                    
                if not has_valid_parameters(user_prompt):
                    st.error("Invalid Command: Unrecognized parameter or missing value.")
                    st.warning("Please make sure you are changing a valid parameter and providing a value (e.g., 'replicas to 5', 'cpu to 250m').")
                    st.stop()
                    
                payload = {
                    "model": "llama3.2",
                    "messages": [
                        {"role": "system", "content": SYSTEM_INSTRUCTION},
                        {"role": "user", "content": f"Apply these changes: {user_prompt}"}
                    ],
                    "stream": False,
                    "format": "json"
                }

                with st.spinner("Processing request with local Llama..."):
                    try:
                        response = requests.post(OLLAMA_API_URL, json=payload, timeout=120)
                        if response.status_code != 200:
                            st.error(f"Error: {response.text}")
                        else:
                            content_str = response.json()["message"]["content"]
                            llm_updates = json.loads(content_str)
                            
                            prompt_lower = user_prompt.lower()
                
                            verified_updates = {}
                            for key, value in llm_updates.items():
                                aliases = KEY_ALIASES.get(key, [key])
                                if any(alias in prompt_lower for alias in aliases):
                                    verified_updates[key] = value

                            # --- CASE CAPITALIZATION & PUNCTUATION NORMALIZATION ---
                            for key, value in list(verified_updates.items()):
                                if isinstance(value, str):
                                    
                                    cleaned_val = value.replace(" ", "").rstrip(".,")
                                    
                                    if key in ["replicas", "container_port", "service_port"]:
                                        try:
                                            verified_updates[key] = int(cleaned_val)
                                        except ValueError:
                                            pass
                                            
                                    elif key in ["memory_request", "memory_limit"]:
                                        match = re.match(r"^(\d+)([a-zA-Z]+)?$", cleaned_val)
                                        if match:
                                            num = match.group(1)
                                            unit = match.group(2)
                                            if unit:
                                                unit_lower = unit.lower()
                                                if "g" in unit_lower:
                                                    cleaned_val = f"{num}Gi"
                                                elif "m" in unit_lower:
                                                    cleaned_val = f"{num}Mi"
                                                elif "k" in unit_lower:
                                                    cleaned_val = f"{num}Ki"
                                                elif "t" in unit_lower:
                                                    cleaned_val = f"{num}Ti"
                                            verified_updates[key] = cleaned_val
                                            
                                    elif key in ["cpu_request", "cpu_limit"]:
                                        cleaned_val = re.sub(r"(cores|core|cpus|cpu)", "", cleaned_val, flags=re.IGNORECASE)
                                        if cleaned_val.endswith("M"):
                                            cleaned_val = cleaned_val[:-1] + "m"
                                        verified_updates[key] = cleaned_val
                                    else:
                                        verified_updates[key] = cleaned_val

                            if "service_type" in verified_updates and isinstance(verified_updates["service_type"], str):
                                s_type_lower = verified_updates["service_type"].lower().strip()
                                type_mapping = {
                                    "clusterip": "ClusterIP",
                                    "nodeport": "NodePort",
                                    "loadbalancer": "LoadBalancer"
                                }
                                if s_type_lower in type_mapping:
                                    verified_updates["service_type"] = type_mapping[s_type_lower]

                            if "log_level" in verified_updates and isinstance(verified_updates["log_level"], str):
                                verified_updates["log_level"] = verified_updates["log_level"].upper().strip()

                            if not verified_updates:
                                st.error("Unrecognized or invalid parameter name.")
                                st.warning("No valid configuration keys (replicas, namespace, image, cpu, memory, port) were matched in your request.")
                                st.stop()

                            try:
                                validated_model = K8sConfigUpdate(**verified_updates)
                                validated_updates = validated_model.model_dump(exclude_unset=True)
                            except Exception as val_err:
                                st.error("AI Validation Error: Invalid parameter types.")
                                st.code(str(val_err), language="text")
                                st.stop()  
                            
                            current_config.update(validated_updates)
                            with open(CONFIG_PATH, "w") as f:
                                json.dump(current_config, f, indent=2)

                            generate_manifests()
                            st.success("Kubernetes Manifests successfully generated!")
                            st.write("**Extracted Changes Applied:**")
                            st.json(verified_updates)
                            st.rerun()

                    except requests.exceptions.ConnectionError:
                        st.error("Connection failed. Ensure Ollama server is running locally.")
                    except Exception as e:
                        st.error(f"Processing failed: {str(e)}")
       
        st.write("")  
        with st.expander("View Allowed Configurations & Prompt Examples", expanded=False):
            st.markdown("""
            You can modify the following configuration values using natural English:
            
            | Configuration Key | Allowed Formats / Values | Example Prompt |
            | :--- | :--- | :--- |
            | **Replicas** | Numbers between 1 and 49 | *“scale deployment to 5 replicas”* |
            | **Namespace** | Standard string text | *“change namespace to staging”* |
            | **Service Type** | `ClusterIP`, `NodePort`, `LoadBalancer` | *“set service type to NodePort”* |
            | **Ports** | Integer values (1 - 65535) | *“set container port to 8080 and service port to 80”* |
            | **Memory** | Suffixes: `Mi`, `Gi`, `Ki` | *“set memory limit to 512Mi and memory request to 256Mi”* |
            | **CPU** | Suffixes: `m` (millicores) or decimal cores | *“set cpu request to 250m and cpu limit to 0.5 cores”* |
            | **Log Level** | `INFO`, `DEBUG`, `WARNING` | *“change log level to warning”* |
            | **Default Frequency**| Intervals like `15min`, `1H`, `1D`, `30D` | *“set default freq to 30D”* |
            | **Domain Name** | Domain address formats | *“change domain name to forecaster.nip.io”* |
            
            
            """)


    st.markdown("---")
    st.subheader("Generated Manifest Previews")
    BUILD_DIR = K8S_DIR / "build"
    for file_name in ["deployment.yaml", "service.yaml", "configmap.yaml", "ingress.yaml"]:
        file_path = BUILD_DIR / file_name
        if file_path.exists():
            with st.expander(f"{file_name}", expanded=False):
                with open(file_path, "r") as f:
                    st.code(f.read(), language="yaml")

elif page == "Cluster Management Console":
    st.title("Kubernetes Cluster Management Console")
    st.write("Apply, monitor, and tear down deployment resources in your local cluster.")
    st.markdown("---")

    conn_check = check_cluster_connection()
    if not conn_check["success"]:
        st.error("**Kubernetes Cluster Unreachable!**")
        st.warning("Please ensure Docker Desktop / Kubernetes cluster daemon is running locally.")
        st.code(conn_check["stderr"], language="text")
        st.stop() 

    all_namespaces = get_namespaces()
    current_config = load_current_config()
    default_ns = sanitize_namespace(current_config.get("namespace", "default"))
    if default_ns not in all_namespaces:
        all_namespaces.append(default_ns)
        
    selected_ns = st.selectbox("Select Target Namespace:", all_namespaces, index=all_namespaces.index(default_ns) if default_ns in all_namespaces else 0)
    target_ns = sanitize_namespace(selected_ns)
    BUILD_DIR = K8S_DIR / "build"

    st.info(f"**Active Targets** | Target Directory: `{BUILD_DIR.name}/` | Namespace: `{target_ns}`")

    col_ops, col_danger = st.columns(2)
    with col_ops:
        st.subheader("Deploy Manifests")
        if st.button("Apply Manifests (kubectl apply)", type="primary", use_container_width=True):
            with st.spinner("Applying manifests..."):
                res = run_kubectl_command(["apply", "-f", str(BUILD_DIR), "-n", target_ns])
                if res["success"]:
                    st.success("Deployment completed successfully!")
                    st.code(res["stdout"], language="text")
                else:
                    st.error("Deployment failed!")
                    st.code(res["stderr"], language="text")

    with col_danger:
        st.subheader("Tear Down Resources")
        confirm_delete = st.checkbox("Confirm deletion of all workspace resources")
        if st.button("Delete Manifests (kubectl delete)", type="secondary", use_container_width=True, disabled=not confirm_delete):
            with st.spinner("Deleting manifests..."):
                res = run_kubectl_command(["delete", "-f", str(BUILD_DIR), "-n", target_ns])
                if res["success"]:
                    st.success("Resources successfully deleted!")
                    st.code(res["stdout"], language="text")
                else:
                    st.error("Deletion failed!")
                    st.code(res["stderr"], language="text")

    st.markdown("---")
    st.subheader("Active Deployments Status")
    dep_res = run_kubectl_command(["get", "deployment", "-n", target_ns, "-o", "json"])
    if dep_res["success"] and dep_res["stdout"]:
        try:
            dep_data = json.loads(dep_res["stdout"])
            items = dep_data.get("items", []) if dep_data.get("kind") == "List" else [dep_data]
            if not items:
                st.info(f"No deployments found in namespace `{target_ns}`.")
            else:
                for dep in items:
                    st.write(f"**Deployment:** `{dep['metadata']['name']}`")
                    m1, m2, m3, m4 = st.columns(4)
                    status = dep.get("status", {})
                    m1.metric("Desired Replicas", dep["spec"].get("replicas", 0))
                    m2.metric("Ready Replicas", status.get("readyReplicas", 0))
                    m3.metric("Available Replicas", status.get("availableReplicas", 0))
                    m4.metric("Up-to-Date", status.get("updatedReplicas", 0))
        except Exception as parse_err:
            st.error(f"Error parsing deployment JSON: {str(parse_err)}")

    st.markdown("---")
    st.subheader("Active Pods Details")
    pod_res = run_kubectl_command(["get", "pods", "-n", target_ns, "-o", "json"])
    if pod_res["success"] and pod_res["stdout"]:
        try:
            pods = json.loads(pod_res["stdout"]).get("items", [])
            if not pods:
                st.info(f"No pods running in namespace `{target_ns}`.")
            else:
                table_rows = []
                for pod in pods:
                    c_statuses = pod.get("status", {}).get("containerStatuses", [])
                    table_rows.append({
                        "Pod Name": pod.get("metadata", {}).get("name", "Unknown"),
                        "Status": pod.get("status", {}).get("phase", "Unknown"),
                        "Ready": f"{sum(1 for c in c_statuses if c.get('ready', False))}/{len(c_statuses)}",
                        "Restarts": sum(c.get("restartCount", 0) for c in c_statuses),
                        "Node": pod.get("spec", {}).get("nodeName", "N/A"),
                        "IP Address": pod.get("status", {}).get("podIP", "N/A"),
                        "Image": c_statuses[0].get("image", "N/A") if c_statuses else "N/A"
                    })
                st.dataframe(table_rows, use_container_width=True)
        except Exception as parse_err:
            st.error(f"Error parsing Pod JSON: {str(parse_err)}")

    st.markdown("---")
    st.subheader("Live Pod Logs Viewer")
    active_pods = get_pod_names(target_ns)
    if not active_pods:
        st.info(f"No active pods found in namespace `{target_ns}` to view logs.")
    else:
        l_col1, l_col2, l_col3 = st.columns([2, 1, 1])
        with l_col1:
            selected_pod = st.selectbox("Select Pod:", active_pods)
        with l_col2:
            tail_lines = st.number_input("Tail Lines:", min_value=10, max_value=500, value=30, step=10)
        with l_col3:
            st.write("")
            st.write("")
            st.button("Refresh Logs", use_container_width=True)
            
        if selected_pod:
            log_res = run_kubectl_command(["logs", selected_pod, "-n", target_ns, f"--tail={tail_lines}"])
            if log_res["success"]:
                if log_res["stdout"]:
                    st.code(log_res["stdout"], language="text")
                else:
                    st.info("Log stream is currently empty.")
            else:
                st.error("Failed to retrieve logs:")
                st.code(log_res["stderr"], language="text")

    st.markdown("---")
    st.subheader("Resource Inspector (kubectl describe)")
    d_col1, d_col2 = st.columns([1, 2])
    with d_col1:
        res_kind = st.radio("Resource Type:", ["Pod", "Deployment", "Service"], horizontal=True)
    
    if res_kind == "Pod":
        available_targets = get_pod_names(target_ns)
    elif res_kind == "Deployment":
        available_targets = get_deployment_names(target_ns)
    else:
        available_targets = get_service_names(target_ns)

    with d_col2:
        if not available_targets:
            st.info(f"No active {res_kind} resources found in namespace `{target_ns}`.")
            selected_target = None
        else:
            selected_target = st.selectbox(f"Select {res_kind} Target:", available_targets)

    if selected_target:
        if st.button(f"Describe {res_kind}: {selected_target}", type="primary"):
            with st.spinner("Running describe..."):
                desc_res = run_kubectl_command(["describe", res_kind.lower(), selected_target, "-n", target_ns])
                if desc_res["success"]:
                    st.code(desc_res["stdout"], language="text")
                else:
                    st.error("Failed to describe resource:")
                    st.code(desc_res["stderr"], language="text")