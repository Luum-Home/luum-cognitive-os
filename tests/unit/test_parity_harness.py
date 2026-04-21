"""Tests for scripts/parity-harness.py (ADR-051 Phase 4).

Covers:
  - YAML task-set loading (PyYAML path + minimal fallback)
  - File snapshotting + diff helpers
  - run_task() with injected provider fns (no real API calls)
  - CSV + Markdown renderers
  - emit_jsonl writes one record per (task, provider) pair
  - CLI parses args, fails gracefully on missing files
"""
from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

_REPO = Path(__file__).resolve().parent.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _load_harness_module():
    """Load scripts/parity-harness.py as a module (has a dash in the name)."""
    path = _REPO / "scripts" / "parity-harness.py"
    spec = importlib.util.spec_from_file_location("parity_harness", str(path))
    module = importlib.util.module_from_spec(spec)
    # Register before exec so dataclasses' type lookups can find the module
    # (required on Py3.9 when combined with `from __future__ import annotations`).
    sys.modules["parity_harness"] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


PH = _load_harness_module()


SMOKE_YAML = """\
tasks:
  - id: t1
    description: first task
    prompt: |
      do the first thing
      on multiple lines
    tools_allowed: [read_file]
  - id: t2
    description: second task
    prompt: do the second thing
    tools_allowed: []
"""


class TestTaskSetLoading(unittest.TestCase):

    def test_loads_smoke_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as fh:
            fh.write(SMOKE_YAML)
            p = Path(fh.name)
        tasks = PH.load_tasks(p)
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].id, "t1")
        self.assertEqual(tasks[0].tools_allowed, ["read_file"])
        self.assertIn("first thing", tasks[0].prompt)
        self.assertEqual(tasks[1].id, "t2")
        self.assertEqual(tasks[1].tools_allowed, [])

    def test_real_smoke_file_parses(self):
        smoke = _REPO / "docs" / "benchmarks" / "parity-smoke.yaml"
        if not smoke.exists():
            self.skipTest("smoke file not committed yet")
        tasks = PH.load_tasks(smoke)
        self.assertGreaterEqual(len(tasks), 3)
        for t in tasks:
            self.assertTrue(t.id)
            self.assertTrue(t.prompt)

    def test_rejects_missing_key(self):
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as fh:
            fh.write("something_else:\n  - 1\n")
            p = Path(fh.name)
        with self.assertRaises(ValueError):
            PH.load_tasks(p)


class TestSnapshotDiff(unittest.TestCase):

    def test_diff_detects_new_and_changed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            f1 = root / "a.txt"
            f1.write_text("hello")
            before = PH._snapshot_files(["a.txt"], root)
            # Modify
            f1.write_text("goodbye")
            after = PH._snapshot_files(["a.txt"], root)
            changed = PH._diff_snapshots(before, after)
            self.assertIn("a.txt", changed)

    def test_diff_empty_when_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            f1 = root / "a.txt"
            f1.write_text("hello")
            before = PH._snapshot_files(["a.txt"], root)
            after = PH._snapshot_files(["a.txt"], root)
            self.assertEqual(PH._diff_snapshots(before, after), [])


class TestRunTaskInjection(unittest.TestCase):
    """run_task() must work with injected providers — NO real API calls."""

    def _mk_task(self):
        return PH.ParityTask(
            id="inject-1",
            description="injected",
            prompt="do the thing",
        )

    def test_both_providers_injected(self):
        def fake_qwen(task, root, verbose=False, **kw):
            return PH.ParityResult(
                task_id=task.id, provider="qwen",
                success=True, text="qwen output",
                tokens_in=10, tokens_out=20, cost_usd=0.00001,
                latency_ms=100, tool_calls=1,
            )

        def fake_claude(task, root, claude_executor=None, verbose=False, **kw):
            return PH.ParityResult(
                task_id=task.id, provider="claude",
                success=True, text="claude output",
                tokens_in=12, tokens_out=30, cost_usd=0.01,
                latency_ms=900, tool_calls=2,
            )

        results = PH.run_task(
            self._mk_task(),
            _REPO,
            qwen_fn=fake_qwen,
            claude_fn=fake_claude,
            claude_executor=object(),  # truthy, not used
        )
        self.assertEqual(len(results), 2)
        providers = {r.provider for r in results}
        self.assertEqual(providers, {"qwen", "claude"})

    def test_only_qwen_filter(self):
        def fake_qwen(task, root, verbose=False, **kw):
            return PH.ParityResult(task_id=task.id, provider="qwen", success=True)
        def fake_claude(task, root, **kw):  # should never be called
            self.fail("claude_fn should not run when only_provider='qwen'")

        results = PH.run_task(
            self._mk_task(), _REPO,
            qwen_fn=fake_qwen, claude_fn=fake_claude,
            only_provider="qwen",
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].provider, "qwen")

    def test_missing_claude_executor_emits_error_result(self):
        def fake_qwen(task, root, verbose=False, **kw):
            return PH.ParityResult(task_id=task.id, provider="qwen", success=True)

        # No claude_fn injected — default run_via_claude requires executor.
        results = PH.run_task(
            self._mk_task(), _REPO,
            qwen_fn=fake_qwen,
            claude_executor=None,
        )
        self.assertEqual(len(results), 2)
        claude_r = next(r for r in results if r.provider == "claude")
        self.assertFalse(claude_r.success)
        self.assertIn("no claude_executor", claude_r.error)


class TestRenderers(unittest.TestCase):

    def _sample_results(self):
        return [
            PH.ParityResult(
                task_id="t1", provider="claude", success=True,
                tokens_in=100, tokens_out=200, cost_usd=0.015,
                latency_ms=1200, tool_calls=3, text="claude t1 text",
            ),
            PH.ParityResult(
                task_id="t1", provider="qwen", success=True,
                tokens_in=100, tokens_out=200, cost_usd=0.0003,
                latency_ms=800, tool_calls=2, text="qwen t1 text",
            ),
            PH.ParityResult(
                task_id="t2", provider="claude", success=False,
                tokens_in=50, tokens_out=10, cost_usd=0.002,
                latency_ms=400, tool_calls=0, error="boom",
            ),
            PH.ParityResult(
                task_id="t2", provider="qwen", success=True,
                tokens_in=40, tokens_out=60, cost_usd=0.0001,
                latency_ms=300, tool_calls=1,
            ),
        ]

    def _sample_tasks(self):
        return [
            PH.ParityTask(id="t1", description="first", prompt="x"),
            PH.ParityTask(id="t2", description="second", prompt="y"),
        ]

    def test_render_csv_has_header_and_rows(self):
        csv_text = PH.render_csv(self._sample_results())
        lines = csv_text.strip().splitlines()
        self.assertGreaterEqual(len(lines), 5)  # header + 4 rows
        self.assertIn("task_id", lines[0])
        self.assertIn("provider", lines[0])

    def test_render_markdown_has_winner_columns(self):
        md = PH.render_markdown(self._sample_results(), self._sample_tasks())
        self.assertIn("Parity Harness Report", md)
        self.assertIn("Winner (cost)", md)
        self.assertIn("qwen", md)
        self.assertIn("claude", md)
        # Qwen is cheaper on both tasks
        self.assertIn("Cost ratio", md)

    def test_emit_jsonl_writes_one_record_per_result(self):
        results = self._sample_results()
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "out.jsonl"
            PH.emit_jsonl(results, path, run_id="abcdef")
            lines = path.read_text().strip().splitlines()
            self.assertEqual(len(lines), 4)
            for line in lines:
                rec = json.loads(line)
                self.assertIn("task_id", rec)
                self.assertIn("provider", rec)
                self.assertEqual(rec["run_id"], "abcdef")
                self.assertIn("ts", rec)


class TestCLI(unittest.TestCase):

    def test_cli_missing_tasks_returns_2(self):
        rc = PH.main(["--tasks", "/nonexistent/path/nope.yaml"])
        self.assertEqual(rc, 2)

    def test_cli_dry_run_renders_no_api_calls(self):
        """--dry-run must not import or invoke any provider."""
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as fh:
            fh.write(SMOKE_YAML)
            yaml_path = fh.name

        with tempfile.TemporaryDirectory() as td:
            jsonl = Path(td) / "parity.jsonl"
            csv_path = Path(td) / "out.csv"
            report = Path(td) / "out.md"

            # Capture stdout; dry-run should succeed without touching network.
            with patch.object(PH, "run_via_qwen") as qmock, \
                 patch.object(PH, "run_via_claude") as cmock:
                rc = PH.main([
                    "--tasks", yaml_path,
                    "--jsonl", str(jsonl),
                    "--csv", str(csv_path),
                    "--report", str(report),
                    "--dry-run",
                ])
                qmock.assert_not_called()
                cmock.assert_not_called()

            self.assertEqual(rc, 0)
            self.assertTrue(jsonl.exists())
            self.assertTrue(csv_path.exists())
            self.assertTrue(report.exists())
            # 2 tasks * 2 providers = 4 records
            lines = jsonl.read_text().strip().splitlines()
            self.assertEqual(len(lines), 4)

    def test_cli_mutually_exclusive_flags(self):
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as fh:
            fh.write(SMOKE_YAML)
            yaml_path = fh.name
        rc = PH.main([
            "--tasks", yaml_path,
            "--only-qwen", "--only-claude",
            "--dry-run",
        ])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
