"""Telemetry aggregator — closes the data-lake-without-consumers gap (ADR-304).

Reads SLO declarations from manifests/observability-slo.yaml, evaluates each
against the declared source stream, and emits findings to the control-plane
remediation queue (the existing consumer per ADR-247/275).

Pure stdlib + pyyaml. No subprocess, no network.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

SCHEMA_VERSION = "telemetry-aggregator/v1"
REMEDIATION_SCHEMA = "control-plane-remediation/v1"

# ─── Data types ──────────────────────────────────────────────────────────────


@dataclass
class Finding:
    slo_id: str
    metric_value: float | None
    target: float | None
    target_comparator: str  # "<" or ">=" or "info"
    severity: str
    stable_id: str
    timestamp: str
    rationale: str
    window_summary: dict = field(default_factory=dict)
    code: str = "telemetry-slo-breach"
    message: str = ""

    def to_remediation_record(self) -> dict:
        """Serialize to the control-plane-remediation/v1 schema."""
        return {
            "adr": "ADR-304",
            "audit_id": "telemetry-aggregator",
            "code": self.code,
            "created_at": self.timestamp,
            "event": "proposed",
            "message": self.message
            or (
                f"SLO {self.slo_id}: measured={self.metric_value} "
                f"target {self.target_comparator} {self.target}"
            ),
            "safe_class": None,
            "schema_version": REMEDIATION_SCHEMA,
            "severity": self.severity,
            "stable_id": self.stable_id,
            "status": "queued",
            "slo_id": self.slo_id,
            "metric_value": self.metric_value,
            "target": self.target,
            "target_comparator": self.target_comparator,
            "rationale": self.rationale,
            "window_summary": self.window_summary,
        }


@dataclass
class AggregationReport:
    schema_version: str
    generated_at: str
    repo_root: str
    slo_manifest: str
    evaluations: list[dict]
    findings: list[Finding]

    def to_snapshot_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "repo_root": self.repo_root,
            "slo_manifest": self.slo_manifest,
            "evaluations": self.evaluations,
            "findings": [asdict(f) for f in self.findings],
            "summary": {
                "n_evaluations": len(self.evaluations),
                "n_findings": len(self.findings),
                "n_breaches": sum(
                    1 for f in self.findings if f.code == "telemetry-slo-breach"
                ),
                "n_stream_missing": sum(
                    1 for f in self.findings if f.code == "telemetry-stream-missing"
                ),
                "n_proposals": sum(
                    1
                    for f in self.findings
                    if f.code == "telemetry-self-tuning-proposal"
                ),
            },
        }


# ─── Schema validation ───────────────────────────────────────────────────────


REQUIRED_SLO_FIELDS = {"id", "source_stream", "metric", "severity_on_breach", "rationale"}


def validate_slo_manifest(manifest: dict) -> None:
    """Strict validation. Raises ValueError on missing fields."""
    if manifest.get("schema_version") != "observability-slo/v1":
        raise ValueError(
            f"Unsupported schema_version: {manifest.get('schema_version')!r}"
        )
    slos = manifest.get("slos") or []
    if not isinstance(slos, list) or not slos:
        raise ValueError("Manifest must declare a non-empty 'slos' list")
    ids = set()
    for idx, slo in enumerate(slos):
        if not isinstance(slo, dict):
            raise ValueError(f"slos[{idx}] must be a mapping")
        missing = REQUIRED_SLO_FIELDS - slo.keys()
        if missing:
            raise ValueError(f"slos[{idx}] missing fields: {sorted(missing)}")
        if slo["id"] in ids:
            raise ValueError(f"Duplicate SLO id: {slo['id']}")
        ids.add(slo["id"])
        if "target_lt" not in slo and "target_gte" not in slo:
            raise ValueError(
                f"slos[{idx}] ({slo['id']}) must declare 'target_lt' or 'target_gte'"
            )
        if "target_lt" in slo and "target_gte" in slo:
            raise ValueError(
                f"slos[{idx}] ({slo['id']}) cannot declare both 'target_lt' and 'target_gte'"
            )


# ─── JSONL reading ───────────────────────────────────────────────────────────


def read_jsonl(path: Path, tail: int | None = None) -> list[dict]:
    """Read JSONL. Returns [] if missing/empty. Skips malformed lines silently."""
    if not path.exists():
        return []
    records: list[dict] = []
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    if tail is not None and len(records) > tail:
        records = records[-tail:]
    return records


# ─── Filter and metric evaluation ────────────────────────────────────────────


_FILTER_TOKEN = re.compile(r'(\w+)\s*==\s*"([^"]*)"')


def _compile_filter(expr: str | None) -> Callable[[dict], bool]:
    """Compile a tiny filter DSL: `field == "value" [or|and field == "value"]...`.

    Pure-Python, no eval. Supports a single boolean operator level."""
    if not expr:
        return lambda rec: True
    expr = expr.strip()
    # Split on top-level 'or' / 'and' (single-level only)
    if " or " in expr:
        parts = expr.split(" or ")
        compiled = [_compile_filter(p.strip()) for p in parts]
        return lambda rec: any(p(rec) for p in compiled)
    if " and " in expr:
        parts = expr.split(" and ")
        compiled = [_compile_filter(p.strip()) for p in parts]
        return lambda rec: all(p(rec) for p in compiled)
    m = _FILTER_TOKEN.fullmatch(expr)
    if not m:
        raise ValueError(f"Unsupported filter expression: {expr!r}")
    field_name, value = m.group(1), m.group(2)
    return lambda rec: rec.get(field_name) == value


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    s = sorted(values)
    if len(s) == 1:
        return float(s[0])
    k = (len(s) - 1) * q
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(s[int(k)])
    return float(s[f] + (s[c] - s[f]) * (k - f))


def _get_nested(record: dict, dotted_path: str) -> Any:
    cur: Any = record
    for part in dotted_path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur



def _is_no_provider_skip(record: dict) -> bool:
    """True when a row represents provider-unavailable skip, not a failed call."""
    if record.get("provider_used") == "none" or record.get("provider") == "none":
        err = str(record.get("error") or "").lower()
        if "no providers" in err or ("provider" in err and "unavailable" in err):
            return True
    return False


_PERCENTILE_RE = re.compile(r"percentile\(\s*(\w+)\s*,\s*([0-9.]+)\s*\)")


def _parse_window(window: str | None) -> int | None:
    if not window:
        return None
    m = re.fullmatch(r"last_(\d+)_records", window.strip())
    return int(m.group(1)) if m else None


def compute_metric(slo: dict, records: list[dict]) -> tuple[float | None, dict]:
    """Returns (value, window_summary). value=None if undefined."""
    metric_expr: str = slo["metric"]
    summary: dict = {"n_samples": len(records)}

    # percentile(field, q)
    m = _PERCENTILE_RE.fullmatch(metric_expr.strip())
    if m:
        field_name, q = m.group(1), float(m.group(2))
        vals = [
            float(r[field_name])
            for r in records
            if isinstance(r.get(field_name), (int, float))
        ]
        summary["n_numeric"] = len(vals)
        if not vals:
            return None, summary
        summary["p50"] = _percentile(vals, 0.5)
        summary["p95"] = _percentile(vals, 0.95)
        summary["p99"] = _percentile(vals, 0.99)
        summary["max"] = float(max(vals))
        return _percentile(vals, q), summary

    # success_ratio: count(success == True) / count(actionable records).
    # Dispatch/enrichment calls made when no provider is configured are an
    # availability/configuration skip, not a model-quality failure. Exclude
    # those from success-ratio math so provider-off machines do not create
    # false SLO breaches; a separate provider-availability SLO can own that.
    if metric_expr.strip() == "success_ratio":
        actionable = [r for r in records if not _is_no_provider_skip(r)]
        n = len(actionable)
        summary["n_skipped_no_provider"] = len(records) - n
        if n == 0:
            return None, summary
        n_ok = sum(1 for r in actionable if r.get("success") is True)
        summary["n_success"] = n_ok
        summary["n_actionable"] = n
        return n_ok / n, summary

    # cache_hit_ratio: cache_hit == True / count
    if metric_expr.strip() == "cache_hit_ratio":
        n = len(records)
        if n == 0:
            return None, summary
        n_hit = sum(1 for r in records if r.get("cache_hit") is True)
        summary["n_cache_hit"] = n_hit
        return n_hit / n, summary

    # exit_success_ratio: exit_code == 0 / count
    if metric_expr.strip() == "exit_success_ratio":
        n = len(records)
        if n == 0:
            return None, summary
        n_ok = sum(1 for r in records if r.get("exit_code") == 0)
        summary["n_exit_success"] = n_ok
        return n_ok / n, summary

    # allow_ratio: allowed == True / count
    if metric_expr.strip() == "allow_ratio":
        n = len(records)
        if n == 0:
            return None, summary
        n_allowed = sum(1 for r in records if r.get("allowed") is True)
        summary["n_allowed"] = n_allowed
        return n_allowed / n, summary

    # latest.<dotted.path>
    if metric_expr.startswith("latest."):
        if not records:
            return None, summary
        path = metric_expr[len("latest.") :]
        val = _get_nested(records[-1], path)
        if isinstance(val, (int, float)):
            return float(val), summary
        return None, summary

    raise ValueError(f"Unsupported metric expression: {metric_expr!r}")


# ─── Aggregation core ────────────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _window_bucket(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H")


def _stable_id(slo_id: str, window_bucket: str, value: float | None) -> str:
    rounded = "na" if value is None else f"{round(value, 2)}"
    raw = f"{slo_id}|{window_bucket}|{rounded}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def aggregate_streams(
    repo_root: Path,
    slo_manifest: Path,
    *,
    now: datetime | None = None,
    enable_self_tuning: bool = True,
    remediation_queue: Path | None = None,
) -> AggregationReport:
    """Evaluate every SLO declared in slo_manifest against its source stream.

    Lazy: missing/empty streams emit an info finding, not a crash.
    Idempotent: stable_id is derived from (slo_id, hour bucket, rounded value).
    """
    with slo_manifest.open("r", encoding="utf-8") as fh:
        manifest = yaml.safe_load(fh)
    validate_slo_manifest(manifest)

    timestamp = _now_iso()
    bucket = _window_bucket(now)
    evaluations: list[dict] = []
    findings: list[Finding] = []

    for slo in manifest["slos"]:
        stream_path = repo_root / slo["source_stream"]
        if not stream_path.exists() or stream_path.stat().st_size == 0:
            sid = _stable_id(slo["id"], bucket, None)
            findings.append(
                Finding(
                    slo_id=slo["id"],
                    metric_value=None,
                    target=None,
                    target_comparator="info",
                    severity="info",
                    stable_id=sid,
                    timestamp=timestamp,
                    rationale=slo["rationale"],
                    window_summary={"reason": "stream_missing_or_empty"},
                    code="telemetry-stream-missing",
                    message=f"Source stream not present: {slo['source_stream']}",
                )
            )
            evaluations.append(
                {
                    "slo_id": slo["id"],
                    "status": "stream_missing",
                    "stream": slo["source_stream"],
                }
            )
            continue

        window_n = _parse_window(slo.get("window"))
        # Correct ordering: filter the source stream first, then apply the
        # declared window to the matching records. Applying `tail` before the
        # filter made sparse streams look like `no_data` whenever the last N
        # global records were unrelated noise (for example SubagentStart mixed
        # into a busy hook-timing.jsonl stream).
        records = read_jsonl(stream_path)

        filter_fn = _compile_filter(slo.get("filter"))
        filtered_all = [r for r in records if filter_fn(r)]
        filtered = (
            filtered_all[-window_n:]
            if window_n is not None and len(filtered_all) > window_n
            else filtered_all
        )

        value, summary = compute_metric(slo, filtered)
        summary["n_records_read"] = len(records)
        summary["n_matched_before_window"] = len(filtered_all)
        if window_n is not None:
            summary["window_records"] = window_n
        if window_n is not None and len(filtered_all) > len(filtered):
            # ADR-309: current regression windows must not be blocked forever by
            # old local incidents, but those incidents still need to remain
            # visible to operators. Attach an all-matched diagnostic summary so
            # snapshots/status can show historical tail evidence without using
            # it as the current SLO value.
            _, all_matched_summary = compute_metric(slo, filtered_all)
            summary["all_matched_summary"] = all_matched_summary
        if value is None:
            evaluations.append(
                {
                    "slo_id": slo["id"],
                    "status": "no_data",
                    "stream": slo["source_stream"],
                    "window_summary": summary,
                }
            )
            continue

        if "target_lt" in slo:
            target = float(slo["target_lt"])
            comparator = "<"
            breach = not (value < target)
        else:
            target = float(slo["target_gte"])
            comparator = ">="
            breach = not (value >= target)

        evaluations.append(
            {
                "slo_id": slo["id"],
                "status": "breach" if breach else "pass",
                "stream": slo["source_stream"],
                "value": value,
                "target": target,
                "comparator": comparator,
                "window_summary": summary,
            }
        )

        if breach:
            sid = _stable_id(slo["id"], bucket, value)
            findings.append(
                Finding(
                    slo_id=slo["id"],
                    metric_value=value,
                    target=target,
                    target_comparator=comparator,
                    severity=slo["severity_on_breach"],
                    stable_id=sid,
                    timestamp=timestamp,
                    rationale=slo["rationale"],
                    window_summary=summary,
                    code="telemetry-slo-breach",
                    message=(
                        f"SLO {slo['id']} breached: measured={value:.2f} "
                        f"target {comparator} {target}"
                    ),
                )
            )

    # Slice 3: self-tuning proposer
    if enable_self_tuning:
        queue_path = remediation_queue or (
            repo_root / ".cognitive-os/tasks/control-plane-remediation.jsonl"
        )
        proposals = _propose_self_tuning(
            manifest, findings, queue_path, repo_root, timestamp
        )
        findings.extend(proposals)

    return AggregationReport(
        schema_version=SCHEMA_VERSION,
        generated_at=timestamp,
        repo_root=str(repo_root),
        slo_manifest=str(slo_manifest),
        evaluations=evaluations,
        findings=findings,
    )


# ─── Slice 3: self-tuning proposer ───────────────────────────────────────────


def _read_remediation_history(queue_path: Path) -> list[dict]:
    return read_jsonl(queue_path)


def _propose_self_tuning(
    manifest: dict,
    current_findings: list[Finding],
    queue_path: Path,
    repo_root: Path,
    timestamp: str,
) -> list[Finding]:
    """Emit `telemetry-self-tuning-proposal` findings when:
      - same slo_id breached for >=3 consecutive aggregator runs (queue history)
      - SLO's source stream is hook-timing.jsonl
      - offending hook in recent records has stdout_bytes == 0
        (skip silently if stdout_bytes field absent — graceful for current
         hook-timing-wrapper schema which does not yet emit stdout_bytes).
    """
    proposals: list[Finding] = []
    if not current_findings:
        return proposals

    slo_by_id = {s["id"]: s for s in manifest["slos"]}
    history = _read_remediation_history(queue_path)

    # group history by slo_id, take last N breach entries
    history_by_slo: dict[str, list[dict]] = {}
    for rec in history:
        sid = rec.get("slo_id") or ""
        if sid and rec.get("code") == "telemetry-slo-breach":
            history_by_slo.setdefault(sid, []).append(rec)

    for finding in current_findings:
        if finding.code != "telemetry-slo-breach":
            continue
        slo = slo_by_id.get(finding.slo_id)
        if not slo:
            continue
        if "hook-timing.jsonl" not in slo.get("source_stream", ""):
            continue

        prior = history_by_slo.get(finding.slo_id, [])
        # current + prior must total >= 3 distinct windows
        prior_buckets = {
            _bucket_from_timestamp(r.get("created_at", ""))
            for r in prior
            if r.get("created_at")
        }
        current_bucket = _bucket_from_timestamp(finding.timestamp)
        all_buckets = prior_buckets | {current_bucket}
        if len(all_buckets) < 3:
            continue

        # Identify offending hook from filter / SLO id heuristic
        offending_hook = _infer_hook_name(slo)
        if not offending_hook:
            continue

        # Check stdout_bytes signal
        hook_timing = repo_root / ".cognitive-os/metrics/hook-timing.jsonl"
        recent_all = [
            r for r in read_jsonl(hook_timing) if r.get("hook") == offending_hook
        ]
        relevant = recent_all[-500:]
        if not relevant:
            continue
        has_stdout_field = any("stdout_bytes" in r for r in relevant)
        if not has_stdout_field:
            # Field absent in schema — skip proposal type gracefully.
            continue
        stdout_emitters = [
            r for r in relevant if isinstance(r.get("stdout_bytes"), (int, float))
            and r["stdout_bytes"] > 0
        ]
        if stdout_emitters:
            continue

        sid = hashlib.sha256(
            f"self-tune|{offending_hook}".encode("utf-8")
        ).hexdigest()[:16]
        proposal = Finding(
            slo_id=finding.slo_id,
            metric_value=finding.metric_value,
            target=finding.target,
            target_comparator=finding.target_comparator,
            severity="warn",
            stable_id=f"telemetry-self-tune/{offending_hook}",
            timestamp=timestamp,
            rationale=(
                f"Hook {offending_hook} breached {finding.slo_id} for "
                f"{len(all_buckets)} consecutive windows and emits no stdout — "
                f"safe to promote to async."
            ),
            window_summary={
                "consecutive_breach_windows": len(all_buckets),
                "offending_hook": offending_hook,
            },
            code="telemetry-self-tuning-proposal",
            message=(
                f"Hook {offending_hook} breached SLO {finding.slo_id} for "
                f"{len(all_buckets)} consecutive windows and emits no stdout — "
                f"propose promoting to async in "
                f"scripts/_lib/settings-driver-claude-code.sh."
            ),
        )
        # Attach proposed_change as an extra field in window_summary for serialization.
        proposal.window_summary["proposed_change"] = {
            "file": "scripts/_lib/settings-driver-claude-code.sh",
            "hook": f"{offending_hook}.sh",
            "from": "false",
            "to": "true",
        }
        proposal.window_summary["manual_application_command"] = (
            "Run: bash scripts/apply-efficiency-profile.sh standard "
            "after editing the driver."
        )
        proposals.append(proposal)

    return proposals


def _bucket_from_timestamp(ts: str) -> str:
    # `2026-05-13T22:48:00Z` -> `2026-05-13T22`
    return ts[:13] if len(ts) >= 13 else ts


def _infer_hook_name(slo: dict) -> str | None:
    """Best-effort: extract hook name from filter expression."""
    expr = slo.get("filter") or ""
    m = re.search(r'hook\s*==\s*"([^"]+)"', expr)
    if m:
        return m.group(1)
    return None


# ─── Output helpers ──────────────────────────────────────────────────────────


def write_snapshot(report: AggregationReport, snapshot_path: Path) -> None:
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    with snapshot_path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(
            report.to_snapshot_dict(), fh, sort_keys=False, default_flow_style=False
        )


def append_findings_idempotent(
    findings: list[Finding], queue_path: Path
) -> tuple[int, int]:
    """Append findings to remediation queue. Skips entries whose stable_id
    is already present. Returns (n_appended, n_skipped)."""
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    existing_ids: set[str] = set()
    if queue_path.exists():
        for rec in read_jsonl(queue_path):
            sid = rec.get("stable_id")
            if sid:
                existing_ids.add(sid)
    appended = 0
    skipped = 0
    with queue_path.open("a", encoding="utf-8") as fh:
        for f in findings:
            if f.stable_id in existing_ids:
                skipped += 1
                continue
            fh.write(json.dumps(f.to_remediation_record(), ensure_ascii=False) + "\n")
            existing_ids.add(f.stable_id)
            appended += 1
    return appended, skipped
