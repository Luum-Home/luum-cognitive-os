"""Audit COS agent-training claims against the canonical harness contract."""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.audit

REPO = Path(__file__).resolve().parents[2]
MANIFEST = REPO / "manifests" / "agent-training-harness.yaml"
CANONICAL_DOC = REPO / "docs" / "architecture" / "agent-training-harness.md"

TRAINING_TERM_RE = re.compile(
    r"\b(train(?:ing|ed)?|fine[- ]?tun(?:e|ing|ed)?|rl|reinforcement learning|entren[a-záéíóúñ]*)\b",
    re.IGNORECASE,
)
AGENT_CONTEXT_RE = re.compile(r"\b(agent(?:s|ic)?|harness|cos|self[- ]?improv|model weights?|provider-weight)\b", re.IGNORECASE)
NEGATING_CONTEXT_RE = re.compile(
    r"\b(not|no|non-goals?|out[- ]of[- ]scope|rejected|cannot|does not|do not|no es|no significa)\b",
    re.IGNORECASE,
)

SCAN_ROOTS = (
    "docs",
    "rules",
    "skills",
    "manifests",
)
SKIP_PARTS = {
    ".git",
    "archive",
    "history",
    "research",
    "reports",
    "adrs",
    "manual-tests",
    "measurements",
}
SCAN_SUFFIXES = {".md", ".yaml", ".yml"}


def _manifest() -> dict:
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))


def _relative(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def _scan_paths() -> list[Path]:
    paths: list[Path] = []
    for root_name in SCAN_ROOTS:
        root = REPO / root_name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in SCAN_SUFFIXES:
                continue
            rel_parts = set(path.relative_to(REPO).parts)
            if rel_parts & SKIP_PARTS:
                continue
            paths.append(path)
    return sorted(paths)


def _is_agent_training_claim(line: str) -> bool:
    if not TRAINING_TERM_RE.search(line):
        return False
    if not AGENT_CONTEXT_RE.search(line):
        return False
    # Explicit non-goals and out-of-scope statements are allowed because they
    # reduce rather than inflate training claims.
    if NEGATING_CONTEXT_RE.search(line):
        return False
    return True


def test_manifest_schema_and_canonical_doc_exist() -> None:
    manifest = _manifest()
    assert manifest["schema_version"] == "agent-training-harness.v1"
    assert manifest["canonical_doc"] == "docs/architecture/agent-training-harness.md"
    assert manifest["position"]["training_mode"] == "operational-learning"
    assert manifest["position"]["provider_weight_training"] is False
    assert manifest["position"]["default_auto_apply"] is False
    assert CANONICAL_DOC.is_file()

    canonical_text = CANONICAL_DOC.read_text(encoding="utf-8")
    for required in (
        "does **not** train model weights inside the harness",
        "operational learning",
        "fine-tuning or reinforcement learning over provider model weights",
        "Acceptance criteria for training changes",
    ):
        assert required in canonical_text


def test_manifest_references_existing_authoritative_and_pointer_paths() -> None:
    manifest = _manifest()
    paths = set(manifest["claim_policy"]["current_authoritative_paths"])
    paths.update(manifest["claim_policy"].get("allowed_pointer_paths", []))
    paths.add(manifest["canonical_doc"])
    paths.add(manifest["validation"]["audit_test"])

    missing = [path for path in sorted(paths) if not (REPO / path).exists()]
    assert missing == []


def test_operational_training_claims_stay_on_authoritative_or_pointer_paths() -> None:
    manifest = _manifest()
    allowed = set(manifest["claim_policy"]["current_authoritative_paths"])
    allowed.update(manifest["claim_policy"].get("allowed_pointer_paths", []))
    allowed.add(manifest["canonical_doc"])

    offenders: list[str] = []
    for path in _scan_paths():
        rel = _relative(path)
        for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            if _is_agent_training_claim(line) and rel not in allowed:
                offenders.append(f"{rel}:{lineno}: {line.strip()}")

    assert offenders == [], (
        "Agent-training claims must live in the canonical doc/manifest or pointer docs. "
        "Link to docs/architecture/agent-training-harness.md or add explicit evidence before expanding claims:\n"
        + "\n".join(offenders[:50])
    )


def test_prioritized_training_primitives_have_lifecycle_metadata() -> None:
    lifecycle = yaml.safe_load((REPO / "manifests" / "primitive-lifecycle.yaml").read_text(encoding="utf-8"))
    rows = {item["id"]: item for item in lifecycle["primitives"]}
    required = {
        "skills/self-improve/SKILL.md": "skill",
        "skills/agent-kpis/SKILL.md": "skill",
        "hooks/error-learning.sh": "hook",
        "hooks/session-learning.sh": "hook",
        "hooks/kpi-trigger.sh": "hook",
        "rules/self-improvement-protocol.md": "rule",
    }

    missing = sorted(set(required) - set(rows))
    assert missing == []

    wrong_kind = [path for path, kind in required.items() if rows[path].get("kind") != kind]
    assert wrong_kind == []

    for path in required:
        row = rows[path]
        assert row["maturity"] in {"observe", "advisory", "blocking"}
        assert row["docs_claim_level"] in {"observe", "advisory", "blocking"}
        assert row["evidence_commands"]
