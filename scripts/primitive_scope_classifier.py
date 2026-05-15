#!/usr/bin/env python3
# SCOPE: os-only
"""Evidence-weighted SCOPE classifier for agentic primitives.

This tool computes a suggested scope from distribution evidence instead of from
raw source-path mentions. It is intentionally conservative: when a primitive has
no export/projection evidence, the suggested scope is `os-only` with low
confidence and an explicit next action. `both` requires positive consumer/export
evidence and should be paired with portability proof.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.portability_proof_paths import paired_candidates, suggested_test_path
from lib.primitive_parser import parse_primitive_file
from lib.project_paths import relpath
from lib.primitive_readiness_common import load_lifecycle

VALID_SCOPES = {"os-only", "project", "both"}
SOURCE_ROOTS = ("hooks", "skills", "rules", "scripts", "templates", "packages")
PROJECTABLE_STATUSES = {"projectable-needs-driver", "shell-ci-candidate", "projected-consumer-surface"}
SHARED_STATUSES = {"shared-surface"}
MAINTAINER_STATUSES = {"maintainer-only", "so-local-only", "lifecycle-declared-maintainer"}
INACTIVE_STATES = {"demoted", "archived", "deleted"}
BOTH_INSTALL_SURFACES = {"bootstrap", "settings-projection", "profile-application"}
PROJECT_LIFECYCLE_ACCESSIBILITY = {"lifecycle-declared-consumer-candidate"}
SHARED_LIFECYCLE_ACCESSIBILITY = {"lifecycle-declared-shared-surface"}

SHARED_HOOK_NAME_PATTERNS = {
    "adaptive-bypass": "shared-agent-workflow-quality",
    "adr-detector": "shared-architecture-governance",
    "adr-relevance-suggest": "shared-architecture-governance",
    "assumption-tracker": "shared-agent-quality",
    "auto-checkpoint": "shared-recovery-safety",
    "auto-rollback-trigger": "shared-recovery-safety",
    "branch-ownership": "shared-git-safety",
    "crash-recovery": "shared-recovery-safety",
    "edit-lock": "shared-concurrent-edit-safety",
    "auto-verify": "shared-verification",
    "blast-radius": "shared-repository-safety",
    "claim-validator": "shared-claim-verification",
    "clarification-gate": "shared-agent-quality",
    "completeness-check": "shared-agent-quality",
    "concurrent-write-guard": "shared-repository-safety",
    "confidence-gate": "shared-agent-quality",
    "context-budget": "shared-context-hygiene",
    "context-diet": "shared-context-hygiene",
    "context-watchdog": "shared-context-hygiene",
    "destructive-git-blocker": "shared-repository-safety",
    "direct-main-guard": "shared-git-safety",
    "engram-crystallize-on-session-end": "shared-memory-lifecycle",
    "engram-daemon-launcher": "shared-memory-lifecycle",
    "engram-reinforce-on-access": "shared-memory-lifecycle",
    "dod-gate": "shared-delivery-quality",
    "large-file-advisor": "shared-context-hygiene",
    "network-egress-guard": "shared-repository-security",
    "post-agent-verify": "shared-subagent-safety",
    "post-git-orphan-notifier": "shared-git-safety",
    "pre-agent-snapshot": "shared-subagent-safety",
    "pre-commit-content-hash-dedupe": "shared-git-safety",
    "prompt-quality": "shared-agent-quality",
    "protected-config-write-guard": "shared-agent-control-plane-safety",
    "resource-check": "shared-runtime-budget",
    "rule-router-prompt-suggest": "shared-rule-routing",
    "scope-creep": "shared-scope-governance",
    "scope-proportionality": "shared-scope-governance",
    "secret-detector": "shared-repository-security",
    "session-start-stash-reapply": "shared-work-preservation",
    "session-start-worktree-nudge": "shared-git-safety",
    "symlink-mutation-guard": "shared-repository-integrity",
    "skill-frontmatter-validator": "shared-skill-authoring-governance",
    "skill-router-bash-gate": "shared-skill-routing",
    "skill-router-prompt-suggest": "shared-skill-routing",
    "token-budget": "shared-runtime-budget",
    "tool-loop": "shared-agent-safety",
    "trust-score": "shared-agent-quality",
    "untracked-work-preservation-guard": "shared-work-preservation",
}

COS_MAINTAINER_HOOK_NAME_PATTERNS = {
    "control-plane-audit": "cos-control-plane",
    "dangerous-env-flag-detector": "cos-dangerous-env-overrides",
    "engram-obsidian-export-on-stop": "cos-memory-export-operator",
    "cosd-": "cos-daemon-control",
    "pending-truth": "cos-planning-ledger",
    "primitive-": "cos-primitive-governance",
    "profile-drift-autoapply": "cos-profile-governance",
    "self-install": "cos-self-maintenance",
    "self-knowledge": "cos-self-maintenance",
    "skill-post-execution-analysis": "cos-skill-evolution-governance",
}

COS_INTERNAL_CORE_TOKENS = (
    ".cognitive-os/",
    "docs/02-decisions/",
    "manifests/",
    "cognitive os",
    "cognitive-os",
    "luum-agent-os",
)


@dataclass(frozen=True)
class Evidence:
    source: str
    scope: str
    weight: int
    detail: str


@dataclass
class ScopeRow:
    path: str
    declared_scope: str | None
    suggested_scope: str
    effective_scope: str
    confidence: str
    decision_source: str
    evidence: list[Evidence] = field(default_factory=list)
    paired_portability_test: str | None = None
    contradiction: str = ""
    next_action: str = ""


def _is_text_file(path: Path) -> bool:
    if not path.is_file() or any(part in {".git", "__pycache__", ".venv", "node_modules"} for part in path.parts):
        return False
    try:
        path.read_text(encoding="utf-8", errors="ignore")[:128]
        return True
    except OSError:
        return False


def _primitive_files(root: Path) -> list[Path]:
    found: dict[str, Path] = {}
    for root_name in SOURCE_ROOTS:
        base = root / root_name
        if not base.exists():
            continue
        if root_name == "skills":
            for path in base.rglob("SKILL.md"):
                if _is_text_file(path):
                    found[relpath(root, path)] = path
            continue
        if root_name == "packages":
            for path in base.glob("*/skills/*/SKILL.md"):
                if _is_text_file(path):
                    found[relpath(root, path)] = path
            continue
        for path in base.rglob("*"):
            if _is_text_file(path):
                found[relpath(root, path)] = path
    return [found[key] for key in sorted(found)]


def _load_scope_overrides(root: Path) -> list[dict[str, str]]:
    path = root / "manifests" / "primitive-scope-overrides.yaml"
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [item for item in data.get("rules", []) if isinstance(item, dict) and item.get("pattern") and item.get("scope")]


def _override_for(rel: str, rules: list[dict[str, str]]) -> dict[str, str] | None:
    # Most-specific matching rule wins. Exact path beats wildcard fallback, then
    # longer/more-specific wildcard beats broad legacy fallback. This preserves
    # the manifest contract: broad `scripts/*.py`/`scripts/*` rules are only
    # fallback classifications.
    matches: list[tuple[int, int, int, dict[str, str]]] = []
    for index, rule in enumerate(rules):
        pattern = str(rule["pattern"])
        if fnmatch.fnmatch(rel, pattern):
            exact = 1 if pattern == rel else 0
            wildcard_count = pattern.count("*")
            specificity = len(pattern.replace("*", ""))
            matches.append((exact, specificity, -wildcard_count, rule))
    if not matches:
        return None
    matches.sort(key=lambda item: (item[0], item[1], item[2]))
    return matches[-1][3]


def _load_consumer_availability(root: Path) -> dict[str, dict[str, Any]]:
    path = root / "manifests" / "primitive-consumer-availability.yaml"
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {str(item["path"]): item for item in data.get("items", []) if isinstance(item, dict) and item.get("path")}


def _load_protected_install_surfaces(root: Path) -> dict[str, dict[str, Any]]:
    path = root / "manifests" / "primitive-readiness-protected-install-surfaces.yaml"
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {str(item["path"]): item for item in data.get("scripts", []) if isinstance(item, dict) and item.get("path")}


def _paired_test(root: Path, rel: str) -> str | None:
    for candidate in paired_candidates(rel):
        if (root / candidate).exists():
            return candidate
    return None



def _semantic_pattern_evidence(root: Path, rel: str, declared: str | None) -> list[Evidence]:
    """Return conservative semantic evidence learned from repeated manual review.

    These patterns are intentionally explainable and lower priority than durable
    manifests. They prevent repeated manual review of common hook families while
    avoiding distribution-tier inference. A semantic pattern is not portability
    proof; declared `both` rows still need paired proof or explicit metadata.
    """
    if not rel.startswith("hooks/"):
        return []
    stem = Path(rel).stem.lower()
    path = root / rel
    try:
        text = path.read_text(encoding="utf-8", errors="ignore").lower()[:12000]
    except OSError:
        text = ""

    # COS governance hooks whose value proposition is bound to COS internals are
    # maintainer-only unless explicit consumer metadata says otherwise.
    for prefix, reason in COS_MAINTAINER_HOOK_NAME_PATTERNS.items():
        if stem.startswith(prefix) and any(token in text for token in COS_INTERNAL_CORE_TOKENS):
            return [Evidence("semantic-pattern", "os-only", 65, reason)]

    # Shared hook families from manual calibration: repo safety, task quality,
    # context/resource hygiene, and generic agent-session governance. These are
    # useful in COS and adopter repos when projected, independent of COS source
    # paths used for metrics/registration. Require a matching declared marker so
    # this does not promote an explicitly os-only hook by name alone.
    if declared == "both":
        for fragment, reason in SHARED_HOOK_NAME_PATTERNS.items():
            if stem == fragment or stem.startswith(f"{fragment}-"):
                return [Evidence("semantic-pattern", "both", 65, reason)]

    return []

def _evidence_for(root: Path, rel: str, declared: str | None, override_rules: list[dict[str, str]], availability: dict[str, dict[str, Any]], protected: dict[str, dict[str, Any]], lifecycle: dict[str, dict[str, Any]]) -> list[Evidence]:
    evidence: list[Evidence] = []
    override = _override_for(rel, override_rules)
    # Scope overrides are fallback metadata for legacy surfaces that predate
    # header enforcement. `manifests/primitive-scope-overrides.yaml` explicitly
    # says header markers remain preferred, so broad fallback patterns must not
    # overrule an explicit SCOPE marker.
    if override and override.get("scope") in VALID_SCOPES and (declared is None or declared == override.get("scope")):
        evidence.append(Evidence("scope-override", str(override["scope"]), 100, str(override.get("rationale") or override.get("pattern"))))

    if rel in protected:
        surface = str(protected[rel].get("surface") or "install/profile surface")
        # Protected install membership means "review before demotion". Only
        # surfaces that directly project/apply consumer profiles count as
        # positive `both` distribution evidence by themselves. Release, doctor,
        # optional-tool, and audit surfaces remain governed but not automatically
        # projectable.
        if surface in BOTH_INSTALL_SURFACES:
            evidence.append(Evidence("protected-install-surface", "both", 90, surface))

    item = availability.get(rel)
    if item:
        status = str(item.get("status") or "")
        if status in MAINTAINER_STATUSES:
            evidence.append(Evidence("consumer-availability", "os-only", 80, status))
        elif status in SHARED_STATUSES:
            evidence.append(Evidence("consumer-availability", "both", 80, status))
        elif status in PROJECTABLE_STATUSES:
            # Consumer-availability proves project-facing distribution, not
            # automatically `both`. A primitive becomes confirmed `both` only
            # when additional evidence shows it is also a COS/core surface.
            evidence.append(Evidence("consumer-availability", "project", 70, status))

    row = lifecycle.get(rel)
    if row:
        distribution = str(row.get("distribution") or "")
        state = str(row.get("lifecycle_state") or "")
        consumer_accessibility = str(row.get("consumer_accessibility") or "")
        # Distribution tiers (`core`, `team`, `maintainer`, `lab`) answer
        # adoption/projection/default-profile questions. They are deliberately
        # orthogonal to semantic SCOPE. A lab primitive may still be `both`, and
        # a core primitive is not automatically `both`.
        #
        # Therefore lifecycle scope evidence comes from explicit consumer
        # accessibility, not from distribution tier or lifecycle state alone.
        if consumer_accessibility in MAINTAINER_STATUSES:
            evidence.append(
                Evidence(
                    "lifecycle",
                    "os-only",
                    65,
                    f"distribution={distribution}; state={state}; consumer_accessibility={consumer_accessibility}",
                )
            )
        elif consumer_accessibility in SHARED_LIFECYCLE_ACCESSIBILITY:
            evidence.append(
                Evidence(
                    "lifecycle",
                    "both",
                    65,
                    f"distribution={distribution}; state={state}; consumer_accessibility={consumer_accessibility}",
                )
            )
        elif consumer_accessibility in PROJECT_LIFECYCLE_ACCESSIBILITY:
            # Lifecycle rows can record candidate consumer-project availability
            # before there is proven shared/portable runtime use. That is
            # positive project-facing evidence, not `both` proof.
            evidence.append(
                Evidence(
                    "lifecycle",
                    "project",
                    60,
                    f"distribution={distribution}; state={state}; consumer_accessibility={consumer_accessibility}",
                )
            )

    # Project-only remains under-modeled in the current manifests. Preserve an
    # explicit project marker as weak pending evidence instead of collapsing it
    # to unknown/os-only/both. This is not high-confidence proof; it keeps the
    # project bucket visible for future project-only evidence modeling.
    if declared == "project" and not evidence:
        evidence.append(Evidence("declared-project-pending-proof", "project", 55, "explicit SCOPE marker without distribution metadata"))

    evidence.extend(_semantic_pattern_evidence(root, rel, declared))

    # A paired portability proof is necessary for `both`, but not sufficient to
    # infer distribution. Keep it out of the weighted scope decision and use it
    # only as a proof gate for declared/suggested `both`.
    return evidence


def _decide(rel: str, declared: str | None, evidence: list[Evidence], paired: str | None) -> tuple[str, str, str, str, str]:
    if declared not in VALID_SCOPES and declared is not None:
        return "os-only", "low", "invalid-declared-scope", "invalid declared scope marker", "replace marker with one of os-only, project, both"

    if evidence:
        totals: dict[str, int] = {}
        for item in evidence:
            totals[item.scope] = totals.get(item.scope, 0) + item.weight
        suggested = max(totals, key=lambda key: (totals[key], key))
        winning = totals[suggested]
        second = max([score for scope, score in totals.items() if scope != suggested], default=0)
        if second and winning - second < 30:
            suggested = "unknown"
            confidence = "low"
            source = "conflicting-distribution-evidence"
        else:
            confidence = "high" if winning >= 90 and winning - second >= 30 else "medium" if winning >= 65 and winning > second else "low"
            if suggested == "project" and winning < 65:
                confidence = "low"
            source = "+".join(item.source for item in evidence if item.scope == suggested)
    else:
        suggested = "unknown"
        confidence = "low"
        source = "insufficient-evidence"

    contradiction = ""
    if declared and declared != suggested and confidence in {"high", "medium"}:
        contradiction = f"declared {declared} conflicts with evidence-derived {suggested}"
    if declared == "both" and not paired:
        contradiction = contradiction or "declared both without paired portability proof"

    if suggested == "both" and not paired:
        next_action = f"add paired portability/falsification test, e.g. {suggested_test_path(rel)}"
    elif suggested == "project" and source == "declared-project-pending-proof":
        next_action = "add positive consumer-project-only projection evidence or reclassify if this is not project-only"
    elif source == "conflicting-distribution-evidence":
        next_action = "resolve conflicting lifecycle/projection/consumer-availability metadata before relying on this classification"
    elif suggested == "unknown" or confidence == "low":
        next_action = "add lifecycle/projection/consumer-availability metadata before relying on this classification"
    elif contradiction:
        next_action = "change SCOPE marker or update distribution evidence so they agree"
    else:
        next_action = "classification evidence is coherent"
    return suggested, confidence, source, contradiction, next_action


def _changed_paths(root: Path) -> set[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain"],
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except Exception:
        return set()
    if result.returncode != 0:
        return set()
    changed: set[str] = set()
    for raw in result.stdout.splitlines():
        if not raw:
            continue
        path = raw[3:] if len(raw) > 3 else raw
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        changed.add(path.strip())
    return changed


def build_rows(root: Path, changed_only: bool = False, only_paths: set[str] | None = None) -> list[ScopeRow]:
    override_rules = _load_scope_overrides(root)
    availability = _load_consumer_availability(root)
    protected = _load_protected_install_surfaces(root)
    lifecycle = load_lifecycle(root)
    rows: list[ScopeRow] = []
    changed = _changed_paths(root) if changed_only else set()
    for path in _primitive_files(root):
        rel = relpath(root, path)
        contract = parse_primitive_file(path, root)
        if not contract.is_primitive:
            continue
        if changed_only and rel not in changed:
            continue
        if only_paths is not None and rel not in only_paths:
            continue
        declared = contract.scope_marker
        paired = _paired_test(root, rel)
        evidence = _evidence_for(root, rel, declared, override_rules, availability, protected, lifecycle)
        suggested, confidence, source, contradiction, next_action = _decide(rel, declared, evidence, paired)
        effective = suggested if suggested != "unknown" else "os-only"
        rows.append(
            ScopeRow(
                path=rel,
                declared_scope=declared,
                suggested_scope=suggested,
                effective_scope=effective,
                confidence=confidence,
                decision_source=source,
                evidence=evidence,
                paired_portability_test=paired,
                contradiction=contradiction,
                next_action=next_action,
            )
        )
    return rows


def summarize(rows: list[ScopeRow]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "total": len(rows),
        "by_suggested_scope": {},
        "by_effective_scope": {},
        "by_confidence": {},
        "contradictions": sum(1 for row in rows if row.contradiction),
        "low_confidence": sum(1 for row in rows if row.confidence == "low"),
        "safe_fallback_os_only_from_unknown": sum(1 for row in rows if row.suggested_scope == "unknown" and row.effective_scope == "os-only"),
    }
    for row in rows:
        summary["by_suggested_scope"][row.suggested_scope] = summary["by_suggested_scope"].get(row.suggested_scope, 0) + 1
        summary["by_effective_scope"][row.effective_scope] = summary["by_effective_scope"].get(row.effective_scope, 0) + 1
        summary["by_confidence"][row.confidence] = summary["by_confidence"].get(row.confidence, 0) + 1
    summary["by_suggested_scope"] = dict(sorted(summary["by_suggested_scope"].items()))
    summary["by_effective_scope"] = dict(sorted(summary["by_effective_scope"].items()))
    summary["by_confidence"] = dict(sorted(summary["by_confidence"].items()))
    return summary


def write_report(rows: list[ScopeRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "primitive-scope-classifier/v1",
        "summary": summarize(rows),
        "rows": [asdict(row) for row in rows],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify primitive SCOPE from distribution/projection evidence")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--json-out", default=".cognitive-os/reports/primitive-scope-classifier.json")
    parser.add_argument("--changed-only", action="store_true", help="Only classify files changed in git status")
    parser.add_argument("--paths", nargs="*", help="Explicit repo-relative primitive paths to classify")
    parser.add_argument("--fail-contradictions", action="store_true")
    parser.add_argument("--fail-low-confidence", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.project_dir).resolve()
    only_paths = set(args.paths) if args.paths else None
    rows = build_rows(root, changed_only=args.changed_only, only_paths=only_paths)
    out = root / args.json_out
    write_report(rows, out)
    summary = summarize(rows)
    print(json.dumps({"json": str(out), **summary}, sort_keys=True))
    if args.fail_contradictions and summary["contradictions"]:
        return 1
    if args.fail_low_confidence and summary["low_confidence"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
