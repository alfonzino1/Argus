"""
Configuration loader with environment variable support and validation.
Supports both YAML config files and .env environment variables.
"""
import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


def _get_env_bool(env_var: str, default: bool) -> bool:
    """Convert environment variable to boolean."""
    value = os.getenv(env_var)
    if value is None:
        return default
    return value.lower() in ('true', '1', 'yes', 'on')


def _get_env_int(env_var: str, default: int) -> int:
    """Convert environment variable to integer."""
    value = os.getenv(env_var)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_env_float(env_var: str, default: float) -> float:
    """Convert environment variable to float."""
    value = os.getenv(env_var)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _get_env_str(env_var: str, default: str) -> str:
    """Get environment variable as string."""
    return os.getenv(env_var, default)


def load_env_config() -> Dict[str, Any]:
    """Load configuration from environment variables."""
    config = {
        "app": {
            "name": _get_env_str("APP_NAME", "Real-Time Vision System"),
            "env": _get_env_str("APP_ENV", "development"),
            "debug": _get_env_bool("DEBUG", False),
            "log_level": _get_env_str("LOG_LEVEL", "INFO"),
        },
        "dashboard": {
            "host": _get_env_str("DASHBOARD_HOST", "0.0.0.0"),
            "port": _get_env_int("DASHBOARD_PORT", 5050),
            "secret_key": _get_env_str("DASHBOARD_SECRET_KEY", "change-this-secret"),
            "username": _get_env_str("DASHBOARD_USERNAME", "admin"),
            "password": _get_env_str("DASHBOARD_PASSWORD", "changeme"),
            "session_timeout": _get_env_int("DASHBOARD_SESSION_TIMEOUT", 3600),
        },
        "source": {
            "type": _get_env_str("SOURCE_TYPE", "video"),
            "video_path": _get_env_str("SOURCE_VIDEO_PATH", "test_video.avi"),
            "camera_index": _get_env_int("SOURCE_CAMERA_INDEX", 0),
            "width": _get_env_int("SOURCE_WIDTH", 1280),
            "height": _get_env_int("SOURCE_HEIGHT", 720),
            "fps": _get_env_int("SOURCE_FPS", 60),
            "backend": _get_env_str("SOURCE_BACKEND", "CAP_ANY"),
            "reconnect_attempts": _get_env_int("SOURCE_RECONNECT_ATTEMPTS", 5),
            "reconnect_delay": _get_env_float("SOURCE_RECONNECT_DELAY", 2.0),
        },
        "detector": {
            "model_path": _get_env_str("DETECTOR_MODEL_PATH", "yolov8n.pt"),
            "confidence_threshold": _get_env_float("DETECTOR_CONFIDENCE_THRESHOLD", 0.5),
            "iou_threshold": _get_env_float("DETECTOR_IOU_THRESHOLD", 0.45),
            "device": _get_env_str("DETECTOR_DEVICE", None) or None,
            "img_size": _get_env_int("DETECTOR_IMG_SIZE", 640),
        },
        "tracker": {
            "type": _get_env_str("TRACKER_TYPE", "iou"),
            "max_lost_frames": _get_env_int("TRACKER_MAX_LOST_FRAMES", 30),
            "iou_threshold": _get_env_float("TRACKER_IOU_THRESHOLD", 0.3),
        },
        "pipeline": {
            "window_name": _get_env_str("PIPELINE_WINDOW_NAME", "Real-Time Vision System"),
            "show_fps": _get_env_bool("PIPELINE_SHOW_FPS", True),
        },
        "events": {
            "log_events": _get_env_bool("EVENTS_LOG_EVENTS", True),
        },
    }
    return config


def load_config(config_path: Optional[str] = None, use_env: bool = True) -> Dict[str, Any]:
    """
    Load configuration from YAML file and/or environment variables.
    
    Environment variables take precedence over YAML config values.
    
    Args:
        config_path: Path to YAML config file. If None, uses only env vars.
        use_env: Whether to merge environment variables (default: True)
    
    Returns:
        Merged configuration dictionary
    
    Raises:
        ConfigValidationError: If configuration validation fails
        FileNotFoundError: If config file not found
    """
    config = {}
    
    # Load from environment variables first
    if use_env:
        config = load_env_config()
    
    # Load from YAML file if provided
    if config_path:
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(path, 'r') as f:
            yaml_config = yaml.safe_load(f)
        
        # Merge YAML config with env config (env takes precedence)
        config = _deep_merge(yaml_config, config)
    
    # Validate configuration
    _validate_config(config)
    
    # Set defaults for missing sections
    config["pipeline"] = config.get("pipeline", {})
    config["tracker"] = config.get("tracker", {})
    config["events"] = config.get("events", {"log_events": True})
    
    return config


def _deep_merge(base: Dict, override: Dict) -> Dict:
    """Deep merge two dictionaries, with override taking precedence."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _validate_config(config: Dict[str, Any]) -> None:
    """
    Validate configuration values.
    
    Raises:
        ConfigValidationError: If validation fails
    """
    # Check required sections
    required_sections = ["source", "detector"]
    for section in required_sections:
        if section not in config:
            raise ConfigValidationError(f"Missing required config section: {section}")
    
    # Validate source section
    source = config["source"]
    source_type = source.get("type", "video")
    if source_type not in ["camera", "video"]:
        raise ConfigValidationError(f"Invalid source type: {source_type}. Must be 'camera' or 'video'")
    
    if source_type == "video" and not source.get("video_path"):
        raise ConfigValidationError("video_path is required when source type is 'video'")
    
    if source_type == "camera":
        if "camera_index" not in source:
            raise ConfigValidationError("camera_index is required when source type is 'camera'")
    
    # Validate detector thresholds
    detector = config["detector"]
    conf_thresh = detector.get("confidence_threshold", 0.5)
    iou_thresh = detector.get("iou_threshold", 0.45)
    
    if not 0 <= conf_thresh <= 1:
        raise ConfigValidationError(f"confidence_threshold must be between 0 and 1, got {conf_thresh}")
    
    if not 0 <= iou_thresh <= 1:
        raise ConfigValidationError(f"iou_threshold must be between 0 and 1, got {iou_thresh}")
    
    # Validate tracker type
    tracker = config.get("tracker", {})
    tracker_type = tracker.get("type", "iou")
    if tracker_type not in ["iou", "bytetrack"]:
        raise ConfigValidationError(f"Invalid tracker type: {tracker_type}. Must be 'iou' or 'bytetrack'")
    
    # Validate dashboard settings in production
    app_env = config.get("app", {}).get("env", "development")
    dashboard = config.get("dashboard", {})
    
    if app_env == "production":
        secret_key = dashboard.get("secret_key", "")
        if secret_key in ["change-this-secret", "changeme", ""]:
            raise ConfigValidationError(
                "DASHBOARD_SECRET_KEY must be set to a secure random value in production"
            )
        
        password = dashboard.get("password", "")
        if password in ["changeme", "admin", "password", ""]:
            raise ConfigValidationError(
                "DASHBOARD_PASSWORD must be changed from default in production"
            )
    
    # Validate log level
    log_level = config.get("app", {}).get("log_level", "INFO")
    valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if log_level not in valid_log_levels:
        raise ConfigValidationError(
            f"Invalid LOG_LEVEL: {log_level}. Must be one of {valid_log_levels}"
        )