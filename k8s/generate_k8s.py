import json
import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
BUILD_DIR = BASE_DIR / "build"
CONFIG_PATH = BASE_DIR / "config.json"

def generate_manifests():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Configuration file not found at: {CONFIG_PATH}")
    
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f) # saves all config in python dictionary 
    
    print(f"Loaded configuration for app: '{config.get('app_name')}'")

    # Setup Jinja2 Environment
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))

    # Ensure the destination build directory exists
    os.makedirs(BUILD_DIR, exist_ok=True)

    templates = [
        "deployment.yaml.j2",
        "service.yaml.j2",
        "configmap.yaml.j2",
        "ingress.yaml.j2"
    ]

    print("\nGenerating Kubernetes manifests...")
    # Loop, render, and save each manifest
    for template_name in templates:
        try:
            # Load template file from templates/
            template = env.get_template(template_name)
            
            # Render template in memory using configuration dictionary
            rendered_content = template.render(config)
            
            # Determine output name (remove .j2 extension)
            output_name = template_name.replace(".j2", "")
            output_path = BUILD_DIR / output_name
            
            # Write compiled content to build/ directory
            with open(output_path, "w") as out_file:
                out_file.write(rendered_content)
                
            print(f" -> Generated: {output_path.name}")
        except Exception as e:
            print(f"Error rendering {template_name}: {str(e)}")

    print("\nManifest generation completed successfully. Ready for deployment!")

if __name__ == "__main__":
    generate_manifests()
