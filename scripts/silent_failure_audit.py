#!/usr/bin/env python3
# SCOPE: os-only
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
VALID_TRANSFERABILITY_STATES = {
    "maintainer_cache",
    "documented_classification",
    "externally_reviewed",
}

CLASS_RATIONALES = {
    "optional_dependency": "Optional dependency or integration probe; absence must degrade without blocking the parent hook.",
    "metrics_best_effort": "Telemetry/JSONL writes are best effort and must never break the guarded user action.",
    "cleanup_best_effort": "Cleanup/reaper work is best effort; failures are surfaced by later hygiene or recovery checks.",
    "probe_best_effort": "Read-only environment/state probe; failure means unknown state, not an immediate hard block.",
    "legacy_audited": "Legacy silent degradation remains audited but needs manual classification before promotion.",
}
TRANSFERABILITY_ACTIONS = {
    "maintainer_cache": "Shape B blocker: requires second-maintainer or external review before this allowlist entry can be treated as transferable.",
    "documented_classification": "Shape A acceptable: classification is explicit; second maintainer may re-review before owning this surface.",
    "externally_reviewed": "Transferable: reviewed by someone other than the original maintainer or by an equivalent external process.",
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



def classify_occurrence(occurrence: Occurrence) -> str:
    text = occurrence.text.lower()
    path = occurrence.path.lower()
    if any(token in path for token in ("safe-jsonl", "metrics", "usage", "feedback", "capture", "learning")) or any(
        token in text for token in ("jsonl", "metrics", "safe_jsonl", "safe-jsonl", ">> $metrics", ">> metrics")
    ):
        return "metrics_best_effort"
    if any(token in text for token in ("command -v", "type -p", "source ", "python3 -", "import ", "jq ", "node ", "go ")):
        return "optional_dependency"
    if any(token in path for token in ("cleanup", "reap", "reaper", "worktree-remove", "drain")) or any(
        token in text for token in ("cleanup", "rm -", "rmdir", "kill ", "pkill", "wait ", "trap ", "git worktree prune", "unlock", "lock")
    ):
        return "cleanup_best_effort"
    if any(token in text for token in ("grep ", "git rev-parse", "git status", "git branch", "pgrep", "test ", "[ -", "[[ ", "cat ", "head ", "tail ", "find ")):
        return "probe_best_effort"
    return "legacy_audited"


def classify_path(path: str, occurrences: list[Occurrence]) -> str:
    from collections import Counter

    classes = [classify_occurrence(item) for item in occurrences if item.path == path]
    if not classes:
        return "legacy_audited"
    counts = Counter(classes)
    # Prefer a concrete class over legacy when tied.
    order = ["metrics_best_effort", "cleanup_best_effort", "optional_dependency", "probe_best_effort", "legacy_audited"]
    return sorted(counts, key=lambda cls: (-counts[cls], order.index(cls)))[0]

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
    class_counts: dict[str, int] = {name: 0 for name in sorted(VALID_CLASSES)}
    transferability_counts: dict[str, int] = {name: 0 for name in sorted(VALID_TRANSFERABILITY_STATES)}
    transferability_occurrences: dict[str, int] = {name: 0 for name in sorted(VALID_TRANSFERABILITY_STATES)}

    for entry in allowlist.values():
        cls = entry.get("degradation_class")
        if cls in class_counts:
            class_counts[cls] += 1

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
        transferability_state = entry.get("transferability_state")
        if transferability_state in transferability_counts:
            transferability_counts[transferability_state] += 1
            transferability_occurrences[transferability_state] += count
        else:
            findings.append(
                Finding(
                    "missing-transferability-state",
                    "fail",
                    path,
                    "allowlist entry must declare transferability_state so ADR-132 debt is explicit",
                    {"valid": sorted(VALID_TRANSFERABILITY_STATES), "value": transferability_state},
                )
            )
        owner = entry.get("owner")
        if not isinstance(owner, str) or len(owner.strip()) < 3:
            findings.append(
                Finding(
                    "missing-silent-failure-owner",
                    "fail",
                    path,
                    "allowlist entry must declare an accountable owner",
                    {},
                )
            )
        reviewed_on = entry.get("reviewed_on")
        if not isinstance(reviewed_on, str) or not re.match(r"^\d{4}-\d{2}-\d{2}$", reviewed_on):
            findings.append(
                Finding(
                    "missing-silent-failure-review-date",
                    "fail",
                    path,
                    "allowlist entry must declare reviewed_on as YYYY-MM-DD",
                    {"value": reviewed_on},
                )
            )
        shape_b_action = entry.get("shape_b_action")
        if not isinstance(shape_b_action, str) or len(shape_b_action.strip()) < 12:
            findings.append(
                Finding(
                    "missing-shape-b-action",
                    "fail",
                    path,
                    "allowlist entry must explain what makes this entry transferable or what must happen before Shape B",
                    {},
                )
            )
        elif transferability_state == "maintainer_cache":
            findings.append(
                Finding(
                    "shape-b-transferability-debt",
                    "info",
                    path,
                    "allowlist entry depends on original-maintainer cache; ADR-132 keeps it visible but defers transferability work until Shape B",
                    {"occurrences": count, "owner": owner, "shape_b_action": shape_b_action},
                )
            )
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
        "counts_by_degradation_class": class_counts,
        "counts_by_transferability_state": transferability_counts,
        "occurrences_by_transferability_state": transferability_occurrences,
        "legacy_audited_count": class_counts.get("legacy_audited", 0),
        "maintainer_cache_file_count": transferability_counts.get("maintainer_cache", 0),
        "maintainer_cache_occurrence_count": transferability_occurrences.get("maintainer_cache", 0),
        "sample_occurrences": [asdict(item) for item in occurrences[:50]],
        "findings": [asdict(item) for item in findings],
        "fail_count": fail_count,
        "warn_count": warn_count,
    }


def write_baseline(path: Path, counts: dict[str, int], occurrences: list[Occurrence] | None = None) -> None:
    occurrence_list = occurrences or []
    entries = []
    for file_path, count in counts.items():
        degradation_class = classify_path(file_path, occurrence_list)
        transferability_state = "maintainer_cache" if degradation_class == "legacy_audited" else "documented_classification"
        entries.append(
            {
                "path": file_path,
                "max_occurrences": count,
                "degradation_class": degradation_class,
                "rationale": CLASS_RATIONALES[degradation_class],
                "owner": "original-maintainer",
                "reviewed_on": "2026-05-03",
                "transferability_state": transferability_state,
                "shape_b_action": TRANSFERABILITY_ACTIONS[transferability_state],
            }
        )
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
        occurrences = scan(args.scan_root, REPO_ROOT)
        write_baseline(args.allowlist, counts_by_path(occurrences), occurrences)

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
