"""
Security and validation tests for eucast-mic-breakpoint-interpreter.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import warnings
import pytest
from agents.base import AuditTrail, PHIGuard, SecurityException
from eucast_interpreter import _validate_safe_path, calculate_metrics


class TestPathValidation:
    """Tests for path traversal protection."""

    def test_valid_path_passes(self, tmp_path):
        safe = _validate_safe_path(str(tmp_path / "data.csv"))
        assert os.path.isabs(safe)

    def test_path_traversal_rejected(self):
        with pytest.raises(ValueError, match="Path traversal"):
            _validate_safe_path("../../../etc/passwd")

    def test_null_bytes_rejected(self):
        with pytest.raises(ValueError, match="null bytes"):
            _validate_safe_path("file\x00name.csv")

    def test_must_exist_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            _validate_safe_path(str(tmp_path / "nonexistent.csv"), must_exist=True)

    def test_must_exist_present_file(self, tmp_path):
        f = tmp_path / "exists.csv"
        f.write_text("data")
        safe = _validate_safe_path(str(f), must_exist=True)
        assert os.path.isfile(safe)


class TestAuditTrailSecurity:
    """Tests for HMAC audit trail security."""

    def test_random_key_generated_without_env(self, monkeypatch):
        """When no AUDIT_SECRET_KEY is set, a random key should be generated."""
        monkeypatch.delenv("AUDIT_SECRET_KEY", raising=False)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            trail = AuditTrail()
            assert len(w) == 1
            assert "AUDIT_SECRET_KEY not set" in str(w[0].message)
        # Key should be a long hex string (64 chars = 32 bytes)
        assert len(trail.secret_key) == 64

    def test_env_key_used_when_set(self, monkeypatch):
        monkeypatch.setenv("AUDIT_SECRET_KEY", "my-test-secret-key")
        trail = AuditTrail()
        assert trail.secret_key == b"my-test-secret-key"

    def test_explicit_key_overrides_env(self, monkeypatch):
        monkeypatch.setenv("AUDIT_SECRET_KEY", "env-key")
        trail = AuditTrail(secret_key="explicit-key")
        assert trail.secret_key == b"explicit-key"

    def test_different_random_keys_each_time(self, monkeypatch):
        """Each instance without env var should get a unique key."""
        monkeypatch.delenv("AUDIT_SECRET_KEY", raising=False)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            t1 = AuditTrail()
            t2 = AuditTrail()
        assert t1.secret_key != t2.secret_key


class TestPHIGuard:
    """Tests for PHI outbound guard."""

    def test_clean_text_passes(self):
        PHIGuard.assert_no_phi("Analytical assay specimen KEY-001 optimal")

    def test_mrn_pattern_blocked(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("Patient MRN-994827 blood culture")

    def test_ssn_pattern_blocked(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("SSN: 123-45-6789")

    def test_redact_phi_works(self):
        redacted = PHIGuard.redact_phi("Patient MRN-994827 test")
        assert "REDACTED_IDENTIFIER" in redacted
        assert "MRN" not in redacted


class TestCalculateMetricsValidation:
    """The old generic score must not be treated as susceptibility."""

    def test_explicit_breakpoints_required(self):
        with pytest.raises(TypeError):
            calculate_metrics(v1=30, v2=5)

    def test_susceptibility_category(self):
        result = calculate_metrics(
            organism="Demo organism", antimicrobial="Demo drug",
            mic="4", s_le="1", r_gt="8", breakpoint_version="illustrative")
        assert result["classification"] == "I"


def test_audit_detects_modified_signature():
    trail = AuditTrail(secret_key="unit-test-only-key")
    event = trail.log("test", "test", "unit-test", {"status": "ok"})
    assert trail.verify_integrity()
    event["current_hash"] = "0" * 64
    assert not trail.verify_integrity()


def test_audit_detects_modified_signed_metadata():
    trail = AuditTrail(secret_key="unit-test-only-key")
    trail.log("test", "test", "unit-test", {"status": "ok"})
    trail.logs[0]["actor"] = "modified"
    assert not trail.verify_integrity()
