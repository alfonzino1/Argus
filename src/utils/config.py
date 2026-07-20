"""
Configuration loader for YAML files.
"""
import yaml
from pathlib import Path
from typing import Any, Dict


def load_config(config_path: str) -> Dict[str, Any]:
    """Load and validate configuration from YAML file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(path, 'r') as f:
        config = yaml.safe_load(f)

    # Basic validation (we'll add more as project grows)
    required_sections = ["source", "detector"]
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required config section: {section}")

    # Set defaults for missing options
    config["pipeline"] = config.get("pipeline", {})
    config["tracker"] = config.get("tracker", {})

    return config