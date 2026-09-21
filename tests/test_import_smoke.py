"""Import smoke test: every promoted core module must import cleanly
with zero private configuration present - no instance/config/, no real
credentials, no private repo."""
from __future__ import annotations

import importlib

_MODULES = [
    "core",
    "core.logger",
    "core.settings",
    "core.filesystem",
    "core.filesystem.safe_path",
    "core.control_plane",
    "core.control_plane.approval",
    "core.control_plane.audit_log",
    "core.control_plane.config_loader",
    "core.control_plane.router",
    "core.agents",
    "core.agents.schema",
    "core.agents.registry",
    "core.agents.evaluators.protocol",
    "core.agents.evaluators.schema_validation",
    "core.agents.implementations",
    "core.agents.runtime",
    "core.skills",
    "core.skills.models",
    "core.skills.registry",
    "core.skills.resolver",
]


def test_every_promoted_core_module_imports_cleanly():
    for module_name in _MODULES:
        importlib.import_module(module_name)  # raises ImportError/ModuleNotFoundError on failure
