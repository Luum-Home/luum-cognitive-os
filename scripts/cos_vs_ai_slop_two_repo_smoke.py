#!/usr/bin/env python3
# SCOPE: os-only
"""Two-repo non-provider smoke for COS-vs-AI-slop falsification.

Creates a vanilla fixture repository and a COS-projected fixture repository. The
smoke proves local substrate and honesty gates before any live model benchmark.
It does not claim quality, speed, or cognitive-load wins.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "docs" / "06-Daily" / "reports" / "cos-vs-ai-slop-two-repo-smoke-latest.json"
DEFAULT_MD = ROOT / "docs" / "06-Daily" / "reports" / "cos-vs-ai-slop-two-repo-smoke-latest.md"


def run(cmd: list[str], cwd: Path, timeout: int = 120, env: dict[str, str] | None = None) -> dict[str, Any]:
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False, timeout=timeout, env=run_env)
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
    }


def json_from_stdout(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except Exception as exc:
                return {"_error": str(exc)}
    return {"_error": "no json object found"}


def write_fixture(repo: Path) -> None:
    (repo / "src").mkdir(parents=True, exist_ok=True)
    (repo / "tests").mkdir(parents=True, exist_ok=True)
    (repo / "README.md").write_text("# Fixture Repo\n\nNative harness vs COS substrate smoke fixture.\n", encoding="utf-8")
    (repo / "src" / "calculator.py").write_text("def add(a: int, b: int) -> int:\n    return a + b\n", encoding="utf-8")
    (repo / "tests" / "test_calculator.py").write_text(
        "from src.calculator import add\n\n\ndef test_add() -> None:\n    assert add(2, 3) == 5\n",
        encoding="utf-8",
    )


def tree_digest(repo: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(repo.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(repo).as_posix().encode())
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()


def exists(repo: Path, rel: str) -> bool:
    return (repo / rel).exists()


def has_any_skill(repo: Path) -> bool:
    root = repo / ".cognitive-os" / "skills" / "cos"
    return root.exists() and any(root.rglob("SKILL.md"))


def probe(ok: bool, rationale: str) -> dict[str, str]:
    return {"status": "pass" if ok else "fail", "rationale": rationale}


def compact(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "cmd": result["cmd"],
        "returncode": result["returncode"],
        "stdout_tail": result.get("stdout_tail", "")[-500:],
        "stderr_tail": result.get("stderr_tail", "")[-500:],
    }


def build_report(root: Path = ROOT, harness: str = "codex", keep: bool = False) -> dict[str, Any]:
    root = root.resolve()
    tmp_ctx = tempfile.TemporaryDirectory(prefix="cos-vs-slop-two-repo-")
    tmp = Path(tmp_ctx.name)
    vanilla = tmp / "vanilla-repo"
    cos_repo = tmp / "cos-repo"
    vanilla.mkdir()
    cos_repo.mkdir()
    write_fixture(vanilla)
    shutil.copytree(vanilla, cos_repo, dirs_exist_ok=True)

    vanilla_before = tree_digest(vanilla)
    cos_before = tree_digest(cos_repo)
    install = run([sys.executable, str(root / "scripts" / "cos_init.py"), "--default", "--harness", harness], cwd=cos_repo)
    status = run(["bash", str(root / "scripts" / "cos-status.sh"), "--json"], cwd=cos_repo, env={"COGNITIVE_OS_PROJECT_DIR": str(cos_repo)})
    claim_gate = run([str(root / "scripts" / "cos-public-claim-gate"), "--json"], cwd=root)
    manifest_tier = run([str(root / "scripts" / "cos-manifest-tier-claim-audit"), "--json"], cwd=root)
    benchmark_plan = run([sys.executable, str(root / "scripts" / "so_vs_vanilla_benchmark.py"), "--dry-run"], cwd=root)

    install_meta = json_from_stdout((cos_repo / ".cognitive-os" / "install-meta.json").read_text(encoding="utf-8") if (cos_repo / ".cognitive-os" / "install-meta.json").exists() else "{}")
    status_json = json_from_stdout(status["stdout"])
    claim_json = json_from_stdout(claim_gate["stdout"])
    tier_json = json_from_stdout(manifest_tier["stdout"])
    hooks_path = cos_repo / ".codex" / "hooks.json"
    hooks_text = hooks_path.read_text(encoding="utf-8") if hooks_path.exists() else ""

    probes = {
        "vanilla_repo_unchanged": probe(vanilla_before == tree_digest(vanilla) and not exists(vanilla, ".cognitive-os"), "Baseline repo remains a clean native-harness fixture."),
        "cos_projection_exists": probe(
            install["returncode"] == 0
            and exists(cos_repo, ".cognitive-os")
            and exists(cos_repo, ".codex/hooks.json")
            and exists(cos_repo, ".cognitive-os/hooks/cos/session-init.sh")
            and exists(cos_repo, ".cognitive-os/rules/cos/RULES-COMPACT.md")
            and has_any_skill(cos_repo),
            "COS repo has inspectable projected substrate.",
        ),
        "driver_boundary_visible": probe("CODEX_PROJECT_DIR" in hooks_text and "CLAUDE_PROJECT_DIR" not in hooks_text, "Codex projection does not hide Claude coupling."),
        "status_visible": probe(status["returncode"] == 0 and status_json.get("health") is not None, "Status tooling inspects the COS repo without model calls."),
        "public_claim_gate_clean": probe(claim_gate["returncode"] == 0 and claim_json.get("status") == "pass", "Public high-risk claims remain bounded by a gate."),
        "manifest_debt_not_hidden": probe(manifest_tier["returncode"] == 0 and tier_json.get("status") == "warn" and int(tier_json.get("warning_count", 0)) > 0, "Remaining manifest debt is visible as warn."),
        "benchmark_plan_available": probe(benchmark_plan["returncode"] == 0 and "tasks × 2 modes" in benchmark_plan["stdout"], "Existing so-vs-vanilla benchmark dry-run is available."),
    }
    passed = sum(1 for row in probes.values() if row["status"] == "pass")
    report = {
        "schema_version": "cos-vs-ai-slop-two-repo-smoke.v1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "pass" if passed == len(probes) else "fail",
        "mode": "non-provider-two-repo-substrate-smoke",
        "harness": harness,
        "temp_root": str(tmp) if keep else "removed",
        "limitations": [
            "Does not execute live model tasks.",
            "Does not prove time-to-merge, defect-rate, or cognitive-load wins.",
            "Only proves the local substrate needed before the A/B/C falsification benchmark.",
        ],
        "digests": {
            "vanilla_before": vanilla_before,
            "vanilla_after": tree_digest(vanilla),
            "cos_before": cos_before,
            "cos_after": tree_digest(cos_repo),
        },
        "install_meta": {
            "harness": install_meta.get("harness"),
            "hooks_installed": install_meta.get("hooks_installed"),
            "rules_installed": install_meta.get("rules_installed"),
            "skills_installed": install_meta.get("skills_installed"),
        },
        "manifest_tier_summary": {
            "status": tier_json.get("status"),
            "primitive_count": tier_json.get("primitive_count"),
            "finding_count": tier_json.get("finding_count"),
            "warning_count": tier_json.get("warning_count"),
            "counts_by_category": tier_json.get("counts_by_category"),
        },
        "probes": probes,
        "commands": {"install": compact(install), "status": compact(status), "public_claim_gate": compact(claim_gate), "manifest_tier": compact(manifest_tier), "benchmark_plan": compact(benchmark_plan)},
    }
    if keep:
        tmp_ctx.cleanup = lambda: None  # type: ignore[method-assign]
    tmp_ctx.cleanup()
    return report


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# COS vs AI Slop Two-Repo Smoke — Latest",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Status: `{report['status']}`",
        f"Mode: `{report['mode']}`",
        f"Harness: `{report['harness']}`",
        "",
        "## Probe Results",
        "",
        "| Probe | Status | Rationale |",
        "|---|---|---|",
    ]
    for name, row in report["probes"].items():
        lines.append(f"| `{name}` | `{row['status']}` | {row['rationale']} |")
    tier = report["manifest_tier_summary"]
    lines += [
        "",
        "## Manifest-Tier Debt Visibility",
        "",
        f"- status: `{tier.get('status')}`",
        f"- primitive_count: `{tier.get('primitive_count')}`",
        f"- finding_count: `{tier.get('finding_count')}`",
        f"- warning_count: `{tier.get('warning_count')}`",
        "",
        "## Limitations",
        "",
    ]
    lines.extend(f"- {item}" for item in report["limitations"])
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=ROOT)
    parser.add_argument("--harness", choices=["codex", "claude"], default="codex")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--keep", action="store_true")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true")
    group.add_argument("--write-report", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(args.project_dir, args.harness, args.keep)
    if args.write_report:
        DEFAULT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        DEFAULT_MD.write_text(render_markdown(report) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"cos-vs-ai-slop-two-repo-smoke: {report['status']} probes={len(report['probes'])}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
