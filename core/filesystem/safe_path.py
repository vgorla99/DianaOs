"""
Single filesystem-write safety primitive.

Root cause this exists to prevent: on WSL/DrvFs setups, a POSIX-side
process can write characters into a filename that are illegal in NTFS
(':' and '\\', among others) - Windows encodes them as Unicode
Private-Use-Area codepoints instead of raising, so a full path string
passed where a relative segment was expected gets silently accepted as a
single mangled directory name rather than failing loudly. `safe_path()`
makes that class of bug impossible for any caller that routes through it:
every write goes through one registered root, one canonical resolution,
and one containment check, with symlinks rejected and every call logged.

Usage:
    from core.filesystem import register_root, safe_path

    register_root("vault", VAULT_PATH)
    full = safe_path("vault", "notes/daily/2026-09-18.md")
"""
from __future__ import annotations

from pathlib import Path

from core.logger import get_logger

log = get_logger("safe_path")

_ILLEGAL_WINDOWS_CHARS = set(':*?"<>|')

_roots: dict[str, Path] = {}


class PathSafetyError(Exception):
    """Raised when a requested path would escape its registered root."""


def register_root(root_id: str, path: str | Path) -> Path:
    """Register a base directory under a stable ID. Call once at startup per root."""
    resolved = Path(path).resolve()
    resolved.mkdir(parents=True, exist_ok=True)
    _roots[root_id] = resolved
    log.info("safe_path: registered root '%s' -> %s", root_id, resolved)
    return resolved


def list_roots() -> list[str]:
    """
    Registered root IDs only - never raw filesystem paths. Safe to use from
    anything that might end up in a public API response, or that needs to
    validate an allowlist (e.g. AgentDefinition.allowed_roots)
    against what's actually registered.
    """
    return sorted(_roots)


def get_root(root_id: str) -> Path:
    """Return a registered root's own resolved path (not a sub-path within it)."""
    if root_id not in _roots:
        raise PathSafetyError(
            f"Unknown root_id '{root_id}'. Registered roots: {sorted(_roots)}."
        )
    return _roots[root_id]


def safe_path(root_id: str, relative_path: str) -> Path:
    """
    Resolve `relative_path` under the root registered as `root_id`, raising
    PathSafetyError if the result would escape the root, contains
    Windows-illegal characters (the exact bug class this module fixes),
    absolute-path segments, `..` traversal, or resolves through a symlink.
    """
    if root_id not in _roots:
        raise PathSafetyError(
            f"Unknown root_id '{root_id}'. Registered roots: {sorted(_roots)}. "
            "Call register_root() once at startup before using safe_path()."
        )
    root = _roots[root_id]

    if not relative_path or not relative_path.strip():
        raise PathSafetyError("relative_path must be non-empty")

    if any(ch in _ILLEGAL_WINDOWS_CHARS for ch in relative_path):
        raise PathSafetyError(
            f"relative_path contains a Windows-illegal character: {relative_path!r} "
            "(this is the exact bug class that produced the malformed vault folder - "
            "a full path string was passed where a relative segment was expected)."
        )

    candidate = Path(relative_path)
    if candidate.is_absolute() or candidate.drive:
        raise PathSafetyError(f"relative_path must not be absolute: {relative_path!r}")

    full = (root / candidate).resolve()

    if not full.is_relative_to(root):
        raise PathSafetyError(
            f"Path '{relative_path}' resolves outside root '{root_id}' ({root}): {full}"
        )

    if full.is_symlink() or any(p.is_symlink() for p in full.parents if p.exists()):
        raise PathSafetyError(f"Path '{relative_path}' passes through a symlink; rejected by default")

    log.info("safe_path: root='%s' relative='%s' -> %s", root_id, relative_path, full)
    return full
