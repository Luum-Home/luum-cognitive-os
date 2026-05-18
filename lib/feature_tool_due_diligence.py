# SCOPE: os-only
"""ADR-255 feature-to-external-tool due-diligence helpers."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = "feature-tool-due-diligence-audit/v1"
BENCHMARK_SCHEMA_VERSION = "feature-vs-tool-benchmark/v1"
SOURCE_FETCH_SCHEMA_VERSION = "external-source-fetch/v1"
GITHUB_RE = re.compile(r"https?://github\.com/([^/\s]+)/([^/#?\s]+)")


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    message: str
    capability_id: str | None = None
    tool_id: str | None = None
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"severity": self.severity, "code": self.code, "message": self.message}
        if self.capability_id:
            payload["capability_id"] = self.capability_id
        if self.tool_id:
            payload["tool_id"] = self.tool_id
        if self.details:
            payload["details"] = self.details
        return payload


def read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def write_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def display_path(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def repo_root(start: Path) -> Path:
    cur = start.resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / ".git").exists():
            return candidate
    return cur


def deepwiki_url_for_github(url: str) -> str | None:
    match = GITHUB_RE.search(url)
    if not match:
        return None
    owner, repo = match.group(1), match.group(2).removesuffix(".git")
    return f"https://deepwiki.com/{owner}/{repo}"


def capability_rows(capability_manifest: Path) -> list[dict[str, Any]]:
    data = read_yaml(capability_manifest)
    return list(data.get("capabilities", []) or [])


def due_diligence_records(manifest_path: Path) -> dict[str, dict[str, Any]]:
    data = read_yaml(manifest_path)
    return {str(row.get("capability_id")): row for row in data.get("features", []) or [] if row.get("capability_id")}


def scan_due_diligence(repo: Path, manifest_path: Path, capability_manifest: Path) -> dict[str, Any]:
    manifest = read_yaml(manifest_path)
    records = due_diligence_records(manifest_path)
    findings: list[Finding] = []
    build_like = []
    for cap in capability_rows(capability_manifest):
        level = str(cap.get("reality_level", "")).upper()
        cid = str(cap.get("id", ""))
        if level in {"REAL", "PARTIAL"}:
            build_like.append(cid)
            record = records.get(cid)
            if not record:
                findings.append(Finding("warn", "missing-feature-due-diligence", "Capability lacks feature-to-external-tool due-diligence record; required before new public BUILD claims or major custom expansion.", cid))
                continue
            candidates = record.get("candidates", []) or []
            if not candidates and manifest.get("policy", {}).get("require_external_candidates", True):
                findings.append(Finding("block", "missing-external-candidates", "BUILD feature record has no external candidates.", cid))
            if not record.get("benchmark") and not record.get("non_benchmarkable_rationale"):
                findings.append(Finding("block", "missing-benchmark-or-rationale", "BUILD feature record needs benchmark pointer or explicit non-benchmarkable rationale.", cid))
            if not record.get("maintenance_cost"):
                findings.append(Finding("block", "missing-maintenance-cost", "BUILD feature record needs maintenance_cost.", cid))
            for candidate in candidates:
                tid = str(candidate.get("tool_id", ""))
                links = candidate.get("source_links", []) or []
                if not links:
                    findings.append(Finding("block", "candidate-missing-source-links", "External candidate lacks source links.", cid, tid))
                github_deepwiki = next((deepwiki_url_for_github(str(link)) for link in links if deepwiki_url_for_github(str(link))), None)
                if github_deepwiki and candidate.get("deepwiki_url") != github_deepwiki:
                    findings.append(Finding("warn", "candidate-deepwiki-url-mismatch", "DeepWiki URL should be derived from GitHub owner/repo.", cid, tid, {"expected": github_deepwiki, "actual": candidate.get("deepwiki_url")}))
                if not candidate.get("reason_not_build_replacement") and str(candidate.get("verdict", "")).upper() not in {"ADOPT", "REMOVE"}:
                    findings.append(Finding("warn", "candidate-missing-fit-rationale", "Candidate needs reason it does or does not replace COS custom feature.", cid, tid))
    finding_dicts = [finding.to_dict() for finding in findings]
    block = sum(1 for item in finding_dicts if item["severity"] == "block")
    warn = sum(1 for item in finding_dicts if item["severity"] == "warn")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "block" if block else "warn" if warn else "pass",
        "summary": {"build_like_capabilities": len(build_like), "records": len(records), "block": block, "warn": warn, "findings": len(finding_dicts)},
        "manifest": display_path(manifest_path),
        "capability_manifest": display_path(capability_manifest),
        "findings": finding_dicts,
    }


def _cache_dir(repo: Path, manifest_path: Path) -> Path:
    data = read_yaml(manifest_path)
    configured = Path(str(data.get("policy", {}).get("scratch_cache", ".cognitive-os/external-source-cache")))
    return configured if configured.is_absolute() else repo / configured


def safe_repo_dir(url: str) -> str:
    match = GITHUB_RE.search(url)
    if match:
        return f"{match.group(1)}__{match.group(2).removesuffix('.git')}"
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def fetch_external_source(repo: Path, manifest_path: Path, url: str, *, execute: bool = False) -> dict[str, Any]:
    cache = _cache_dir(repo, manifest_path)
    target = cache / safe_repo_dir(url)
    report: dict[str, Any] = {
        "schema_version": SOURCE_FETCH_SCHEMA_VERSION,
        "status": "planned",
        "url": url,
        "target": display_path(target),
        "deepwiki_url": deepwiki_url_for_github(url),
        "executed": execute,
    }
    if not execute:
        return report
    cache.mkdir(parents=True, exist_ok=True)
    if target.exists():
        proc = subprocess.run(["git", "-C", str(target), "fetch", "--depth", "1", "origin"], text=True, capture_output=True, check=False, timeout=120)
        report["operation"] = "fetch"
    else:
        proc = subprocess.run(["git", "clone", "--depth", "1", url, str(target)], text=True, capture_output=True, check=False, timeout=180)
        report["operation"] = "clone"
    report["returncode"] = proc.returncode
    report["stderr_tail"] = "\n".join((proc.stderr or "").splitlines()[-10:])
    report["status"] = "pass" if proc.returncode == 0 else "block"
    if target.exists():
        head = subprocess.run(["git", "-C", str(target), "rev-parse", "HEAD"], text=True, capture_output=True, check=False, timeout=60)
        report["head"] = head.stdout.strip() if head.returncode == 0 else None
    return report


def benchmark_due_diligence(manifest_path: Path) -> dict[str, Any]:
    data = read_yaml(manifest_path)
    findings: list[Finding] = []
    for record in data.get("features", []) or []:
        cid = str(record.get("capability_id", ""))
        if not record.get("benchmark") and not record.get("non_benchmarkable_rationale"):
            findings.append(Finding("block", "feature-missing-benchmark", "Feature record lacks benchmark or non-benchmarkable rationale.", cid))
        for candidate in record.get("candidates", []) or []:
            tid = str(candidate.get("tool_id", ""))
            if not candidate.get("source_links"):
                findings.append(Finding("block", "tool-missing-source-link", "Candidate tool lacks source links.", cid, tid))
            if not candidate.get("license"):
                findings.append(Finding("warn", "tool-missing-license", "Candidate tool lacks license posture.", cid, tid))
    finding_dicts = [finding.to_dict() for finding in findings]
    block = sum(1 for item in finding_dicts if item["severity"] == "block")
    warn = sum(1 for item in finding_dicts if item["severity"] == "warn")
    return {"schema_version": BENCHMARK_SCHEMA_VERSION, "status": "block" if block else "warn" if warn else "pass", "summary": {"block": block, "warn": warn, "findings": len(finding_dicts)}, "findings": finding_dicts}
