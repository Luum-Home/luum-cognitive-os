# SCOPE: os-only
"""hook_registration_audit — is a declared hook actually reachable, or an orphan?

WHY THIS EXISTS. `cognitive-os.yaml > harness.hooks` is the canonical hook
DECLARATION (ADR-064), but for the Claude Code harness it is not the
registration: `scripts/_lib/settings-driver-claude-code.sh` carries its registry
as shell literals and never reads the yaml (the sibling bare/codex/opencode
drivers do read it). The two lists are kept in step BY HAND, so a hook added
only to the yaml never reaches Claude Code and nothing reported it. The live
case that motivated this module is `hooks/publication-safety.sh`.

WHAT IT ASSERTS, AND WHAT IT DOES NOT. This audits the CLAUDE CODE lane only.
Codex, OpenCode and the bare runner derive their projections from the yaml
programmatically, so they cannot drift by hand the way this one does; their
coverage is reported as context (`harness_coverage`) and never fails the gate.

THE DECISION IT MAKES is not "is this hook on every surface" — no hook is on
every surface, and demanding that would turn every declared omission into a red
and guarantee the gate gets switched off. It is: **is its absence declared
somewhere?** A hook absent with `default_projection: false` is fine. A hook
absent with nothing saying so is `publication-safety`.

RELATIONSHIP TO `cos_lib/wiring_validator.py`. That module answers a different
and broader question (per-component structural triage over hooks, libs and
rules) with a three-boolean score. Its hook signals are structural presence
checks, not reachability, and it takes `cognitive-os.yaml` as the Claude
registration signal — which is exactly the premise this module exists to
refute. It is not a duplicate criterion: `WiringValidator.validate_hook` stays
the per-file triage used by editor-time advisories, and THIS module is the
authoritative orphan gate. See docs/06-Daily/reports/gate-registro-de-hooks-2026-08-19.md.
"""

from __future__ import annotations

import gzip
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

HOOK_PATH_RE = re.compile(r"hooks/([A-Za-z0-9._-]+)\.sh")
COMMENT_LINE_RE = re.compile(r"\s*#")

# Surfaces that make a hook REACHABLE under Claude Code. Absence from all of
# them is the precondition for an orphan verdict.
CLAUDE_REACHABILITY_SURFACES = (
    "driver-claude-code",
    "claude-settings",
    "hot-path-dispatcher",
    "security-profiles",
)

# Surfaces reported for context only. They are generated FROM the yaml by their
# own drivers, so a gap there is a harness capability question, not hand drift.
INFORMATIONAL_SURFACES = ("codex", "opencode", "bare-runner", "ai-primitives")


def _strip_shell_comments(text: str) -> str:
    """Drop whole-line shell comments.

    Not cosmetic: the Claude driver's own header NAMES publication-safety.sh
    while documenting that it is missing. A raw substring test counts that
    documentation as implementation and reports the orphan as present.
    """
    return "\n".join(l for l in text.splitlines() if not COMMENT_LINE_RE.match(l))


def _names_in_text(text: str) -> set[str]:
    return set(HOOK_PATH_RE.findall(text))


def _names_in_json(path: Path) -> set[str]:
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return set()
    found: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, str):
            found.update(HOOK_PATH_RE.findall(node))
        elif isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(data)
    return found


@dataclass
class HookVerdict:
    name: str
    script: str
    entries: list[str]
    surfaces: dict[str, bool]
    omissions: list[str] = field(default_factory=list)
    firings: int = 0
    inherited_from: str | None = None

    @property
    def reachable(self) -> bool:
        return any(self.surfaces.get(s) for s in CLAUDE_REACHABILITY_SURFACES)

    @property
    def claude_opt_out(self) -> bool:
        """True when a yaml entry declares this hook OFF the Claude projection."""
        return any(
            r.endswith("default_projection=false") or r.endswith("claude_projection=false")
            for r in self.omissions
        )

    @property
    def status(self) -> str:
        if self.reachable:
            # Declared off the Claude projection, yet wired on a Claude surface:
            # two declarations that disagree. A different defect from "nothing
            # declares it" -- reported, but not the blocking class, so that
            # fixing an orphan can actually turn the gate green.
            return "contradicted-omission" if self.claude_opt_out else "registered"
        if self.omissions:
            return "omission-declared"
        if self.firings > 0:
            return "unreachable-but-observed"
        return "orphan"


class HookRegistrationAudit:
    """Cross-references declared hooks against the surfaces that make them run."""

    def __init__(self, project_root: str | Path = ".") -> None:
        self.root = Path(project_root).resolve()

    # ── surface extraction ───────────────────────────────────────────────────

    def _read(self, rel: str) -> str:
        path = self.root / rel
        try:
            return path.read_text(errors="ignore")
        except OSError:
            return ""

    def declared(self) -> dict[str, dict[str, Any]]:
        """Hook name -> {script, entries: [(key, entry)]} from the canonical yaml.

        The yaml declares the same script under more than one entry, so the
        entry count is not the script count (202 entries, 192 scripts on the
        tree this was written against).
        """
        import yaml  # local import: keeps the module importable without PyYAML

        raw = self._read("cognitive-os.yaml")
        parsed = yaml.safe_load(raw) if raw else {}
        hooks = ((parsed or {}).get("harness") or {}).get("hooks") or {}
        out: dict[str, dict[str, Any]] = {}
        for key, entry in hooks.items():
            if not isinstance(entry, dict) or not entry.get("script"):
                continue
            name = Path(entry["script"]).stem
            slot = out.setdefault(name, {"script": entry["script"], "entries": []})
            slot["entries"].append((key, entry))
        return out

    def surfaces(self) -> dict[str, set[str]]:
        profiles: set[str] = set()
        profiles_dir = self.root / "templates" / "security-profiles"
        if profiles_dir.is_dir():
            for profile in sorted(profiles_dir.glob("*.json")):
                profiles |= _names_in_json(profile)

        ai_primitives: set[str] = set()
        primitives_dir = self.root / ".ai" / "primitives" / "hooks"
        if primitives_dir.is_dir():
            for prim in primitives_dir.glob("*.json"):
                try:
                    source = json.loads(prim.read_text()).get("source_id", "")
                except (OSError, ValueError):
                    continue
                if source.startswith("hooks/") and source.endswith(".sh"):
                    ai_primitives.add(Path(source).stem)

        return {
            "driver-claude-code": _names_in_text(
                _strip_shell_comments(self._read("scripts/_lib/settings-driver-claude-code.sh"))
            ),
            "claude-settings": _names_in_json(self.root / ".claude" / "settings.json"),
            "hot-path-dispatcher": _names_in_text(
                _strip_shell_comments(self._read("hooks/bash-hot-path-dispatcher.sh"))
            ),
            "security-profiles": profiles,
            "codex": _names_in_json(self.root / ".codex" / "hooks.json"),
            "opencode": _names_in_json(self.root / ".opencode" / "cos-hooks.json"),
            "bare-runner": _names_in_json(
                self.root / ".cognitive-os" / "cos-runner-hooks.json"
            ),
            "ai-primitives": ai_primitives,
        }

    # ── declared omission ────────────────────────────────────────────────────

    def excluded_hooks(self) -> dict[str, str]:
        """`tests/contracts/EXCLUDED_HOOKS.txt` — `<file.sh> | <reason>`."""
        out: dict[str, str] = {}
        for line in self._read("tests/contracts/EXCLUDED_HOOKS.txt").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "|" not in line:
                continue
            script, _, reason = line.partition("|")
            script = script.strip()
            if script.endswith(".sh"):
                out[Path(script).stem] = reason.strip()
        return out

    def omissions_for(self, name: str, entries: list[tuple[str, dict]], excluded: dict[str, str]) -> list[str]:
        """Every declared reason this hook may legitimately be off a surface.

        Five mechanisms live in the yaml itself, plus the excluded-hooks
        whitelist. Classifying by `default_projection` alone misreads most of
        them, which is how the count that hid the first error was produced.
        """
        reasons: list[str] = []
        for key, entry in entries:
            if entry.get("default_projection") is False:
                reasons.append(f"{key}: default_projection=false")
            if entry.get("claude_projection") is False:
                reasons.append(f"{key}: claude_projection=false")
            for harness in ("codex", "opencode", "bare"):
                value = entry.get(f"{harness}_projection")
                if value in (False, "gap", "partial"):
                    reasons.append(f"{key}: {harness}_projection={value}")
            if entry.get("profiles"):
                reasons.append(f"{key}: profiles={sorted(entry['profiles'])}")
            if entry.get("projection_note"):
                reasons.append(f"{key}: projection_note")
        if name in excluded:
            reasons.append(f"EXCLUDED_HOOKS.txt: {excluded[name]}")
        return reasons

    # ── firing evidence ──────────────────────────────────────────────────────

    def firings(self) -> dict[str, int]:
        """Hook -> rows in hook-timing, LIVE FILE PLUS ITS ROTATED ARCHIVES.

        Counting the live file alone produces false 'never fired' verdicts: it
        holds hours, not history. `hook-health.jsonl` is NOT usable for this —
        hooks with zero rows there have five figures of runs in the timing
        wrapper.
        """
        counts: dict[str, int] = {}
        metrics = self.root / ".cognitive-os" / "metrics"
        sources: list[tuple[Path, bool]] = []
        live = metrics / "hook-timing.jsonl"
        if live.exists():
            sources.append((live, False))
        archive = metrics / ".archive"
        if archive.is_dir():
            sources.extend((p, True) for p in sorted(archive.glob("hook-timing-*.jsonl.gz")))

        for path, gzipped in sources:
            try:
                opener = gzip.open(path, "rt", errors="ignore") if gzipped else path.open(errors="ignore")
                with opener as handle:
                    for line in handle:
                        if '"hook"' not in line:
                            continue
                        try:
                            hook = json.loads(line).get("hook")
                        except ValueError:
                            continue
                        if hook:
                            counts[hook] = counts.get(hook, 0) + 1
            except OSError:
                continue
        return counts

    # ── audit ────────────────────────────────────────────────────────────────

    def audit(self) -> dict[str, Any]:
        declared = self.declared()
        surfaces = self.surfaces()
        excluded = self.excluded_hooks()
        firings = self.firings()
        dispatcher_children = surfaces["hot-path-dispatcher"]
        dispatcher_runs = firings.get("bash-hot-path-dispatcher", 0)

        verdicts: list[HookVerdict] = []
        for name, slot in sorted(declared.items()):
            present = {label: name in names for label, names in surfaces.items()}
            observed = firings.get(name, 0)
            inherited = None
            # A dispatcher child has no telemetry of its own: it runs inside the
            # dispatcher's process. Zero rows is not zero runs.
            if observed == 0 and name in dispatcher_children and dispatcher_runs:
                observed = dispatcher_runs
                inherited = "bash-hot-path-dispatcher"
            verdicts.append(
                HookVerdict(
                    name=name,
                    script=slot["script"],
                    entries=[key for key, _ in slot["entries"]],
                    surfaces=present,
                    omissions=self.omissions_for(name, slot["entries"], excluded),
                    firings=observed,
                    inherited_from=inherited,
                )
            )

        by_status: dict[str, list[HookVerdict]] = {}
        for verdict in verdicts:
            by_status.setdefault(verdict.status, []).append(verdict)

        return {
            "declared_scripts": len(declared),
            "declared_entries": sum(len(s["entries"]) for s in declared.values()),
            "surface_totals": {label: len(names) for label, names in surfaces.items()},
            "harness_coverage": {
                label: sum(1 for n in declared if n in surfaces[label])
                for label in INFORMATIONAL_SURFACES
            },
            "verdicts": verdicts,
            "orphans": by_status.get("orphan", []),
            "contradicted_omission": by_status.get("contradicted-omission", []),
            "unreachable_but_observed": by_status.get("unreachable-but-observed", []),
            "omission_declared": by_status.get("omission-declared", []),
            "registered": by_status.get("registered", []),
        }
