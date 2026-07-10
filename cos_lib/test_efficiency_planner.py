# SCOPE: both
"""ADR-237 test execution efficiency planner for COS maintainers."""
from __future__ import annotations

import fnmatch
import json
import re
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # PyYAML is optional for stdlib-only CLI usage.
    yaml = None  # type: ignore[assignment]

SCHEMA_VERSION = "test-efficiency-plan/v1"
DEFAULT_MANIFEST = Path("manifests/test-execution-efficiency.yaml")


@dataclass(frozen=True)
class TestLane:
    name: str
    command: str
    reason: str
    heavy: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TestEfficiencyPlan:
    schema_version: str
    lanes: list[TestLane]
    final_lane: TestLane | None
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "lanes": [lane.to_dict() for lane in self.lanes],
            "final_lane": self.final_lane.to_dict() if self.final_lane else None,
            "warnings": self.warnings,
        }


def _load_policy_fallback(text: str) -> dict[str, Any]:
    policy: dict[str, Any] = {}
    in_policy = False
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        stripped = raw.strip()
        if indent == 0:
            in_policy = stripped == "policy:"
            continue
        if not in_policy or indent != 2 or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        value = value.strip()
        if value.lower() == "false":
            parsed: Any = False
        elif value.lower() == "true":
            parsed = True
        elif value.isdigit():
            parsed = int(value)
        else:
            parsed = value.strip("\"'")
        policy[key.strip()] = parsed
    return {"policy": policy}


def load_policy(project_dir: str | Path) -> dict[str, Any]:
    path = Path(project_dir).resolve() / DEFAULT_MANIFEST
    text = path.read_text(encoding="utf-8")
    if yaml is None:
        return _load_policy_fallback(text)
    return yaml.safe_load(text)


def changed_files_from_git(project_dir: str | Path, base_ref: str = "origin/main") -> list[str]:
    root = Path(project_dir).resolve()
    commands = [
        ["git", "diff", "--name-only", base_ref, "HEAD"],
        ["git", "diff", "--name-only"],
        ["git", "diff", "--name-only", "--cached"],
    ]
    files: list[str] = []
    for cmd in commands:
        proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=10)
        if proc.returncode == 0:
            files.extend(line.strip() for line in proc.stdout.splitlines() if line.strip())
    return sorted(dict.fromkeys(files))


def _matches(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def _python_files(changed_files: list[str]) -> list[str]:
    return [path for path in changed_files if path.endswith(".py") or Path(path).name.startswith("cos-")]


def _lane_command(name: str, changed_files: list[str], failure_text: str = "") -> str:
    if name == "syntax":
        py = _python_files(changed_files)
        return "python3 -m py_compile " + " ".join(py or ["lib/test_efficiency_planner.py"])
    if name == "unit":
        return "python3 -m pytest tests/unit -q"
    if name == "behavior":
        return "python3 -m pytest tests/behavior -q"
    if name == "integration":
        return "python3 -m pytest tests/integration -q"
    if name == "chaos":
        return "python3 -m pytest tests/chaos -q"
    if name == "audit":
        return "python3 scripts/derived_artifact_gate.py"
    if name == "failed-nodeids":
        nodeids = extract_failed_nodeids(failure_text)
        return "python3 -m pytest " + " ".join(nodeids) + " -q"
    raise ValueError(f"unknown lane: {name}")


def extract_failed_nodeids(text: str) -> list[str]:
    nodeids: list[str] = []
    for line in text.splitlines():
        for match in re.findall(r"(tests/[A-Za-z0-9_./-]+\.py::[^\s]+)", line):
            nodeids.append(match.rstrip(".:"))
    return sorted(dict.fromkeys(nodeids))


def plan_tests(
    project_dir: str | Path,
    *,
    changed_files: list[str] | None = None,
    failure_text: str = "",
    include_final_laptop: bool = False,
) -> TestEfficiencyPlan:
    policy = load_policy(project_dir)
    changed = sorted(dict.fromkeys(changed_files or []))
    selected: list[TestLane] = []
    warnings: list[str] = []

    failed_nodeids = extract_failed_nodeids(failure_text)
    if failed_nodeids:
        selected.append(TestLane("failed-nodeids", _lane_command("failed-nodeids", changed, failure_text), "rerun exact failed nodeids before broad lanes"))
    elif "tests/chaos/" in failure_text or "chaos" in failure_text.lower():
        selected.append(TestLane("chaos", _lane_command("chaos", changed), "failure text references chaos lane", heavy=True))

    if changed:
        if _python_files(changed):
            selected.append(TestLane("syntax", _lane_command("syntax", changed), "python/script files changed"))
        if any(path.startswith(("lib/", "packages/")) for path in changed):
            selected.append(TestLane("unit", _lane_command("unit", changed), "runtime/package files changed"))
        if any(path.startswith(("scripts/", "hooks/")) for path in changed):
            selected.append(TestLane("behavior", _lane_command("behavior", changed), "script/hook behavior changed"))
        if any(path.startswith(("docs/", "manifests/", "rules/", ".codex/skills/")) for path in changed):
            selected.append(TestLane("audit", _lane_command("audit", changed), "docs/manifests/rules/skills changed"))
        if any(path.startswith("tests/chaos/") or "handoff" in path or "dispatch_gate" in path for path in changed):
            selected.append(TestLane("chaos", _lane_command("chaos", changed), "chaos-sensitive surface changed", heavy=True))
        if any(path.startswith("tests/integration/") or path in {"lib/dispatch.py", "lib/claude_executor.py"} for path in changed):
            selected.append(TestLane("integration", _lane_command("integration", changed), "integration-sensitive surface changed", heavy=True))

    dedup: dict[str, TestLane] = {}
    for lane in selected:
        dedup.setdefault(lane.name, lane)
    lanes = list(dedup.values())
    if not lanes:
        lanes = [TestLane("audit", "python3 scripts/derived_artifact_gate.py", "no changed files; run cheap guardrail")]

    final_lane = None
    if include_final_laptop:
        final_lane = TestLane("laptop", str(policy["policy"]["final_laptop_lane"]), "final broad confidence lane after targeted groups pass", heavy=True)
    if policy["policy"].get("broad_first_default") is not False:
        warnings.append("policy drift: broad_first_default must remain false")
    return TestEfficiencyPlan(SCHEMA_VERSION, lanes, final_lane, warnings)


def dumps_json(plan: TestEfficiencyPlan) -> str:
    return json.dumps(plan.to_dict(), indent=2, sort_keys=True)
