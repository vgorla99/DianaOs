"""Tests for core.control_plane.approval - the approval-level gate.
Level 3+ (EXTERNAL_HIGH_IMPACT and above) must always require explicit
approval; lower levels never do."""
from __future__ import annotations

import pytest

from core.control_plane.approval import ApprovalLevel, ApprovalRequiredError, check_approval


def test_level_0_read_allowed_without_approval_token():
    check_approval("example-read-action", ApprovalLevel.READ, approved=False)  # must not raise


def test_level_3_external_high_impact_denied_without_approval():
    with pytest.raises(ApprovalRequiredError):
        check_approval("example-external-action", ApprovalLevel.EXTERNAL_HIGH_IMPACT, approved=False)


def test_level_3_external_high_impact_allowed_with_approval():
    check_approval("example-external-action", ApprovalLevel.EXTERNAL_HIGH_IMPACT, approved=True)  # must not raise


def test_level_4_critical_denied_without_approval():
    with pytest.raises(ApprovalRequiredError):
        check_approval("example-critical-action", ApprovalLevel.CRITICAL, approved=False)
