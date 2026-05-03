#!/usr/bin/env python3
# SCOPE: both
"""Audit intentional shell error swallowing in hooks.

This is a control-plane gate for the `|| true`, `|| :`, and `2>/dev/null`
surface. Those patterns are sometimes legitimate for optional telemetry or
best-effort cleanup, but every occurrence must be represented in the allowlist
with a rationale and must not grow silently.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ALLOWLIST = REPO_ROOT / "manifests" / "silent-failure-allowlist.yaml"
DEFAULT_SCAN_ROOT = REPO_ROOT / "hooks"
PATTERNS = {
    "or_true": re.compile(r"\|\|\s*true(?:\s|$|[;#])"),
    "or_colon": re.compile(r"\|\|\s*:(?:\s|$|[;#])"),
    "stderr_devnull": re.compile(r"(?:^|\s)2>\s*/dev/null"),
}
VALID_CLASSES = {
    "optional_dependency",
    "metrics_best_effort",
    "cleanup_best_effort",
    "probe_best_effort",
    "legacy_audited",
}


@dataclass(frozen=True)
class Occurrence:
    path: str
    line: int
    pattern: str
    text: str


@dataclass(frozen=True)
class Finding:
    id: str
    severity: str
    path: str
    message: str
    details: dict[str, Any]


def scan(root: Path = DEFAULT_SCAN_ROOT, repo_root: Path = REPO_ROOT) -> list[Occurrence]:
    occurrences: list[Occurrence] = []
    if not root.exists():
        return occurrences
    for path in sorted(root.rglob("*.sh")):
        rel = str(path.relative_to(repo_root))
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            for name, regex in PATTERNS.items():
                if regex.search(line):
                    occurrences.append(Occurrence(rel, idx, name, stripped[:240]))
    return occurrences


def counts_by_path(occurrences: list[Occurrence]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for occ in occurrences:
        counts[occ.path] = counts.get(occ.path, 0) + 1
    return dict(sorted(counts.items()))


def load_allowlist(path: Path = DEFAULT_ALLOWLIST) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": 1, "entries": []}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {"schema_version": 1, "entries": []}


def allowlist_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    entries = data.get("entries", [])
    result: dict[str, dict[str, Any]] = {}
    if not isinstance(entries, list):
        return result
    for entry in entries:
        if isinstance(entry, dict) and isinstance(entry.get("path"), str):
            result[entry["path"]] = entry
    return result


def build_report(
    repo_root: Path = REPO_ROOT,
    scan_root: Path = DEFAULT_SCAN_ROOT,
    allowlist_path: Path = DEFAULT_ALLOWLIST,
) -> dict[str, Any]:
    occurrences = scan(scan_root, repo_root)
    counts = counts_by_path(occurrences)
    allowlist = allowlist_map(load_allowlist(allowlist_path))
    findings: list[Finding] = []

    for path, count in counts.items():
        entry = allowlist.get(path)
        if entry is None:
            findings.append(
                Finding(
                    "unclassified-silent-failure",
                    "fail",
                    path,
                    "silent-failure pattern exists without allowlist classification",
                    {"count": count},
                )
            )
            continue
        max_allowed = entry.get("max_occurrences")
        if not isinstance(max_allowed, int) or max_allowed < 0:
            findings.append(
                Finding(
                    "invalid-silent-failure-baseline",
                    "fail",
                    path,
                    "allowlist entry must declare non-negative max_occurrences",
                    {"value": max_allowed},
                )
            )
        elif count > max_allowed:
            findings.append(
                Finding(
                    "silent-failure-surface-increased",
                    "fail",
                    path,
                    "silent-failure patterns increased above audited baseline",
                    {"count": count, "max_occurrences": max_allowed},
                )
            )
        degradation_class = entry.get("degradation_class")
        if degradation_class not in VALID_CLASSES:
            findings.append(
                Finding(
                    "invalid-degradation-class",
                    "fail",
                    path,
                    "allowlist entry must classify why degradation is acceptable",
                    {"value": degradation_class, "valid": sorted(VALID_CLASSES)},
                )
            )
        rationale = entry.get("rationale")
        if not isinstance(rationale, str) or len(rationale.strip()) < 12:
            findings.append(
                Finding(
                    "missing-silent-failure-rationale",
                    "fail",
                    path,
                    "allowlist entry must explain why the swallowed failure is acceptable",
                    {},
                )
            )

    for path in sorted(set(allowlist) - set(counts)):
        findings.append(
            Finding(
                "stale-silent-failure-allowlist-entry",
                "warn",
                path,
                "allowlist entry has no matching current silent-failure patterns",
                {"max_occurrences": allowlist[path].get("max_occurrences")},
            )
        )

    fail_count = sum(1 for item in findings if item.severity == "fail")
    warn_count = sum(1 for item in findings if item.severity == "warn")
    return {
        "status": "fail" if fail_count else ("warn" if warn_count else "pass"),
        "scan_root": str(scan_root),
        "allowlist": str(allowlist_path),
        "pattern_names": sorted(PATTERNS),
        "file_count": len(counts),
        "occurrence_count": len(occurrences),
        "counts_by_path": counts,
        "sample_occurrences": [asdict(item) for item in occurrences[:50]],
        "findings": [asdict(item) for item in findings],
        "fail_count": fail_count,
        "warn_count": warn_count,
    }


def write_baseline(path: Path, counts: dict[str, int]) -> None:
    entries = [
        {
            "path": file_path,
            "max_occurrences": count,
            "degradation_class": "legacy_audited",
            "rationale": "Legacy best-effort degradation audited as baseline; increases require explicit review.",
        }
        for file_path, count in counts.items()
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"schema_version": 1, "entries": entries}, sort_keys=False), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allowlist", type=Path, default=DEFAULT_ALLOWLIST)
    parser.add_argument("--scan-root", type=Path, default=DEFAULT_SCAN_ROOT)
    parser.add_argument("--json", action="store_true", help="emit JSON report")
    parser.add_argument("--write-baseline", action="store_true", help="write allowlist from current scan")
    parser.add_argument("--fail-on-findings", action="store_true", help="exit non-zero on fail findings")
    args = parser.parse_args(argv)

    if args.write_baseline:
        write_baseline(args.allowlist, counts_by_path(scan(args.scan_root, REPO_ROOT)))

    report = build_report(REPO_ROOT, args.scan_root, args.allowlist)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"silent failure audit: {report['status']} files={report['file_count']} occurrences={report['occurrence_count']} fail={report['fail_count']} warn={report['warn_count']}")
        for finding in report["findings"][:20]:
            print(f"- {finding['severity'].upper()} {finding['id']} {finding['path']}: {finding['message']}")
    if args.fail_on_findings and report["fail_count"]:
        return 1
    return 0 if report["status"] != "fail" else 1


if __name__ == "__main__":
    raise SystemExit(main())
