"""Skill Runner — harness-agnostic skill discovery and invocation engine.

This module is the engine behind ``bin/cos-skill``. It provides:

- Discovery: walk ``skills/*/SKILL.md`` and parse YAML frontmatter.
- ``list_skills()`` — enumerate all installed skills as ``SkillRecord`` objects.
- ``describe_skill(name)`` — full record including body text.
- ``run_skill(name, args, harness)`` — invoke a skill portably.

Harness detection
-----------------
Harness is resolved via the ``COGNITIVE_OS_HARNESS`` environment variable first,
then via heuristics:

- ``COGNITIVE_OS_HARNESS=claude_code``  → CC slash-command stop-gap (see below).
- ``COGNITIVE_OS_HARNESS=codex``        → rendered SKILL.md body on stdout.
- ``COGNITIVE_OS_HARNESS=bare_cli``     → rendered SKILL.md body on stdout.
- Unset / unknown                       → bare_cli behaviour.

Claude Code stop-gap
--------------------
When the harness is ``claude_code``, ``run_skill`` prints the slash-command
form (e.g. ``/my-skill --arg value``) to stdout and returns it as the result.
The human or agent reading the terminal then pastes or relays it into the CC
chat interface.  This is a deliberate stop-gap: once ``cos-agent`` exists
(ADR-064 Surface 4), ``run_skill`` on CC can pipe directly into it.

Future work
-----------
When ``cos-agent spawn`` is available, replace the CC branch with::

    cos-agent spawn --task "$(rendered_body)" --model <hint> --harness claude_code

Arg substitution
----------------
SKILL.md bodies may contain ``{{arg_name}}`` placeholders. ``run_skill``
substitutes ``args`` dict values before returning the rendered body.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class SkillRecord:
    """Metadata and body of a single skill."""

    name: str
    tier: str          # effort/model hint: opus | sonnet | haiku | unknown
    description: str
    scope: str         # both | os-only | project
    platforms: List[str]
    version: str
    path: Path
    body: str = field(default="", repr=False)  # full body text (post frontmatter)
    raw_frontmatter: Dict[str, Any] = field(default_factory=dict, repr=False)


@dataclass
class RunResult:
    """Result of a run_skill invocation."""

    skill_name: str
    harness: str
    rendered: str       # the text emitted / to be emitted
    success: bool = True
    message: str = ""


# ---------------------------------------------------------------------------
# Frontmatter parser
# ---------------------------------------------------------------------------

_YAML_FENCE_RE = re.compile(r"^---\s*$", re.MULTILINE)
_HTML_COMMENT_SCOPE_RE = re.compile(r"<!--\s*SCOPE:\s*(\S+)\s*-->")


def _parse_frontmatter(text: str) -> tuple[Dict[str, Any], str]:
    """Extract YAML frontmatter between ``---`` markers and return (meta, body).

    Falls back to an empty dict if no frontmatter is found.
    Handles the ``<!-- SCOPE: … -->`` HTML-comment convention used in some
    SKILL.md files as a pre-frontmatter annotation.
    """
    # Strip leading HTML comment scope annotation if present
    stripped = text.lstrip()
    meta: Dict[str, Any] = {}

    # Capture scope from HTML comment (may precede the --- block)
    comment_match = _HTML_COMMENT_SCOPE_RE.match(stripped)
    if comment_match:
        meta["_scope_comment"] = comment_match.group(1)
        stripped = stripped[comment_match.end():].lstrip()

    # Must start with ---
    if not stripped.startswith("---"):
        return meta, text

    # Find closing ---
    parts = _YAML_FENCE_RE.split(stripped, maxsplit=2)
    if len(parts) < 3:
        return meta, text

    # parts[0] == "" (before first ---), parts[1] == yaml block, parts[2] == body
    yaml_block = parts[1]
    body = parts[2].lstrip("\n")

    # Minimal YAML key-value parser (avoids PyYAML dependency)
    for line in yaml_block.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, _, v = line.partition(":")
            k = k.strip()
            v = v.strip()
            # Strip inline YAML string quotes
            if v.startswith(('"', "'")) and v.endswith(('"', "'")):
                v = v[1:-1]
            # Parse simple lists: ["a", "b"]
            if v.startswith("[") and v.endswith("]"):
                inner = v[1:-1]
                items = [i.strip().strip('"').strip("'") for i in inner.split(",") if i.strip()]
                meta[k] = items
            else:
                meta[k] = v

    return meta, body


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def _skills_root() -> Path:
    """Return the absolute path to the skills/ directory.

    Anchored to the git repo root via ``git rev-parse --show-toplevel`` when
    possible; falls back to the directory two levels above this file.
    """
    env_root = os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.environ.get("CLAUDE_PROJECT_DIR")
    if env_root:
        candidate = Path(env_root) / "skills"
        if candidate.is_dir():
            return candidate

    # Derive from this file's location: lib/skill_runner.py → repo root
    this_file = Path(__file__).resolve()
    # Follow symlinks
    repo_root = this_file.parent.parent
    candidate = repo_root / "skills"
    if candidate.is_dir():
        return candidate

    raise FileNotFoundError(f"Cannot locate skills/ directory (tried {candidate})")


def _tier_from_meta(meta: Dict[str, Any]) -> str:
    """Resolve the model tier from frontmatter fields."""
    for field_name in ("effort", "tier", "model"):
        val = meta.get(field_name, "")
        if val:
            return str(val).lower().strip().rstrip(">").strip()
    return "sonnet"


def _scope_from_meta(meta: Dict[str, Any]) -> str:
    # HTML comment annotation takes precedence
    scope = meta.get("_scope_comment") or meta.get("scope") or meta.get("audience") or "both"
    return str(scope).lower().strip()


def _load_skill(skill_md: Path) -> SkillRecord:
    """Parse a single SKILL.md file into a SkillRecord."""
    text = skill_md.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text)

    name = meta.get("name") or skill_md.parent.name
    description = meta.get("description", "")
    # Multi-line block scalar in minimal parser comes through with trailing >
    description = description.rstrip(">").strip()
    # Fallback: grab first non-empty body line as description
    if not description:
        for line in body.splitlines():
            line = line.strip().lstrip("#").strip()
            if line and not line.startswith("**") and len(line) > 10:
                description = line[:120]
                break

    platforms_raw = meta.get("platforms", [])
    if isinstance(platforms_raw, str):
        platforms_raw = [platforms_raw]

    return SkillRecord(
        name=str(name),
        tier=_tier_from_meta(meta),
        description=description,
        scope=_scope_from_meta(meta),
        platforms=platforms_raw,
        version=str(meta.get("version", "0.0.0")),
        path=skill_md,
        body=body,
        raw_frontmatter=meta,
    )


def list_skills(skills_root: Optional[Path] = None) -> List[SkillRecord]:
    """Return a sorted list of all installed skills.

    Walks ``skills/*/SKILL.md``. Sub-directories without a SKILL.md are
    skipped silently (e.g. ``auto-generated/``, ``CATALOG*.md``).
    """
    root = skills_root or _skills_root()
    records: List[SkillRecord] = []
    for skill_md in sorted(root.glob("*/SKILL.md"), key=lambda p: p.parent.name.lower()):
        try:
            records.append(_load_skill(skill_md))
        except Exception as exc:  # noqa: BLE001
            # Never crash on a bad SKILL.md; emit a placeholder
            records.append(SkillRecord(
                name=skill_md.parent.name,
                tier="unknown",
                description=f"[parse error: {exc}]",
                scope="unknown",
                platforms=[],
                version="?",
                path=skill_md,
            ))
    return records


def describe_skill(name: str, skills_root: Optional[Path] = None) -> SkillRecord:
    """Return the full SkillRecord for a given skill name.

    Raises ``KeyError`` if the skill is not found.
    """
    root = skills_root or _skills_root()
    skill_md = root / name / "SKILL.md"
    if not skill_md.exists():
        # Try case-insensitive search
        for candidate in root.glob("*/SKILL.md"):
            if candidate.parent.name.lower() == name.lower():
                skill_md = candidate
                break
        else:
            raise KeyError(f"Skill '{name}' not found in {root}")
    return _load_skill(skill_md)


# ---------------------------------------------------------------------------
# Harness detection
# ---------------------------------------------------------------------------

def detect_harness() -> str:
    """Detect the current harness.

    Priority:
    1. ``COGNITIVE_OS_HARNESS`` env var (explicit).
    2. ``CLAUDE_MCP_SERVER`` / ``CLAUDE_PROJECT_DIR`` env → claude_code.
    3. ``CODEX_PROJECT_DIR`` / ``CODEX_SESSION_ID`` → codex.
    4. Default: bare_cli.
    """
    explicit = os.environ.get("COGNITIVE_OS_HARNESS", "").lower()
    if explicit:
        return explicit

    if os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get("CLAUDE_MCP_SERVER"):
        return "claude_code"

    if os.environ.get("CODEX_PROJECT_DIR") or os.environ.get("CODEX_SESSION_ID"):
        return "codex"

    return "bare_cli"


# ---------------------------------------------------------------------------
# Arg substitution
# ---------------------------------------------------------------------------

def _substitute_args(body: str, args: Dict[str, str]) -> str:
    """Replace ``{{key}}`` placeholders in body with values from args."""
    for k, v in args.items():
        body = body.replace("{{" + k + "}}", v)
    return body


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def run_skill(
    name: str,
    args: Optional[Dict[str, str]] = None,
    harness: Optional[str] = None,
    skills_root: Optional[Path] = None,
) -> RunResult:
    """Invoke a skill in a harness-appropriate way.

    Parameters
    ----------
    name:
        Skill directory name (e.g. ``"verification-before-completion"``).
    args:
        Key-value pairs substituted into ``{{key}}`` placeholders in the body.
    harness:
        Override harness detection. If ``None``, ``detect_harness()`` is used.
    skills_root:
        Override skills root directory (useful for testing).
    """
    if args is None:
        args = {}

    resolved_harness = harness or detect_harness()

    try:
        record = describe_skill(name, skills_root=skills_root)
    except KeyError as exc:
        return RunResult(
            skill_name=name,
            harness=resolved_harness,
            rendered="",
            success=False,
            message=str(exc),
        )

    if resolved_harness == "claude_code":
        # Stop-gap: emit the slash-command form.
        # Future: pipe into `cos-agent spawn` once ADR-064 Surface 4 ships.
        arg_parts = " ".join(f"--{k}={v}" for k, v in args.items())
        command_name = record.raw_frontmatter.get("command", f"/{name}").lstrip("/")
        slash_cmd = f"/{command_name}" + (f" {arg_parts}" if arg_parts else "")
        return RunResult(
            skill_name=name,
            harness=resolved_harness,
            rendered=slash_cmd,
            success=True,
            message="CC stop-gap: paste this slash command into the Claude Code chat interface.",
        )

    # codex / bare_cli / unknown → render body with arg substitution
    rendered = _substitute_args(record.body, args)
    return RunResult(
        skill_name=name,
        harness=resolved_harness,
        rendered=rendered,
        success=True,
        message="",
    )


# ---------------------------------------------------------------------------
# CLI helpers (called by bin/cos-skill)
# ---------------------------------------------------------------------------

def _print_table(records: List[SkillRecord], *, json_mode: bool = False) -> None:
    """Print skills as a formatted table or JSON."""
    if json_mode:
        import json as _json
        out = [
            {
                "name": r.name,
                "tier": r.tier,
                "scope": r.scope,
                "description": r.description,
                "platforms": r.platforms,
                "version": r.version,
            }
            for r in records
        ]
        print(_json.dumps(out, indent=2))
        return

    # Compute column widths
    name_w = max((len(r.name) for r in records), default=4)
    tier_w = max((len(r.tier) for r in records), default=4)
    name_w = max(name_w, 4)
    tier_w = max(tier_w, 4)

    header = f"{'NAME':<{name_w}}  {'TIER':<{tier_w}}  DESCRIPTION"
    print(header)
    print("-" * min(120, len(header) + 40))
    for r in records:
        desc = r.description[:80] if r.description else ""
        print(f"{r.name:<{name_w}}  {r.tier:<{tier_w}}  {desc}")


def main_cli(argv: Optional[List[str]] = None) -> int:
    """Entry point for ``bin/cos-skill`` (called via subprocess by the shell wrapper)."""
    import json as _json

    args = argv if argv is not None else sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0

    subcommand = args[0]
    rest = args[1:]

    if subcommand == "list":
        json_mode = "--json" in rest
        records = list_skills()
        _print_table(records, json_mode=json_mode)
        return 0

    if subcommand == "describe":
        if not rest:
            print("Usage: cos-skill describe <name>", file=sys.stderr)
            return 1
        name = rest[0]
        json_mode = "--json" in rest[1:]
        try:
            record = describe_skill(name)
        except KeyError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        if json_mode:
            out = {
                "name": record.name,
                "tier": record.tier,
                "scope": record.scope,
                "description": record.description,
                "platforms": record.platforms,
                "version": record.version,
                "frontmatter": {k: v for k, v in record.raw_frontmatter.items() if not k.startswith("_")},
                "body_preview": record.body[:500],
            }
            print(_json.dumps(out, indent=2))
        else:
            print(f"Name:        {record.name}")
            print(f"Tier:        {record.tier}")
            print(f"Scope:       {record.scope}")
            print(f"Version:     {record.version}")
            print(f"Platforms:   {', '.join(record.platforms) or 'all'}")
            print(f"Description: {record.description}")
            print(f"Path:        {record.path}")
            print()
            print("--- Body ---")
            print(record.body[:2000])
            if len(record.body) > 2000:
                print(f"\n[... {len(record.body) - 2000} more chars — view full file: {record.path}]")
        return 0

    if subcommand == "run":
        if not rest:
            print("Usage: cos-skill run <name> [--key=value ...]", file=sys.stderr)
            return 1
        skill_name = rest[0]
        # Parse --key=value pairs
        run_args: Dict[str, str] = {}
        harness_override: Optional[str] = None
        for token in rest[1:]:
            if token.startswith("--harness="):
                harness_override = token.split("=", 1)[1]
            elif token.startswith("--") and "=" in token:
                k, _, v = token[2:].partition("=")
                run_args[k] = v
        result = run_skill(skill_name, args=run_args, harness=harness_override)
        if not result.success:
            print(f"error: {result.message}", file=sys.stderr)
            return 1
        print(result.rendered)
        if result.message:
            print(f"\n# {result.message}", file=sys.stderr)
        return 0

    print(f"Unknown subcommand: {subcommand}", file=sys.stderr)
    print("Available: list, describe, run", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main_cli())
