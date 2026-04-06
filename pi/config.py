"""
Configuration loader for Surf E-Ink Frame.
Loads settings from config.yaml and environment variables.
"""

import os
import re
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


class Config:
    """Loads and provides access to configuration settings."""

    def __init__(self, config_path: str = None):
        # Load .env file for secrets
        load_dotenv()

        # Find config file
        if config_path is None:
            config_path = self._find_config()

        self.config_path = Path(config_path)
        self._config = self._load_config()

    def _find_config(self) -> str:
        """Find config.yaml in standard locations."""
        search_paths = [
            Path(__file__).parent.parent / "config" / "config.yaml",
            Path(__file__).parent / "config.yaml",
            Path.cwd() / "config" / "config.yaml",
            Path.cwd() / "config.yaml",
        ]
        for path in search_paths:
            if path.exists():
                return str(path)
        raise FileNotFoundError("config.yaml not found")

    def _load_config(self) -> dict:
        """Load and parse config.yaml with environment variable substitution."""
        with open(self.config_path, "r") as f:
            content = f.read()

        # Substitute ${VAR_NAME} with environment variables
        def replace_env(match):
            var_name = match.group(1)
            return os.environ.get(var_name, "")

        content = re.sub(r"\$\{(\w+)\}", replace_env, content)
        return yaml.safe_load(content)

    def get(self, *keys, default=None) -> Any:
        """Get nested config value. Example: config.get('timing', 'fetch_interval_minutes')"""
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    @property
    def cameras(self) -> list:
        """Get list of enabled cameras sorted by priority."""
        cams = self.get("cameras", default=[])
        enabled = [c for c in cams if c.get("enabled", True)]
        return sorted(enabled, key=lambda c: c.get("priority", 99))

    @property
    def timing(self) -> dict:
        return self.get("timing", default={})

    @property
    def display(self) -> dict:
        return self.get("display", default={})

    @property
    def overlay(self) -> dict:
        return self.get("overlay", default={})

    @property
    def server(self) -> dict:
        return self.get("server", default={})

    @property
    def paths(self) -> dict:
        return self.get("paths", default={})

    @property
    def filter_settings(self) -> dict:
        return self.get("filter", default={})

    def reload(self):
        """Reload configuration from file."""
        self._config = self._load_config()


# Global config instance
_config = None


def get_config(config_path: str = None) -> Config:
    """Get or create global config instance."""
    global _config
    if _config is None or config_path is not None:
        _config = Config(config_path)
    return _config
