# SCOPE: os-only
"""MLflow bridge for Cognitive OS observability.

Syncs cost-events.jsonl and skill-metrics.jsonl to MLflow tracking.
Graceful if mlflow is not installed — all methods are safe no-ops.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class MLflowBridge:
    """Bridge between Cognitive OS metrics and MLflow tracking."""

    _SYNCED_IDS_FILE = ".cognitive-os/metrics/.mlflow-synced-ids"

    def __init__(self, tracking_uri: str = "sqlite:///mlflow.db"):
        """Initialize. Graceful if mlflow not installed."""
        self._tracking_uri = tracking_uri
        self._client: Any = None
        if self.is_available():
            try:
                import mlflow  # noqa: PLC0415
                mlflow.set_tracking_uri(tracking_uri)
                self._mlflow = mlflow
            except Exception:
                self._mlflow = None
        else:
            self._mlflow = None

    @staticmethod
    def is_available() -> bool:
        """Check if mlflow is installed."""
        try:
            import mlflow  # noqa: F401, PLC0415
            return True
        except ImportError:
            return False

    # ------------------------------------------------------------------
    # Deduplication helpers
    # ------------------------------------------------------------------

    def _load_synced_ids(self) -> set[str]:
        path = Path(self._SYNCED_IDS_FILE)
        if not path.exists():
            return set()
        try:
            return set(path.read_text().splitlines())
        except OSError:
            return set()

    def _save_synced_ids(self, ids: set[str]) -> None:
        path = Path(self._SYNCED_IDS_FILE)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("\n".join(sorted(ids)))
        except OSError:
            pass

    @staticmethod
    def _event_id(record: dict) -> str:
        """Stable content-hash ID for a JSONL record."""
        blob = json.dumps(record, sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()[:16]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def sync_cost_events(self, metrics_dir: str = ".cognitive-os/metrics") -> dict:
        """Read cost-events.jsonl and log to MLflow.

        Returns: {synced: int, skipped: int, errors: int}
        """
        result = {"synced": 0, "skipped": 0, "errors": 0}
        if not self._mlflow:
            return result
        path = Path(metrics_dir) / "cost-events.jsonl"
        if not path.exists():
            return result
        synced_ids = self._load_synced_ids()
        try:
            with path.open() as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        eid = self._event_id(record)
                        if eid in synced_ids:
                            result["skipped"] += 1
                            continue
                        with self._mlflow.start_run(
                            run_name=f"cost:{record.get('agent', 'unknown')[:40]}",
                            experiment_id=self._get_or_create_experiment("cos/cost-events"),
                        ):
                            self._mlflow.log_metrics({
                                "estimated_cost_usd": float(record.get("estimated_cost_usd", 0)),
                                "tokens_estimated": float(record.get("tokens_estimated", 0)),
                            })
                            self._mlflow.log_params({
                                "agent": str(record.get("agent", ""))[:250],
                                "model": str(record.get("model", "unknown")),
                                "timestamp": str(record.get("timestamp", "")),
                            })
                        synced_ids.add(eid)
                        result["synced"] += 1
                    except Exception:
                        result["errors"] += 1
        except OSError:
            result["errors"] += 1
        self._save_synced_ids(synced_ids)
        return result

    def sync_skill_metrics(self, metrics_dir: str = ".cognitive-os/metrics") -> dict:
        """Read skill-metrics.jsonl and log skill invocations to MLflow."""
        result = {"synced": 0, "skipped": 0, "errors": 0}
        if not self._mlflow:
            return result
        path = Path(metrics_dir) / "skill-metrics.jsonl"
        if not path.exists():
            return result
        synced_ids = self._load_synced_ids()
        try:
            with path.open() as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        eid = self._event_id(record)
                        if eid in synced_ids:
                            result["skipped"] += 1
                            continue
                        with self._mlflow.start_run(
                            run_name=f"skill:{record.get('skill', 'unknown')[:40]}",
                            experiment_id=self._get_or_create_experiment("cos/skill-metrics"),
                        ):
                            self._mlflow.log_metrics({
                                "tokens": float(record.get("tokens", 0)),
                                "duration_ms": float(record.get("duration_ms", 0)),
                                "success": 1.0 if record.get("success") else 0.0,
                            })
                            self._mlflow.log_params({
                                "skill": str(record.get("skill", ""))[:250],
                                "model": str(record.get("model", "unknown")),
                                "timestamp": str(record.get("timestamp", "")),
                            })
                        synced_ids.add(eid)
                        result["synced"] += 1
                    except Exception:
                        result["errors"] += 1
        except OSError:
            result["errors"] += 1
        self._save_synced_ids(synced_ids)
        return result

    def log_agent_run(
        self,
        agent_name: str,
        model: str,
        tokens: int,
        duration_ms: int,
        success: bool,
        cost_usd: float = 0,
    ) -> None:
        """Log a single agent run to MLflow. Call after each agent completion."""
        if not self._mlflow:
            return
        try:
            with self._mlflow.start_run(
                run_name=f"agent:{agent_name[:40]}",
                experiment_id=self._get_or_create_experiment("cos/agent-runs"),
            ):
                self._mlflow.log_metrics({
                    "tokens": float(tokens),
                    "duration_ms": float(duration_ms),
                    "success": 1.0 if success else 0.0,
                    "cost_usd": float(cost_usd),
                })
                self._mlflow.log_params({
                    "agent_name": agent_name[:250],
                    "model": model,
                })
        except Exception:
            pass

    def log_agent_completion(
        self,
        skill_name: str,
        task_type: str,
        trust_score: int,
        tokens_used: int,
        success: bool,
        task_id: str,
        model: str = "unknown",
        cost_usd: float = 0,
    ) -> None:
        """Log the agent-completion contract (agent metrics mirror)."""
        if not self._mlflow:
            return
        try:
            normalized_trust = max(0, min(100, int(trust_score))) / 100.0
            with self._mlflow.start_run(
                run_name=f"completion:{skill_name[:40]}",
                experiment_id=self._get_or_create_experiment("cos/agent-completions"),
            ):
                self._mlflow.log_metrics({
                    "trust_score": float(trust_score),
                    "trust_score_normalized": normalized_trust,
                    "tokens_used": float(tokens_used),
                    "success": 1.0 if success else 0.0,
                    "cost_usd": float(cost_usd),
                })
                self._mlflow.log_params({
                    "skill_name": skill_name[:250],
                    "task_type": task_type[:250],
                    "task_id": task_id[:250],
                    "model": model[:250],
                    "status": "success" if success else "failure",
                })
        except Exception:
            pass

    def log_session_summary(
        self,
        session_id: str,
        agents_launched: int,
        total_cost: float,
        total_tokens: int,
    ) -> None:
        """Log session-level summary as an MLflow experiment."""
        if not self._mlflow:
            return
        try:
            with self._mlflow.start_run(
                run_name=f"session:{session_id[:40]}",
                experiment_id=self._get_or_create_experiment("cos/sessions"),
            ):
                self._mlflow.log_metrics({
                    "agents_launched": float(agents_launched),
                    "total_cost_usd": float(total_cost),
                    "total_tokens": float(total_tokens),
                })
                self._mlflow.log_params({"session_id": session_id[:250]})
        except Exception:
            pass

    def format_sync_report(self, results: dict) -> str:
        """One-line: 'MLflow sync: 42 events synced, 0 errors'"""
        synced = results.get("synced", 0)
        errors = results.get("errors", 0)
        skipped = results.get("skipped", 0)
        return f"MLflow sync: {synced} events synced, {skipped} skipped, {errors} errors"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_or_create_experiment(self, name: str) -> str:
        """Return experiment ID, creating it if it does not exist."""
        exp = self._mlflow.get_experiment_by_name(name)
        if exp is not None:
            return exp.experiment_id
        return self._mlflow.create_experiment(name)
