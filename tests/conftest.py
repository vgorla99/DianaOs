"""Shared fixtures for DianaOS's public test suite.

Every fixture here builds synthetic, offline, deterministic state - no
real network call, no real LLM call, no owner-specific or otherwise
private data of any kind. Written fresh for this public repo; not copied
from any private source.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def isolated_audit_log(tmp_path, monkeypatch):
    """Redirects the audit log to a throwaway file so tests never touch
    any real database path."""
    from core.control_plane import audit_log

    monkeypatch.setattr(audit_log, "_DB_PATH", tmp_path / "test_audit.db")
    audit_log._ensure_table()
    return audit_log


@pytest.fixture()
def isolated_config_root(tmp_path, monkeypatch):
    """Redirects core.control_plane.config_loader's INSTANCE_CONFIG_ROOT to
    a throwaway directory, returning a helper to write synthetic YAML
    config files into it."""
    import yaml
    from core.control_plane import config_loader

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    monkeypatch.setattr(config_loader, "INSTANCE_CONFIG_ROOT", config_dir)

    def _write(relative_path: str, data: dict) -> None:
        full = config_dir / relative_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(yaml.safe_dump(data), encoding="utf-8")

    return _write
