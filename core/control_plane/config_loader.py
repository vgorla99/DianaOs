"""
Unified config loader for instance/config/.

The single point every agent/skill/control-plane module should use to
read its own YAML config, instead of opening instance/config/ paths
directly.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

INSTANCE_CONFIG_ROOT = Path(os.getenv("INSTANCE_CONFIG_ROOT", "instance/config"))


class ConfigNotFoundError(FileNotFoundError):
    pass


def load_config(name: str) -> Any:
    """
    Load a YAML file by name, relative to instance/config/
    (e.g. "projects.yaml", "brands.yaml", "agents/ceo.yaml").
    Returns whatever structure the YAML contains via yaml.safe_load.
    """
    path = INSTANCE_CONFIG_ROOT / name
    if not path.exists():
        raise ConfigNotFoundError(f"Config file not found: {path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)
