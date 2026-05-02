#!/usr/bin/env python3
# SCOPE: both
"""Detect when conversational workflow should become an agentic primitive.

The harvester is advisory. It classifies a conversation into one of:
CREATE_PRIMITIVE, IMPROVE_EXISTING, USE_EXISTING, DOCUMENT_ONLY, or DISCARD.
It does not write artifacts; it emits a plan that another governed worker can
implement and validate.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

CREATE_PRIMITIVE = "CREATE_PRIMITIVE"
IMPROVE_EXISTING = "IMPROVE_EXISTING"
USE_EXISTING = "USE_EXISTING"
DOCUMENT_ONLY = "DOCUMENT_ONLY"
DISCARD = "DISCARD"

CONVERSION_PATTERNS = [
    r"\bautom[aá]tic[oa]s?\b",
    r"\bprimitiv[ao]s?\b",
    r"\bskills?\b",
    r"\bscript\b",
    r"\breutilizable\b",
    r"\bno (?:deber[ií]a|debe) quedar como receta manual\b",
    r"\bque quede\b",
    r"\bimplement[eé]moslo\b",
    r"\btests? automatizados?\b",
]

IMPROVEMENT_PATTERNS = [
    r"\bmejor(ar|a|emos)\b",
    r"\bextender\b",
    r"\bagrega(?:r)?\b",
    r"\bedge cases?\b",
    r"\bcasos?\b",
    r"\bno ten(?:ido|er) en cuenta\b",
]

DOC_PATTERNS = [r"\bADR\b", r"\bdocumentaci[oó]n\b", r"\bdocumentar\b", r"\bdecisi[oó]n\b"]
RISK_PATTERNS = [r"\bstash", r"\bworktrees?\b", r"\bcleanup\b", r"\bborrar\b", r"\bdrop\b", r"\bpush\b", r"\bcommit\b", r"\brollback\b", r"\bsecrets?\b", r"\bcredenciales\b", r"\bconcurrenc", r"\bagentes?\b"]
VERIFY_PATTERNS = [r"\btest", r"\bvalidar\b", r"\bverificar\b", r"\bchecklist\b", r"\bdoctor\b", r"\binventory\b", r"\bacceptance\b"]
COMMAND_PATTERN = re.compile(r"^\s*(?:git|python3?|bash|pytest|make|scripts/|\.\/scripts/|for\s+\w+\s+in\s+)\b", re.MULTILINE)

STOPWORDS = {
    "esto", "esta", "este", "para", "como", "todo", "todos", "todas", "hacer", "hace",
    "tiene", "tienen", "puede", "pueden", "que", "con", "los", "las", "una", "unos", "unas",
    "the", "and", "for", "with", "should", "could", "would", "from", "into", "when", "then",
    "run", "test", "tests", "script", "python", "python3", "automatizado", "automatizados", "automática", "automatico", "automático",
}

DOMAIN_HINTS = [
    ("preserved-wip-cleanup", ["stash", "stashes", "worktree", "cleanup", "preserve", "preservado", "bloqueadores", "blockers"]),
    ("worktree-triage", ["worktree", "triage", "portar", "cherry-pick", "bb5a"]),
    ("session-filesystem-reaper", ["reaper", "session", "filesystem", "archive", "zombie"]),
    ("staged-path-scan", ["staged", "gitlink", "submodule", "paths", "pre-commit", "rename", "symlink"]),
    ("primitive-harvester", ["conversation", "conversaci", "clasificar", "descarta", "harvester"]),
]


@dataclass(frozen=True)
class ExistingPrimitive:
    kind: str
    name: str
    path: str
    tokens: list[str]


@dataclass(frozen=True)
class HarvestResult:
    decision: str
    confidence: float
    candidate_name: str | None
    primitive_type: str | None
    existing_match: dict[str, Any] | None
    reasons: list[str]
    risks: list[str]
    artifact_plan: list[str]
    validation_plan: list[str]
    next_action: str


def normalize_tokens(text: str) -> list[str]:
    raw = re.findall(r"[A-Za-zÁÉÍÓÚáéíóúÑñ0-9]+", text.lower())
    return [token for token in raw if len(token) > 2 and token not in STOPWORDS]


def count_matches(patterns: list[str], text: str) -> int:
    return sum(1 for pattern in patterns if re.search(pattern, text, flags=re.IGNORECASE))


def command_count(text: str) -> int:
    return len(COMMAND_PATTERN.findall(text))


def discover_existing_primitives(repo: Path) -> list[ExistingPrimitive]:
    primitives: list[ExistingPrimitive] = []
    skills_dir = repo / "skills"
    if skills_dir.exists():
        for skill in sorted(skills_dir.glob("*/SKILL.md")):
            name = skill.parent.name
            primitives.append(ExistingPrimitive("skill", name, str(skill), normalize_tokens(name.replace("-", " "))))
    scripts_dir = repo / "scripts"
    if scripts_dir.exists():
        for script in sorted(scripts_dir.glob("cos_*.py")):
            name = script.stem.removeprefix("cos_").replace("_", "-")
            primitives.append(ExistingPrimitive("script", name, str(script), normalize_tokens(name.replace("-", " "))))
    hooks_dir = repo / "hooks"
    if hooks_dir.exists():
        for hook in sorted(hooks_dir.glob("*.sh")):
            name = hook.stem
            primitives.append(ExistingPrimitive("hook", name, str(hook), normalize_tokens(name.replace("-", " "))))
    return primitives


def infer_candidate_name(text: str) -> str:
    tokens = set(normalize_tokens(text))
    best_name = "conversation-primitive"
    best_score = 0
    for name, hints in DOMAIN_HINTS:
        score = sum(1 for hint in hints if any(token.startswith(hint.lower()) or hint.lower() in token for token in tokens))
        if score > best_score:
            best_name = name
            best_score = score
    if best_score:
        return best_name
    frequent: dict[str, int] = {}
    for token in tokens:
        if len(token) >= 5:
            frequent[token] = frequent.get(token, 0) + 1
    top = sorted(frequent, key=lambda item: (-frequent[item], item))[:3]
    return "-".join(top) if top else best_name


def best_existing_match(candidate: str, text: str, existing: list[ExistingPrimitive]) -> tuple[ExistingPrimitive | None, float]:
    candidate_tokens = set(normalize_tokens(candidate.replace("-", " ")))
    text_tokens = set(normalize_tokens(text))
    best: ExistingPrimitive | None = None
    best_score = 0.0
    for primitive in existing:
        primitive_tokens = set(primitive.tokens)
        if not primitive_tokens:
            continue
        overlap_candidate = len(candidate_tokens & primitive_tokens) / max(1, len(primitive_tokens))
        overlap_text = len(text_tokens & primitive_tokens) / max(1, len(primitive_tokens))
        score = max(overlap_candidate, overlap_text)
        if primitive.name == candidate:
            score = 1.0
        elif len(primitive_tokens) < 2:
            score = min(score, 0.5)
        if score > best_score:
            best = primitive
            best_score = score
    return best, best_score


def infer_primitive_type(text: str) -> str:
    lower = text.lower()
    if any(word in lower for word in ["hook", "pre-commit", "posttooluse", "pretooluse"]):
        return "hook-or-gate"
    if command_count(text) or any(word in lower for word in ["cleanup", "borrar", "drop", "archive", "reaper"]):
        return "action-layer-script"
    if count_matches(DOC_PATTERNS, text) and not command_count(text):
        return "documentation-decision"
    return "skill-and-script"


def artifact_plan_for(candidate: str, primitive_type: str, decision: str, existing: ExistingPrimitive | None) -> list[str]:
    if decision == DISCARD:
        return []
    if decision == USE_EXISTING and existing:
        return [existing.path]
    if decision == IMPROVE_EXISTING and existing:
        base = [existing.path]
        base.extend([
            f"tests/behavior/test_{candidate.replace('-', '_')}.py",
            f"tests/red_team/portability/test_{candidate.replace('-', '_')}_portability.py",
        ])
        return base
    if primitive_type == "documentation-decision":
        return [f"docs/adrs/ADR-XXX-{candidate}.md", f"docs/architecture/{candidate}.md"]
    artifacts = [f"skills/{candidate}/SKILL.md"]
    if primitive_type in {"action-layer-script", "skill-and-script"}:
        artifacts.insert(0, f"scripts/cos_{candidate.replace('-', '_')}.py")
    if primitive_type == "hook-or-gate":
        artifacts.insert(0, f"hooks/{candidate}.sh")
    artifacts.extend([
        f"tests/behavior/test_{candidate.replace('-', '_')}.py",
        f"tests/red_team/portability/test_{candidate.replace('-', '_')}_portability.py",
        f"docs/adrs/ADR-XXX-{candidate}.md",
        f"docs/architecture/{candidate}.md",
    ])
    return artifacts


def validation_plan_for(decision: str, candidate: str) -> list[str]:
    if decision == DISCARD:
        return []
    test_name = candidate.replace("-", "_")
    return [
        f"python3 -m pytest tests/behavior/test_{test_name}.py -q",
        f"python3 -m pytest tests/red_team/portability/test_{test_name}_portability.py -q",
        "python3 scripts/cos_work_inventory.py --all --strict --json",
    ]


def risk_labels(text: str) -> list[str]:
    labels: list[str] = []
    lower = text.lower()
    mapping = {
        "git-state": ["stash", "worktree", "commit", "push", "branch"],
        "data-loss": ["drop", "borrar", "remove", "cleanup", "limpiar"],
        "security": ["secret", "credencial", "token", "path absoluto"],
        "concurrency": ["agente", "concurr", "multi-session", "ide"],
    }
    for label, needles in mapping.items():
        if any(needle in lower for needle in needles):
            labels.append(label)
    return labels


def harvest(text: str, repo: Path) -> HarvestResult:
    conversion = count_matches(CONVERSION_PATTERNS, text)
    improvement = count_matches(IMPROVEMENT_PATTERNS, text)
    docs = count_matches(DOC_PATTERNS, text)
    risks = count_matches(RISK_PATTERNS, text)
    verify = count_matches(VERIFY_PATTERNS, text)
    commands = command_count(text)
    candidate = infer_candidate_name(text)
    existing, existing_score = best_existing_match(candidate, text, discover_existing_primitives(repo))
    primitive_type = infer_primitive_type(text)
    reasons: list[str] = []

    if conversion:
        reasons.append(f"conversion_signals={conversion}")
    if improvement:
        reasons.append(f"improvement_signals={improvement}")
    if risks:
        reasons.append(f"risk_signals={risks}")
    if verify:
        reasons.append(f"verification_signals={verify}")
    if commands:
        reasons.append(f"command_lines={commands}")
    if existing and existing_score >= 0.67:
        reasons.append(f"existing_{existing.kind}_match={existing.name}:{existing_score:.2f}")

    if not text.strip():
        decision = DISCARD
        confidence = 0.84
        next_action = "discard; capture as ordinary conversation only"
    elif docs and not commands and risks == 0 and conversion == 0:
        decision = DOCUMENT_ONLY
        confidence = 0.78
        next_action = "write ADR/docs; do not create executable primitive"
    elif existing and existing_score >= 0.67 and improvement:
        decision = IMPROVE_EXISTING
        confidence = min(0.95, 0.65 + existing_score * 0.2 + min(0.1, improvement * 0.03) + min(0.1, verify * 0.02))
        next_action = f"extend existing {existing.kind} `{existing.name}` with tests"
    elif existing and existing_score >= 0.84:
        decision = USE_EXISTING
        confidence = 0.88
        next_action = f"invoke existing {existing.kind} `{existing.name}` instead of creating a duplicate"
    elif (conversion + docs + risks + verify + commands) < 2:
        decision = DISCARD
        confidence = 0.84
        next_action = "discard; capture as ordinary conversation only"
    elif conversion and (risks or verify or commands):
        decision = CREATE_PRIMITIVE
        confidence = min(0.94, 0.55 + min(0.15, conversion * 0.04) + min(0.12, risks * 0.03) + min(0.12, verify * 0.03) + min(0.1, commands * 0.02))
        next_action = "create proposed artifacts behind governed review"
    else:
        decision = DISCARD
        confidence = 0.72
        next_action = "discard; insufficient repeatability, risk, or verification signal"

    match_payload = asdict(existing) | {"score": round(existing_score, 3)} if existing else None
    return HarvestResult(
        decision=decision,
        confidence=round(confidence, 3),
        candidate_name=None if decision == DISCARD else candidate,
        primitive_type=None if decision == DISCARD else primitive_type,
        existing_match=match_payload if decision in {IMPROVE_EXISTING, USE_EXISTING} else None,
        reasons=reasons or ["insufficient_signal"],
        risks=risk_labels(text),
        artifact_plan=artifact_plan_for(candidate, primitive_type, decision, existing),
        validation_plan=validation_plan_for(decision, candidate),
        next_action=next_action,
    )


def read_input(args: argparse.Namespace) -> str:
    if args.text is not None:
        return args.text
    if args.conversation_file:
        return Path(args.conversation_file).read_text(encoding="utf-8")
    if args.from_engram:
        proc = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return proc.stdout
    raise SystemExit("Provide --text or --conversation-file")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--conversation-file")
    parser.add_argument("--text")
    parser.add_argument("--from-engram", action="store_true", help="Reserved adapter hook; currently emits environment context only.")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = harvest(read_input(args), Path(args.repo).resolve())
    payload = asdict(result)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"decision={result.decision}")
        print(f"confidence={result.confidence}")
        print(f"candidate={result.candidate_name or ''}")
        print(f"next_action={result.next_action}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
