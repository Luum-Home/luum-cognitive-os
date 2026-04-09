"""Tests for lib/auto_repair.py — minimal auto-repair system."""
import os
import sys
import json
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from lib.auto_repair import (
    Remediation,
    REMEDIATION_REGISTRY,
    classify_error,
    apply_remediation,
    format_repair_suggestion,
)


class TestClassifyError:
    def test_python_import_error(self):
        r = classify_error("COMMAND_FAILURE", "ModuleNotFoundError: No module named 'requests'")
        assert r is not None
        assert "pip install" in r.fix_command

    def test_npm_module_error(self):
        r = classify_error("BUILD_ERROR", "Cannot find module 'express'")
        assert r is not None
        assert "npm install" in r.fix_command

    def test_go_mod_error(self):
        r = classify_error("BUILD_ERROR", "go: some/module missing go.sum entry")
        assert r is not None
        assert "go mod tidy" in r.fix_command

    def test_permission_denied(self):
        r = classify_error("COMMAND_FAILURE", "permission denied: ./hooks/my-hook.sh")
        assert r is not None
        assert "chmod" in r.fix_command

    def test_port_in_use(self):
        r = classify_error("RUNTIME_ERROR", "address already in use :::3000")
        assert r is not None
        assert "lsof" in r.fix_command

    def test_unknown_error_returns_none(self):
        r = classify_error("UNKNOWN", "some completely unknown error message xyz")
        assert r is None

    def test_registry_has_minimum_patterns(self):
        assert len(REMEDIATION_REGISTRY) >= 5


class TestApplyRemediation:
    def test_dry_run_never_executes(self):
        r = Remediation(
            error_pattern=r"test", fix_command="echo hello",
            description="test", safe=True
        )
        result = apply_remediation(r, message="test", dry_run=True,
                                   metrics_dir=tempfile.mkdtemp())
        assert result["action"] == "suggest"
        assert result["dry_run"] is True

    def test_unsafe_remediation_only_suggests(self):
        r = Remediation(
            error_pattern=r"test", fix_command="rm -rf /",
            description="dangerous", safe=False
        )
        result = apply_remediation(r, message="test", dry_run=False,
                                   metrics_dir=tempfile.mkdtemp())
        assert result["action"] == "suggest"

    def test_safe_remediation_executes(self):
        r = Remediation(
            error_pattern=r"test", fix_command="echo OK",
            description="safe echo", safe=True
        )
        result = apply_remediation(r, message="test", dry_run=False,
                                   metrics_dir=tempfile.mkdtemp())
        assert result["action"] == "applied"
        assert result["exit_code"] == 0

    def test_logs_to_metrics(self):
        tmpdir = tempfile.mkdtemp()
        r = Remediation(
            error_pattern=r"test", fix_command="echo logged",
            description="log test", safe=True
        )
        apply_remediation(r, message="test", dry_run=False, metrics_dir=tmpdir)
        log_path = os.path.join(tmpdir, "repair-outcomes.jsonl")
        assert os.path.exists(log_path)
        with open(log_path) as f:
            entry = json.loads(f.readline())
        assert "timestamp" in entry
        assert entry["action"] == "applied"


class TestFormatSuggestion:
    def test_safe_tag(self):
        r = Remediation(
            error_pattern=r"test", fix_command="echo hi",
            description="test fix", safe=True
        )
        s = format_repair_suggestion(r)
        assert "[AUTO]" in s

    def test_manual_tag(self):
        r = Remediation(
            error_pattern=r"test", fix_command="rm something",
            description="manual fix", safe=False
        )
        s = format_repair_suggestion(r)
        assert "[MANUAL]" in s

    def test_placeholder_replacement(self):
        r = Remediation(
            error_pattern=r"No module named '(\w+)'",
            fix_command="pip install {module}",
            description="install", safe=False
        )
        s = format_repair_suggestion(r, "ModuleNotFoundError: No module named 'flask'")
        assert "pip install flask" in s
