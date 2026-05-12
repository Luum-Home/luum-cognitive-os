#!/usr/bin/env python3
"""Benchmark candidate code-intelligence backends for primitive coverage.

This is intentionally a metadata/protocol benchmark by default. It reads local
candidate clones, classifies license/capabilities, and compares them against the
questions COS needs a backend to answer. It does not vendor or install candidate
code, which keeps AGPL/custom-license tools evaluable without contaminating the
repo.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_URLS = {
    "qartez": "https://github.com/kuberstar/qartez-mcp",
    "jcodemunch": "https://github.com/jgravelle/jcodemunch-mcp",
    "repowise": "https://github.com/repowise-dev/repowise",
    "codegraphcontext": "https://github.com/CodeGraphContext/CodeGraphContext",
}

CANDIDATE_DIRS = {
    "qartez": "qartez-mcp",
    "jcodemunch": "jcodemunch-mcp",
    "repowise": "repowise",
    "codegraphcontext": "CodeGraphContext",
}

SAFE_LICENSE_PATTERNS = ("mit license", "apache license", "bsd ", "isc license")
BLOCKED_LICENSE_PATTERNS = ("agpl", "affero", "sspl", "server side public license", "elastic license", "business source license")
CUSTOM_LICENSE_PATTERNS = ("commercial license", "non-commercial", "noncommercial", "dual-use", "dual license", "paid license", "small team license")

QUESTION_WEIGHTS = {
    "first_class_primitives": 15,
    "primitive_context_query": 15,
    "unused_consumers": 15,
    "stale_docs": 15,
    "json_sarif": 10,
    "token_savings": 10,
    "local_offline": 10,
    "license_compatible": 10,
    "adapter_fit": 10,
}

TEXT_EXTENSIONS = {
    ".adoc",
    ".cfg",
    ".css",
    ".go",
    ".html",
    ".ini",
    ".java",
    ".js",
    ".json",
    ".jsonl",
    ".jsx",
    ".md",
    ".py",
    ".rs",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}

@dataclass
class QuestionAnswer:
    answer: str
    score: int
    evidence: list[str] = field(default_factory=list)
    notes: str = ""

@dataclass
class CandidateBenchmark:
    name: str
    repo_url: str
    local_path: str
    present: bool
    license_kind: str
    license_compatible: bool
    license_notes: str
    package: dict[str, Any]
    answers: dict[str, QuestionAnswer]
    total_score: int
    max_score: int
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["answers"] = {key: asdict(value) for key, value in self.answers.items()}
        return data


def read_optional(path: Path, limit: int | None = None) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="ignore")
    return text[:limit] if limit else text


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower())


def classify_license(license_text: str, package_text: str = "") -> tuple[str, bool, str]:
    haystack = normalize(license_text + "\n" + package_text)
    if any(pattern in haystack for pattern in BLOCKED_LICENSE_PATTERNS):
        return "blocked", False, "License gate blocks AGPL/SSPL/BSL/ELv2-style terms for embedding."
    if any(pattern in haystack for pattern in SAFE_LICENSE_PATTERNS):
        return "compatible", True, "Permissive license detected."
    if any(pattern in haystack for pattern in CUSTOM_LICENSE_PATTERNS):
        return "review-required", False, "Custom/commercial or non-commercial terms require legal/commercial approval."
    if not haystack.strip():
        return "unknown", False, "No license text found in local clone."
    return "review-required", False, "License text is not in the default safe allowlist; review before integration."


def extract_package_metadata(candidate_dir: Path) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    pyproject = read_optional(candidate_dir / "pyproject.toml")
    cargo = read_optional(candidate_dir / "Cargo.toml")
    package_json = read_optional(candidate_dir / "package.json")
    for key, text in (("pyproject", pyproject), ("cargo", cargo), ("package_json", package_json)):
        if not text:
            continue
        name_match = re.search(r'(?m)^name\s*=\s*["\']([^"\']+)["\']', text) or re.search(r'"name"\s*:\s*"([^"]+)"', text)
        version_match = re.search(r'(?m)^version\s*=\s*["\']([^"\']+)["\']', text) or re.search(r'"version"\s*:\s*"([^"]+)"', text)
        license_match = re.search(r'(?m)^license\s*=\s*["\']([^"\']+)["\']', text) or re.search(r'"license"\s*:\s*"([^"]+)"', text)
        metadata[key] = {
            "name": name_match.group(1) if name_match else None,
            "version": version_match.group(1) if version_match else None,
            "license": license_match.group(1) if license_match else None,
        }
    return metadata


def score_answer(condition: bool, weight_key: str, evidence: list[str], positive: str, negative: str, notes: str = "") -> QuestionAnswer:
    return QuestionAnswer(
        answer="yes" if condition else "no",
        score=QUESTION_WEIGHTS[weight_key] if condition else 0,
        evidence=evidence,
        notes=positive if condition else (notes or negative),
    )


def detect_token_claim(readme: str) -> list[str]:
    matches = re.findall(r"(?:\d+x|\d+×|\d+%|~\d+%|\d+\s*percent)[^\n.]{0,90}(?:token|cost|file|read|context)[^\n.]{0,120}", readme, flags=re.I)
    if not matches:
        matches = re.findall(r"(?:token|cost|file|read|context)[^\n.]{0,120}(?:\d+x|\d+×|\d+%|~\d+%)", readme, flags=re.I)
    return [m.strip() for m in matches[:3]]


def evaluate_candidate(name: str, root: Path) -> CandidateBenchmark:
    local_dir = root / CANDIDATE_DIRS[name]
    present = local_dir.exists()
    readme = read_optional(local_dir / "README.md") if present else ""
    license_text = read_optional(local_dir / "LICENSE") if present else ""
    package_text = "\n".join(read_optional(local_dir / fname) for fname in ("pyproject.toml", "Cargo.toml", "package.json")) if present else ""
    haystack = normalize(readme + "\n" + package_text)
    license_kind, license_compatible, license_notes = classify_license(license_text, package_text)
    package = extract_package_metadata(local_dir) if present else {}

    if not present:
        missing = QuestionAnswer("missing", 0, [], "Local clone is missing; benchmark cannot inspect it.")
        return CandidateBenchmark(
            name=name,
            repo_url=REPO_URLS[name],
            local_path=str(local_dir),
            present=False,
            license_kind="unknown",
            license_compatible=False,
            license_notes="Local clone is missing.",
            package={},
            answers={key: missing for key in QUESTION_WEIGHTS},
            total_score=0,
            max_score=sum(QUESTION_WEIGHTS.values()),
            recommendation="clone-before-eval",
        )

    primitive_terms = all(term in haystack for term in ("skills", "hooks", "rules")) or "agentic primitive" in haystack
    graph_terms = any(term in haystack for term in ("tree-sitter", "dependency graph", "code graph", "call graph", "symbol", "references", "blast radius"))
    docs_terms = any(term in haystack for term in ("documentation", "wiki", "decision", "architecture decision", "stale"))
    mcp_or_cli = any(term in haystack for term in ("mcp", "cli", "command line", "server"))
    json_terms = "json" in haystack or "structured" in haystack
    sarif_terms = "sarif" in haystack
    local_terms = any(term in haystack for term in ("local", "offline", "index", "pip install", "cargo install"))
    token_claims = detect_token_claim(readme)

    # Candidate-specific conservative overrides based on inspected public docs.
    first_class = primitive_terms and "agentic primitive" in haystack
    primitive_query = first_class
    unused_consumers = graph_terms and name in {"qartez", "repowise", "codegraphcontext"}
    stale_docs = docs_terms and name == "repowise"
    emits_json_or_sarif = sarif_terms or (json_terms and name in {"qartez", "jcodemunch"})
    adapter_fit = license_compatible and graph_terms and mcp_or_cli

    answers = {
        "first_class_primitives": score_answer(
            first_class,
            "first_class_primitives",
            ["Looked for explicit skills/hooks/rules/agentic primitive semantics in README/package metadata."],
            "Candidate documents COS-like primitive semantics.",
            "Detects code/docs entities, but not COS skills/hooks/rules as first-class rows.",
        ),
        "primitive_context_query": score_answer(
            primitive_query,
            "primitive_context_query",
            ["Question requires a primitive-to-file evidence map, not just code search."],
            "Can answer which primitive avoids reading specific files.",
            "No native evidence that it maps files to primitive-level context-saving affordances.",
        ),
        "unused_consumers": score_answer(
            unused_consumers,
            "unused_consumers",
            ["Graph/reference terms present in docs."],
            "Graph/index can likely support consumer-gap detection with a COS adapter.",
            "No enough cross-reference evidence to detect scripts/primitives without consumers.",
        ),
        "stale_docs": score_answer(
            stale_docs,
            "stale_docs",
            ["Docs/wiki/decision-intelligence terms present."],
            "Documentation intelligence appears close enough to support stale-doc signals.",
            "No native stale-doc or docs-vs-code freshness signal found.",
        ),
        "json_sarif": QuestionAnswer(
            answer="partial" if emits_json_or_sarif and not sarif_terms else ("yes" if sarif_terms else "no"),
            score=QUESTION_WEIGHTS["json_sarif"] if sarif_terms else (QUESTION_WEIGHTS["json_sarif"] // 2 if emits_json_or_sarif else 0),
            evidence=["Scanned README/package metadata for JSON/SARIF/structured output claims."],
            notes="SARIF not found; JSON/structured output may be available via MCP/tool protocol." if emits_json_or_sarif and not sarif_terms else ("SARIF output claimed." if sarif_terms else "No SARIF/JSON reporting claim found."),
        ),
        "token_savings": score_answer(
            bool(token_claims),
            "token_savings",
            token_claims or ["No token-saving benchmark claim found in README."],
            "README contains explicit token/cost/context reduction claims.",
            "No explicit token-saving claim found.",
        ),
        "local_offline": score_answer(
            local_terms and mcp_or_cli,
            "local_offline",
            ["Local install/index/server terms found."],
            "Designed to run as a local CLI/MCP indexing backend.",
            "Local/offline operation is not clear from README/package metadata.",
        ),
        "license_compatible": score_answer(
            license_compatible,
            "license_compatible",
            [license_notes],
            "License is compatible with the repo allowlist.",
            license_notes,
        ),
        "adapter_fit": score_answer(
            adapter_fit,
            "adapter_fit",
            ["Adapter fit requires compatible license plus local CLI/MCP/code graph."],
            "Good backend candidate for primitive_coverage adapters without rewriting the framework.",
            "Would need licensing clearance and/or an additional COS semantic adapter before use.",
        ),
    }

    total = sum(answer.score for answer in answers.values())
    if name == "repowise" and license_kind == "blocked":
        recommendation = "evaluate-only-license-blocked"
    elif license_compatible and total >= 55:
        recommendation = "preferred-spike-backend"
    elif license_kind == "review-required":
        recommendation = "license-review-before-spike"
    else:
        recommendation = "secondary-or-reference-only"

    return CandidateBenchmark(
        name=name,
        repo_url=REPO_URLS[name],
        local_path=str(local_dir),
        present=present,
        license_kind=license_kind,
        license_compatible=license_compatible,
        license_notes=license_notes,
        package=package,
        answers=answers,
        total_score=total,
        max_score=sum(QUESTION_WEIGHTS.values()),
        recommendation=recommendation,
    )


def estimate_repo_text_bytes(project_dir: Path) -> dict[str, Any]:
    ignored_parts = {".git", ".venv", "node_modules", "__pycache__", ".mypy_cache", ".pytest_cache"}
    total = 0
    file_count = 0
    report_bytes = 0
    report_files: list[str] = []
    for path in project_dir.rglob("*"):
        if not path.is_file():
            continue
        if any(part in ignored_parts for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        total += size
        file_count += 1
        rel = path.relative_to(project_dir).as_posix()
        if rel.startswith("docs/06-Daily/reports/primitive-") or rel.startswith("docs/04-Concepts/architecture/primitive-coverage"):
            report_bytes += size
            report_files.append(rel)
    return {
        "text_file_count": file_count,
        "repo_text_bytes": total,
        "primitive_evidence_bytes": report_bytes,
        "primitive_evidence_files": sorted(report_files),
        "evidence_to_repo_ratio": round(report_bytes / total, 6) if total else 0,
        "rough_token_savings_vs_read_all": round(1 - (report_bytes / total), 4) if total else 0,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Primitive Coverage Backend Benchmark — 2026-05-01",
        "",
        "## Scope",
        "",
        "Local metadata/protocol benchmark of four code-intelligence candidates as possible backends for `primitive_coverage/`.",
        "The benchmark deliberately avoids installing or vendoring candidates; it inspects local clones, licenses, package metadata, and README claims.",
        "",
        "## Summary",
        "",
        "| Candidate | Score | License | Recommendation |",
        "|---|---:|---|---|",
    ]
    for candidate in report["candidates"]:
        lines.append(
            f"| [{candidate['name']}]({candidate['repo_url']}) | {candidate['total_score']}/{candidate['max_score']} | {candidate['license_kind']} | {candidate['recommendation']} |"
        )
    lines.extend([
        "",
        "## Question Matrix",
        "",
        "| Candidate | Primitives first-class | Context-saving query | Unused consumers | Stale docs | JSON/SARIF | Token savings | Local/offline | License OK | Adapter fit |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ])
    keys = list(QUESTION_WEIGHTS)
    for candidate in report["candidates"]:
        cells = []
        for key in keys:
            answer = candidate["answers"][key]
            cells.append(f"{answer['answer']} ({answer['score']})")
        lines.append(f"| {candidate['name']} | " + " | ".join(cells) + " |")
    lines.extend([
        "",
        "## Token-Economy Baseline",
        "",
        f"- Text files counted: {report['token_baseline']['text_file_count']}",
        f"- Repo text bytes: {report['token_baseline']['repo_text_bytes']}",
        f"- Existing primitive evidence bytes: {report['token_baseline']['primitive_evidence_bytes']}",
        f"- Evidence/repo ratio: {report['token_baseline']['evidence_to_repo_ratio']}",
        f"- Rough savings vs reading every text file: {report['token_baseline']['rough_token_savings_vs_read_all']}",
        "",
        "## Notes by Candidate",
        "",
    ])
    for candidate in report["candidates"]:
        lines.extend([
            f"### {candidate['name']}",
            "",
            f"- Repo: {candidate['repo_url']}",
            f"- Local path: `{candidate['local_path']}`",
            f"- License: {candidate['license_kind']} — {candidate['license_notes']}",
            f"- Recommendation: `{candidate['recommendation']}`",
            "",
        ])
        for key in keys:
            answer = candidate["answers"][key]
            lines.append(f"- `{key}`: **{answer['answer']}** ({answer['score']} pts). {answer['notes']}")
        lines.append("")
    lines.extend([
        "## Recommendation",
        "",
        "Keep COS `primitive_coverage/` as the semantic orchestrator. Use an external graph backend only below it.",
        "CodeGraphContext is the safest first adapter spike because it is MIT-licensed and local/MCP-oriented.",
        "Qartez and jCodeMunch are promising token-efficiency references but require license review before integration.",
        "Repowise is the closest conceptual product for graph+docs+decisions, but AGPL makes it evaluation-only unless legal explicitly approves a separate-process boundary.",
        "",
        "## Inputs",
        "",
        f"- Generated at: `{report['generated_at']}`",
        f"- Candidates dir: `{report['candidates_dir']}`",
        f"- Project dir: `{report['project_dir']}`",
    ])
    return "\n".join(lines) + "\n"


def build_report(candidates_dir: Path, project_dir: Path) -> dict[str, Any]:
    candidates = [evaluate_candidate(name, candidates_dir).to_dict() for name in CANDIDATE_DIRS]
    candidates.sort(key=lambda item: (-item["total_score"], item["name"]))
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "candidates_dir": str(candidates_dir),
        "project_dir": "<repo-root>",
        "questions": QUESTION_WEIGHTS,
        "token_baseline": estimate_repo_text_bytes(project_dir),
        "candidates": candidates,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark candidate backends for primitive coverage")
    parser.add_argument("--candidates-dir", default=os.environ.get("COS_CANDIDATES_DIR", "/tmp/cos-code-intel-candidates"))
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--json-out", default="docs/06-Daily/reports/primitive-coverage-backend-benchmark-2026-05-01.json")
    parser.add_argument("--markdown-out", default="docs/06-Daily/reports/primitive-coverage-backend-benchmark-2026-05-01.md")
    parser.add_argument("--stdout", action="store_true", help="Print JSON report to stdout instead of writing files")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    project_dir = Path(args.project_dir).resolve()
    candidates_dir = Path(args.candidates_dir).resolve()
    report = build_report(candidates_dir, project_dir)
    if args.stdout:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    json_out = project_dir / args.json_out
    md_out = project_dir / args.markdown_out
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_out.write_text(render_markdown(report), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
