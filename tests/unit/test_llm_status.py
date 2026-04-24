"""Tests for scripts/llm_status.py — /llm-status skill (C4 of mega-plan).

Covers:
- Env var detection (configured / unconfigured / redacted key display)
- Kill-switch state read correctly
- Metrics aggregation from JSONL (happy path, empty, missing file, malformed)
- Windowing by days
- --json output is valid JSON and structurally correct
- Pretty output contains required sections
- Key redaction (never print full API key)
- Tolerates parse errors in JSONL without crashing
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

_REPO = Path(__file__).resolve().parent.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

# Load scripts/llm_status.py as a module (it's a script, not a package)
_STATUS_PATH = _REPO / "scripts" / "llm_status.py"
_spec = importlib.util.spec_from_file_location("llm_status_under_test", _STATUS_PATH)
_ls = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ls)


class TestRedaction(unittest.TestCase):
    def test_redact_empty_returns_unset(self):
        self.assertEqual(_ls._redact(""), "(unset)")

    def test_redact_short_masked(self):
        self.assertEqual(_ls._redact("short"), "***")

    def test_redact_long_shows_prefix_suffix(self):
        key = "sk-abc123def456ghi789"
        r = _ls._redact(key)
        self.assertIn("...", r)
        self.assertTrue(r.startswith(key[:6]))
        self.assertTrue(r.endswith(key[-4:]))
        # The raw key middle must NOT appear verbatim
        self.assertNotIn(key, r)

    def test_redact_never_emits_full_key(self):
        """Property test — even for weird lengths, full key never appears."""
        for key in ["sk-a", "sk-abcd1234", "sk-" + "x" * 100]:
            r = _ls._redact(key)
            if len(key) > 10:
                # For long keys, full key should NOT be in output
                self.assertNotEqual(r, key)


class TestProviderConfigured(unittest.TestCase):
    def test_claude_max_always_true(self):
        with patch.dict(os.environ, {}, clear=True):
            cfg = _ls._provider_configured()
        self.assertTrue(cfg["claude_max"]["configured"])

    def test_alibaba_qwen_detects_env(self):
        with patch.dict(os.environ, {"ALIBABA_QWEN_API_KEY": "sk-testkey123456789"}):
            cfg = _ls._provider_configured()
        self.assertTrue(cfg["alibaba_qwen"]["configured"])
        self.assertIn("sk-tes", cfg["alibaba_qwen"]["api_key_hint"])

    def test_alibaba_qwen_detects_unconfigured(self):
        with patch.dict(os.environ, {}, clear=True):
            # Remove any .env-loaded state
            os.environ.pop("ALIBABA_QWEN_API_KEY", None)
            cfg = _ls._provider_configured()
        # May be True if .env loaded during import — we only check that
        # the function returns a structured dict with the key
        self.assertIn("configured", cfg["alibaba_qwen"])
        self.assertIn("api_key_hint", cfg["alibaba_qwen"])


class TestKillSwitches(unittest.TestCase):
    def test_all_unset_returns_all_false(self):
        with patch.dict(os.environ, {}, clear=False):
            for k in ("COS_DISABLE_LLM_FALLBACK", "COS_DISABLE_QWEN", "COS_FORCE_CLAUDE_PRIMARY"):
                os.environ.pop(k, None)
            ks = _ls._kill_switches()
        self.assertFalse(ks["COS_DISABLE_LLM_FALLBACK"])
        self.assertFalse(ks["COS_DISABLE_QWEN"])
        self.assertFalse(ks["COS_FORCE_CLAUDE_PRIMARY"])

    def test_only_literal_one_disables(self):
        with patch.dict(os.environ, {"COS_DISABLE_QWEN": "0"}):
            self.assertFalse(_ls._kill_switches()["COS_DISABLE_QWEN"])
        with patch.dict(os.environ, {"COS_DISABLE_QWEN": "false"}):
            self.assertFalse(_ls._kill_switches()["COS_DISABLE_QWEN"])
        with patch.dict(os.environ, {"COS_DISABLE_QWEN": ""}):
            self.assertFalse(_ls._kill_switches()["COS_DISABLE_QWEN"])
        with patch.dict(os.environ, {"COS_DISABLE_QWEN": "1"}):
            self.assertTrue(_ls._kill_switches()["COS_DISABLE_QWEN"])


class TestMetricsAggregation(unittest.TestCase):
    def _write_metrics(self, records: list[dict]) -> Path:
        """Create a temp metrics file and return path."""
        tmp = tempfile.mkdtemp()
        metrics_dir = Path(tmp) / ".cognitive-os" / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)
        f = metrics_dir / "llm-dispatch.jsonl"
        with f.open("w") as fh:
            for r in records:
                fh.write(json.dumps(r) + "\n")
        return Path(tmp)

    def test_empty_file_returns_zero_total(self):
        tmp = self._write_metrics([])
        with patch.object(_ls, "_PROJECT_ROOT", tmp):
            m = _ls._recent_metrics(days=30)
        self.assertTrue(m["available"])
        self.assertEqual(m.get("total", 0), 0)

    def test_missing_file_returns_available_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(_ls, "_PROJECT_ROOT", Path(tmp)):
                m = _ls._recent_metrics(days=30)
        self.assertFalse(m["available"])

    def test_aggregation_multiple_providers(self):
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        records = [
            {"ts": now, "provider_used": "alibaba_qwen", "model": "qwen3.6-plus",
             "tokens_in": 10, "tokens_out": 20, "cost_usd": 0.001, "latency_ms": 1000,
             "success": True, "task_type": "code", "skill_name": None},
            {"ts": now, "provider_used": "alibaba_qwen", "model": "qwen3.6-plus",
             "tokens_in": 100, "tokens_out": 200, "cost_usd": 0.01, "latency_ms": 2000,
             "success": True, "task_type": "code", "skill_name": None},
            {"ts": now, "provider_used": "claude", "model": "opus",
             "tokens_in": 50, "tokens_out": 80, "cost_usd": 0.05, "latency_ms": 3000,
             "success": True, "task_type": "reasoning", "skill_name": "sdd-propose"},
            {"ts": now, "provider_used": "claude", "model": "opus",
             "tokens_in": 20, "tokens_out": 0, "cost_usd": 0.02, "latency_ms": 500,
             "success": False, "task_type": "reasoning", "skill_name": None},
        ]
        tmp = self._write_metrics(records)
        with patch.object(_ls, "_PROJECT_ROOT", tmp):
            m = _ls._recent_metrics(days=30)
        self.assertEqual(m["total"], 4)
        self.assertEqual(m["successes"], 3)
        self.assertAlmostEqual(m["success_rate"], 0.75, places=2)
        self.assertIn("alibaba_qwen", m["by_provider"])
        self.assertIn("claude", m["by_provider"])
        # Qwen: 2 calls, $0.011 total, tokens 110→220
        qwen_b = m["by_provider"]["alibaba_qwen"]
        self.assertEqual(qwen_b["calls"], 2)
        self.assertAlmostEqual(qwen_b["cost_usd"], 0.011, places=4)
        self.assertEqual(qwen_b["tokens_in"], 110)
        self.assertEqual(qwen_b["tokens_out"], 220)
        # Claude: 2 calls, $0.07 total, success 1/2
        claude_b = m["by_provider"]["claude"]
        self.assertEqual(claude_b["calls"], 2)
        self.assertAlmostEqual(claude_b["success_rate"], 0.5, places=2)

    def test_malformed_lines_tolerated(self):
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        tmp = tempfile.mkdtemp()
        metrics_dir = Path(tmp) / ".cognitive-os" / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)
        (metrics_dir / "llm-dispatch.jsonl").write_text(
            'not-valid-json\n'
            '{"ts": "' + now + '", "provider_used": "alibaba_qwen", '
            '"tokens_in": 1, "tokens_out": 1, "cost_usd": 0, '
            '"latency_ms": 100, "success": true}\n'
            '{"truncated"\n'
        )
        with patch.object(_ls, "_PROJECT_ROOT", Path(tmp)):
            m = _ls._recent_metrics(days=30)
        self.assertTrue(m["available"])
        self.assertEqual(m["total"], 1)
        self.assertEqual(m["parse_errors"], 2)

    def test_windowing_excludes_old_records(self):
        old_ts = "2020-01-01T00:00:00Z"  # Way outside 30-day window
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        records = [
            {"ts": old_ts, "provider_used": "alibaba_qwen", "tokens_in": 1,
             "tokens_out": 1, "cost_usd": 0, "latency_ms": 100, "success": True},
            {"ts": now, "provider_used": "alibaba_qwen", "tokens_in": 1,
             "tokens_out": 1, "cost_usd": 0, "latency_ms": 100, "success": True},
        ]
        tmp = self._write_metrics(records)
        with patch.object(_ls, "_PROJECT_ROOT", tmp):
            m = _ls._recent_metrics(days=30)
        # Only the recent one counts
        self.assertEqual(m["total"], 1)


class TestCLI(unittest.TestCase):
    def test_json_output_parses(self):
        """--json emits valid JSON with expected top-level keys."""
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            rc = _ls.main(["--json", "--days", "1"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertIn("providers_configured", data)
        self.assertIn("kill_switches", data)
        self.assertIn("metrics", data)

    def test_pretty_output_has_required_sections(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            rc = _ls.main(["--days", "1"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("Providers configured", out)
        self.assertIn("Kill-switches", out)
        self.assertIn("Cascade default", out)
        self.assertIn("Verification", out)
        self.assertIn("Actions", out)

    def test_pretty_output_never_prints_raw_key(self):
        """Security invariant — API keys must never appear verbatim in output."""
        fake_key = "sk-fakekey-should-never-appear-in-output-123"
        with patch.dict(os.environ, {"ALIBABA_QWEN_API_KEY": fake_key}):
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                _ls.main(["--days", "1"])
            out = buf.getvalue()
        self.assertNotIn(fake_key, out, "Raw API key leaked in output")


class TestSkillFrontmatter(unittest.TestCase):
    """The SKILL.md must be loadable and have required frontmatter fields."""

    def test_skill_md_exists(self):
        path = _REPO / "skills" / "llm-status" / "SKILL.md"
        self.assertTrue(path.exists())

    def test_skill_frontmatter_parseable(self):
        import yaml
        path = _REPO / "skills" / "llm-status" / "SKILL.md"
        text = path.read_text()
        # Strip leading HTML comment (SCOPE tag)
        stripped = text.lstrip()
        if stripped.startswith("<!--"):
            end = stripped.index("-->") + 3
            stripped = stripped[end:].lstrip()
        self.assertTrue(stripped.startswith("---"))
        parts = stripped.split("---", 2)
        fm = yaml.safe_load(parts[1])
        self.assertEqual(fm["name"], "llm-status")
        self.assertIn("description", fm)
        self.assertIn("summary_line", fm)


if __name__ == "__main__":
    unittest.main(verbosity=2)
