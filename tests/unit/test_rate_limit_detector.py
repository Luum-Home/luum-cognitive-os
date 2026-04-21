"""Tests for hooks/rate-limit-detector.sh.

Verifies the PostToolUse advisory hook that detects Claude Code rate-limit
errors and suggests falling back to direct-SDK overflow per ADR-049.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HOOK = REPO_ROOT / "hooks" / "rate-limit-detector.sh"


def _run(stdin: str, env: dict | None = None, timeout: float = 5.0) -> subprocess.CompletedProcess:
    merged_env = dict(os.environ)
    if env:
        merged_env.update(env)
    # Always set CLAUDE_PROJECT_DIR so the hook doesn't pollute the repo
    merged_env.setdefault("CLAUDE_PROJECT_DIR", merged_env.get("CLAUDE_PROJECT_DIR", str(REPO_ROOT)))
    return subprocess.run(
        ["bash", str(HOOK)],
        input=stdin,
        env=merged_env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


class TestHookExistence(unittest.TestCase):
    def test_hook_exists_executable(self):
        self.assertTrue(HOOK.is_file(), f"{HOOK} missing")
        self.assertTrue(os.access(HOOK, os.X_OK), f"{HOOK} not executable")

    def test_bash_syntax_clean(self):
        r = subprocess.run(["bash", "-n", str(HOOK)], capture_output=True, text=True, timeout=5)
        self.assertEqual(r.returncode, 0, r.stderr)


class TestDetection(unittest.TestCase):
    def _env_tmpdir(self, tmp):
        return {
            "CLAUDE_PROJECT_DIR": tmp,
            "COGNITIVE_OS_SESSION_ID": "test-sess",
        }

    def test_matches_out_of_extra_usage(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = _run(
                '{"tool_response":{"error":"You\'re out of extra usage · resets 2pm"}}',
                env=self._env_tmpdir(tmp),
            )
            self.assertEqual(r.returncode, 0)
            self.assertIn("rate-limit-detector", r.stderr)

    def test_matches_approaching_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = _run(
                "You're approaching your usage limit for 5-hour window",
                env=self._env_tmpdir(tmp),
            )
            self.assertEqual(r.returncode, 0)
            self.assertIn("rate-limit-detector", r.stderr)

    def test_matches_rate_limit_exceeded(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = _run("rate limit exceeded", env=self._env_tmpdir(tmp))
            self.assertEqual(r.returncode, 0)
            self.assertIn("rate-limit-detector", r.stderr)

    def test_no_match_on_ordinary_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = _run(
                '{"tool_response":{"output":"everything fine, 42 tests pass"}}',
                env=self._env_tmpdir(tmp),
            )
            self.assertEqual(r.returncode, 0)
            self.assertEqual(r.stderr.strip(), "")

    def test_always_exits_zero_even_on_match(self):
        """Hook is advisory — must never block the pipeline."""
        with tempfile.TemporaryDirectory() as tmp:
            r = _run(
                "out of extra usage · resets 1pm",
                env=self._env_tmpdir(tmp),
            )
            self.assertEqual(r.returncode, 0)

    def test_writes_jsonl_metric_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = _run(
                "out of extra usage · resets 2pm",
                env=self._env_tmpdir(tmp),
            )
            self.assertEqual(r.returncode, 0)
            metric_file = Path(tmp) / ".cognitive-os" / "metrics" / "rate-limit-events.jsonl"
            self.assertTrue(metric_file.exists(), "metric file not created")
            line = metric_file.read_text().strip().splitlines()[0]
            record = json.loads(line)
            self.assertEqual(record["session_id"], "test-sess")
            self.assertIn("match", record)

    def test_deduplicates_advisory_per_session(self):
        """Second hit in same session should NOT re-emit the advisory to stderr."""
        with tempfile.TemporaryDirectory() as tmp:
            env = self._env_tmpdir(tmp)
            r1 = _run("out of extra usage · resets 2pm", env=env)
            r2 = _run("out of extra usage · resets 2pm", env=env)
            self.assertIn("rate-limit-detector", r1.stderr)
            # Second run: flag exists, advisory dedup'd
            self.assertEqual(r2.stderr.strip(), "")
            # But metric file still has BOTH records
            metric_file = Path(tmp) / ".cognitive-os" / "metrics" / "rate-limit-events.jsonl"
            self.assertEqual(len(metric_file.read_text().strip().splitlines()), 2)


class TestConfiguredAdvice(unittest.TestCase):
    def test_advice_varies_when_api_key_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {
                "CLAUDE_PROJECT_DIR": str(REPO_ROOT),  # real repo so qwen_provider.py exists
                "COGNITIVE_OS_SESSION_ID": "test-configured",
                "ALIBABA_QWEN_API_KEY": "sk-fake-for-test",
            }
            # Clean up any stale flag from prior runs
            flag = REPO_ROOT / ".cognitive-os" / "sessions" / "test-configured" / "rate-limit-advised.flag"
            if flag.exists():
                flag.unlink()
            r = _run("out of extra usage · resets 2pm", env=env)
            self.assertIn("Dispatch via lib/qwen_provider.py", r.stderr)
            # Cleanup
            if flag.exists():
                flag.unlink()

    def test_advice_varies_when_not_configured(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {
                "CLAUDE_PROJECT_DIR": str(REPO_ROOT),
                "COGNITIVE_OS_SESSION_ID": "test-not-configured",
            }
            env.pop("ALIBABA_QWEN_API_KEY", None)
            flag = REPO_ROOT / ".cognitive-os" / "sessions" / "test-not-configured" / "rate-limit-advised.flag"
            if flag.exists():
                flag.unlink()
            r = _run("out of extra usage · resets 2pm", env=env)
            self.assertIn("NOT configured", r.stderr)
            self.assertIn("Alibaba Qwen Coding Plan Pro", r.stderr)
            if flag.exists():
                flag.unlink()


class TestRegistration(unittest.TestCase):
    def test_registered_in_both_profile_scripts(self):
        apply_text = (REPO_ROOT / "scripts" / "apply-efficiency-profile.sh").read_text()
        secure_text = (REPO_ROOT / "scripts" / "set-security-profile.sh").read_text()
        self.assertIn("rate-limit-detector", apply_text)
        self.assertIn("rate-limit-detector", secure_text)

    def test_registered_in_settings_json(self):
        settings = (REPO_ROOT / ".claude" / "settings.json").read_text()
        self.assertIn("rate-limit-detector", settings)


if __name__ == "__main__":
    unittest.main(verbosity=2)
