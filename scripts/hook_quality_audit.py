#!/usr/bin/env python3
"""Hook Quality System audit and manifest synchronizer."""
from __future__ import annotations

import argparse, json, re, subprocess, sys
from pathlib import Path
from typing import Any
import yaml

REPO = Path(__file__).resolve().parents[1]
QUALITY_MANIFEST = REPO / "manifests" / "hook-quality.yaml"
CONFIG = REPO / "cognitive-os.yaml"
TEST_ROOTS = [REPO / "tests" / n for n in ("unit", "behavior", "contracts", "chaos")]
_TEST_TEXT_INDEX: list[tuple[Path, str]] | None = None
REQUIRED_BEHAVIOR_COVERAGE = ["secret-detector", "dispatch-gate", "clarification-gate", "blast-radius", "completion-gate", "claim-validator", "trust-score-validator", "confidence-gate", "auto-rollback-trigger", "content-policy"]
SECURITY_TERMS = ("secret", "confidential", "content-policy", "lethal", "destructive", "private-mode", "semgrep", "mcp-scan")
QUALITY_TERMS = ("completion", "claim", "trust", "confidence", "frontmatter", "validator", "adr", "doc-sync", "surface-fix", "review")
COORDINATION_TERMS = ("dispatch", "lock", "snapshot", "heartbeat", "work-queue", "prelaunch", "agent-", "dequeue")
LIFECYCLE_TERMS = ("session", "memory", "engram", "changelog", "resume", "startup")
VALID_TIERS = {"native", "governed", "cos_owned", "unsupported"}
VALID_MATURITY = {"observe", "warn", "block", "emergency"}


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"{path} must parse as a mapping")
    return data


def registered_hooks() -> dict[str, dict[str, Any]]:
    config = load_yaml(CONFIG)
    raw = ((config.get("harness") or {}).get("hooks") or {})
    out: dict[str, dict[str, Any]] = {}
    for hook_id, entry in raw.items():
        if not isinstance(entry, dict) or not entry.get("script") or not entry.get("event"):
            continue
        out[str(hook_id)] = {
            "script": str(entry["script"]),
            "event": str(entry["event"]),
            "matcher": str(entry.get("matcher") or ""),
            "async": bool(entry.get("async", False)),
            "scope": str(entry.get("scope") or "os-only"),
        }
    return out


def classify_criticality(hook_id: str, script: str) -> str:
    text = f"{hook_id} {script}".lower()
    if any(t in text for t in SECURITY_TERMS): return "security"
    if any(t in text for t in QUALITY_TERMS): return "quality"
    if any(t in text for t in COORDINATION_TERMS): return "coordination"
    if any(t in text for t in LIFECYCLE_TERMS): return "lifecycle"
    return "standard"


def max_runtime_ms(criticality: str, async_flag: bool) -> int:
    if async_flag: return 2500
    return {"security": 750, "quality": 1500, "coordination": 1000, "lifecycle": 2000}.get(criticality, 1500)


def safe_degradation(criticality: str) -> str:
    if criticality == "security": return "fail_closed_when_confident_otherwise_warn"
    if criticality == "quality": return "warn_or_block_by_policy"
    return "warn_and_continue_unless_exit_2"


def default_maturity(criticality: str) -> str:
    if criticality in {"security", "quality", "coordination"}:
        return "warn"
    return "observe"


def default_bypass_policy(maturity: str) -> str:
    if maturity == "emergency":
        return "time_limited_operator_override_with_metric"
    if maturity == "block":
        return "explicit_operator_override_with_metric"
    if maturity == "warn":
        return "not_required_warning_only"
    return "not_required_observe_only"


def split_matcher(matcher: str) -> set[str]:
    return {p.strip() for p in matcher.split("|") if p.strip()}


def claude_tier(event: str, _matcher: str) -> str:
    return "cos_owned" if event in {"TeammateIdle", "TaskCreated", "TaskCompleted"} else "native"


def codex_tier(event: str, matcher: str) -> str:
    parts = split_matcher(matcher)
    if event in {"SessionStart", "UserPromptSubmit", "Stop"}: return "native"
    if event in {"PreToolUse", "PostToolUse"}:
        if parts == {"Bash"}: return "native"
        if not parts or parts & {"Agent", "Edit", "Write", "MultiEdit"}: return "governed"
        return "unsupported"
    if event in {"TeammateIdle", "TaskCreated", "TaskCompleted"}: return "cos_owned"
    return "unsupported"


def test_text_index() -> list[tuple[Path, str]]:
    global _TEST_TEXT_INDEX
    if _TEST_TEXT_INDEX is not None:
        return _TEST_TEXT_INDEX
    rows: list[tuple[Path, str]] = []
    for root in TEST_ROOTS:
        if not root.is_dir():
            continue
        for path in sorted(root.glob("test_*.py")):
            rows.append((path, path.read_text(encoding="utf-8", errors="ignore")))
    _TEST_TEXT_INDEX = rows
    return rows


def discover_behavior_tests(hook_id: str, script: str) -> list[str]:
    base = Path(script).name
    needles = {hook_id, base, base.removesuffix(".sh")}
    found: list[str] = []
    for path, text in test_text_index():
        if any(n and n in text for n in needles):
            found.append(str(path.relative_to(REPO)))
    return sorted(set(found))


def desired_manifest(existing: dict[str, Any] | None = None) -> dict[str, Any]:
    existing = existing or {}
    old_hooks = existing.get("hooks") if isinstance(existing.get("hooks"), dict) else {}
    hooks: dict[str, Any] = {}
    for hook_id, entry in registered_hooks().items():
        criticality = classify_criticality(hook_id, entry["script"])
        old = old_hooks.get(hook_id, {}) if isinstance(old_hooks, dict) else {}
        old_maturity = old.get("maturity") if isinstance(old, dict) else None
        maturity = str(old_maturity) if old_maturity in VALID_MATURITY else default_maturity(criticality)
        false_positive_tests = old.get("false_positive_tests", []) if isinstance(old, dict) else []
        hooks[hook_id] = {
            "script": entry["script"], "event": entry["event"], "matcher": entry["matcher"], "scope": entry["scope"],
            "criticality": criticality, "max_runtime_ms": max_runtime_ms(criticality, entry["async"]), "safe_degradation": safe_degradation(criticality),
            "maturity": maturity, "bypass_policy": str(old.get("bypass_policy") or default_bypass_policy(maturity)) if isinstance(old, dict) else default_bypass_policy(maturity),
            "false_positive_tests": false_positive_tests if isinstance(false_positive_tests, list) else [],
            "harness_tiers": {"claude": claude_tier(entry["event"], entry["matcher"]), "codex": codex_tier(entry["event"], entry["matcher"])},
            "behavior_tests": discover_behavior_tests(hook_id, entry["script"]),
        }
        if isinstance(old, dict) and old.get("manual_tests"): hooks[hook_id]["manual_tests"] = old["manual_tests"]
        if isinstance(old, dict) and old.get("notes"): hooks[hook_id]["notes"] = old["notes"]
    return {"schema_version": 1, "generated_by": "scripts/hook_quality_audit.py --sync", "policy": {"tier_values": sorted(VALID_TIERS), "maturity_values": sorted(VALID_MATURITY), "required_behavior_coverage": REQUIRED_BEHAVIOR_COVERAGE, "blocking_exit_code": 2, "project_env_precedence": ["COGNITIVE_OS_PROJECT_DIR", "CODEX_PROJECT_DIR", "CLAUDE_PROJECT_DIR", "cwd"]}, "hooks": hooks}


def normalize(data: dict[str, Any]) -> str:
    return yaml.safe_dump(data, sort_keys=True, allow_unicode=True)


def write_manifest() -> None:
    QUALITY_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    QUALITY_MANIFEST.write_text(yaml.safe_dump(desired_manifest(load_yaml(QUALITY_MANIFEST)), sort_keys=True, allow_unicode=True), encoding="utf-8")


def header_scope(path: Path) -> str | None:
    text = "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[:8])
    m = re.search(r"\bSCOPE:\s*([A-Za-z0-9_-]+)", text)
    return m.group(1) if m else None


def audit() -> tuple[list[str], dict[str, Any]]:
    failures: list[str] = []
    manifest = load_yaml(QUALITY_MANIFEST)
    if normalize(manifest) != normalize(desired_manifest(manifest)):
        failures.append("manifests/hook-quality.yaml is out of sync; run `python3 scripts/hook_quality_audit.py --sync`.")
    hooks = manifest.get("hooks", {}) if isinstance(manifest.get("hooks"), dict) else {}
    registry = registered_hooks()
    if set(hooks) != set(registry): failures.append("hook-quality manifest keys differ from cognitive-os.yaml harness.hooks")
    checked = 0
    for hook_id, entry in sorted(hooks.items()):
        script = REPO / str(entry.get("script", ""))
        if not script.is_file():
            failures.append(f"hook {hook_id} script missing: {entry.get('script')}"); continue
        if header_scope(script) not in {"os-only", "project", "both"}: failures.append(f"hook {hook_id} script missing valid SCOPE header")
        proc = subprocess.run(["bash", "-n", str(script)], cwd=REPO, text=True, capture_output=True, check=False)
        checked += 1
        if proc.returncode != 0: failures.append(f"hook {hook_id} fails bash -n: {proc.stderr.strip()}")
        tiers = entry.get("harness_tiers") or {}
        if tiers.get("claude") not in VALID_TIERS or tiers.get("codex") not in VALID_TIERS: failures.append(f"hook {hook_id} invalid harness_tiers")
        maturity = entry.get("maturity")
        if maturity not in VALID_MATURITY:
            failures.append(f"hook {hook_id} invalid maturity {maturity!r}")
        if not entry.get("bypass_policy"):
            failures.append(f"hook {hook_id} missing bypass_policy")
        if maturity in {"block", "emergency"}:
            tests = [t for t in (entry.get("false_positive_tests") or []) if (REPO / str(t)).is_file()]
            if not tests:
                failures.append(f"hook {hook_id} is {maturity} but has no false_positive_tests")
        if hook_id in REQUIRED_BEHAVIOR_COVERAGE:
            tests = [t for t in (entry.get("behavior_tests") or []) if (REPO / str(t)).is_file()]
            if not tests: failures.append(f"hook {hook_id} is critical but has no behavior_tests")
    return failures, {"hooks": len(hooks), "syntax_checked": checked, "failures": failures}


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit or synchronize COS hook quality metadata.")
    ap.add_argument("--sync", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if args.sync:
        write_manifest()
        if not args.json: print(f"hook-quality: wrote {QUALITY_MANIFEST.relative_to(REPO)}")
    failures, report = audit()
    if args.json: print(json.dumps(report, indent=2, sort_keys=True))
    elif args.check:
        if failures:
            print("hook-quality: FAIL", file=sys.stderr)
            for f in failures: print(f"- {f}", file=sys.stderr)
        else:
            print(f"hook-quality: OK ({report['hooks']} hooks, {report['syntax_checked']} syntax checks)")
    return 1 if args.check and failures else 0

if __name__ == "__main__":
    raise SystemExit(main())
