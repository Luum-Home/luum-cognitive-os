#!/usr/bin/env python3
# SCOPE: project
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.script_io import read_text as read_text

DONE_WORDS = re.compile(r"\b(done|implemented|completed|shipped|added|wired|accepted|resolved|closed)\b", re.I)
PLAN_WORDS = re.compile(r"\b(todo|next steps?|remaining|planned|future|pending|backlog|not yet|to implement)\b", re.I)
PROPOSED_WORDS = re.compile(r"\b(proposed|proposal|design|option|candidate|recommendation|should|could)\b", re.I)
CHECKBOX_RE = re.compile(r"^\s*[-*]\s+\[(?P<mark>[ xX])\]\s+(?P<text>.+)$")
BULLET_RE = re.compile(r"^\s*[-*]\s+(?P<text>.+)$")
PATHISH_RE = re.compile(r"^(?:docs|scripts|hooks|skills|rules|tests|primitive_coverage|\.github|\.cognitive-os|manifests|lib|packages)/")
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\((?P<target>[^)#]+)(?:#[^)]+)?\)")
INLINE_CODE_RE = re.compile(r"`(?P<code>[^`]+)`")
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{3,}")
GENERATED_STATE_PREFIXES = (
    ".cognitive-os/metrics/",
    ".cognitive-os/agents/",
    ".cognitive-os/skills/",
    ".cognitive-os/coordination/",
)
GENERATED_STATE_FILES = {".cognitive-os/work-queue.json"}
DOC_SOURCE_EXCLUDED_PREFIXES = ("docs/reports/", "docs/archive/")

STOPWORDS = {"this", "that", "with", "from", "into", "docs", "documentation", "cognitive", "agent", "agents", "should", "could", "would", "will", "have", "has", "the", "and", "for", "status", "report", "latest"}

@dataclass(frozen=True)
class DocsExecutionRow:
    path: str
    line: int
    kind: str
    item: str
    declared_status: str
    inferred_status: str
    confidence: float
    evidence: list[str]
    next_action: str

def candidate_docs(root: Path) -> list[Path]:
    paths: list[Path] = []
    for pattern in ("README.md", "AGENTS.md", "docs/**/*.md"):
        paths.extend(p for p in root.glob(pattern) if p.is_file())
    return sorted(p for p in paths if not p.relative_to(root).as_posix().startswith(DOC_SOURCE_EXCLUDED_PREFIXES))

def evidence_files(root: Path) -> list[Path]:
    patterns = ("scripts/**/*.py", "hooks/**/*.sh", "skills/**/SKILL.md", "rules/**/*.md", "tests/**/*.py", ".github/workflows/*.yml", ".github/workflows/*.yaml", "primitive_coverage/**/*.py", "primitive_coverage/**/*.yaml", "manifests/**/*.json", "lib/**/*.py", ".cognitive-os/plans/**/*.md")
    out: list[Path] = []
    for pattern in patterns:
        out.extend(p for p in root.glob(pattern) if p.is_file())
    return sorted(out)

def build_evidence(root: Path) -> tuple[str, set[str]]:
    chunks: list[str] = []
    paths: set[str] = set()
    for p in evidence_files(root):
        rel = p.relative_to(root).as_posix()
        paths.add(rel)
        chunks.append(rel)
        chunks.append(read_text(p)[:50000])
    return "\n".join(chunks).lower(), paths

def tokens(text: str) -> set[str]:
    return {t.lower() for t in TOKEN_RE.findall(text) if t.lower() not in STOPWORDS}

def is_actionable_ref(ref: str) -> bool:
    if not ref or ref.startswith(("http://", "https://", "mailto:", "#")):
        return False
    if "{" in ref or "}" in ref or "<" in ref or ">" in ref or ref in {"hooks/X.sh"}:
        return False
    if ref.startswith(("./", "../")):
        return True
    if not PATHISH_RE.match(ref):
        return False
    return bool(Path(ref).suffix or ref.endswith("/"))

def extract_refs(text: str) -> list[str]:
    refs: list[str] = []
    for match in MARKDOWN_LINK_RE.finditer(text):
        ref = match.group("target").strip().rstrip(".,;:)")
        if is_actionable_ref(ref):
            refs.append(ref)
    for match in INLINE_CODE_RE.finditer(text):
        ref = match.group("code").strip().rstrip(".,;:)")
        if is_actionable_ref(ref):
            refs.append(ref)
    return refs

def normalize_ref(root: Path, source_rel: str, ref: str) -> str:
    ref = ref.split()[0].split("::")[0]
    if ref.startswith(("./", "../")):
        base = root / source_rel
        resolved = (base.parent / ref).resolve()
        try:
            return resolved.relative_to(root).as_posix()
        except ValueError:
            return ref
    return ref

def ref_exists(root: Path, ref: str, known: set[str]) -> bool:
    if ref in GENERATED_STATE_FILES or ref.startswith(GENERATED_STATE_PREFIXES):
        return True
    if ref in known or (root / ref).exists():
        return True
    if any(ch in ref for ch in "*?["):
        return any(root.glob(ref))
    return False

def tolerate_missing_ref(item: str) -> bool:
    lowered = item.lower()
    return bool(re.search(r"\b(missing|remove|fix|was not|moved to|stale count)\b|no `", lowered))

def declared(kind: str, item: str, mark: str | None = None) -> str:
    if kind == "checkbox":
        return "done" if mark and mark.lower() == "x" else "planned"
    if DONE_WORDS.search(item):
        return "done"
    if PLAN_WORDS.search(item):
        return "planned"
    if PROPOSED_WORDS.search(item):
        return "proposed"
    return "unknown"

def extract_items(root: Path) -> list[tuple[str, int, str, str, str]]:
    rows: list[tuple[str, int, str, str, str]] = []
    for p in candidate_docs(root):
        rel = p.relative_to(root).as_posix()
        fence = False
        for n, raw in enumerate(read_text(p).splitlines(), 1):
            s = raw.strip()
            if s.startswith("```"):
                fence = not fence
                continue
            if fence or not s or s.startswith("|"):
                continue
            checkbox = CHECKBOX_RE.match(raw)
            if checkbox:
                item = checkbox.group("text").strip()
                rows.append((rel, n, "checkbox", item, declared("checkbox", item, checkbox.group("mark"))))
                continue
            bullet = BULLET_RE.match(raw)
            if bullet:
                item = bullet.group("text").strip()
                if DONE_WORDS.search(item) or PLAN_WORDS.search(item) or PROPOSED_WORDS.search(item):
                    rows.append((rel, n, "bullet", item, declared("bullet", item)))
                continue
            if len(s) <= 220 and not s.startswith("#") and (DONE_WORDS.search(s) or PLAN_WORDS.search(s)):
                rows.append((rel, n, "prose", s, declared("prose", s)))
    return rows

def classify(root: Path, source_rel: str, item: str, decl: str, corpus: str, known: set[str]) -> tuple[str, float, list[str], str]:
    evidence: list[str] = []
    missing: list[str] = []
    for raw_ref in extract_refs(item):
        ref = normalize_ref(root, source_rel, raw_ref)
        if ref_exists(root, ref, known):
            evidence.append(f"path:{ref}")
        elif not tolerate_missing_ref(item):
            missing.append(ref)
    item_terms = tokens(item)
    hits = sorted(t for t in item_terms if t in corpus)[:8]
    if len(hits) >= 3:
        evidence.append("terms:" + ",".join(hits))
    elif hits:
        evidence.append("weak_terms:" + ",".join(hits))
    if missing and decl == "done":
        return "stale", 0.82, evidence + [f"missing_path:{p}" for p in missing], "update stale path or demote completion claim"
    if decl == "planned":
        return "planned", 0.90, evidence, "keep planned or add implementation proof when complete"
    if decl == "proposed":
        return "proposed", 0.86, evidence, "keep as proposal until accepted/implemented"
    if decl == "done":
        strong = [x for x in evidence if x.startswith(("path:", "terms:"))]
        if len(strong) >= 2:
            return "done_with_proof", 0.86, evidence, "keep marked done; maintain proof links"
        if evidence:
            return "done_weak_proof", 0.62, evidence, "add explicit test/workflow/proof link"
        return "claimed_done_no_proof", 0.74, evidence, "add proof or demote checkbox/status"
    return "unknown", 0.45 if evidence else 0.35, evidence, "triage manually"

def audit(root: Path) -> list[DocsExecutionRow]:
    corpus, known = build_evidence(root)
    rows: list[DocsExecutionRow] = []
    for rel, line, kind, item, decl in extract_items(root):
        inferred, confidence, evidence, action = classify(root, rel, item, decl, corpus, known)
        rows.append(DocsExecutionRow(rel, line, kind, item[:260], decl, inferred, confidence, evidence[:10], action))
    return rows

def summarize(rows: list[DocsExecutionRow]) -> dict[str, object]:
    statuses: dict[str, int] = {}
    docs: dict[str, dict[str, int]] = {}
    for row in rows:
        statuses[row.inferred_status] = statuses.get(row.inferred_status, 0) + 1
        docs.setdefault(row.path, {})
        docs[row.path][row.inferred_status] = docs[row.path].get(row.inferred_status, 0) + 1
    return {"items": len(rows), "statuses": dict(sorted(statuses.items())), "documents": docs}

def write_markdown(rows: list[DocsExecutionRow], path: Path) -> None:
    summary = summarize(rows)
    lines = ["# Documentation Execution Audit — Latest", "", "## Summary", "", f"Total items: {summary['items']}"]
    for status, count in summary["statuses"].items():
        lines.append(f"- {status}: {count}")
    lines += ["", "## Items Needing Attention", "", "| File | Line | Declared | Inferred | Confidence | Item | Evidence | Next action |", "|---|---:|---|---|---:|---|---|---|"]
    for row in rows:
        if row.inferred_status not in {"claimed_done_no_proof", "done_weak_proof", "stale", "contradicted", "unknown"}:
            continue
        item = row.item.replace("|", "\\|")
        evidence = ", ".join(row.evidence).replace("|", "\\|")
        lines.append(f"| {row.path} | {row.line} | {row.declared_status} | {row.inferred_status} | {row.confidence:.2f} | {item} | {evidence} | {row.next_action} |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

def main() -> int:
    parser = argparse.ArgumentParser(description="Audit documentation execution state against repo evidence")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--json-out", default="docs/reports/docs-execution-latest.json")
    parser.add_argument("--md-out", default="docs/reports/docs-execution-latest.md")
    parser.add_argument("--fail-claimed-done-no-proof", action="store_true")
    parser.add_argument("--fail-hard-gaps", action="store_true", help="Exit non-zero for stale, contradicted, or claimed-done-without-proof rows.")
    args = parser.parse_args()
    root = Path(args.project_dir).resolve()
    rows = audit(root)
    payload = {"summary": summarize(rows), "rows": [asdict(row) for row in rows]}
    json_path = root / args.json_out
    md_path = root / args.md_out
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(rows, md_path)
    print(json.dumps({"items": len(rows), "json": str(json_path), "markdown": str(md_path)}, sort_keys=True))
    hard_gap_statuses = {"stale", "claimed_done_no_proof", "contradicted"}
    if args.fail_claimed_done_no_proof and any(row.inferred_status == "claimed_done_no_proof" for row in rows):
        return 2
    if args.fail_hard_gaps and any(row.inferred_status in hard_gap_statuses for row in rows):
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
