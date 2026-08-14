"""Utility helpers for the sample project."""

import json


def parse_config(path):
    """Load and parse a JSON config file."""
    with open(path) as f:
        raw = f.read()
    data = json.loads(raw)
    return data


def validate(cfg):
    """Return True if the config has the required keys."""
    required = ["name", "version"]
    for key in required:
        if key not in cfg:
            return False
    return True


class ConfigError(Exception):
    def __init__(self, message):
        """Raised when a config file is invalid."""
        self.message = message
        super().__init__(message)
