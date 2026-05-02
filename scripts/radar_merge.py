#!/usr/bin/env python3
# SCOPE: project
"""radar_merge.py — Tech Radar merge engine for /radar-update.

Reads one or more /repo-scout markdown artifacts, merges their auto-owned fields
into the canonical radar docs (ecosystem-tools.md, blocked-tools.md), and emits
a unified diff (dry-run) or writes in place (--apply).

Usage:
    python3 scripts/radar_merge.py \\
        --artifacts .cognitive-os/reports/repo-scout/owner_repo.md [owner2_repo2.md ...] \\
        --ecosystem-tools docs/patterns/ecosystem-tools.md \\
        --blocked-tools docs/blocked-tools.md \\
        [--apply] \\
        [--changelog CHANGELOG.md] \\
        [--output-diff path/to/output.diff]

Design contract:
  - Auto-owned fields: repo, stars, last_commit, last_release, license, ci_health,
    score, classification, one_liner, last_evaluated
  - Human-owned fields: usage_examples, adoption_notes, gotchas, limitations,
    linked_adrs, replaces, superseded_by
  - The merge engine rewrites only the frontmatter block (---...---) of each entry.
  - Everything after the frontmatter until the next ### heading is preserved verbatim.

ADR: docs/adrs/ADR-065-radar-update-curation-pipeline.md
"""

from __future__ import annotations

import argparse
import difflib
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

AUTO_OWNED_FIELDS = {
    "repo",
    "stars",
    "last_commit",
    "last_release",
    "license",
    "ci_health",
    "score",
    "classification",
    "one_liner",
    "last_evaluated",
}

HUMAN_OWNED_FIELDS = {
    "usage_examples",
    "adoption_notes",
    "gotchas",
    "limitations",
    "linked_adrs",
    "replaces",
    "superseded_by",
}

CLASSIFICATION_TO_DOC = {
    "ADOPT": "ecosystem-tools",
    "TRIAL": "ecosystem-tools",
    "ASSESS": "ecosystem-tools",
    "HOLD": "ecosystem-tools",
    "REJECT": "blocked-tools",
}


@dataclass
class RepoEval:
    """Parsed evaluation result from a /repo-scout artifact."""

    repo: str  # owner/name
    owner: str
    name: str
    classification: str
    stars: int = 0
    license: str = ""
    ci_health: str = "none"
    score: int = 0
    one_liner: str = ""
    last_evaluated: str = ""
    last_commit: str = ""
    last_release: str = ""
    # Raw fields from artifact for full frontmatter reconstruction
    raw_fields: dict = field(default_factory=dict)


@dataclass
class MergeAction:
    """Records what the merge engine did for a single repo."""

    repo: str
    action: str  # "added", "updated", "refreshed", "moved", "skipped", "error"
    target_doc: str
    prev_classification: Optional[str] = None
    new_classification: Optional[str] = None
    prev_license: Optional[str] = None
    new_license: Optional[str] = None
    message: str = ""


# ---------------------------------------------------------------------------
# Artifact parser
# ---------------------------------------------------------------------------

def parse_artifact(path: Path) -> Optional[RepoEval]:
    """Parse a /repo-scout markdown artifact and extract auto-owned fields.

    The artifact is a freeform markdown file. We look for YAML-like key: value
    lines near the top, and also scan for common patterns /repo-scout uses.
    """
    text = path.read_text(encoding="utf-8")
    fields: dict[str, str] = {}

    # Strategy 1: look for a YAML frontmatter block at the top
    fm_match = re.match(r"^---\s*\n(.*?\n)---\s*\n", text, re.DOTALL)
    if fm_match:
        for line in fm_match.group(1).splitlines():
            if ":" in line and not line.startswith(" "):
                k, _, v = line.partition(":")
                fields[k.strip().lower()] = v.strip().strip('"').strip("'")

    # Strategy 2: scan for key: value table rows (| key | value |) or inline fields
    # /repo-scout artifacts typically have a table with Property/Value
    for m in re.finditer(r"\|\s*([A-Za-z_]+)\s*\|\s*([^|]+?)\s*\|", text):
        k = m.group(1).strip().lower().replace(" ", "_")
        v = m.group(2).strip()
        if k and v and k not in fields:
            fields[k] = v

    # Strategy 3: look for explicit assignment lines like "classification: ADOPT"
    for line in text.splitlines():
        m = re.match(r"^\*\*([A-Za-z_ ]+)\*\*:?\s+(.+)$", line)
        if m:
            k = m.group(1).strip().lower().replace(" ", "_")
            v = m.group(2).strip()
            if k not in fields:
                fields[k] = v
        # Also catch bare "Classification: ADOPT" lines
        m2 = re.match(r"^([A-Za-z_]+):\s+(.+)$", line)
        if m2:
            k = m2.group(1).strip().lower()
            v = m2.group(2).strip()
            if k not in fields:
                fields[k] = v

    # Extract repo from filename (owner_repo.md) as fallback
    stem = path.stem  # e.g. "ryoppippi_ccusage"
    if "_" in stem and "repo" not in fields:
        parts = stem.split("_", 1)
        fields["repo"] = f"{parts[0]}/{parts[1]}"

    # Normalise classification
    classification = fields.get("classification", "").upper().strip()
    if not classification:
        # Try to detect from STATUS field or text
        for line in text.splitlines():
            m = re.search(r"\b(ADOPT|TRIAL|ASSESS|HOLD|REJECT)\b", line, re.IGNORECASE)
            if m:
                classification = m.group(1).upper()
                break

    if not classification:
        classification = "ASSESS"  # safe default

    repo = fields.get("repo", "")
    if not repo:
        return None

    # Parse owner/name
    if "/" in repo:
        owner, name = repo.split("/", 1)
    else:
        owner, name = "", repo

    # Parse stars as int
    stars_raw = fields.get("stars", "0")
    try:
        stars = int(re.sub(r"[^0-9]", "", stars_raw) or "0")
    except ValueError:
        stars = 0

    # Parse score as int
    score_raw = fields.get("score", "0")
    try:
        score = int(re.sub(r"[^0-9]", "", score_raw) or "0")
    except ValueError:
        score = 0

    one_liner = fields.get("one_liner", fields.get("description", ""))[:120]
    last_evaluated = fields.get("last_evaluated", str(date.today()))

    return RepoEval(
        repo=repo,
        owner=owner,
        name=name,
        classification=classification,
        stars=stars,
        license=fields.get("license", ""),
        ci_health=fields.get("ci_health", "none"),
        score=score,
        one_liner=one_liner,
        last_evaluated=last_evaluated,
        last_commit=fields.get("last_commit", ""),
        last_release=fields.get("last_release", ""),
        raw_fields=fields,
    )


# ---------------------------------------------------------------------------
# Entry frontmatter builder
# ---------------------------------------------------------------------------

def build_frontmatter(ev: RepoEval) -> str:
    """Build a YAML frontmatter block from auto-owned fields."""
    lines = ["---"]
    lines.append(f"repo: {ev.repo}")
    lines.append(f"classification: {ev.classification}")
    lines.append(f"stars: {ev.stars}")
    if ev.license:
        lines.append(f"license: {ev.license}")
    lines.append(f"ci_health: {ev.ci_health}")
    lines.append(f"score: {ev.score}")
    if ev.one_liner:
        lines.append(f'one_liner: "{ev.one_liner}"')
    lines.append(f"last_evaluated: {ev.last_evaluated}")
    if ev.last_commit:
        lines.append(f"last_commit: {ev.last_commit}")
    if ev.last_release:
        lines.append(f"last_release: {ev.last_release}")
    lines.append("---")
    return "\n".join(lines)


def build_new_entry(ev: RepoEval, github_url: str = "") -> str:
    """Build a complete new entry block (heading + frontmatter + placeholder body)."""
    label = f"({ev.classification})" if ev.classification in {"ASSESS", "HOLD", "TRIAL"} else ev.classification
    title = f"### {ev.name} — {ev.one_liner or 'No description'} ({label})"
    fm = build_frontmatter(ev)
    gh_line = f"| GitHub | [{ev.repo}](https://github.com/{ev.repo}) |" if not github_url else f"| GitHub | [{ev.repo}]({github_url}) |"
    body = "\n".join([
        "",
        gh_line,
        "",
        "**Adoption notes**: _Add project-specific usage context here._",
        "",
    ])
    return f"{title}\n\n{fm}\n{body}"


# ---------------------------------------------------------------------------
# Document parser / section locator
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?\n)---\s*\n", re.DOTALL)
_REPO_FM_RE = re.compile(r"^repo:\s*(.+)$", re.MULTILINE)


def parse_doc_entries(text: str) -> list[dict]:
    """Parse a radar doc into a list of entry dicts.

    Each entry has:
      - start, end: character offsets in the original text
      - heading: the ### heading line
      - repo: value of the repo: field in frontmatter (or None)
      - name: bare repo name (for fuzzy matching)
      - frontmatter_start, frontmatter_end: offsets of the --- block within entry
      - body: text after frontmatter until next heading
    """
    entries = []
    # Find all ### headings and record their positions
    heading_matches = [(m.start(), m.end(), m.group()) for m in re.finditer(r"^###\s+.+$", text, re.MULTILINE)]

    for i, (hstart, hend, heading) in enumerate(heading_matches):
        end = heading_matches[i + 1][0] if i + 1 < len(heading_matches) else len(text)
        chunk = text[hstart:end]

        # Find frontmatter block within this chunk
        fm_match = re.search(r"\n---\s*\n(.*?\n)---\s*\n", chunk, re.DOTALL)
        fm_fields: dict[str, str] = {}
        if fm_match:
            for line in fm_match.group(1).splitlines():
                if ":" in line and not line.startswith(" "):
                    k, _, v = line.partition(":")
                    fm_fields[k.strip().lower()] = v.strip().strip('"').strip("'")

        repo = fm_fields.get("repo")

        # Fuzzy name: last path component of heading text (strip status markers)
        heading_text = re.sub(r"\s*\([A-Z]+\)\s*$", "", heading)
        heading_name = heading_text.lstrip("#").strip().split("—")[0].split("-")[0].strip().lower()

        entries.append({
            "start": hstart,
            "end": end,
            "heading": heading,
            "repo": repo,
            "name": heading_name,
            "fm_fields": fm_fields,
            "chunk": chunk,
        })

    return entries


def find_entry(entries: list[dict], ev: RepoEval) -> tuple[Optional[dict], str]:
    """Find an existing entry for a given RepoEval.

    Returns (entry_dict, match_type) where match_type is 'exact', 'fuzzy', or 'none'.
    """
    # Exact match by repo: frontmatter field
    for entry in entries:
        if entry.get("repo") == ev.repo:
            return entry, "exact"

    # Fuzzy match by heading name (case-insensitive, ignoring owner prefix)
    ev_name_lower = ev.name.lower()
    for entry in entries:
        name = entry.get("name", "")
        if name and (name == ev_name_lower or name.startswith(ev_name_lower) or ev_name_lower.startswith(name)):
            return entry, "fuzzy"

    return None, "none"


# ---------------------------------------------------------------------------
# Rewrite helpers
# ---------------------------------------------------------------------------

def rewrite_frontmatter_in_chunk(chunk: str, ev: RepoEval) -> str:
    """Rewrite the --- frontmatter block in a chunk, preserving the body."""
    fm_match = re.search(r"\n---\s*\n(.*?\n)---\s*\n", chunk, re.DOTALL)
    if not fm_match:
        # No existing frontmatter — insert after the heading line
        lines = chunk.split("\n", 1)
        if len(lines) == 2:
            return f"{lines[0]}\n\n{build_frontmatter(ev)}\n\n{lines[1]}"
        return chunk + f"\n{build_frontmatter(ev)}\n"

    new_fm = build_frontmatter(ev)
    # Replace the frontmatter block; preserve everything before and after it
    prefix = chunk[: fm_match.start()]
    suffix = chunk[fm_match.end():]
    return f"{prefix}\n{new_fm}\n\n{suffix}"


def insert_entry_alphabetically(text: str, new_entry: str, ev: RepoEval) -> str:
    """Insert a new entry in alphabetical order by heading name.

    Appends to the end of the file if no suitable position is found.
    """
    entries = parse_doc_entries(text)
    if not entries:
        return text.rstrip() + "\n\n" + new_entry + "\n"

    ev_name_lower = ev.name.lower()
    insert_before = None
    for entry in entries:
        if entry.get("name", "") > ev_name_lower:
            insert_before = entry
            break

    if insert_before is None:
        # Append after last entry
        return text.rstrip() + "\n\n" + new_entry + "\n"
    else:
        pos = insert_before["start"]
        return text[:pos] + new_entry + "\n\n" + text[pos:]


# ---------------------------------------------------------------------------
# Merge engine
# ---------------------------------------------------------------------------

def merge_into_doc(
    doc_text: str,
    evaluations: list[RepoEval],
    doc_name: str,
    today: str,
) -> tuple[str, list[MergeAction]]:
    """Merge evaluations into a single doc, returning (new_text, actions)."""
    actions: list[MergeAction] = []
    entries = parse_doc_entries(doc_text)
    result = doc_text

    for ev in evaluations:
        entry, match_type = find_entry(entries, ev)

        if match_type == "exact":
            # Rewrite frontmatter; preserve body
            old_chunk = entry["chunk"]
            prev_class = entry["fm_fields"].get("classification")
            prev_license = entry["fm_fields"].get("license")
            new_chunk = rewrite_frontmatter_in_chunk(old_chunk, ev)
            result = result[: entry["start"]] + new_chunk + result[entry["end"]:]
            # Re-parse so offsets stay valid for subsequent updates
            entries = parse_doc_entries(result)

            if prev_class and prev_class.upper() != ev.classification:
                action = "updated"
            else:
                action = "refreshed"
            actions.append(MergeAction(
                repo=ev.repo,
                action=action,
                target_doc=doc_name,
                prev_classification=prev_class,
                new_classification=ev.classification,
                prev_license=prev_license,
                new_license=ev.license,
            ))

        elif match_type == "fuzzy":
            print(f"  WARN: fuzzy match found for {ev.repo} — treating as new insert, please review dry-run diff",
                  file=sys.stderr)
            new_entry_text = build_new_entry(ev)
            result = insert_entry_alphabetically(result, new_entry_text, ev)
            entries = parse_doc_entries(result)
            actions.append(MergeAction(
                repo=ev.repo,
                action="added",
                target_doc=doc_name,
                new_classification=ev.classification,
                message="fuzzy match — may be duplicate",
            ))

        else:
            # New insert
            new_entry_text = build_new_entry(ev)
            result = insert_entry_alphabetically(result, new_entry_text, ev)
            entries = parse_doc_entries(result)
            actions.append(MergeAction(
                repo=ev.repo,
                action="added",
                target_doc=doc_name,
                new_classification=ev.classification,
            ))

    return result, actions


def handle_classification_shift(
    ecosystem_text: str,
    blocked_text: str,
    ev: RepoEval,
    today: str,
) -> tuple[str, str, Optional[MergeAction]]:
    """Handle a repo that is now REJECT but exists in ecosystem-tools (or vice versa).

    Returns (new_ecosystem_text, new_blocked_text, action_or_none).
    """
    eco_entries = parse_doc_entries(ecosystem_text)
    blocked_entries = parse_doc_entries(blocked_text)

    if ev.classification == "REJECT":
        # Check if it exists in ecosystem-tools
        entry, match_type = find_entry(eco_entries, ev)
        if entry and match_type == "exact":
            # Move: extract from ecosystem-tools
            moved_comment = f"<!-- moved from ecosystem-tools.md on {today} by /radar-update -->\n"
            old_chunk = entry["chunk"]
            # Preserve body + prepend moved comment
            new_chunk_in_blocked = moved_comment + rewrite_frontmatter_in_chunk(old_chunk, ev)
            # Remove from ecosystem-tools
            new_ecosystem = ecosystem_text[: entry["start"]] + ecosystem_text[entry["end"]:]
            # Insert into blocked-tools
            new_blocked = blocked_text.rstrip() + "\n\n" + new_chunk_in_blocked + "\n"
            prev_class = entry["fm_fields"].get("classification", "?")
            prev_license = entry["fm_fields"].get("license", "?")
            action = MergeAction(
                repo=ev.repo,
                action="moved",
                target_doc="blocked-tools",
                prev_classification=prev_class,
                new_classification=ev.classification,
                prev_license=prev_license,
                new_license=ev.license,
            )
            return new_ecosystem, new_blocked, action
    else:
        # Non-REJECT: check if it erroneously exists in blocked-tools
        entry, match_type = find_entry(blocked_entries, ev)
        if entry and match_type == "exact":
            # Move: extract from blocked-tools
            moved_comment = f"<!-- moved from blocked-tools.md on {today} by /radar-update -->\n"
            old_chunk = entry["chunk"]
            new_chunk_in_eco = moved_comment + rewrite_frontmatter_in_chunk(old_chunk, ev)
            new_blocked = blocked_text[: entry["start"]] + blocked_text[entry["end"]:]
            new_eco = ecosystem_text.rstrip() + "\n\n" + new_chunk_in_eco + "\n"
            prev_class = entry["fm_fields"].get("classification", "?")
            action = MergeAction(
                repo=ev.repo,
                action="moved",
                target_doc="ecosystem-tools",
                prev_classification=prev_class,
                new_classification=ev.classification,
                prev_license=entry["fm_fields"].get("license"),
                new_license=ev.license,
            )
            return new_eco, new_blocked, action

    return ecosystem_text, blocked_text, None


# ---------------------------------------------------------------------------
# CHANGELOG updater
# ---------------------------------------------------------------------------

def update_changelog(changelog_path: Path, actions: list[MergeAction], today: str) -> str:
    """Append radar entries to CHANGELOG.md under [Unreleased] → ### Documentation.

    Returns the updated changelog text.
    """
    text = changelog_path.read_text(encoding="utf-8")

    changelog_lines = []
    for action in actions:
        if action.action == "added":
            changelog_lines.append(f"- radar: added {action.repo} as {action.new_classification}")
        elif action.action == "updated":
            changelog_lines.append(
                f"- radar: updated {action.repo} ({action.prev_classification}→{action.new_classification})"
            )
        elif action.action == "moved":
            if action.new_classification == "REJECT":
                changelog_lines.append(
                    f"- radar: moved {action.repo} to blocked-tools (license: {action.prev_license}→{action.new_license})"
                )
            else:
                changelog_lines.append(
                    f"- radar: moved {action.repo} to ecosystem-tools ({action.prev_classification}→{action.new_classification})"
                )
        elif action.action == "refreshed":
            changelog_lines.append(f"- radar: refreshed {action.repo} metrics")

    if not changelog_lines:
        return text

    new_entries = "\n".join(changelog_lines)

    # Case 1: [Unreleased] with ### Documentation already exists
    m = re.search(r"(## \[Unreleased\][^\n]*\n)(.*?)(### Documentation\n)", text, re.DOTALL)
    if m:
        # Insert new entries after "### Documentation\n"
        insert_pos = m.end()
        return text[:insert_pos] + new_entries + "\n" + text[insert_pos:]

    # Case 2: [Unreleased] exists but no ### Documentation
    m2 = re.search(r"(## \[Unreleased\][^\n]*\n)", text)
    if m2:
        insert_pos = m2.end()
        return text[:insert_pos] + "\n### Documentation\n" + new_entries + "\n" + text[insert_pos:]

    # Case 3: No [Unreleased] at all — prepend it
    header = "# Changelog\n\n" if text.startswith("# Changelog") else ""
    unreleased_block = f"## [Unreleased]\n\n### Documentation\n{new_entries}\n\n"
    if header:
        # Insert after the "# Changelog\n\n" header
        pos = text.index("\n\n") + 2 if "\n\n" in text else len(header)
        return text[:pos] + unreleased_block + text[pos:]
    return unreleased_block + text


# ---------------------------------------------------------------------------
# Diff generation
# ---------------------------------------------------------------------------

def generate_diff(original: str, modified: str, filename: str) -> str:
    """Generate a unified diff between two texts."""
    original_lines = original.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)
    diff = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
    )
    return "".join(diff)


# ---------------------------------------------------------------------------
# Atomic file write
# ---------------------------------------------------------------------------

def atomic_write(path: Path, content: str) -> None:
    """Write content atomically via a temp file in the same directory."""
    tmp_fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Summary printer
# ---------------------------------------------------------------------------

def print_summary(actions: list[MergeAction], diff_path: Optional[Path], apply: bool) -> None:
    eco_added = sum(1 for a in actions if a.action == "added" and "ecosystem" in a.target_doc)
    eco_updated = sum(1 for a in actions if a.action in ("updated", "refreshed") and "ecosystem" in a.target_doc)
    eco_moved = sum(1 for a in actions if a.action == "moved" and "ecosystem" in a.target_doc)
    blk_added = sum(1 for a in actions if a.action == "added" and "blocked" in a.target_doc)
    blk_updated = sum(1 for a in actions if a.action in ("updated", "refreshed") and "blocked" in a.target_doc)
    blk_moved = sum(1 for a in actions if a.action == "moved" and "blocked" in a.target_doc)
    errors = sum(1 for a in actions if a.action == "error")
    fuzzy = sum(1 for a in actions if "fuzzy" in a.message)

    mode = "apply" if apply else "dry-run"
    print(f"\n--- radar-update {mode} summary ---")
    print(f"ecosystem-tools.md : {eco_added} added, {eco_updated} updated, {eco_moved} moved")
    print(f"blocked-tools.md   : {blk_added} added, {blk_updated} updated, {blk_moved} moved")
    print(f"Total repos        : {len(actions)} ({errors} errors, {fuzzy} fuzzy warnings)")
    if diff_path:
        print(f"Diff saved to      : {diff_path}")
    if not apply:
        print("Run with --apply to write changes.")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Merge /repo-scout artifacts into tech radar docs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--artifacts",
        nargs="+",
        required=True,
        metavar="FILE",
        help="One or more /repo-scout markdown artifact files",
    )
    parser.add_argument(
        "--ecosystem-tools",
        required=True,
        metavar="FILE",
        help="Path to docs/patterns/ecosystem-tools.md",
    )
    parser.add_argument(
        "--blocked-tools",
        required=True,
        metavar="FILE",
        help="Path to docs/blocked-tools.md",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Write changes to disk (default: dry-run only)",
    )
    parser.add_argument(
        "--changelog",
        metavar="FILE",
        help="Path to CHANGELOG.md (required for --apply)",
    )
    parser.add_argument(
        "--output-diff",
        metavar="FILE",
        help="Save unified diff to this file (dry-run mode)",
    )

    args = parser.parse_args(argv)

    # Validate inputs
    ecosystem_path = Path(args.ecosystem_tools)
    blocked_path = Path(args.blocked_tools)

    if not ecosystem_path.exists():
        print(f"ERROR: --ecosystem-tools file not found: {ecosystem_path}", file=sys.stderr)
        return 2
    if not blocked_path.exists():
        print(f"ERROR: --blocked-tools file not found: {blocked_path}", file=sys.stderr)
        return 2

    if args.apply and not args.changelog:
        print("ERROR: --apply requires --changelog", file=sys.stderr)
        return 2

    # Parse artifacts
    evaluations: list[RepoEval] = []
    for artifact_path_str in args.artifacts:
        artifact_path = Path(artifact_path_str)
        if not artifact_path.exists():
            print(f"  WARN: artifact not found, skipping: {artifact_path}", file=sys.stderr)
            continue
        ev = parse_artifact(artifact_path)
        if ev is None:
            print(f"  WARN: could not parse artifact: {artifact_path}", file=sys.stderr)
            continue
        evaluations.append(ev)

    if not evaluations:
        print("No valid evaluations to merge.", file=sys.stderr)
        return 1

    # Dedup: if same repo appears multiple times, keep last occurrence
    seen: dict[str, RepoEval] = {}
    for ev in evaluations:
        seen[ev.repo] = ev
    evaluations = list(seen.values())

    today = str(date.today())
    eco_original = ecosystem_path.read_text(encoding="utf-8")
    blk_original = blocked_path.read_text(encoding="utf-8")

    eco_text = eco_original
    blk_text = blk_original
    all_actions: list[MergeAction] = []

    # Handle classification shifts first (moves between docs)
    for ev in evaluations:
        new_eco, new_blk, action = handle_classification_shift(eco_text, blk_text, ev, today)
        eco_text = new_eco
        blk_text = new_blk
        if action:
            all_actions.append(action)

    # Separate evaluations by target doc
    eco_evals = [ev for ev in evaluations if CLASSIFICATION_TO_DOC.get(ev.classification) == "ecosystem-tools"]
    blk_evals = [ev for ev in evaluations if CLASSIFICATION_TO_DOC.get(ev.classification) == "blocked-tools"]

    # Remove repos already handled by move
    moved_repos = {a.repo for a in all_actions if a.action == "moved"}
    eco_evals = [ev for ev in eco_evals if ev.repo not in moved_repos]
    blk_evals = [ev for ev in blk_evals if ev.repo not in moved_repos]

    # Merge into each doc
    if eco_evals:
        eco_text, eco_actions = merge_into_doc(eco_text, eco_evals, "ecosystem-tools", today)
        all_actions.extend(eco_actions)

    if blk_evals:
        blk_text, blk_actions = merge_into_doc(blk_text, blk_evals, "blocked-tools", today)
        all_actions.extend(blk_actions)

    # Generate diffs
    eco_diff = generate_diff(eco_original, eco_text, "docs/patterns/ecosystem-tools.md")
    blk_diff = generate_diff(blk_original, blk_text, "docs/blocked-tools.md")
    combined_diff = eco_diff + blk_diff

    # Print diff to stdout
    if combined_diff:
        print(combined_diff, end="")
    else:
        print("(no changes — all repos already up to date)")

    # Save diff file
    diff_path: Optional[Path] = None
    if args.output_diff:
        diff_path = Path(args.output_diff)
        diff_path.parent.mkdir(parents=True, exist_ok=True)
        diff_path.write_text(combined_diff, encoding="utf-8")

    if args.apply:
        # Stale-write protection: re-read and compare current state
        current_eco = ecosystem_path.read_text(encoding="utf-8")
        current_blk = blocked_path.read_text(encoding="utf-8")
        if current_eco != eco_original:
            print(
                f"\nABORT: {ecosystem_path} changed since dry-run. "
                "Re-run without --apply to regenerate diff.",
                file=sys.stderr,
            )
            return 3
        if current_blk != blk_original:
            print(
                f"\nABORT: {blocked_path} changed since dry-run. "
                "Re-run without --apply to regenerate diff.",
                file=sys.stderr,
            )
            return 3

        # Write files
        if eco_text != eco_original:
            atomic_write(ecosystem_path, eco_text)
            print(f"Written: {ecosystem_path}")
        if blk_text != blk_original:
            atomic_write(blocked_path, blk_text)
            print(f"Written: {blocked_path}")

        # Update CHANGELOG
        changelog_path = Path(args.changelog)
        if changelog_path.exists():
            new_changelog = update_changelog(changelog_path, all_actions, today)
            if new_changelog != changelog_path.read_text(encoding="utf-8"):
                atomic_write(changelog_path, new_changelog)
                print(f"Written: {changelog_path}")
        else:
            print(f"  WARN: CHANGELOG not found at {changelog_path}, skipping", file=sys.stderr)

    print_summary(all_actions, diff_path, args.apply)
    return 0


if __name__ == "__main__":
    sys.exit(main())
