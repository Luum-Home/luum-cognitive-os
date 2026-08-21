#!/usr/bin/env python3
# SCOPE: os-only
"""Gate: no registration ENTRY may point at something that cannot run.

Read-only. Deterministic. Exit 0 = clean, 1 = findings, 2 = could not run.

    .venv/bin/python scripts/audit_registration_reverse.py
    .venv/bin/python scripts/audit_registration_reverse.py --json
    .venv/bin/python scripts/audit_registration_reverse.py --strict

WHY THIS EXISTS -- the direction the other gate does not walk
-------------------------------------------------------------
`scripts/audit_hook_registration.py` walks COMPONENT -> CONFIG: a hook declared
in cognitive-os.yaml that no surface wires is an orphan. It is silent about the
opposite: a config entry pointing at a path that does not exist, or that exists
but cannot be executed the way the caller invokes it. Such an entry is green on
that gate and dead at runtime.

The failure mode is documented by the vendor, not inferred. Claude Code's hooks
reference (https://code.claude.com/docs/en/hooks, read 2026-08-21) says:

    "A hook that can't start lands in the same non-blocking bucket. When the
    script path doesn't exist or isn't executable, the shell exits with a code
    like 127 ... For most hook events, the action proceeds. When you set up a
    policy hook, watch for this notice on its first run: a mistyped path in
    settings.json leaves the gate silently disabled."

Two of this repo's own dispatchers fail open the same way, and neither reports:

    hooks/bash-hot-path-dispatcher.sh:40
        [ -x "$path" ] || [ -f "$path" ] || return 0
    .opencode/plugins/cos-primitive-guard.js:157
        if (!existsSync(scriptPath)) return null

THREE STATES, NOT TWO
---------------------
Every entry lands in exactly one of VALID / BROKEN / UNVERIFIABLE. The third is
the point: an entry whose command shape this parser cannot resolve to a path is
NOT evidence that the entry is fine. Collapsing UNVERIFIABLE into VALID is
fail-open, and fail-open dressed as green is the defect this gate exists to
catch, so it would be an odd way to build it.

UNVERIFIABLE does not set the exit code by default, for the same reason
audit_hook_registration.py does not gate on contradicted omissions: a gate that
cannot be turned green gets switched off. It is always counted, always printed,
and `--strict` makes it gate for callers that want that.

ANTI-VACUUM
-----------
A checker that walks zero entries exits green exactly like a healthy one. Three
guards make that impossible:

  * zero entries across all surfaces           -> exit 2
  * a surface file that EXISTS but yields zero -> exit 2
  * zero VALID entries (parser degenerated to
    all-unverifiable)                          -> exit 2
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
from dataclasses import dataclass, field
from pathlib import Path

VALID = "VALID"
BROKEN = "BROKEN"
UNVERIFIABLE = "UNVERIFIABLE"

# Variables that expand to the project root at hook runtime. Each harness names
# it differently; all of them resolve to the same directory.
ROOT_VARS = (
    "CLAUDE_PROJECT_DIR",
    "COGNITIVE_OS_PROJECT_DIR",
    "CODEX_PROJECT_DIR",
    "PWD",
    "PROJECT_DIR",
    "HOOK_DIR_PARENT",
)

INTERPRETERS = {"bash", "sh", "zsh", "dash", "python", "python3", "source", "."}

# Wrappers that receive the real hook path as an argument rather than running the
# token next to the interpreter. Value = how the wrapper invokes its target.
# Both entries are verified, not assumed:
#   scripts/hook-timing-wrapper.sh:61   HOOK_PATH="$2"
#   scripts/hook-timing-wrapper.sh:384  ... | bash "$HOOK_PATH" "${HOOK_ARGS[@]}"
WRAPPERS = {
    "scripts/hook-timing-wrapper.sh": {"path_arg_index": 1, "invoker": "bash"},
}

# Matcher contract per event, from the Claude Code hooks reference
# (https://code.claude.com/docs/en/hooks, read 2026-08-21).
#   "none"  -> event takes no matcher; a non-empty one is dead config
#   "open"  -> matcher is a name/regex we cannot enumerate (tool, agent, server)
#   tuple   -> closed enumeration; anything outside it never matches
MATCHER_POLICY: dict[str, object] = {
    "SessionStart": ("startup", "resume", "clear", "compact", "fork"),
    "Setup": ("init", "maintenance"),
    "UserPromptSubmit": "none",
    "UserPromptExpansion": "open",
    "PreToolUse": "open",
    "PermissionRequest": "open",
    "PermissionDenied": "open",
    "PostToolUse": "open",
    "PostToolUseFailure": "open",
    "PostToolBatch": "none",
    "Notification": (
        "permission_prompt",
        "idle_prompt",
        "auth_success",
        "elicitation_dialog",
        "elicitation_url_dialog",
        "elicitation_complete",
        "elicitation_response",
        "agent_needs_input",
        "agent_completed",
    ),
    "MessageDisplay": "none",
    "SubagentStart": "open",
    "SubagentStop": "open",
    "TaskCreated": "none",
    "TaskCompleted": "none",
    "Stop": "none",
    "StopFailure": (
        "rate_limit",
        "overloaded",
        "authentication_failed",
        "oauth_org_not_allowed",
        "billing_error",
        "invalid_request",
        "model_not_found",
        "server_error",
        "max_output_tokens",
        "unknown",
    ),
    "TeammateIdle": "none",
    "InstructionsLoaded": (
        "session_start",
        "nested_traversal",
        "path_glob_match",
        "include",
        "compact",
    ),
    "ConfigChange": (
        "user_settings",
        "project_settings",
        "local_settings",
        "policy_settings",
        "skills",
    ),
    "CwdChanged": "none",
    "DirectoryAdded": ("slash_command", "register_repo_root"),
    "FileChanged": "open",
    "WorktreeCreate": "none",
    "WorktreeRemove": "none",
    "PreCompact": ("manual", "auto"),
    "PostCompact": "none",
    "Elicitation": "open",
    "ElicitationResult": "open",
    "SessionEnd": ("clear", "resume", "logout", "prompt_input_exit", "other"),
}

SCRIPT_SUFFIXES = (".sh", ".py", ".js", ".mjs", ".ts", ".bash")


class NoRegistry(Exception):
    """The file exists but carries no hook registry at all.

    Distinct from 'the parser found zero entries in a registry that is there',
    which is a parser failure and must exit 2. `.claude/settings.local.json`
    legitimately holds only `permissions`; treating that as a broken parser
    would be a false red, and a gate that cannot go green gets switched off.
    """


@dataclass
class Entry:
    """One registration entry, resolved as far as the parser honestly can."""

    surface: str
    event: str
    matcher: str | None
    raw: str
    target: str | None = None  # repo-relative when resolvable
    abs_path: str | None = None
    invoker: str = "unknown"  # bash | direct | unknown
    exec_required: bool = False
    status: str = UNVERIFIABLE
    reasons: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "surface": self.surface,
            "event": self.event,
            "matcher": self.matcher,
            "target": self.target,
            "invoker": self.invoker,
            "exec_required": self.exec_required,
            "status": self.status,
            "reasons": self.reasons,
            "raw": self.raw if len(self.raw) <= 300 else self.raw[:297] + "...",
        }


# ── path resolution ──────────────────────────────────────────────────────────


def _expand(token: str, root: Path) -> str | None:
    """Expand root-vars. Return None when an unknown expansion remains."""
    out = token
    for var in ROOT_VARS:
        out = out.replace("${%s}" % var, str(root)).replace("$" + var, str(root))
    # `${VAR:-fallback}` shapes: try the fallback if it is itself a root-var.
    out = re.sub(r"\$\{[A-Za-z_][A-Za-z0-9_]*:-([^}]*)\}", r"\1", out)
    for var in ROOT_VARS:
        out = out.replace("${%s}" % var, str(root)).replace("$" + var, str(root))
    if "$" in out or "`" in out or "*" in out or "?" in out:
        return None
    return out


def _looks_like_script(token: str) -> bool:
    return token.endswith(SCRIPT_SUFFIXES) and ("/" in token or token.startswith("."))


def _resolve(token: str, root: Path) -> tuple[str | None, str | None]:
    """(repo-relative target, absolute path) or (None, None) if unresolvable."""
    expanded = _expand(token, root)
    if expanded is None:
        return None, None
    p = Path(expanded)
    if not p.is_absolute():
        p = root / p
    try:
        rel = os.path.relpath(str(p), str(root))
    except ValueError:  # pragma: no cover - different drive on Windows
        rel = str(p)
    return rel, str(p)


def _classify_command(command: str, root: Path) -> list[tuple[str, str, str, bool]]:
    """Extract (target, abs_path, invoker, exec_required) tuples from a command.

    Returns [] when nothing script-shaped is found, which the caller turns into
    UNVERIFIABLE rather than into a pass.
    """
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return []

    # `[ -x "<path>" ]` guards (the Codex driver shape) mean the caller skips the
    # hook unless the execute bit is set: silently, and without reporting.
    exec_guarded = set()
    for i, tok in enumerate(tokens):
        if tok == "-x" and i + 1 < len(tokens):
            rel, _ = _resolve(tokens[i + 1], root)
            if rel:
                exec_guarded.add(rel)

    found: list[tuple[str, str, str, bool]] = []
    seen: set[str] = set()
    wrapper_active: dict | None = None
    wrapper_seen_args = 0

    for i, tok in enumerate(tokens):
        if not _looks_like_script(tok):
            if wrapper_active is not None:
                wrapper_seen_args += 1
            continue
        rel, abs_path = _resolve(tok, root)
        if rel is None or abs_path is None:
            continue

        if rel in WRAPPERS:
            wrapper_active = WRAPPERS[rel]
            wrapper_seen_args = 0
            invoker = _invoker_from_prev(tokens, i)
            exec_required = invoker == "direct"
        elif wrapper_active is not None:
            # A path argument handed to a known wrapper: the wrapper decides how
            # it runs, not the token that precedes it in the shell line.
            invoker = wrapper_active["invoker"]
            exec_required = invoker == "direct"
        else:
            invoker = _invoker_from_prev(tokens, i)
            exec_required = invoker == "direct"

        if rel in exec_guarded:
            exec_required = True

        if rel in seen:
            continue
        seen.add(rel)
        found.append((rel, abs_path, invoker, exec_required))

    return found


def _invoker_from_prev(tokens: list[str], i: int) -> str:
    if i == 0:
        return "direct"
    prev = os.path.basename(tokens[i - 1])
    if prev in INTERPRETERS:
        return "bash" if prev in {"bash", "sh", "zsh", "dash", "source", "."} else prev
    if prev in {"then", ";", "&&", "||", "|", "("}:
        return "direct"
    return "direct"


# ── per-entry verdict ────────────────────────────────────────────────────────


def _verdict(entry: Entry) -> None:
    reasons: list[str] = []

    # matcher dimension (Claude Code only; other harnesses have no doc contract)
    if entry.surface == "claude-settings":
        policy = MATCHER_POLICY.get(entry.event)
        m = entry.matcher or ""
        if policy is None:
            reasons.append(f"UNVERIFIABLE: event '{entry.event}' not in the documented event list")
            entry.status = UNVERIFIABLE
        elif m == "":
            pass  # empty matcher = match-all, valid on every event
        elif policy == "none":
            reasons.append(
                f"BROKEN: event '{entry.event}' takes no matcher, but one is set ({m!r})"
            )
        elif policy == "open":
            try:
                re.compile(m)
            except re.error as exc:
                reasons.append(f"BROKEN: matcher {m!r} is not a valid regex ({exc})")
        elif isinstance(policy, tuple):
            parts = [p for p in m.split("|") if p]
            bad = [p for p in parts if p not in policy]
            if bad:
                reasons.append(
                    f"BROKEN: matcher value(s) {bad} not in the documented "
                    f"enumeration for '{entry.event}' ({'|'.join(policy)})"
                )

    # path dimension
    if entry.target is None:
        reasons.append("UNVERIFIABLE: no script path could be resolved from this entry")
        entry.reasons = reasons
        entry.status = BROKEN if any(r.startswith("BROKEN") for r in reasons) else UNVERIFIABLE
        return

    p = Path(entry.abs_path or "")
    if p.is_symlink() and not p.exists():
        reasons.append(f"BROKEN: dangling symlink -> {os.readlink(p)}")
    elif not p.exists():
        reasons.append("BROKEN: path does not exist")
    elif p.is_dir():
        reasons.append("BROKEN: path is a directory, not a script")
    else:
        if entry.exec_required and not os.access(str(p), os.X_OK):
            reasons.append(
                "BROKEN: invoked without an interpreter (or guarded by `[ -x ]`) "
                "but the execute bit is not set"
            )
        if not os.access(str(p), os.R_OK):
            reasons.append("BROKEN: file is not readable")

    entry.reasons = reasons
    if any(r.startswith("BROKEN") for r in reasons):
        entry.status = BROKEN
    elif any(r.startswith("UNVERIFIABLE") for r in reasons):
        entry.status = UNVERIFIABLE
    else:
        entry.status = VALID


# ── surface parsers ──────────────────────────────────────────────────────────


def _entries_from_command(surface: str, event: str, matcher: str | None,
                          command: str, root: Path) -> list[Entry]:
    hits = _classify_command(command, root)
    if not hits:
        return [Entry(surface, event, matcher, command)]
    out = []
    for rel, abs_path, invoker, exec_required in hits:
        out.append(
            Entry(surface, event, matcher, command, rel, abs_path, invoker, exec_required)
        )
    return out


def parse_claude_settings(path: Path, root: Path) -> tuple[list[Entry], list[str]]:
    data = json.loads(path.read_text())
    entries: list[Entry] = []
    notes: list[str] = []
    if "hooks" not in data:
        raise NoRegistry("no 'hooks' key")
    hooks = data.get("hooks") or {}
    for event, groups in hooks.items():
        if not groups:
            notes.append(f"event '{event}' is declared with zero hook groups (dead key)")
            continue
        for group in groups:
            matcher = group.get("matcher", "")
            inner = group.get("hooks") or []
            if not inner:
                notes.append(
                    f"event '{event}' matcher {matcher!r} has a group with zero hooks"
                )
                continue
            for hook in inner:
                cmd = hook.get("command", "")
                if hook.get("type") != "command":
                    entries.append(
                        Entry("claude-settings", event, matcher, json.dumps(hook)[:200])
                    )
                    continue
                entries.extend(
                    _entries_from_command("claude-settings", event, matcher, cmd, root)
                )
    return entries, notes


def parse_cognitive_os_yaml(path: Path, root: Path) -> tuple[list[Entry], list[str]]:
    import yaml  # local import: the other surfaces do not need it

    data = yaml.safe_load(path.read_text()) or {}
    hooks = ((data.get("harness") or {}).get("hooks")) or {}
    entries: list[Entry] = []
    for name, spec in hooks.items():
        if not isinstance(spec, dict):
            entries.append(Entry("cognitive-os-yaml", str(name), None, repr(spec)[:200]))
            continue
        script = spec.get("script")
        event = str(spec.get("event") or "unknown")
        if not script:
            entries.append(Entry("cognitive-os-yaml", event, None, f"{name}: no script key"))
            continue
        rel, abs_path = _resolve(str(script), root)
        entries.append(
            Entry(
                "cognitive-os-yaml", event, None, f"{name}: {script}",
                rel, abs_path,
                # The yaml is a declarative registry: the drivers that read it
                # all spawn `bash <script>`, so the execute bit is not required.
                invoker="bash", exec_required=False,
            )
        )
    return entries, []


def parse_shell_gate_list(surface: str, path: Path, root: Path,
                          invoker: str) -> tuple[list[Entry], list[str]]:
    """Script literals inside a dispatcher. Comment lines are stripped first.

    Stripping matters: this repo has already published a false 'present' by
    substring-matching a file whose own header NAMES the hook it was looking for.
    """
    entries: list[Entry] = []
    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        if re.match(r"\s*(#|//|\*)", line):
            continue
        for m in re.finditer(r'"((?:\$\{?[A-Za-z_][A-Za-z0-9_]*\}?/)?hooks/[A-Za-z0-9_.\-]+\.sh)"',
                             line):
            rel, abs_path = _resolve(m.group(1), root)
            entries.append(
                Entry(surface, "dispatch", None, f"{path.name}:{lineno}: {m.group(1)}",
                      rel, abs_path, invoker=invoker, exec_required=False)
            )
    # dedupe on target, keeping the first site
    seen: set[str] = set()
    uniq: list[Entry] = []
    for e in entries:
        key = e.target or e.raw
        if key in seen:
            continue
        seen.add(key)
        uniq.append(e)
    return uniq, []


def parse_cursor(path: Path, root: Path) -> tuple[list[Entry], list[str]]:
    data = json.loads(path.read_text())
    entries: list[Entry] = []
    for event, items in (data.get("hooks") or {}).items():
        if not items:
            continue
        for item in items:
            cmd = item.get("command", "")
            if not cmd:
                continue
            entries.extend(_entries_from_command("cursor", event, None, cmd, root))
    return entries, []


def parse_codex(path: Path, root: Path) -> tuple[list[Entry], list[str]]:
    data = json.loads(path.read_text())
    entries: list[Entry] = []
    for event, groups in (data.get("hooks") or {}).items():
        for group in groups or []:
            for hook in group.get("hooks") or []:
                cmd = hook.get("command", "")
                if not cmd:
                    continue
                entries.extend(_entries_from_command("codex", event, None, cmd, root))
    return entries, []


def parse_opencode(path: Path, root: Path) -> tuple[list[Entry], list[str]]:
    data = json.loads(path.read_text())
    entries: list[Entry] = []
    for event, items in (data.get("events") or {}).items():
        for item in items or []:
            script = item.get("script")
            if not script:
                entries.append(Entry("opencode", event, item.get("matcher"),
                                     json.dumps(item)[:200]))
                continue
            rel, abs_path = _resolve(str(script), root)
            entries.append(
                Entry("opencode", event, item.get("matcher"), f"{item.get('id')}: {script}",
                      rel, abs_path,
                      # .opencode/plugins/cos-primitive-guard.js:168
                      #   spawn("bash", [scriptPath], ...)
                      invoker="bash", exec_required=False)
            )
    return entries, []


def parse_opencode_plugin(path: Path, root: Path) -> tuple[list[Entry], list[str]]:
    entries: list[Entry] = []
    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        if re.match(r"\s*(//|\*|/\*)", line):
            continue
        for m in re.finditer(r'"(hooks/[A-Za-z0-9_.\-]+\.sh)"', line):
            rel, abs_path = _resolve(m.group(1), root)
            entries.append(
                Entry("opencode-plugin", "classifier-map", None,
                      f"{path.name}:{lineno}: {m.group(1)}",
                      rel, abs_path, invoker="bash", exec_required=False)
            )
    seen: set[str] = set()
    uniq: list[Entry] = []
    for e in entries:
        if e.target in seen:
            continue
        seen.add(e.target or e.raw)
        uniq.append(e)
    return uniq, []


def parse_package_exports(path: Path, root: Path) -> tuple[list[Entry], list[str]]:
    """packages/<pkg>/cos-package.yaml > exports[] with type: hook.

    The entry carries its own hook_event/hook_matcher, so both dimensions of the
    check apply here, not just the path one.

    WHICH ROOT `source` IS RELATIVE TO IS NOT DECIDABLE FROM THE CODE. Measured
    2026-08-21, nothing reads the field:

        grep -rn "exports" scripts/ cos_lib/ --include='*.py' | grep -i package
        # only the audit scripts themselves

    So the resolution rule here is deliberately generous: the package directory
    first, then the repo root, and BROKEN only when the file is under NEITHER.
    Picking one root and reporting the other's hits as dead would manufacture
    reds out of an ambiguity this checker has no standing to resolve -- and a
    gate that cries wolf about a convention nobody enforces gets switched off
    before it ever reports the one entry that is genuinely dangling.
    """
    import yaml

    data = yaml.safe_load(path.read_text()) or {}
    exports = data.get("exports") or []
    if not isinstance(exports, list):
        raise NoRegistry("exports is not a list")
    pkg_dir = path.parent
    entries: list[Entry] = []
    for exp in exports:
        if not isinstance(exp, dict) or exp.get("type") != "hook":
            continue
        source = exp.get("source")
        event = str(exp.get("hook_event") or "unknown")
        matcher = exp.get("hook_matcher")
        label = f"{pkg_dir.name}: {source}"
        if not source:
            entries.append(Entry("package-exports", event, matcher, label))
            continue
        rel, abs_path = _resolve(str(source), pkg_dir)
        if abs_path and not Path(abs_path).exists():
            alt_rel, alt_abs = _resolve(str(source), root)
            if alt_abs and Path(alt_abs).exists():
                rel, abs_path = alt_rel, alt_abs
                label += "  (resolved at repo root, not under the package)"
        if abs_path:  # always display repo-relative, whichever root won
            rel = os.path.relpath(abs_path, str(root))
        entries.append(
            Entry("package-exports", event, matcher, label, rel, abs_path,
                  invoker="bash", exec_required=False)
        )
    if not entries:
        raise NoRegistry("no exports of type: hook")
    return entries, []


def parse_package_exports_all(_path: Path, root: Path) -> tuple[list[Entry], list[str]]:
    entries: list[Entry] = []
    notes: list[str] = []
    files = sorted((root / "packages").glob("*/cos-package.yaml"))
    if not files:
        raise NoRegistry("no packages/*/cos-package.yaml")
    declaring = 0
    for f in files:
        try:
            found, n = parse_package_exports(f, root)
        except NoRegistry:
            continue
        declaring += 1
        entries.extend(found)
        notes.extend(n)
    if not declaring:
        raise NoRegistry(f"{len(files)} package manifests, none exports a hook")
    notes.append(f"{declaring}/{len(files)} package manifests export hooks")
    return entries, notes


SURFACES: list[tuple[str, str, object]] = [
    ("claude-settings", ".claude/settings.json", parse_claude_settings),
    ("claude-settings-local", ".claude/settings.local.json", parse_claude_settings),
    ("package-exports", "packages", parse_package_exports_all),
    ("cognitive-os-yaml", "cognitive-os.yaml", parse_cognitive_os_yaml),
    ("bash-hot-path-dispatcher", "hooks/bash-hot-path-dispatcher.sh",
     lambda p, r: parse_shell_gate_list("bash-hot-path-dispatcher", p, r, "bash")),
    ("cursor", ".cursor/hooks.json", parse_cursor),
    ("codex", ".codex/hooks.json", parse_codex),
    ("opencode", ".opencode/cos-hooks.json", parse_opencode),
    ("opencode-plugin", ".opencode/plugins/cos-primitive-guard.js", parse_opencode_plugin),
]


# ── driver ───────────────────────────────────────────────────────────────────


def audit(root: Path) -> dict:
    entries: list[Entry] = []
    surface_report: dict[str, dict] = {}
    notes: list[str] = []
    empty_surfaces: list[str] = []

    for name, rel, parser in SURFACES:
        path = root / rel
        if not path.exists():
            surface_report[name] = {"path": rel, "state": "ABSENT", "entries": 0}
            continue
        try:
            found, surface_notes = parser(path, root)  # type: ignore[operator]
        except NoRegistry as exc:
            surface_report[name] = {
                "path": rel, "state": "NO-REGISTRY", "entries": 0, "error": str(exc),
            }
            continue
        except Exception as exc:  # noqa: BLE001
            surface_report[name] = {
                "path": rel, "state": "UNPARSED", "entries": 0, "error": f"{type(exc).__name__}: {exc}",
            }
            empty_surfaces.append(f"{name} ({rel}): parser raised {type(exc).__name__}: {exc}")
            continue
        notes.extend(f"{name}: {n}" for n in surface_notes)
        if not found:
            surface_report[name] = {"path": rel, "state": "PARSER-EMPTY", "entries": 0}
            empty_surfaces.append(f"{name} ({rel}): file present, parser found zero entries")
            continue
        for e in found:
            _verdict(e)
        entries.extend(found)
        surface_report[name] = {
            "path": rel,
            "state": "PARSED",
            "entries": len(found),
            "valid": sum(1 for e in found if e.status == VALID),
            "broken": sum(1 for e in found if e.status == BROKEN),
            "unverifiable": sum(1 for e in found if e.status == UNVERIFIABLE),
        }

    return {
        "root": str(root),
        "surfaces": surface_report,
        "notes": notes,
        "empty_surfaces": empty_surfaces,
        "entries": entries,
        "totals": {
            "entries": len(entries),
            "valid": sum(1 for e in entries if e.status == VALID),
            "broken": sum(1 for e in entries if e.status == BROKEN),
            "unverifiable": sum(1 for e in entries if e.status == UNVERIFIABLE),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parent.parent),
        help="project root (default: the repo this script lives in, not the cwd)",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="make UNVERIFIABLE entries set exit 1 as well",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"audit_registration_reverse: ERROR: no such root: {root}", file=sys.stderr)
        return 2

    try:
        report = audit(root)
    except Exception as exc:  # noqa: BLE001
        print(f"audit_registration_reverse: ERROR: {exc}", file=sys.stderr)
        return 2

    totals = report["totals"]
    entries: list[Entry] = report["entries"]
    broken = [e for e in entries if e.status == BROKEN]
    unver = [e for e in entries if e.status == UNVERIFIABLE]

    # ── anti-vacuum guards, evaluated before any green is printed ────────────
    vacuum: list[str] = []
    if totals["entries"] == 0:
        vacuum.append("zero registration entries found across every surface")
    if totals["valid"] == 0 and totals["entries"] > 0:
        vacuum.append("zero entries could be positively verified (parser degenerated)")
    vacuum.extend(report["empty_surfaces"])

    if args.json:
        print(json.dumps({
            "root": report["root"],
            "surfaces": report["surfaces"],
            "totals": totals,
            "vacuum_guard": vacuum,
            "notes": report["notes"],
            "broken": [e.as_dict() for e in broken],
            "unverifiable": [e.as_dict() for e in unver],
        }, indent=2, sort_keys=True))
        if vacuum:
            return 2
        if broken or (args.strict and unver):
            return 1
        return 0

    print("=== REGISTRATION AUDIT, REVERSE DIRECTION (entry -> component) ===")
    print(f"root: {report['root']}")
    for name, info in report["surfaces"].items():
        line = f"  {name:26} {info['state']:13} {info['entries']:4} entries  {info['path']}"
        if info["state"] == "PARSED":
            line += f"   [ok {info['valid']} / broken {info['broken']} / unverifiable {info['unverifiable']}]"
        if info.get("error"):
            line += f"   {info['error']}"
        print(line)
    print(
        f"\ntotals: {totals['entries']} entries  "
        f"VALID={totals['valid']}  BROKEN={totals['broken']}  "
        f"UNVERIFIABLE={totals['unverifiable']}"
    )

    if report["notes"]:
        print("\nNOTE - registration surfaces that declare nothing:")
        for n in report["notes"]:
            print(f"  . {n}")

    if unver:
        print("\nUNVERIFIABLE - not a pass; this checker could not resolve these:")
        for e in unver:
            print(f"  ? [{e.surface}/{e.event}] {e.raw}")
            for r in e.reasons:
                print(f"      {r}")

    if vacuum:
        print("\nFAIL (exit 2) - the checker could not honestly claim to have checked:")
        for v in vacuum:
            print(f"  !! {v}")
        return 2

    if broken:
        print("\nFAIL - registration entries that cannot run:")
        for e in broken:
            print(f"  X [{e.surface}/{e.event}] matcher={e.matcher!r}")
            print(f"      entry: {e.raw}")
            print(f"      target: {e.target}  (invoked via {e.invoker})")
            for r in e.reasons:
                print(f"      {r}")
        if args.strict and unver:
            print(f"\n--strict: {len(unver)} unverifiable entries also count as findings.")
        return 1

    if args.strict and unver:
        print(f"\nFAIL (--strict) - {len(unver)} unverifiable entries.")
        return 1

    print("\nOK: every resolvable registration entry points at a runnable script.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
