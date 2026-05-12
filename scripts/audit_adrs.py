#!/usr/bin/env python3
"""audit_adrs.py — Validate ADR YAML frontmatter and implementation file existence.

Walks docs/02-Decisions/adrs/*.md, parses the YAML
frontmatter block (between leading --- delimiters), and reports:

  MISSING_FRONTMATTER      — ADR has no YAML frontmatter (warn only)
  MALFORMED_YAML           — frontmatter exists but fails yaml.safe_load()
  STATUS_REALITY_MISMATCH  — declared implementation_files missing on disk
  SUPERSEDES_BROKEN_REF    — supersedes[] lists an ADR number not found on disk
  ADR_RELATION_CHAIN_LONG  — extends/supersedes chains exceed the scope-creep budget
  ADR_RELATION_CYCLE       — relationship graph contains a cycle
  OK                       — frontmatter parses, files verified (or none declared)

CLI flags:
  --json          Machine-readable JSON output (CI-friendly)
  --strict        Exit non-zero on any finding (except MISSING_FRONTMATTER)
  --migrate-from-prose
                  Dry-run: suggest frontmatter for ADRs that lack it (no writes)

Usage:
  python3 scripts/audit_adrs.py
  python3 scripts/audit_adrs.py --strict
  python3 scripts/audit_adrs.py --json
  python3 scripts/audit_adrs.py --migrate-from-prose
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML not installed — run: pip install pyyaml")

# ── Repo layout ───────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[1]

ADR_DIRS: list[Path] = [
    REPO_ROOT / "docs" / "adrs",
]

# ── Finding level constants ───────────────────────────────────────────────────

LEVEL_OK = "OK"
LEVEL_WARN = "WARN"
LEVEL_FAIL = "FAIL"

# Finding codes
CODE_MISSING_FRONTMATTER = "MISSING_FRONTMATTER"
CODE_MALFORMED_YAML = "MALFORMED_YAML"
CODE_STATUS_REALITY_MISMATCH = "STATUS_REALITY_MISMATCH"
CODE_SUPERSEDES_BROKEN_REF = "SUPERSEDES_BROKEN_REF"
CODE_ADR_RELATION_CHAIN_LONG = "ADR_RELATION_CHAIN_LONG"
CODE_ADR_RELATION_CYCLE = "ADR_RELATION_CYCLE"
CODE_INVALID_STATUS = "INVALID_STATUS"
CODE_INVALID_IMPLEMENTATION_STATUS = "INVALID_IMPLEMENTATION_STATUS"
CODE_MISSING_REQUIRED_FRONTMATTER = "MISSING_REQUIRED_FRONTMATTER"
CODE_INVALID_CLASSIFICATION_BASIS = "INVALID_CLASSIFICATION_BASIS"
CODE_INVALID_STATUS_TRANSITION = "INVALID_STATUS_TRANSITION"
CODE_INDEX_STALE = "ADR_INDEX_STALE"

# Valid status values
VALID_STATUSES = {"proposed", "exploration", "accepted", "implemented", "resolved", "superseded", "deprecated", "tombstone"}
VALID_IMPLEMENTATION_STATUSES = {"not-applicable", "planned", "partial", "partial-blocked", "blocked", "deferred", "implemented", "resolved"}
REQUIRED_FRONTMATTER_FIELDS = {
    "adr",
    "title",
    "status",
    "implementation_status",
    "classification_basis",
    "implementation_files",
    "tier",
    "tags",
}
TERMINAL_STATUSES = {"tombstone", "superseded", "deprecated"}
NOT_APPLICABLE_PREFIXES = ("governance-only:", "policy-only:")
PARTIAL_BASIS_RE = re.compile(
    r"\b(partial|slice|phase|future|deferred|pending|blocked|follow-up|remaining|remains|not implemented|staged|operator|rollout|incomplete|migration|planned)\b",
    re.IGNORECASE,
)
FUTURE_WORK_RE = re.compile(
    r"\b(slice a implemented|future work|future slice|future slices|not implemented yet|remaining work|remains follow-up|deferred|pending|planned|staged for operator|runtime enforcement remains)\b",
    re.IGNORECASE,
)
IMPLEMENTED_CLOSURE_RE = re.compile(
    r"\b(implemented|closed|complete|satisf(?:y|ies|ied)|no remaining in-scope|no remaining in scope|design-only|contract scope|policy-only|governance-only)\b",
    re.IGNORECASE,
)
OUT_OF_SCOPE_FUTURE_RE = re.compile(
    r"\b(no remaining in-scope|no remaining in scope|future .*?(separate|out of scope|out-of-scope)|separate implementation scope|design-only|contract scope|not core closure)\b",
    re.IGNORECASE,
)

# Relationship-chain budget: current reconstruction allows short lineage, but
# chains longer than this need consolidation instead of another ADR-on-ADR layer.
MAX_RELATION_CHAIN_DEPTH = 2
# Historical ADRs are normalized by the backfill reports but may not have every
# future authoring field populated. The hard authoring contract applies to new
# ADRs from ADR-276 onward; set COS_STRICT_ADR_LIFECYCLE_ALL=1 to audit legacy
# records with the same strictness during explicit cleanup sprints.
NEW_ADR_CONTRACT_MIN_ADR = 276

# ── Helpers ───────────────────────────────────────────────────────────────────


def _extract_frontmatter(text: str) -> tuple[str | None, str]:
    """Return (frontmatter_string_or_None, body_remainder).

    Frontmatter must start at line 1 with '---' and close with '---' before
    any non-whitespace body content.
    """
    lines = text.splitlines(keepends=True)
    if not lines:
        return None, text
    if lines[0].rstrip() != "---":
        return None, text

    closing_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.rstrip() == "---":
            closing_idx = i
            break

    if closing_idx is None:
        return None, text

    fm_lines = lines[1:closing_idx]
    body = "".join(lines[closing_idx + 1 :])
    return "".join(fm_lines), body


def _adr_number_from_filename(path: Path) -> int | None:
    """Extract ADR number from filename like ADR-105-... or 105-..."""
    m = re.match(r"(?:ADR-)?0*([0-9]+)", path.stem)
    return int(m.group(1)) if m else None


def _adr_record_key(path: Path) -> str | None:
    """Return a stable ADR identity key while preserving suffixed follow-ups.

    ADR-174, ADR-174b, and ADR-174c are distinct decision records. Deprecated
    redirect directories can still contain duplicate numeric stubs, so this key
    deduplicates exact ADR identities rather than every file sharing a number.
    """
    match = re.match(r"(?:ADR-)?0*([0-9]+)([a-z]?)\b", path.stem, flags=re.IGNORECASE)
    if not match:
        return None
    number, suffix = match.groups()
    return f"{int(number):03d}{suffix.lower()}"


def _adr_sort_key(path: Path) -> tuple[int, str]:
    num = _adr_number_from_filename(path) or 0
    key = _adr_record_key(path) or ""
    suffix = key.removeprefix(f"{num:03d}") if num else key
    return (num, suffix)


def _collect_adr_files() -> list[Path]:
    """Return all ADR markdown files from both ADR directories.

    Deduplicates by ADR identity, not only numeric slot. This preserves
    legitimate suffixed follow-ups such as ADR-174b/ADR-174c while still letting
    docs/02-Decisions/adrs/ take precedence over deprecated redirect stubs with the same key.
    """
    by_key: dict[str | None, Path] = {}
    # Process docs/02-Decisions/adrs first so it takes precedence
    for d in ADR_DIRS:
        if not d.exists():
            continue
        for p in sorted(d.glob("*.md")):
            if p.stem.upper() == "README":
                continue
            key = _adr_record_key(p)
            if key is None:
                continue
            # Only insert if not yet seen (first dir wins = docs/02-Decisions/adrs takes precedence)
            if key not in by_key:
                by_key[key] = p
    return sorted(by_key.values(), key=_adr_sort_key)


def _known_adr_numbers(files: list[Path]) -> set[int]:
    nums: set[int] = set()
    for f in files:
        n = _adr_number_from_filename(f)
        if n is not None:
            nums.add(n)
    return nums




def _coerce_adr_ref(value: Any) -> int | None:
    """Parse ADR references from ints, "ADR-043", or prose-ish strings."""
    if isinstance(value, int):
        return value
    match = re.search(r"0*([0-9]+)", str(value))
    return int(match.group(1)) if match else None


def _relationship_refs(path: Path, fm: dict[str, Any] | None, body: str) -> set[int]:
    """Return outgoing extends/supersedes/replaces refs for scope-creep analysis."""
    refs: set[int] = set()
    if isinstance(fm, dict):
        for key in ("supersedes", "extends", "replaces"):
            raw = fm.get(key) or []
            if isinstance(raw, (str, int)):
                raw = [raw]
            if isinstance(raw, list):
                for item in raw:
                    ref = _coerce_adr_ref(item)
                    if ref is not None:
                        refs.add(ref)
    for match in re.finditer(
        r"(?i)\b(?:supersedes|extends|replaces)\s+ADR[- ]0*([0-9]+)", body
    ):
        refs.add(int(match.group(1)))
    return refs



def _relationship_chain_exempt(fm: dict[str, Any] | None, body: str) -> bool:
    """Return True for ADRs intentionally consolidated by an implementation ledger."""
    if isinstance(fm, dict) and fm.get("relationship_chain_exempt") is True:
        return True
    return "ADR_RELATION_CHAIN_EXEMPT" in body


def analyze_relationship_graph(files: list[Path]) -> list[dict[str, Any]]:
    """Warn on ADR relationship cycles and chains that encourage scope creep."""
    by_num: dict[int, tuple[Path, set[int]]] = {}
    known = _known_adr_numbers(files)
    findings: list[dict[str, Any]] = []

    for path in files:
        adr_num = _adr_number_from_filename(path)
        if adr_num is None:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        fm_str, body = _extract_frontmatter(text)
        fm: dict[str, Any] | None = None
        if fm_str is not None:
            try:
                loaded = yaml.safe_load(fm_str) or {}
                fm = loaded if isinstance(loaded, dict) else None
            except yaml.YAMLError:
                fm = None
        if _relationship_chain_exempt(fm, body):
            continue
        refs = {ref for ref in _relationship_refs(path, fm, body) if ref in known and ref != adr_num}
        if refs:
            by_num[adr_num] = (path, refs)

    def paths_from(start: int, path_so_far: list[int]) -> list[list[int]]:
        if start in path_so_far:
            return [path_so_far + [start]]
        refs = by_num.get(start, (Path(), set()))[1]
        if not refs:
            return [path_so_far + [start]]
        out: list[list[int]] = []
        for ref in sorted(refs):
            out.extend(paths_from(ref, path_so_far + [start]))
        return out

    emitted_cycles: set[tuple[int, ...]] = set()
    for start, (path, _refs) in sorted(by_num.items()):
        for chain in paths_from(start, []):
            if len(chain) != len(set(chain)):
                first = chain[-1]
                idx = chain.index(first)
                cycle = tuple(chain[idx:])
                if cycle not in emitted_cycles:
                    emitted_cycles.add(cycle)
                    findings.append({
                        "adr": start,
                        "file": str(path.relative_to(REPO_ROOT)),
                        "level": LEVEL_FAIL,
                        "code": CODE_ADR_RELATION_CYCLE,
                        "chain": [f"ADR-{n:03d}" for n in cycle],
                        "message": "ADR extends/supersedes graph contains a cycle",
                    })
                continue
            depth = len(chain) - 1
            if depth > MAX_RELATION_CHAIN_DEPTH:
                findings.append({
                    "adr": start,
                    "file": str(path.relative_to(REPO_ROOT)),
                    "level": LEVEL_WARN,
                    "code": CODE_ADR_RELATION_CHAIN_LONG,
                    "chain_depth": depth,
                    "max_chain_depth": MAX_RELATION_CHAIN_DEPTH,
                    "chain": [f"ADR-{n:03d}" for n in chain],
                    "message": (
                        f"Relationship chain depth {depth} exceeds budget {MAX_RELATION_CHAIN_DEPTH}; "
                        "consolidate with a tombstone, index ADR, or implementation ledger before adding another layer."
                    ),
                })
    return findings

def _implementation_path_exists(rel: str) -> bool:
    """Return True when a declared implementation path exists on disk.

    `implementation_files` is a falsifiable disk claim, not prose evidence.
    Globs are allowed for narrow generated/document batches such as
    `templates/foo/*.md`, but at least one path must match.
    """
    candidate = REPO_ROOT / rel
    if candidate.resolve().exists():
        return True
    if rel.endswith("/") and (REPO_ROOT / rel.rstrip("/")).resolve().exists():
        return True
    if "*" in rel:
        return bool(list(REPO_ROOT.glob(rel)))
    return False


def _verify_implementation_files(
    impl_files: list[str],
) -> tuple[list[str], list[str]]:
    """Return (present, missing) lists for every declared implementation file.

    This check is unconditional for declared paths: decision `status` and
    `implementation_status` do not change whether a path claim is true.
    """
    present: list[str] = []
    missing: list[str] = []
    for rel in impl_files:
        if _implementation_path_exists(str(rel)):
            present.append(str(rel))
        else:
            missing.append(str(rel))
    return present, missing


def _extract_prose_status(body: str) -> str | None:
    """Extract status from common prose patterns for migration suggestions."""
    patterns = [
        r"\*\*Status\*\*:\s*(.+)",
        r"^#+\s*Status\s*$",
        r"^Status:\s*(.+)",
    ]
    for pattern in patterns:
        m = re.search(pattern, body, re.MULTILINE | re.IGNORECASE)
        if m and m.lastindex:
            raw = m.group(1).strip()
            # Map common prose values to schema values
            lower = raw.lower()
            if "exploration" in lower:
                return "exploration"
            if "resolved" in lower:
                return "resolved"
            if "tombstone" in lower:
                return "tombstone"
            if "implement" in lower:
                return "implemented"
            if "accept" in lower:
                return "accepted"
            if "proposed" in lower or "draft" in lower:
                return "proposed"
            if "superseded" in lower:
                return "superseded"
            if "deprecated" in lower or "retired" in lower:
                return "deprecated"
    return None


def _suggest_frontmatter(path: Path, body: str) -> str:
    """Generate a suggested frontmatter block for an ADR lacking it."""
    adr_num = _adr_number_from_filename(path) or 0
    # Extract title from first heading
    title = "UNKNOWN"
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            title = re.sub(r"^#+\s*", "", stripped)
            title = re.sub(r"\s*—.*$", "", title).strip()
            break

    status = _extract_prose_status(body) or "accepted"

    lines = [
        "---",
        f"adr: {adr_num}",
        f'title: "{title}"',
        f"status: {status}",
        "date: YYYY-MM-DD",
        "supersedes: []",
        "superseded_by: null",
        "classification_basis: planned: prose-only migration suggestion requires operator triage",
        "implementation_files: []",
        "tier: standard",
        "tags: []",
        "---",
    ]
    return "\n".join(lines)


def _has_section(body: str, names: tuple[str, ...]) -> bool:
    for name in names:
        if re.search(rf"^##\s+{re.escape(name)}\b", body, re.MULTILINE | re.IGNORECASE):
            return True
    return False


def _has_implemented_evidence(fm: dict[str, Any], body: str, classification_basis: str) -> bool:
    impl_files = fm.get("implementation_files") or []
    if isinstance(impl_files, list) and impl_files:
        return True
    if _has_section(body, ("Implementation Evidence", "Implementation", "Verification")):
        return True
    return bool(IMPLEMENTED_CLOSURE_RE.search(classification_basis))


def _append_fail(findings: list[dict[str, Any]], base: dict[str, Any], code: str, message: str, **extra: Any) -> None:
    findings.append({**base, "level": LEVEL_FAIL, "code": code, "message": message, **extra})


def _strict_lifecycle_applies(base: dict[str, Any]) -> bool:
    return bool(base.get("adr", 0) >= NEW_ADR_CONTRACT_MIN_ADR or __import__("os").environ.get("COS_STRICT_ADR_LIFECYCLE_ALL") == "1")


def _validate_lifecycle_contract(
    base: dict[str, Any],
    fm: dict[str, Any],
    body: str,
    status: str,
    implementation_status: str,
    impl_files: list[str],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    strict_lifecycle = _strict_lifecycle_applies(base)

    required_fields = REQUIRED_FRONTMATTER_FIELDS if strict_lifecycle else {"adr", "title", "status", "implementation_status", "implementation_files", "tier", "tags"}
    missing = sorted(field for field in required_fields if field not in fm)
    if missing:
        _append_fail(
            findings,
            base,
            CODE_MISSING_REQUIRED_FRONTMATTER,
            "ADR frontmatter is missing required field(s): " + ", ".join(missing),
            missing_fields=missing,
        )

    classification_basis = str(fm.get("classification_basis") or "").strip()
    if strict_lifecycle and not classification_basis:
        _append_fail(
            findings,
            base,
            CODE_INVALID_CLASSIFICATION_BASIS,
            "classification_basis is required and must explain the implementation_status classification",
        )

    if "tags" in fm and not isinstance(fm.get("tags"), list):
        _append_fail(findings, base, CODE_MISSING_REQUIRED_FRONTMATTER, "tags must be a YAML list")
    if "implementation_files" in fm and not isinstance(fm.get("implementation_files") or [], list):
        _append_fail(findings, base, CODE_MISSING_REQUIRED_FRONTMATTER, "implementation_files must be a YAML list")

    if strict_lifecycle and implementation_status == "not-applicable" and not classification_basis.startswith(NOT_APPLICABLE_PREFIXES):
        _append_fail(
            findings,
            base,
            CODE_INVALID_CLASSIFICATION_BASIS,
            "not-applicable requires classification_basis to start with governance-only: or policy-only:",
            classification_basis=classification_basis,
        )

    if strict_lifecycle and status == "accepted" and not impl_files:
        allowed_empty = implementation_status == "planned" or (
            implementation_status == "not-applicable" and classification_basis.startswith(NOT_APPLICABLE_PREFIXES)
        )
        if not allowed_empty:
            _append_fail(
                findings,
                base,
                CODE_INVALID_STATUS_TRANSITION,
                "accepted ADRs with empty implementation_files must be planned, governance-only, or policy-only",
                implementation_status=implementation_status,
            )

    if strict_lifecycle and status == "accepted" and impl_files and implementation_status in {"not-applicable", "planned"}:
        _append_fail(
            findings,
            base,
            CODE_INVALID_STATUS_TRANSITION,
            "accepted ADRs with implementation_files must classify implementation_status as implemented or partial/blocked/deferred/resolved",
            implementation_status=implementation_status,
        )

    if status in TERMINAL_STATUSES and implementation_status not in {"not-applicable", "resolved"}:
        _append_fail(
            findings,
            base,
            CODE_INVALID_STATUS_TRANSITION,
            "tombstone/superseded/deprecated ADRs must use implementation_status not-applicable or resolved",
            implementation_status=implementation_status,
        )

    if status == "exploration" and implementation_status not in {"not-applicable", "planned"}:
        _append_fail(
            findings,
            base,
            CODE_INVALID_STATUS_TRANSITION,
            "exploration ADRs must not claim implemented/partial execution status",
            implementation_status=implementation_status,
        )

    if strict_lifecycle and implementation_status == "implemented":
        if not _has_implemented_evidence(fm, body, classification_basis):
            _append_fail(
                findings,
                base,
                CODE_INVALID_STATUS_TRANSITION,
                "implemented ADRs require implementation_files, an evidence/verification section, or explicit closure basis",
            )
        if FUTURE_WORK_RE.search(body) and not OUT_OF_SCOPE_FUTURE_RE.search(classification_basis):
            _append_fail(
                findings,
                base,
                CODE_INVALID_STATUS_TRANSITION,
                "implemented ADR text mentions future/deferred/not-implemented work; classification_basis must state that future work is separate/out of scope or that no in-scope work remains",
            )

    if strict_lifecycle and implementation_status in {"partial", "partial-blocked", "blocked", "deferred"}:
        if not PARTIAL_BASIS_RE.search(classification_basis):
            _append_fail(
                findings,
                base,
                CODE_INVALID_CLASSIFICATION_BASIS,
                "partial/deferred/blocked ADRs require classification_basis to name the remaining, deferred, blocked, staged, rollout, or follow-up work",
                classification_basis=classification_basis,
            )

    return findings


# ── Audit core ────────────────────────────────────────────────────────────────


def audit_file(path: Path, known_adrs: set[int]) -> dict[str, Any]:
    """Audit a single ADR file. Returns a findings dict."""
    adr_num = _adr_number_from_filename(path) or 0
    text = path.read_text(encoding="utf-8")
    fm_str, body = _extract_frontmatter(text)

    try:
        rel_path = str(path.relative_to(REPO_ROOT))
    except ValueError:
        rel_path = str(path)
    base: dict[str, Any] = {"adr": adr_num, "file": rel_path}

    # ── No frontmatter ────────────────────────────────────────────────────────
    if fm_str is None:
        return {
            **base,
            "level": LEVEL_WARN,
            "code": CODE_MISSING_FRONTMATTER,
            "message": "No YAML frontmatter found (prose-only ADR)",
        }

    # ── Parse YAML ────────────────────────────────────────────────────────────
    try:
        fm: dict[str, Any] = yaml.safe_load(fm_str) or {}
    except yaml.YAMLError as exc:
        return {
            **base,
            "level": LEVEL_FAIL,
            "code": CODE_MALFORMED_YAML,
            "message": f"YAML parse error: {exc}",
        }

    if not isinstance(fm, dict):
        return {
            **base,
            "level": LEVEL_FAIL,
            "code": CODE_MALFORMED_YAML,
            "message": "Frontmatter parsed but is not a YAML mapping",
        }

    raw_status = fm.get("status", "")
    if not isinstance(raw_status, str):
        return {
            **base,
            "level": LEVEL_FAIL,
            "code": CODE_INVALID_STATUS,
            "message": "frontmatter status must be a scalar string; split mixed lifecycle states into a follow-up ADR",
        }
    status: str = raw_status.lower()
    raw_impl_status = fm.get("implementation_status", "")
    if not isinstance(raw_impl_status, str) or not raw_impl_status.strip():
        return {
            **base,
            "level": LEVEL_FAIL,
            "code": CODE_INVALID_IMPLEMENTATION_STATUS,
            "message": "frontmatter implementation_status is required and must be a scalar string",
        }
    implementation_status: str = raw_impl_status.strip().lower()
    impl_files: list[str] = fm.get("implementation_files") or []
    supersedes: list[int] = fm.get("supersedes") or []

    findings: list[dict[str, Any]] = []
    _strict_lifecycle_applies(base)
    findings.extend(_validate_lifecycle_contract(base, fm, body, status, implementation_status, impl_files))

    if status and status not in VALID_STATUSES:
        findings.append(
            {
                **base,
                "level": LEVEL_FAIL,
                "code": CODE_INVALID_STATUS,
                "status": status,
                "message": f"status={status!r} is not one of {sorted(VALID_STATUSES)}",
            }
        )

    if implementation_status not in VALID_IMPLEMENTATION_STATUSES:
        findings.append(
            {
                **base,
                "level": LEVEL_FAIL,
                "code": CODE_INVALID_IMPLEMENTATION_STATUS,
                "implementation_status": implementation_status,
                "message": f"implementation_status={implementation_status!r} is not one of {sorted(VALID_IMPLEMENTATION_STATUSES)}",
            }
        )

    # ── Supersedes reference check ────────────────────────────────────────────
    for raw_ref in supersedes:
        ref_num = _coerce_adr_ref(raw_ref)
        if ref_num is not None and ref_num not in known_adrs:
            findings.append(
                {
                    **base,
                    "level": LEVEL_WARN,
                    "code": CODE_SUPERSEDES_BROKEN_REF,
                    "message": f"supersedes references ADR-{ref_num} which was not found on disk",
                }
            )

    # ── Implementation file verification ─────────────────────────────────────
    present: list[str] = []
    if impl_files:
        present, missing = _verify_implementation_files(impl_files)
        if missing:
            findings.append(
                {
                    **base,
                    "level": LEVEL_FAIL,
                    "code": CODE_STATUS_REALITY_MISMATCH,
                    "status": status,
                    "implementation_status": implementation_status,
                    "missing_files": missing,
                    "files_verified": len(present),
                    "message": (
                        f"{len(missing)} declared implementation_file(s) missing: "
                        + ", ".join(missing)
                    ),
                }
            )

    if findings:
        # Return worst finding first
        findings.sort(key=lambda f: (0 if f["level"] == LEVEL_FAIL else 1))
        return findings[0]

    return {
        **base,
        "level": LEVEL_OK,
        "code": "OK",
        "status": status,
        "files_verified": len(present),
        "message": (f"OK — {len(present)} file(s) verified" if present else f"OK — status={status!r}, no implementation_files declared"),
    }


# Needed after defining audit_file
CODE_OK = "OK"


def run_audit(
    strict: bool = False,
    output_json: bool = False,
    migrate_from_prose: bool = False,
) -> int:
    """Main audit runner. Returns exit code."""
    adr_files = _collect_adr_files()
    known_adrs = _known_adr_numbers(adr_files)

    findings: list[dict[str, Any]] = []
    migration_suggestions: list[dict[str, str]] = []

    for path in adr_files:
        result = audit_file(path, known_adrs)
        findings.append(result)

        if migrate_from_prose and result.get("code") == CODE_MISSING_FRONTMATTER:
            text = path.read_text(encoding="utf-8")
            _fm, body = _extract_frontmatter(text)
            suggestion = _suggest_frontmatter(path, body)
            migration_suggestions.append(
                {
                    "file": result["file"],
                    "suggested_frontmatter": suggestion,
                }
            )

    scanned = len(findings)
    with_frontmatter = sum(
        1 for f in findings if f.get("code") != CODE_MISSING_FRONTMATTER
    )

    relationship_findings = analyze_relationship_graph(adr_files)
    findings.extend(relationship_findings)

    has_failures = any(f.get("level") == LEVEL_FAIL for f in findings)

    if output_json:
        output: dict[str, Any] = {
            "scanned": scanned,
            "with_frontmatter": with_frontmatter,
            "findings": findings,
        }
        if migration_suggestions:
            output["migration_suggestions"] = migration_suggestions
        print(json.dumps(output, indent=2))
    else:
        _print_human_report(findings, migration_suggestions)

    if strict and has_failures:
        return 1
    return 0


def _print_human_report(
    findings: list[dict[str, Any]],
    suggestions: list[dict[str, str]],
) -> None:
    file_findings = [f for f in findings if f.get("code") != CODE_ADR_RELATION_CHAIN_LONG and f.get("code") != CODE_ADR_RELATION_CYCLE]
    scanned = len(file_findings)
    with_fm = sum(1 for f in file_findings if f.get("code") != CODE_MISSING_FRONTMATTER)
    ok_count = sum(1 for f in findings if f.get("level") == LEVEL_OK)
    warn_count = sum(1 for f in findings if f.get("level") == LEVEL_WARN)
    fail_count = sum(1 for f in findings if f.get("level") == LEVEL_FAIL)

    print(
        f"\nADR Frontmatter Audit — {scanned} ADR records scanned, "
        f"{with_fm} with frontmatter\n"
        f"  OK: {ok_count}  WARN: {warn_count}  FAIL: {fail_count}\n"
    )

    for f in findings:
        level = f.get("level", "?")
        code = f.get("code", "?")
        adr = f.get("adr", "?")
        msg = f.get("message", "")
        if level == LEVEL_OK:
            print(f"  [OK]   ADR-{adr:03d}  {msg}")
        elif level == LEVEL_WARN:
            print(f"  [WARN] ADR-{adr:03d}  {code}: {msg}")
        else:
            print(f"  [FAIL] ADR-{adr:03d}  {code}: {msg}")

    if suggestions:
        print("\n--- Migration suggestions (--migrate-from-prose) ---\n")
        for s in suggestions:
            print(f"# {s['file']}")
            print(s["suggested_frontmatter"])
            print()


# ── CLI entry point ───────────────────────────────────────────────────────────


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit ADR YAML frontmatter and validate implementation_files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Machine-readable JSON output",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero on any FAIL finding",
    )
    parser.add_argument(
        "--migrate-from-prose",
        action="store_true",
        dest="migrate_from_prose",
        help="Dry-run: suggest frontmatter for ADRs that lack it (no writes)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    exit_code = run_audit(
        strict=args.strict,
        output_json=args.output_json,
        migrate_from_prose=args.migrate_from_prose,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
