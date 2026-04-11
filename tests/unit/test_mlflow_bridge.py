"""Unit tests for MLflowBridge — all pass whether or not mlflow is installed."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestIsAvailableCheck:
    def test_returns_bool(self):
        from lib.mlflow_bridge import MLflowBridge
        result = MLflowBridge.is_available()
        assert isinstance(result, bool)

    def test_true_when_mlflow_importable(self):
        fake_mlflow = MagicMock()
        with patch.dict(sys.modules, {"mlflow": fake_mlflow}):
            from importlib import reload
            import lib.mlflow_bridge as mod
            reload(mod)
            assert mod.MLflowBridge.is_available() is True

    def test_false_when_mlflow_missing(self):
        # Simulate ImportError by temporarily removing mlflow from sys.modules
        saved = sys.modules.pop("mlflow", None)
        try:
            # Patch the import inside is_available
            import builtins
            real_import = builtins.__import__

            def fake_import(name, *args, **kwargs):
                if name == "mlflow":
                    raise ImportError("no mlflow")
                return real_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=fake_import):
                from importlib import reload
                import lib.mlflow_bridge as mod
                reload(mod)
                assert mod.MLflowBridge.is_available() is False
        finally:
            if saved is not None:
                sys.modules["mlflow"] = saved


class TestGracefulWithoutMlflow:
    """All public methods must succeed even when mlflow is absent."""

    def _bridge_no_mlflow(self):
        from lib.mlflow_bridge import MLflowBridge
        b = MLflowBridge.__new__(MLflowBridge)
        b._tracking_uri = "sqlite:///mlflow.db"
        b._mlflow = None  # simulate not installed
        return b

    def test_sync_cost_events_returns_zeros(self):
        b = self._bridge_no_mlflow()
        result = b.sync_cost_events("/nonexistent")
        assert result == {"synced": 0, "skipped": 0, "errors": 0}

    def test_sync_skill_metrics_returns_zeros(self):
        b = self._bridge_no_mlflow()
        result = b.sync_skill_metrics("/nonexistent")
        assert result == {"synced": 0, "skipped": 0, "errors": 0}

    def test_log_agent_run_does_not_raise(self):
        b = self._bridge_no_mlflow()
        b.log_agent_run("test", "sonnet", 100, 500, True, 0.01)

    def test_log_session_summary_does_not_raise(self):
        b = self._bridge_no_mlflow()
        b.log_session_summary("sess-1", 3, 0.15, 5000)


class TestLogAgentRunSchema:
    def test_calls_mlflow_with_correct_fields(self):
        fake_mlflow = MagicMock()
        fake_run_ctx = MagicMock()
        fake_mlflow.start_run.return_value.__enter__ = MagicMock(return_value=fake_run_ctx)
        fake_mlflow.start_run.return_value.__exit__ = MagicMock(return_value=False)
        fake_mlflow.get_experiment_by_name.return_value = MagicMock(experiment_id="1")

        from lib.mlflow_bridge import MLflowBridge
        b = MLflowBridge.__new__(MLflowBridge)
        b._mlflow = fake_mlflow
        b._tracking_uri = "sqlite:///mlflow.db"

        b.log_agent_run("my-agent", "sonnet", tokens=1200, duration_ms=3000, success=True, cost_usd=0.07)

        fake_mlflow.log_metrics.assert_called_once()
        metrics_call = fake_mlflow.log_metrics.call_args[0][0]
        assert "tokens" in metrics_call
        assert "duration_ms" in metrics_call
        assert "success" in metrics_call
        assert "cost_usd" in metrics_call
        assert metrics_call["tokens"] == 1200.0
        assert metrics_call["success"] == 1.0


class TestSyncCostEventsReadsJsonl:
    def test_reads_real_jsonl_format(self):
        fake_mlflow = MagicMock()
        fake_mlflow.start_run.return_value.__enter__ = MagicMock(return_value=MagicMock())
        fake_mlflow.start_run.return_value.__exit__ = MagicMock(return_value=False)
        fake_mlflow.get_experiment_by_name.return_value = MagicMock(experiment_id="1")

        records = [
            {"timestamp": "2026-04-10T14:30:31Z", "agent": "Test agent", "model": "sonnet",
             "estimated_cost_usd": 0.028, "tokens_estimated": 1900, "is_estimate": True},
            {"timestamp": "2026-04-10T14:40:00Z", "agent": "Another agent", "model": "haiku",
             "estimated_cost_usd": 0.003, "tokens_estimated": 500, "is_estimate": True},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            metrics_dir = Path(tmpdir) / "metrics"
            metrics_dir.mkdir()
            _write_jsonl(metrics_dir / "cost-events.jsonl", records)

            from lib.mlflow_bridge import MLflowBridge
            b = MLflowBridge.__new__(MLflowBridge)
            b._mlflow = fake_mlflow
            b._tracking_uri = "sqlite:///mlflow.db"
            b._SYNCED_IDS_FILE = str(Path(tmpdir) / ".mlflow-synced-ids")

            result = b.sync_cost_events(str(metrics_dir))
            assert result["synced"] == 2
            assert result["errors"] == 0


class TestSyncSkillMetricsReadsJsonl:
    def test_reads_real_jsonl_format(self):
        fake_mlflow = MagicMock()
        fake_mlflow.start_run.return_value.__enter__ = MagicMock(return_value=MagicMock())
        fake_mlflow.start_run.return_value.__exit__ = MagicMock(return_value=False)
        fake_mlflow.get_experiment_by_name.return_value = MagicMock(experiment_id="2")

        records = [
            {"timestamp": "2026-04-11T15:06:32Z", "skill": "sdd-apply", "model": "sonnet",
             "tokens": 2000, "duration_ms": 1500, "success": True},
            {"timestamp": "2026-04-11T15:07:20Z", "skill": "sdd-verify", "model": "sonnet",
             "tokens": 800, "duration_ms": 900, "success": False},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            metrics_dir = Path(tmpdir) / "metrics"
            metrics_dir.mkdir()
            _write_jsonl(metrics_dir / "skill-metrics.jsonl", records)

            from lib.mlflow_bridge import MLflowBridge
            b = MLflowBridge.__new__(MLflowBridge)
            b._mlflow = fake_mlflow
            b._tracking_uri = "sqlite:///mlflow.db"
            b._SYNCED_IDS_FILE = str(Path(tmpdir) / ".mlflow-synced-ids")

            result = b.sync_skill_metrics(str(metrics_dir))
            assert result["synced"] == 2
            assert result["errors"] == 0


class TestFormatSyncReport:
    def test_readable_string(self):
        from lib.mlflow_bridge import MLflowBridge
        b = MLflowBridge.__new__(MLflowBridge)
        b._mlflow = None
        report = b.format_sync_report({"synced": 42, "skipped": 5, "errors": 0})
        assert "42" in report
        assert "synced" in report
        assert "0" in report

    def test_format_with_errors(self):
        from lib.mlflow_bridge import MLflowBridge
        b = MLflowBridge.__new__(MLflowBridge)
        b._mlflow = None
        report = b.format_sync_report({"synced": 10, "skipped": 2, "errors": 3})
        assert "3" in report
        assert "error" in report.lower()


class TestSessionSummarySchema:
    def test_correct_experiment_structure(self):
        fake_mlflow = MagicMock()
        fake_mlflow.start_run.return_value.__enter__ = MagicMock(return_value=MagicMock())
        fake_mlflow.start_run.return_value.__exit__ = MagicMock(return_value=False)
        fake_mlflow.get_experiment_by_name.return_value = MagicMock(experiment_id="3")

        from lib.mlflow_bridge import MLflowBridge
        b = MLflowBridge.__new__(MLflowBridge)
        b._mlflow = fake_mlflow
        b._tracking_uri = "sqlite:///mlflow.db"

        b.log_session_summary("session-abc", agents_launched=5, total_cost=0.35, total_tokens=8000)

        fake_mlflow.log_metrics.assert_called_once()
        metrics = fake_mlflow.log_metrics.call_args[0][0]
        assert "agents_launched" in metrics
        assert "total_cost_usd" in metrics
        assert "total_tokens" in metrics
        assert metrics["agents_launched"] == 5.0
        assert metrics["total_cost_usd"] == 0.35


class TestDeduplication:
    def test_same_event_not_synced_twice(self):
        fake_mlflow = MagicMock()
        fake_mlflow.start_run.return_value.__enter__ = MagicMock(return_value=MagicMock())
        fake_mlflow.start_run.return_value.__exit__ = MagicMock(return_value=False)
        fake_mlflow.get_experiment_by_name.return_value = MagicMock(experiment_id="1")

        records = [
            {"timestamp": "2026-04-10T14:30:31Z", "agent": "Test agent", "model": "sonnet",
             "estimated_cost_usd": 0.028, "tokens_estimated": 1900},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            metrics_dir = Path(tmpdir) / "metrics"
            metrics_dir.mkdir()
            _write_jsonl(metrics_dir / "cost-events.jsonl", records)
            synced_ids_file = str(Path(tmpdir) / ".mlflow-synced-ids")

            from lib.mlflow_bridge import MLflowBridge
            b = MLflowBridge.__new__(MLflowBridge)
            b._mlflow = fake_mlflow
            b._tracking_uri = "sqlite:///mlflow.db"
            b._SYNCED_IDS_FILE = synced_ids_file

            # First sync
            r1 = b.sync_cost_events(str(metrics_dir))
            assert r1["synced"] == 1
            assert r1["skipped"] == 0

            # Second sync — same data
            r2 = b.sync_cost_events(str(metrics_dir))
            assert r2["synced"] == 0
            assert r2["skipped"] == 1
