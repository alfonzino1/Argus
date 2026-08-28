"""
Tests for Real-Time Vision System configuration module.
"""
import os
import pytest
from pathlib import Path

from src.utils.config import (
    load_config,
    load_env_config,
    ConfigValidationError,
    _get_env_bool,
    _get_env_int,
    _get_env_float,
    _get_env_str,
)


class TestEnvHelpers:
    """Test environment variable helper functions."""
    
    def test_get_env_bool_true_values(self):
        """Test boolean conversion for true values."""
        os.environ['TEST_VAR'] = 'true'
        assert _get_env_bool('TEST_VAR', False) is True
        
        os.environ['TEST_VAR'] = '1'
        assert _get_env_bool('TEST_VAR', False) is True
        
        os.environ['TEST_VAR'] = 'yes'
        assert _get_env_bool('TEST_VAR', False) is True
        
        os.environ['TEST_VAR'] = 'on'
        assert _get_env_bool('TEST_VAR', False) is True
    
    def test_get_env_bool_false_values(self):
        """Test boolean conversion for false values."""
        os.environ['TEST_VAR'] = 'false'
        assert _get_env_bool('TEST_VAR', True) is False
        
        os.environ['TEST_VAR'] = '0'
        assert _get_env_bool('TEST_VAR', True) is False
    
    def test_get_env_bool_default(self):
        """Test boolean default value."""
        if 'TEST_VAR' in os.environ:
            del os.environ['TEST_VAR']
        assert _get_env_bool('TEST_VAR', True) is True
        assert _get_env_bool('TEST_VAR', False) is False
    
    def test_get_env_int(self):
        """Test integer conversion."""
        os.environ['TEST_INT'] = '42'
        assert _get_env_int('TEST_INT', 0) == 42
        
        if 'TEST_INT' in os.environ:
            del os.environ['TEST_INT']
        assert _get_env_int('TEST_INT', 100) == 100
    
    def test_get_env_float(self):
        """Test float conversion."""
        os.environ['TEST_FLOAT'] = '3.14'
        assert _get_env_float('TEST_FLOAT', 0.0) == 3.14
        
        if 'TEST_FLOAT' in os.environ:
            del os.environ['TEST_FLOAT']
        assert _get_env_float('TEST_FLOAT', 2.5) == 2.5
    
    def test_get_env_str(self):
        """Test string conversion."""
        os.environ['TEST_STR'] = 'hello'
        assert _get_env_str('TEST_STR', 'default') == 'hello'
        
        if 'TEST_STR' in os.environ:
            del os.environ['TEST_STR']
        assert _get_env_str('TEST_STR', 'default') == 'default'


class TestLoadEnvConfig:
    """Test loading configuration from environment variables."""
    
    def test_load_env_config_defaults(self):
        """Test default configuration values."""
        # Clear relevant env vars
        env_vars = [
            'APP_NAME', 'APP_ENV', 'DEBUG', 'LOG_LEVEL',
            'DASHBOARD_PORT', 'DASHBOARD_USERNAME', 'DASHBOARD_PASSWORD',
            'SOURCE_TYPE', 'DETECTOR_MODEL_PATH', 'TRACKER_TYPE'
        ]
        original_values = {}
        for var in env_vars:
            if var in os.environ:
                original_values[var] = os.environ[var]
                del os.environ[var]
        
        try:
            config = load_env_config()
            
            assert config['app']['env'] == 'development'
            assert config['app']['debug'] is False
            assert config['dashboard']['port'] == 5050
            assert config['dashboard']['username'] == 'admin'
            assert config['source']['type'] == 'video'
            assert config['detector']['model_path'] == 'yolov8n.pt'
            assert config['tracker']['type'] == 'iou'
        finally:
            # Restore original values
            for var, value in original_values.items():
                os.environ[var] = value
    
    def test_load_env_config_custom_values(self):
        """Test custom configuration values from environment."""
        os.environ['APP_ENV'] = 'production'
        os.environ['DASHBOARD_PORT'] = '8080'
        os.environ['DETECTOR_CONFIDENCE_THRESHOLD'] = '0.7'
        os.environ['TRACKER_TYPE'] = 'bytetrack'
        
        config = load_env_config()
        
        assert config['app']['env'] == 'production'
        assert config['dashboard']['port'] == 8080
        assert config['detector']['confidence_threshold'] == 0.7
        assert config['tracker']['type'] == 'bytetrack'


class TestLoadConfig:
    """Test loading configuration from YAML and environment."""
    
    def test_load_config_yaml_only(self):
        """Test loading config from YAML file only."""
        config_path = "configs/default.yaml"
        config = load_config(config_path, use_env=False)
        
        assert 'source' in config
        assert 'detector' in config
        assert config['source']['type'] in ['video', 'camera']
    
    def test_load_config_missing_file(self):
        """Test error when config file is missing."""
        with pytest.raises(FileNotFoundError):
            load_config('/nonexistent/path/config.yaml')
    
    def test_load_config_validation_invalid_source_type(self, tmp_path):
        """Test validation error for invalid source type."""
        config_file = tmp_path / "invalid_config.yaml"
        config_file.write_text("""
source:
  type: "invalid_type"
detector:
  model_path: "yolov8n.pt"
""")
        
        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(str(config_file), use_env=False)
        
        assert "Invalid source type" in str(exc_info.value)
    
    def test_load_config_validation_thresholds(self, tmp_path):
        """Test validation error for invalid thresholds."""
        config_file = tmp_path / "invalid_thresholds.yaml"
        config_file.write_text("""
source:
  type: "video"
  video_path: "test.mp4"
detector:
  model_path: "yolov8n.pt"
  confidence_threshold: 1.5
""")
        
        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(str(config_file), use_env=False)
        
        assert "confidence_threshold must be between 0 and 1" in str(exc_info.value)
    
    def test_load_config_production_security_check(self, tmp_path):
        """Test production security validation."""
        config_file = tmp_path / "prod_config.yaml"
        config_file.write_text("""
app:
  env: production
source:
  type: "video"
  video_path: "test.mp4"
detector:
  model_path: "yolov8n.pt"
dashboard:
  secret_key: changeme
  password: changeme
""")
        
        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(str(config_file), use_env=False)
        
        assert "DASHBOARD_SECRET_KEY must be set" in str(exc_info.value) or \
               "DASHBOARD_PASSWORD must be changed" in str(exc_info.value)


class TestDeepMerge:
    """Test deep merge functionality."""
    
    def test_deep_merge_simple(self):
        """Test simple dictionary merge."""
        base = {'a': 1, 'b': 2}
        override = {'b': 3, 'c': 4}
        
        from src.utils.config import _deep_merge
        result = _deep_merge(base, override)
        
        assert result['a'] == 1
        assert result['b'] == 3
        assert result['c'] == 4
    
    def test_deep_merge_nested(self):
        """Test nested dictionary merge."""
        base = {'outer': {'inner1': 1, 'inner2': 2}}
        override = {'outer': {'inner2': 3, 'inner3': 4}}
        
        from src.utils.config import _deep_merge
        result = _deep_merge(base, override)
        
        assert result['outer']['inner1'] == 1
        assert result['outer']['inner2'] == 3
        assert result['outer']['inner3'] == 4
