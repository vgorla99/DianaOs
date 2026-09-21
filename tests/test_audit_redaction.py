"""Tests for core.control_plane.audit_log's secret redaction. Uses only
fake, obviously-synthetic token/secret-shaped strings - never a real
credential of any kind."""
from __future__ import annotations

from core.control_plane.approval import ApprovalLevel


def test_token_shaped_string_is_not_persisted_raw(isolated_audit_log):
    fake_secret_string = "api_key=FAKE1234567890ABCDEFTESTONLY"

    isolated_audit_log.record_action(
        "example-action", ApprovalLevel.READ, True, detail=fake_secret_string,
    )

    rows = isolated_audit_log.read_recent_full(limit=1)
    assert len(rows) == 1
    assert fake_secret_string not in rows[0]["detail"]
    assert "[REDACTED]" in rows[0]["detail"]


def test_sk_shaped_token_is_not_persisted_raw(isolated_audit_log):
    fake_sk_token = "sk-FAKEFAKEFAKEFAKEFAKEFAKETESTONLY"

    isolated_audit_log.record_action(
        "example-action", ApprovalLevel.READ, True, detail=f"leaked: {fake_sk_token}",
    )

    rows = isolated_audit_log.read_recent_full(limit=1)
    assert fake_sk_token not in rows[0]["detail"]


def test_action_without_secret_shaped_content_is_unredacted(isolated_audit_log):
    isolated_audit_log.record_action(
        "example-action", ApprovalLevel.READ, True, detail="nothing sensitive here",
    )

    rows = isolated_audit_log.read_recent_full(limit=1)
    assert rows[0]["detail"] == "nothing sensitive here"
