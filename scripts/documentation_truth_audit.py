#!/usr/bin/env python3
# SCOPE: both
"""Audit volatile documentation claims against generated truth sources.

This is stricter than a Markdown linter: claims are declared in
manifests/documentation-truth-claims.yaml, facts are derived from generated
reports/manifests, and docs are checked for stale forbidden prose, required
phrases, source report availability, and generated fact blocks.
"""
from __future__ import annotations
import os as _cos_os
import sys as _cos_sys
_cos_sys.path.insert(0, _cos_os.path.dirname(_cos_os.path.dirname(__file__)))
from cos_lib.script_helpers import read_yaml_dict as read_yaml
from cos_lib.script_helpers import read_json_dict as read_json
from cos_lib.project_paths import relpath as rel

import argparse
import json
import os as _os
import re
import sys
from fnmatch import fnmatch
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "documentation-truth-audit.v1"
DEFAULT_MANIFEST = Path("manifests/documentation-truth-claims.yaml")
DEFAULT_JSON = Path("docs/06-Daily/reports/documentation-truth-latest.json")
DEFAULT_MD = Path("docs/06-Daily/reports/documentation-truth-latest.md")
BLOCK_START = "<!-- GENERATED:documentation-truth:{marker}:start -->"
BLOCK_END = "<!-- GENERATED:documentation-truth:{marker}:end -->"


@dataclass(frozen=True)
class TruthRow:
    claim_id: str
    check: str
    status: str
    severity: str
    doc: str | None
    message: str
    evidence: list[str]
    next_action: str


def implemented_harnesses(root: Path) -> list[str]:
    data = read_yaml(root / "manifests" / "harness-projection.yaml")
    harnesses = []
    for item in data.get("harnesses", []):
        if item.get("status") == "implemented" and item.get("id"):
            harnesses.append(str(item["id"]))
    return sorted(harnesses)


def json_summary(root: Path, report: str) -> dict[str, Any]:
    data = read_json(root / report)
    summary = data.get("summary", {}) if isinstance(data, dict) else {}
    status = data.get("status") or data.get("gate", {}).get("status")
    return {"status": status, "summary": summary}


def block_payload(root: Path, claim_id: str) -> list[str]:
    if claim_id == "consumer_projection_harnesses":
        harnesses = implemented_harnesses(root)
        projection = json_summary(root, "docs/06-Daily/reports/primitive-projection-fidelity-latest.json")
        projection_summary = projection.get("summary", {})
        return [
            "Generated documentation truth: consumer projection harnesses.",
            f"Implemented harnesses ({len(harnesses)}): {', '.join(harnesses)}.",
            f"Projection fidelity summary: {json.dumps(projection_summary, sort_keys=True)}.",
            "Structural projection is not runtime enforcement; native lifecycle enforcement remains harness-specific.",
            "Sources: manifests/harness-projection.yaml; docs/06-Daily/reports/primitive-projection-fidelity-latest.json.",
        ]
    if claim_id == "primitive_authority_write_effects":
        authority = json_summary(root, "docs/06-Daily/reports/primitive-authority-latest.json")
        summary = authority.get("summary", {})
        return [
            "Generated documentation truth: primitive authority/write-effects.",
            f"Authority audit status: {authority.get('status') or 'unknown'}.",
            f"Scripts audited: {summary.get('total_scripts', 0)}; blockers: {summary.get('block_count', 0)}; dynamic smokes: {summary.get('dynamic_smokes', 0)}; dynamic blocks: {summary.get('dynamic_blocks', 0)}.",
            "Contract surfaces: manifests/primitive-authority.yaml; scripts/primitive_authority_audit.py; ACC adapter authority_write_effects.",
            "Sources: docs/06-Daily/reports/primitive-authority-latest.json; docs/02-Decisions/adrs/ADR-276-primitive-authority-write-effects.md.",
        ]
    if claim_id == "documentation_truth_control":
        manifest = read_yaml(root / DEFAULT_MANIFEST)
        claims = sorted((manifest.get("claims") or {}).keys())
        return [
            "Generated documentation truth: documentation truth control.",
            f"Declared truth claims ({len(claims)}): {', '.join(claims)}.",
            "Contract surfaces: manifests/documentation-truth-claims.yaml; scripts/documentation_truth_audit.py; ACC adapter documentation_truth.",
            "Report surfaces: docs/06-Daily/reports/documentation-truth-latest.json; docs/06-Daily/reports/documentation-truth-latest.md.",
        ]
    return [f"Generated documentation truth: {claim_id}."]


def render_block(root: Path, claim_id: str, marker: str) -> str:
    lines = [BLOCK_START.format(marker=marker)]
    lines.extend(block_payload(root, claim_id))
    lines.append(BLOCK_END.format(marker=marker))
    return "\n".join(lines)


def find_block(text: str, marker: str) -> tuple[int, int, str] | None:
    start = BLOCK_START.format(marker=marker)
    end = BLOCK_END.format(marker=marker)
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    match = pattern.search(text)
    if not match:
        return None
    return match.start(), match.end(), match.group(0)


def update_block(root: Path, doc: str, claim_id: str, marker: str) -> bool:
    path = root / doc
    expected = render_block(root, claim_id, marker)
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    found = find_block(text, marker)
    if found:
        start, end, current = found
        if current == expected:
            return False
        path.write_text(text[:start] + expected + text[end:], encoding="utf-8")
        return True
    insertion = "\n\n" + expected + "\n"
    path.write_text(text.rstrip() + insertion, encoding="utf-8")
    return True


# --- Forbidden-phrase scan surface (ADR-277 extension) --------------------
# A forbidden phrase used to be searched only inside the claim's own
# required_docs, so a claim without required_docs checked zero files and passed.
# The surface below is declared in the manifest, reported in the output, and
# covers prose AND code, because the live copies of 2026-08-19 lived in a .md,
# a .sh and a .py docstring.

DEFAULT_SCAN_CONFIG: dict[str, Any] = {
    "include_suffixes": [".md", ".sh", ".py", ".yaml", ".yml"],
    "prune_dirs": [
        ".git", ".venv", "venv", "node_modules", "reference", ".cognitive-os",
        "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
        "dist", "build", "target", ".worktrees", "htmlcov", ".egg-info",
    ],
    "exclude_globs": [],
    "skip_date_anchored": True,
    "historical_adr_statuses": ["superseded", "deprecated", "rejected", "withdrawn"],
}
DATE_ANCHOR_RE = re.compile(r"(?<!\d)(19|20)\d{2}-[01]\d-[0-3]\d(?!\d)")
ADR_STATUS_RE = re.compile(r"^status:\s*['\"]?([A-Za-z_-]+)", re.M)
# Characters that may sit between the words of a phrase without changing it:
# whitespace plus the markdown/rst decoration that wraps identifiers.
PHRASE_SEP = r"[\s`'\"*_]+"
# A phrase is a phrase, not a substring: "plan-only Claude/Codex" must not
# match the phrase "only Claude/Codex".
PHRASE_LEFT = r"(?<![0-9A-Za-z_/-])"
PHRASE_RIGHT = r"(?![0-9A-Za-z_/-])"
_WORDISH = re.compile(r"[0-9A-Za-z_/-]")


def scan_config(manifest: dict[str, Any]) -> dict[str, Any]:
    cfg = dict(DEFAULT_SCAN_CONFIG)
    declared = manifest.get("forbidden_phrase_scan") or {}
    for key in ("include_suffixes", "prune_dirs", "skip_date_anchored", "historical_adr_statuses"):
        if key in declared:
            cfg[key] = declared[key]
    cfg["exclude_globs"] = list(declared.get("exclude_globs") or [])
    return cfg


def phrase_pattern(phrase: str) -> re.Pattern[str]:
    """Compile a phrase into a decoration-tolerant, boundary-aware pattern.

    Backticks and quotes around an identifier are typography, not content: the
    same lie shipped as ``cognitive-os.yaml`` in a Python docstring and bare in
    a shell heredoc. Atoms are matched literally, separators are flexible.
    """
    atoms = [a for a in re.split(PHRASE_SEP, phrase.strip()) if a]
    if not atoms:
        return re.compile(r"(?!x)x")
    body = PHRASE_SEP.join(re.escape(a) for a in atoms)
    left = PHRASE_LEFT if _WORDISH.match(atoms[0][0]) else ""
    right = PHRASE_RIGHT if _WORDISH.match(atoms[-1][-1]) else ""
    return re.compile(left + body + right, re.I)


def _is_historical(path: Path, rel_posix: str, cfg: dict[str, Any]) -> str | None:
    if cfg.get("skip_date_anchored") and DATE_ANCHOR_RE.search(path.name):
        return "date-anchored filename: historical record, cites old claims on purpose"
    statuses = {str(s).lower() for s in cfg.get("historical_adr_statuses") or []}
    if statuses and rel_posix.startswith("docs/02-Decisions/adrs/"):
        try:
            head = path.read_text(encoding="utf-8", errors="replace")[:1200]
        except OSError:
            return None
        match = ADR_STATUS_RE.search(head)
        if match and match.group(1).lower() in statuses:
            return f"ADR status {match.group(1).lower()}: superseded decisions keep their original prose"
    return None


def collect_scan_surface(root: Path, cfg: dict[str, Any], always: list[str]) -> tuple[list[str], dict[str, int]]:
    """Walk the repo once and return the declared scan surface.

    Symlinks are resolved and de-duplicated by real path, so a hook reachable
    both as hooks/x.sh and packages/*/hooks/x.sh is one file, not two.
    """
    prune = {str(d) for d in cfg.get("prune_dirs") or []}
    suffixes = {str(s) for s in cfg.get("include_suffixes") or []}
    excludes = [(str(e.get("glob")), str(e.get("reason") or "undeclared")) for e in cfg.get("exclude_globs") or [] if e.get("glob")]
    excluded: dict[str, int] = {}
    seen_real: set[Path] = set()
    files: list[str] = []
    for dirpath, dirnames, filenames in _os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in prune)
        base = Path(dirpath)
        for name in sorted(filenames):
            path = base / name
            if path.suffix not in suffixes:
                continue
            rel_posix = path.relative_to(root).as_posix()
            hit_glob = next((g for g, _ in excludes if fnmatch(rel_posix, g)), None)
            if hit_glob is not None and rel_posix not in always:
                reason = next(r for g, r in excludes if g == hit_glob)
                excluded[f"{hit_glob} :: {reason}"] = excluded.get(f"{hit_glob} :: {reason}", 0) + 1
                continue
            try:
                real = path.resolve()
            except OSError:
                continue
            if real in seen_real:
                continue
            historical = _is_historical(path, rel_posix, cfg) if rel_posix not in always else None
            if historical:
                excluded[historical] = excluded.get(historical, 0) + 1
                continue
            seen_real.add(real)
            files.append(rel_posix)
    for rel_posix in always:
        if rel_posix not in files and (root / rel_posix).exists():
            files.append(rel_posix)
    return sorted(set(files)), excluded


def phrase_anchor(phrase: str) -> str:
    """Longest literal atom of a phrase, used as a cheap per-file prefilter."""
    atoms = [a for a in re.split(PHRASE_SEP, phrase.strip()) if a]
    return max(atoms, key=len).lower() if atoms else phrase.lower()


def scan_phrases(root: Path, files: list[str], patterns: dict[str, re.Pattern[str]]) -> tuple[dict[str, list[str]], int]:
    """One pass over the surface for every declared phrase.

    Cost control: a regex alternation over ~70 MB is seconds; a literal
    substring prefilter is milliseconds. Each phrase contributes one anchor
    (its longest atom); the regex only runs on files whose anchor is present.
    """
    hits: dict[str, list[str]] = {phrase: [] for phrase in patterns}
    if not patterns:
        return hits, 0
    anchors = [(phrase, phrase_anchor(phrase)) for phrase in patterns]
    total_bytes = 0
    for rel_posix in files:
        try:
            text = (root / rel_posix).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        total_bytes += len(text)
        lowered = text.lower()
        candidates = [phrase for phrase, anchor in anchors if anchor in lowered]
        for phrase in candidates:
            for match in patterns[phrase].finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                hits[phrase].append(f"{rel_posix}:{line}")
    return hits, total_bytes


def normalize_phrase_entries(claim: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    claim_scope = claim.get("scan_scope")
    claim_reason = claim.get("scan_scope_reason")
    for raw in claim.get("forbidden_phrases", []) or []:
        if isinstance(raw, dict):
            entry = {
                "phrase": str(raw.get("phrase") or ""),
                "scope": [str(g) for g in (raw.get("scope") or claim_scope or [])],
                "scope_reason": str(raw.get("scope_reason") or claim_reason or ""),
                "scoped": bool(raw.get("scope") or claim_scope),
            }
        else:
            entry = {
                "phrase": str(raw),
                "scope": [str(g) for g in (claim_scope or [])],
                "scope_reason": str(claim_reason or ""),
                "scoped": bool(claim_scope),
            }
        if entry["phrase"]:
            entries.append(entry)
    return entries


def scope_files(files: list[str], scope: list[str]) -> list[str]:
    if not scope:
        return files
    return [f for f in files if any(fnmatch(f, g) for g in scope)]


# --- executable claims (the ledger stops comparing text and runs a command) --
# A forbidden/required phrase can only compare prose against prose. A claim like
# "42 of 256 hooks/*.sh are symlinks" is true only while the repo agrees, and no
# phrase list can know that. The two check families below close that gap:
#
#   path_claims           every repo path the doc quotes must resolve today
#   executable_assertions a declared command runs, and its OUTPUT must be the
#                         prose the doc publishes ("the sentence is true iff
#                         this command prints it")
#
# Anti-void discipline, same defect that shipped on 2026-08-19: a check with no
# surface must BLOCK, never pass quietly. Zero docs, zero tokens, empty stdout
# and an unknown expectation are all declaration errors, not green rows.

DEFAULT_ASSERTION_POLICY: dict[str, Any] = {
    "allowed_executables": ["bash", "sh", "python3", ".venv/bin/python3", "git", "grep"],
    "timeout_seconds": 60,
}
PATH_SUFFIXES = (".py", ".sh", ".md", ".json", ".yaml", ".yml", ".txt", ".bats")
CODE_FENCE_RE = re.compile(r"```[a-zA-Z0-9]*\n(.*?)```", re.S)
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
GLOB_CHARS = ("*", "?", "[")


def assertion_policy(manifest: dict[str, Any]) -> dict[str, Any]:
    policy = dict(DEFAULT_ASSERTION_POLICY)
    declared = manifest.get("executable_assertion_policy") or {}
    for key in ("allowed_executables", "timeout_seconds"):
        if key in declared:
            policy[key] = declared[key]
    return policy


def path_tokens(text: str) -> list[str]:
    """Repo paths a doc quotes, from inline code and from fenced blocks.

    A token is a path candidate when it has no whitespace, carries no shell or
    placeholder syntax, and either contains a slash or ends in a known suffix.
    Placeholders (`<pid>`, `$h`) are not paths and are dropped here rather than
    forcing every doc to declare them as ignores.
    """
    chunks = [(m, True) for m in INLINE_CODE_RE.findall(text)]
    for block in CODE_FENCE_RE.findall(text):
        # Fenced blocks carry commands AND output templates ("status:
        # completed|failed|partial"). Only suffixed tokens are paths there;
        # a bare slash inside a template is prose, not a file.
        chunks.extend((tok, False) for tok in block.split())
    out: list[str] = []
    for raw, inline in chunks:
        token = raw.strip().lstrip("([").rstrip(").,;:]")  # leading dot is part of .claude/
        if not token or any(c in token for c in " \t<>$|\"'"):
            continue
        if token.startswith("#") or token.startswith("-"):
            continue
        if not token.endswith(PATH_SUFFIXES) and not (inline and "/" in token):
            continue
        if token.startswith(("http://", "https://")):
            continue
        out.append(token)
    return sorted(set(out))


def path_resolves(root: Path, token: str) -> bool:
    if any(c in token for c in GLOB_CHARS):
        return bool(list(root.glob(token)))
    target = root / token
    if token.endswith("/"):
        return target.is_dir()
    return target.exists()


def path_claim_rows(root: Path, claim_id: str, claim: dict[str, Any], severity: str) -> list[TruthRow]:
    spec = claim.get("path_claims") or {}
    if not spec:
        return []
    rows: list[TruthRow] = []
    docs = [str(d) for d in (spec.get("docs") or [])]
    ignores: dict[str, str] = {}
    for entry in spec.get("ignore") or []:
        token = str((entry or {}).get("token") or "")
        reason = str((entry or {}).get("reason") or "")
        if not token:
            continue
        if not reason:
            rows.append(TruthRow(claim_id, "path_claim_ignore", "block", severity, None, f"Ignored path token without a written reason: {token}", [token], "write why this token is not a repo path, or drop the ignore"))
        ignores[token] = reason
    if not docs:
        rows.append(TruthRow(claim_id, "path_claim_surface", "block", severity, None, "path_claims declared with no docs to check", ["docs:0"], "declare the docs whose quoted paths must resolve"))
        return rows
    for doc in docs:
        path = root / doc
        if not path.exists():
            rows.append(TruthRow(claim_id, "path_claim_surface", "block", severity, doc, "path_claims doc is missing", [doc], "fix the declared doc path"))
            continue
        tokens = [t for t in path_tokens(path.read_text(encoding="utf-8", errors="replace")) if t not in ignores]
        if not tokens:
            rows.append(TruthRow(claim_id, "path_claim_surface", "block", severity, doc, "path_claims doc quotes no repo path at all (0 tokens): the check would pass without checking anything", [doc, "tokens:0"], "point the claim at a doc that quotes paths, or drop it"))
            continue
        rows.append(TruthRow(claim_id, "path_claim_surface", "pass", severity, doc, f"path_claims doc quotes {len(tokens)} repo path(s)", [doc, f"tokens:{len(tokens)}"], "keep the doc declared"))
        missing = [t for t in tokens if not path_resolves(root, t)]
        if missing:
            rows.append(TruthRow(claim_id, "path_claim", "block", severity, doc, f"{len(missing)} quoted path(s) do not resolve, checked {len(tokens)}: {', '.join(missing[:8])}", missing[:20] + [f"tokens:{len(tokens)}"], "fix the path in the doc (readlink -f), or declare it as an ignore with a reason"))
        else:
            rows.append(TruthRow(claim_id, "path_claim", "pass", severity, doc, f"all {len(tokens)} quoted path(s) resolve", [doc, f"tokens:{len(tokens)}"], "keep quoted paths real"))
    return rows


def run_assertion(root: Path, command: list[str], timeout: int) -> tuple[int, str, str]:
    import subprocess

    proc = subprocess.run(command, cwd=str(root), capture_output=True, text=True, timeout=timeout)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()[:400]


def executable_assertion_rows(root: Path, claim_id: str, claim: dict[str, Any], severity: str, policy: dict[str, Any]) -> list[TruthRow]:
    assertions = claim.get("executable_assertions") or []
    if not assertions:
        return []
    rows: list[TruthRow] = []
    allowed = {str(x) for x in policy.get("allowed_executables") or []}
    default_timeout = int(policy.get("timeout_seconds") or 60)
    for raw in assertions:
        entry = raw if isinstance(raw, dict) else {}
        aid = str(entry.get("id") or "")
        label = f"{claim_id}/{aid or 'unnamed'}"
        command = entry.get("command")
        expect = entry.get("expect") or {}
        if not aid or not str(entry.get("claim") or "").strip():
            rows.append(TruthRow(claim_id, "executable_assertion_declaration", "block", severity, None, f"Assertion without id or without the prose claim it defends: {label}", [json.dumps(entry, sort_keys=True)[:200]], "give the assertion an id and write the sentence it keeps true"))
            continue
        if not isinstance(command, list) or not command or not all(isinstance(c, str) for c in command):
            rows.append(TruthRow(claim_id, "executable_assertion_declaration", "block", severity, None, f"Assertion command must be a non-empty argv list: {label}", [str(command)[:200]], "declare command as a list of strings (no shell string)"))
            continue
        if command[0] not in allowed:
            rows.append(TruthRow(claim_id, "executable_assertion_declaration", "block", severity, None, f"Assertion executable not allow-listed: {label} -> {command[0]}", [command[0]], "use an allow-listed executable or extend executable_assertion_policy with a reason"))
            continue
        known = {"exit_code", "stdout_phrase_in", "stdout_not_phrase_in"}
        unknown = sorted(set(expect) - known)
        if not expect or unknown:
            rows.append(TruthRow(claim_id, "executable_assertion_declaration", "block", severity, None, f"Assertion has no usable expectation: {label} (unknown: {', '.join(unknown) or 'none declared'})", [json.dumps(expect, sort_keys=True)[:200]], f"declare one of: {', '.join(sorted(known))}"))
            continue
        doc_keys = [k for k in ("stdout_phrase_in", "stdout_not_phrase_in") if k in expect]
        if "exit_code" in expect and not doc_keys:
            # An exit-code probe carries its own subject, so the ledger cannot
            # see what it is about. Naming the live files it reads is the only
            # thing that stops "exit 0 because it found nothing to check".
            surface = [str(d) for d in (entry.get("surface") or [])]
            live = [d for d in surface if (root / d).exists()]
            if not live:
                rows.append(TruthRow(claim_id, "executable_assertion_surface", "block", severity, None, f"exit_code assertion without a live surface: {label} declares {len(surface)} file(s), {0} exist", [f"surface:{','.join(surface) or 'none'}"], "declare surface: the existing files this probe reads"))
                continue
            rows.append(TruthRow(claim_id, "executable_assertion_surface", "pass", severity, live[0], f"exit_code assertion reads {len(live)} live file(s): {label}", [f"surface:{','.join(live)}"], "keep the surface declared"))
        docs = [str(d) for k in doc_keys for d in (expect.get(k) or [])]
        existing_docs = [d for d in docs if (root / d).exists()]
        if doc_keys and not existing_docs:
            rows.append(TruthRow(claim_id, "executable_assertion_surface", "block", severity, None, f"Assertion compares command output against {len(docs)} doc(s), none of which exist: {label}", [f"docs:{len(docs)}", "existing:0"], "declare the live doc that carries the sentence"))
            continue
        if doc_keys:
            rows.append(TruthRow(claim_id, "executable_assertion_surface", "pass", severity, existing_docs[0], f"Assertion has {len(existing_docs)} live doc surface(s): {label}", [f"existing:{len(existing_docs)}"], "keep the surface declared"))
        try:
            code, out, err = run_assertion(root, command, int(entry.get("timeout_seconds") or default_timeout))
        except Exception as exc:  # noqa: BLE001 - a probe that cannot run is a blocker, not a pass
            rows.append(TruthRow(claim_id, "executable_assertion", "block", severity, None, f"Assertion command failed to run: {label}: {type(exc).__name__}: {exc}", [" ".join(command)[:200]], "fix the command or the environment it needs"))
            continue
        evidence = [" ".join(command)[:200], f"exit:{code}", f"stdout:{out[:160]}"]
        if err:
            evidence.append(f"stderr:{err[:160]}")
        if "exit_code" in expect:
            want = int(expect["exit_code"])
            status = "pass" if code == want else "block"
            rows.append(TruthRow(claim_id, "executable_assertion", status, severity, None, f"Assertion {label}: exit {code}, expected {want} -- {entry['claim']}", evidence, str(entry.get("next_action") or "make the claim true again, or rewrite the sentence the assertion defends")))
        for key in doc_keys:
            atoms = [a for a in re.split(PHRASE_SEP, out) if a]
            if not out or not atoms:
                rows.append(TruthRow(claim_id, "executable_assertion", "block", severity, None, f"Assertion {label} compares an EMPTY command output against prose: it would match everything", evidence, "make the command print the sentence it defends"))
                continue
            pattern = phrase_pattern(out)
            hit = next((d for d in existing_docs if pattern.search((root / d).read_text(encoding="utf-8", errors="replace"))), None)
            wants_hit = key == "stdout_phrase_in"
            status = "pass" if bool(hit) == wants_hit else "block"
            verb = "must appear in" if wants_hit else "must be absent from"
            rows.append(TruthRow(claim_id, "executable_assertion", status, severity, hit, f"Assertion {label}: command output {verb} the doc -- measured now: {out[:120]!r} -- {entry['claim']}", evidence + [f"docs:{','.join(existing_docs)}"], str(entry.get("next_action") or "update the sentence in the doc to the measured output, or drop the number")))
    return rows


def audit(root: Path, manifest_path: Path) -> tuple[list[TruthRow], dict[str, Any]]:
    manifest = read_yaml(manifest_path)
    claims = dict(sorted((manifest.get("claims") or {}).items()))
    cfg = scan_config(manifest)
    policy = assertion_policy(manifest)
    try:
        manifest_rel = manifest_path.resolve().relative_to(root).as_posix()
    except ValueError:
        manifest_rel = None
    # The claims manifest and this auditor quote every phrase by construction.
    cfg["exclude_globs"] = list(cfg["exclude_globs"]) + [
        {"glob": manifest_rel or DEFAULT_MANIFEST.as_posix(), "reason": "the claims manifest declares the phrases"},
        {"glob": "scripts/documentation_truth_audit.py", "reason": "the auditor itself quotes phrase syntax"},
    ]
    # required_docs are operator-declared live surfaces: they are always scanned,
    # even when a generic exclusion would otherwise drop them.
    always = sorted({str(d) for claim in claims.values() for d in (claim.get("required_docs") or [])})
    surface, excluded = collect_scan_surface(root, cfg, always)

    entries_by_claim = {cid: normalize_phrase_entries(claim) for cid, claim in claims.items()}
    patterns = {
        entry["phrase"]: phrase_pattern(entry["phrase"])
        for entries in entries_by_claim.values()
        for entry in entries
    }
    hits, scanned_bytes = scan_phrases(root, surface, patterns)
    scan_meta = {
        "surface_files": len(surface),
        "surface_bytes": scanned_bytes,
        "include_suffixes": list(cfg.get("include_suffixes") or []),
        "pruned_dirs": sorted(str(d) for d in cfg.get("prune_dirs") or []),
        "excluded_by_reason": dict(sorted(excluded.items())),
        "phrases": len(patterns),
        "always_scanned_required_docs": len(always),
    }

    rows: list[TruthRow] = []
    for claim_id, claim in claims.items():
        severity = str(claim.get("severity") or "medium")
        source_reports = [str(p) for p in claim.get("source_reports", [])]
        required_docs = [str(p) for p in claim.get("required_docs", [])]
        existing_doc_text: dict[str, str] = {}
        for report in source_reports:
            path = root / report
            if report == DEFAULT_JSON.as_posix():
                rows.append(TruthRow(claim_id, "source_report_self", "pass", severity, report, "Self-generated documentation truth report is produced by this audit", [report], "keep audit in refresh lane"))
                continue
            if not path.exists():
                rows.append(TruthRow(claim_id, "source_report_exists", "block", severity, report, "Required source report is missing", [report], "generate the source report or demote the claim"))
                continue
            data = read_json(path) if path.suffix == ".json" else {}
            status = data.get("status") if isinstance(data, dict) else None
            if status == "block":
                rows.append(TruthRow(claim_id, "source_report_status", "block", severity, report, "Source report is currently blocking", [f"status:{status}"], "fix source report blockers before claiming docs are current"))
            else:
                rows.append(TruthRow(claim_id, "source_report_exists", "pass", severity, report, "Required source report exists", [report], "keep report generated"))
        for doc in required_docs:
            path = root / doc
            if not path.exists():
                rows.append(TruthRow(claim_id, "required_doc_exists", "block", severity, doc, "Required documentation surface is missing", [doc], "create or relink the canonical doc"))
                continue
            existing_doc_text[doc] = path.read_text(encoding="utf-8", errors="replace")
            rows.append(TruthRow(claim_id, "required_doc_exists", "pass", severity, doc, "Required documentation surface exists", [doc], "keep doc linked"))

        # --- forbidden phrases: repo-wide declared surface, never zero files ---
        for entry in entries_by_claim[claim_id]:
            phrase = entry["phrase"]
            scope = entry["scope"]
            scoped_files = scope_files(surface, scope)
            checked = len(scoped_files)
            if entry["scoped"] and not entry["scope_reason"]:
                rows.append(TruthRow(claim_id, "forbidden_phrase_scope", "block", severity, None, f"Narrowed scan scope without a written reason: {phrase}", [f"scope:{','.join(scope)}"], "add scan_scope_reason/scope_reason, or drop the narrowing"))
            if checked == 0:
                rows.append(TruthRow(claim_id, "forbidden_phrase_surface", "block", severity, None, f"Forbidden phrase declared with no surface to check it against (0 files): {phrase}", [f"scope:{','.join(scope) or 'repo-surface'}", "checked_files:0"], "widen or fix scan_scope so the phrase is checked against at least one existing file"))
                continue
            rows.append(TruthRow(claim_id, "forbidden_phrase_surface", "pass", severity, None, f"Forbidden phrase has a non-empty scan surface: {phrase}", [f"scope:{','.join(scope) or 'repo-surface'}", f"checked_files:{checked}"], "keep the surface declared"))
            scoped_hits = [h for h in hits.get(phrase, []) if h.rsplit(":", 1)[0] in set(scoped_files)]
            if scoped_hits:
                rows.append(TruthRow(claim_id, "forbidden_phrase", "block", severity, scoped_hits[0].rsplit(":", 1)[0], f"Forbidden stale phrase present in {len(scoped_hits)} place(s), checked against {checked} files: {phrase}", scoped_hits[:20] + [f"checked_files:{checked}"], "remove stale or contradictory prose at the listed file:line"))
            else:
                rows.append(TruthRow(claim_id, "forbidden_phrase", "pass", severity, None, f"Forbidden stale phrase absent, checked against {checked} files: {phrase}", [phrase, f"checked_files:{checked}"], "keep the phrase out of the scanned surface"))

        joined_docs = "\n".join(existing_doc_text.values())
        required_phrases = [str(p) for p in claim.get("required_phrases", []) or []]
        if required_phrases and not existing_doc_text:
            rows.append(TruthRow(claim_id, "required_phrase_surface", "block", severity, None, f"{len(required_phrases)} required phrase(s) declared with no existing required_docs to check them against", [f"required_docs:{len(required_docs)}"], "declare the required_docs that must carry the current-truth prose"))
        else:
            for phrase in required_phrases:
                status = "pass" if phrase in joined_docs else "block"
                rows.append(TruthRow(claim_id, "required_phrase", status, severity, None, f"Required phrase {'present' if status == 'pass' else 'missing'} in {len(existing_doc_text)} required doc(s): {phrase}", [phrase], "add or regenerate current-truth prose"))
        block = claim.get("generated_block") or {}
        if block.get("required"):
            doc = str(block.get("doc") or "")
            marker = str(block.get("marker") or claim_id)
            path = root / doc
            expected = render_block(root, claim_id, marker)
            if not path.exists():
                rows.append(TruthRow(claim_id, "generated_block", "block", severity, doc, "Generated block doc is missing", [doc], "create doc and generated block"))
            else:
                found = find_block(path.read_text(encoding="utf-8", errors="replace"), marker)
                if not found:
                    rows.append(TruthRow(claim_id, "generated_block", "block", severity, doc, "Generated truth block is missing", [marker], "run documentation_truth_audit.py --update-generated"))
                elif found[2] != expected:
                    rows.append(TruthRow(claim_id, "generated_block", "block", severity, doc, "Generated truth block is stale", [marker], "run documentation_truth_audit.py --update-generated"))
                else:
                    rows.append(TruthRow(claim_id, "generated_block", "pass", severity, doc, "Generated truth block matches current facts", [marker], "keep block generated"))
        rows.extend(path_claim_rows(root, claim_id, claim, severity))
        rows.extend(executable_assertion_rows(root, claim_id, claim, severity, policy))
    scan_meta["executable_assertions"] = sum(1 for r in rows if r.check == "executable_assertion")
    scan_meta["path_claim_tokens"] = sum(int(e.split(":", 1)[1]) for r in rows if r.check == "path_claim_surface" and r.status == "pass" for e in r.evidence if e.startswith("tokens:"))
    return rows, scan_meta


def summarize(rows: list[TruthRow]) -> dict[str, Any]:
    by_status: dict[str, int] = {}
    by_claim: dict[str, dict[str, int]] = {}
    for row in rows:
        by_status[row.status] = by_status.get(row.status, 0) + 1
        by_claim.setdefault(row.claim_id, {})
        by_claim[row.claim_id][row.status] = by_claim[row.claim_id].get(row.status, 0) + 1
    return {"rows": len(rows), "by_status": dict(sorted(by_status.items())), "by_claim": by_claim, "block_count": by_status.get("block", 0)}


def render_markdown(report: dict[str, Any]) -> str:
    PIPE = '\\|'
    lines = ["# Documentation Truth Audit — Latest", "", f"Generated: {report['generated_at']}", f"Status: `{report['status']}`", "", "## Summary", ""]
    scan = report["summary"].get("forbidden_phrase_scan", {})
    for key, value in report["summary"].items():
        if key == "forbidden_phrase_scan":
            continue
        lines.append(f"- {key}: `{value}`")
    if scan:
        lines += [
            "",
            "## Forbidden-phrase scan surface",
            "",
            f"- Files checked: `{scan.get('surface_files', 0)}` ({scan.get('surface_bytes', 0)} bytes)",
            f"- Declared phrases: `{scan.get('phrases', 0)}`",
            f"- Suffixes: `{', '.join(scan.get('include_suffixes') or [])}`",
            f"- Pruned dirs: `{', '.join(scan.get('pruned_dirs') or [])}`",
            f"- required_docs always scanned: `{scan.get('always_scanned_required_docs', 0)}`",
            "",
            "| Files excluded | Reason |",
            "|---|---|",
        ]
        for reason, count in (scan.get("excluded_by_reason") or {}).items():
            lines.append(f"| `{count}` | {reason.replace('|', PIPE)} |")
    lines += ["", "## Blocking rows", "", "| Claim | Check | Doc | Message | Next action |", "|---|---|---|---|---|"]
    blockers = [row for row in report["rows"] if row["status"] == "block"]
    if not blockers:
        lines.append("| none | - | - | - | - |")
    for row in blockers[:120]:
        lines.append(f"| `{row['claim_id']}` | `{row['check']}` | `{row.get('doc') or ''}` | {row['message'].replace('|', PIPE)} | {row['next_action'].replace('|', PIPE)} |")
    return "\n".join(lines) + "\n"


def _manifest_label(root: Path, manifest_path: Path) -> str:
    """rel() raises when --manifest points outside --project-dir (e.g. a temp
    manifest used to reproduce a claim). The label is cosmetic; do not crash."""
    try:
        return rel(root, manifest_path)
    except ValueError:
        return str(manifest_path)


def build_report(root: Path, manifest_path: Path) -> dict[str, Any]:
    rows, scan_meta = audit(root, manifest_path)
    summary = summarize(rows)
    summary["forbidden_phrase_scan"] = scan_meta
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "block" if summary["block_count"] else "pass",
        "manifest": _manifest_label(root, manifest_path),
        "summary": summary,
        "rows": [asdict(row) for row in rows],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", default=str(ROOT))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--update-generated", action="store_true")
    parser.add_argument("--fail-on-block", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.project_dir).resolve()
    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = root / manifest_path
    manifest = read_yaml(manifest_path)
    if args.update_generated:
        for claim_id, claim in sorted((manifest.get("claims") or {}).items()):
            block = claim.get("generated_block") or {}
            if block.get("required"):
                update_block(root, str(block.get("doc") or ""), claim_id, str(block.get("marker") or claim_id))
    report = build_report(root, manifest_path)
    if not args.no_write:
        json_path = root / DEFAULT_JSON
        md_path = root / DEFAULT_MD
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        md_path.write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(json.dumps({"status": report["status"], "summary": report["summary"]}, sort_keys=True))
    if args.fail_on_block and report["status"] == "block":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
