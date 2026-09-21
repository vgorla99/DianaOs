"""Tests for core.filesystem.safe_path - the containment-checked
filesystem-write primitive. All synthetic tmp_path data, no real paths."""
from __future__ import annotations

import pytest

from core.filesystem.safe_path import PathSafetyError, register_root, safe_path


@pytest.fixture()
def scratch_root(tmp_path):
    register_root("test_scratch_root", tmp_path)
    return tmp_path


def test_normal_relative_resolution_succeeds(scratch_root):
    resolved = safe_path("test_scratch_root", "notes/example.md")
    assert resolved == (scratch_root / "notes" / "example.md").resolve()


def test_parent_traversal_rejected(scratch_root):
    with pytest.raises(PathSafetyError):
        safe_path("test_scratch_root", "../escape.md")


def test_absolute_windows_path_rejected(scratch_root):
    with pytest.raises(PathSafetyError):
        safe_path("test_scratch_root", "C:\\Windows\\System32\\evil.txt")


def test_absolute_posix_path_rejected(scratch_root):
    with pytest.raises(PathSafetyError):
        safe_path("test_scratch_root", "/etc/passwd")


def test_escape_outside_root_via_subdir_rejected(scratch_root):
    with pytest.raises(PathSafetyError):
        safe_path("test_scratch_root", "sub/../../outside.md")


def test_unknown_root_id_rejected():
    with pytest.raises(PathSafetyError):
        safe_path("no_such_root_was_ever_registered", "anything.md")
