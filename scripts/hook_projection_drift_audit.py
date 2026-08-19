#!/usr/bin/env python3
# SCOPE: os-only
"""Audit hooks declared in cognitive-os.yaml that never reach a harness.

WHY THIS EXISTS. `cognitive-os.yaml > harness.hooks` is the declared registry of
Cognitive OS hooks. Three of the four harness drivers read it. The Claude Code
driver does NOT: `scripts/_lib/settings-driver-claude-code.sh` carries the hook
list as shell literals and is kept in step with the yaml BY HAND. A hook added
only to the yaml is declared, documented, believed active -- and never runs.
Nothing reported it until this script.

The audit answers one question per (harness, declared entry):

  projected           the script reaches the harness artifact, directly or
                      through a registered dispatcher
  omitted-by-design   it does not, and something declares why (a projection
                      flag, the driver capability matrix, or a profile the
                      operator has not activated)
  lost                it does not, and nothing declares why  <-- the finding

WHAT IT DOES NOT DO. It never re-derives what a driver *would* emit. The
on-disk artifacts are the drivers' own output and `derived_artifact_gate.py`
already keeps them in sync, so the artifact IS the projection. This script only
explains the absences, and it takes every explanation from a declared source:
the yaml flags, `manifests/harness-driver-capabilities.yaml`,
`manifests/harness-hook-projection-policy.yaml`, and two constants read live out
of `settings-driver-codex.sh` / `settings-driver-opencode.sh` rather than copied
here (a copy would drift the same way the registry did).

TRAPS THIS SCRIPT WAS BUILT AROUND, all of them hit while writing it:

  - The yaml declares the same script under more than one entry: 200 entries,
    190 distinct scripts. Counting entries is not counting scripts, and the
    unit of the verdict is the ENTRY, because one script can be projected for
    one event and lost for another.
  - A substring test against a driver file counts its COMMENTS as
    implementation. The header of settings-driver-claude-code.sh names
    publication-safety.sh while documenting its absence, which turns the very
    hook being hunted into a false positive. Comment lines are stripped.
  - A hook absent from settings.json may still run: 27 of the 36 Claude
    absences are dispatched by hooks/bash-hot-path-dispatcher.sh. Ignoring the
    dispatcher inflates the finding sevenfold.
  - An empty metrics file does not prove a hook never fired -- the logger could
    be dead. `--with-telemetry` reports the fire count of a KNOWN-LIVE hook
    alongside the zeros, so the zeros mean something.

Read-only. Never writes. Exit 0 = no lost entries, 1 = lost entries found,
2 = error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

CONFIG_REL = "cognitive-os.yaml"
CAPABILITIES_REL = "manifests/harness-driver-capabilities.yaml"
POLICY_REL = "manifests/harness-hook-projection-policy.yaml"

# Harness id -> (hook artifact, driver source, policy key in the projection
# policy manifest).
#
# The artifact is the file that carries the HOOK LIST, which for opencode is not
# `drivers.opencode.settings_path`: that manifest field points at opencode.json,
# the harness config, whose only hook content is the pointer
# `experimental.cognitive_os_hooks -> .opencode/cos-hooks.json`. Trusting the
# manifest field here made the audit read a file with zero hook scripts in it
# and abort. The capability matrix is authoritative for EVENTS, not for where
# the hooks are written.
HARNESSES: dict[str, dict[str, str]] = {
    "claude": {
        "artifact": ".claude/settings.json",
        "driver": "scripts/_lib/settings-driver-claude-code.sh",
        "policy_key": "claude-code",
    },
    "codex": {
        "artifact": ".codex/hooks.json",
        "driver": "scripts/_lib/settings-driver-codex.sh",
        "policy_key": "codex",
    },
    "opencode": {
        "artifact": ".opencode/cos-hooks.json",
        "driver": "scripts/_lib/settings-driver-opencode.sh",
        "policy_key": "opencode",
    },
}

# Per-harness yaml key that overrides `default_projection` for that harness.
PROJECTION_FLAG = {"claude": "claude_projection", "codex": "codex_projection", "opencode": "opencode_projection"}

# A hook whose basename matches this is treated as a fan-out point: the scripts
# it names in non-comment lines are reachable when the dispatcher is projected.
DISPATCHER_RE = re.compile(r"-dispatcher\.sh$")

SH_TOKEN_RE = re.compile(r"([A-Za-z0-9_.-]+\.sh)")
COMMENT_LINE_RE = re.compile(r"\s*#")

CLASS_PROJECTED = "projected"
CLASS_BY_DESIGN = "omitted-by-design"
CLASS_LOST = "lost"


class AuditError(RuntimeError):
    """Unrecoverable input problem: missing manifest, unparseable artifact."""


@dataclass(frozen=True)
class Verdict:
    harness: str
    entry: str
    script: str
    event: str
    matcher: str
    scope: str
    classification: str
    reason: str


@dataclass
class HarnessFacts:
    """Everything the classifier needs about one harness, all of it declared."""

    harness: str
    artifact: str
    projected: set[str] = field(default_factory=set)
    dispatched: set[str] = field(default_factory=set)
    unsupported_events: dict[str, str] = field(default_factory=dict)
    script_excluded_events: set[str] = field(default_factory=set)
    translatable_tool_names: set[str] = field(default_factory=set)
    tool_events: set[str] = field(default_factory=set)
    active_profile: str = "unknown"
    inactive_profile_scripts: dict[str, str] = field(default_factory=dict)
    # True when the driver itself collapses the PreToolUse/Bash hot path to the
    # dispatcher outside PROFILE=full (ADR-311). Codex implements this in the
    # driver over the yaml; Claude Code implements it through the profile lists
    # in manifests/harness-hook-projection-policy.yaml, which is why only one of
    # the two needs this flag.
    bash_hot_path_collapsed: bool = False

    @property
    def reachable(self) -> set[str]:
        return self.projected | self.dispatched


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise AuditError(f"missing required manifest: {path}")
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:  # pragma: no cover - malformed manifest
        raise AuditError(f"cannot parse {path}: {exc}") from exc


def _read_json(path: Path) -> Any:
    if not path.is_file():
        raise AuditError(f"missing harness artifact: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AuditError(f"cannot parse {path}: {exc}") from exc


def _strip_comments(text: str) -> str:
    """Drop whole-line shell comments.

    Not cosmetic. The Claude driver documents the absence of
    publication-safety.sh by naming it, so a raw substring search reports the
    hook present on the strength of the paragraph explaining that it is not.
    """
    return "\n".join(line for line in text.splitlines() if not COMMENT_LINE_RE.match(line))


def _walk_strings(node: Any) -> Iterable[str]:
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for value in node.values():
            yield from _walk_strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk_strings(value)


def scripts_in_artifact(payload: Any) -> set[str]:
    """Collect hook basenames from a projected artifact, structurally.

    Walks the parsed JSON rather than grepping the file, so a script named
    inside a `description` or a disabled sibling key is still seen for what it
    is: a string in the document. JSON has no comments, which is why the
    comment-stripping applied to drivers is not needed here.
    """
    found: set[str] = set()
    for text in _walk_strings(payload):
        found.update(SH_TOKEN_RE.findall(text))
    return found


def dispatched_scripts(project_dir: Path, projected: set[str]) -> set[str]:
    """Expand one level of dispatcher indirection.

    A hook the harness never names can still run on every Bash call if a
    projected dispatcher calls it. Treating those as absent is the single
    largest source of false findings in this audit.
    """
    out: set[str] = set()
    for name in sorted(projected):
        if not DISPATCHER_RE.search(name):
            continue
        path = project_dir / "hooks" / name
        if not path.is_file():
            continue
        out.update(SH_TOKEN_RE.findall(_strip_comments(path.read_text(encoding="utf-8"))))
    return out - projected


def _driver_constant_set(driver_text: str, constant: str) -> set[str]:
    """Read a `NAME = {...}` python-literal set out of a driver's heredoc.

    The codex and opencode drivers embed their projection rules as Python
    constants. Copying them here would reintroduce exactly the hand-sync that
    this audit exists to catch, so they are parsed from the driver instead and
    the pairing is asserted in the portability proof.
    """
    match = re.search(rf"^{re.escape(constant)}\s*=\s*\{{(.*?)\}}", driver_text, re.MULTILINE | re.DOTALL)
    if not match:
        return set()
    return set(re.findall(r"[\"']([^\"']+)[\"']", match.group(1)))


def _driver_translation_keys(driver_text: str) -> set[str]:
    match = re.search(r"^TOOL_NAME_TRANSLATION\s*=\s*\{(.*?)\n\}", driver_text, re.MULTILINE | re.DOTALL)
    if not match:
        return set()
    return set(re.findall(r"^\s*[\"']([^\"']+)[\"']\s*:", match.group(1), re.MULTILINE))


def _opencode_event_map(driver_text: str) -> dict[str, str]:
    match = re.search(r"^COS_TO_OPENCODE_EVENT\s*=\s*\{(.*?)\n\}", driver_text, re.MULTILINE | re.DOTALL)
    if not match:
        return {}
    return dict(re.findall(r"[\"']([^\"']+)[\"']\s*:\s*[\"']([^\"']+)[\"']", match.group(1)))


def build_harness_facts(project_dir: Path, harness: str) -> HarnessFacts:
    spec = HARNESSES[harness]
    capabilities = _read_yaml(project_dir / CAPABILITIES_REL)
    driver_cfg = (capabilities.get("drivers") or {}).get(harness) or {}
    artifact_rel = spec["artifact"]

    facts = HarnessFacts(harness=harness, artifact=artifact_rel)
    facts.projected = scripts_in_artifact(_read_json(project_dir / artifact_rel))
    facts.dispatched = dispatched_scripts(project_dir, facts.projected)

    for event, meta in (driver_cfg.get("supported_events") or {}).items():
        if not isinstance(meta, dict):
            continue
        status = meta.get("status")
        if status == "unsupported":
            facts.unsupported_events[str(event)] = f"{harness} driver marks {event} unsupported"
        elif status == "cognitive_os_extension" and meta.get("projection"):
            # A COS-only lifecycle event the harness never emits natively. The
            # manifest names the substitute path, so the absence is answered.
            facts.unsupported_events[str(event)] = (
                f"{event} is a Cognitive OS extension; {harness} projection is {meta['projection']!r}"
            )

    driver_path = project_dir / spec["driver"]
    driver_text = driver_path.read_text(encoding="utf-8") if driver_path.is_file() else ""
    if harness == "codex":
        facts.tool_events = _driver_constant_set(driver_text, "TOOL_EVENTS")
        facts.translatable_tool_names = _driver_translation_keys(driver_text)
        facts.bash_hot_path_collapsed = (
            'profile != "full"' in driver_text and "bash-hot-path-dispatcher.sh" in _strip_comments(driver_text)
        )
    elif harness == "opencode":
        excluded = _driver_constant_set(driver_text, "SCRIPT_PROJECTION_EXCLUDED_EVENTS")
        reverse = {v: k for k, v in _opencode_event_map(driver_text).items()}
        facts.script_excluded_events = {reverse[e] for e in excluded if e in reverse}
        supported = set(_opencode_event_map(driver_text))
        declared = {str(e) for e in (driver_cfg.get("supported_events") or {})}
        for event in sorted(declared - supported):
            facts.unsupported_events.setdefault(event, f"{event} is absent from the opencode driver event map")

    _load_profiles(project_dir, spec["policy_key"], facts)
    return facts


def _load_profiles(project_dir: Path, policy_key: str, facts: HarnessFacts) -> None:
    """Record scripts a profile would project that the ACTIVE profile does not.

    The projection policy is a real declaration of intent, so a hook listed only
    in an inactive profile is not drift -- but it is not running either, which
    is why it gets its own reason code instead of being folded into silence.
    """
    policy = _read_yaml(project_dir / POLICY_REL)
    profiles = ((policy.get("harnesses") or {}).get(policy_key) or {}).get("profiles") or {}
    resolved: dict[str, set[str]] = {}
    for name, body in profiles.items():
        if not isinstance(body, dict):
            continue
        target = body
        alias = body.get("alias_of")
        if alias and isinstance(profiles.get(alias), dict):
            target = profiles[alias]
        names: set[str] = set()
        for group in target.get("hooks") or []:
            for script in (group or {}).get("scripts") or []:
                names.add(Path(str(script)).name)
        resolved[str(name)] = names

    # Several profiles can resolve to the same script set (core, default,
    # maintainer and team all collapse to the dispatcher today). Naming one of
    # them arbitrarily would read as a measurement; naming all of them says what
    # was actually observed. The classification is unaffected either way, since
    # the tied profiles project the same scripts.
    matched = sorted(name for name, names in resolved.items() if names and names <= facts.reachable)
    if matched:
        facts.active_profile = "|".join(matched)
    active: set[str] = set()
    for name in matched:
        active |= resolved[name]
    for name, names in sorted(resolved.items()):
        if name in matched:
            continue
        for script in sorted(names - active):
            facts.inactive_profile_scripts.setdefault(script, name)


def declared_entries(project_dir: Path) -> dict[str, dict[str, Any]]:
    config = _read_yaml(project_dir / CONFIG_REL)
    hooks = ((config.get("harness") or {}).get("hooks")) or {}
    out: dict[str, dict[str, Any]] = {}
    for key, entry in hooks.items():
        if isinstance(entry, dict) and entry.get("script") and entry.get("event"):
            out[str(key)] = entry
    return out


def classify(entry_key: str, entry: dict[str, Any], facts: HarnessFacts) -> Verdict:
    script = Path(str(entry["script"])).name
    event = str(entry.get("event") or "")
    matcher = str(entry.get("matcher") or "")

    def verdict(classification: str, reason: str) -> Verdict:
        return Verdict(
            harness=facts.harness,
            entry=entry_key,
            script=script,
            event=event,
            matcher=matcher,
            scope=str(entry.get("scope") or ""),
            classification=classification,
            reason=reason,
        )

    if script in facts.projected:
        return verdict(CLASS_PROJECTED, "named in artifact")
    if script in facts.dispatched:
        return verdict(CLASS_PROJECTED, "dispatched by a projected dispatcher")

    # Declared intent outranks inferred capability: an operator who wrote the
    # opt-out flag has already answered the question this audit asks.
    flag_key = PROJECTION_FLAG.get(facts.harness, "")
    if entry.get(flag_key) is False:
        return verdict(CLASS_BY_DESIGN, f"{flag_key}: false")
    if entry.get("default_projection") is False:
        return verdict(CLASS_BY_DESIGN, "default_projection: false")

    if event in facts.unsupported_events:
        return verdict(CLASS_BY_DESIGN, facts.unsupported_events[event])
    if event in facts.script_excluded_events:
        return verdict(CLASS_BY_DESIGN, f"{facts.harness} driver excludes script projection for {event}")
    if event in facts.tool_events and facts.translatable_tool_names:
        wanted = {name.strip() for name in matcher.split("|") if name.strip()}
        if not wanted & facts.translatable_tool_names:
            return verdict(CLASS_BY_DESIGN, f"matcher {matcher!r} has no {facts.harness} tool translation")

    # ADR-311 Bash hot path. Where the driver reads the yaml, PROFILE=full
    # projects every declared PreToolUse/Bash entry, so an absence under the
    # active profile is a profile choice and not drift. Where the driver does
    # NOT read the yaml (Claude Code), full membership is whatever the profile
    # manifest lists, and a hook missing from that list is missing everywhere --
    # which is why publication-safety.sh falls through to `lost` on Claude and
    # is answered here on Codex.
    if facts.bash_hot_path_collapsed and event == "PreToolUse" and "Bash" in matcher.split("|"):
        return verdict(
            CLASS_BY_DESIGN,
            f"Bash hot path collapsed to the dispatcher outside PROFILE=full ({facts.harness} driver, ADR-311)",
        )

    profile = facts.inactive_profile_scripts.get(script)
    if profile:
        return verdict(CLASS_BY_DESIGN, f"listed only in inactive profile {profile!r} (active: {facts.active_profile!r})")

    return verdict(CLASS_LOST, "declared active, absent from every projection path, nothing declares why")


def build_verdicts(project_dir: Path, harnesses: Iterable[str]) -> list[Verdict]:
    entries = declared_entries(project_dir)
    if not entries:
        raise AuditError(f"{CONFIG_REL} > harness.hooks declared no usable entries; the scan is broken, not clean")
    out: list[Verdict] = []
    for harness in harnesses:
        facts = build_harness_facts(project_dir, harness)
        if not facts.projected:
            raise AuditError(f"{facts.artifact} named no hook scripts; the scan is broken, not clean")
        for key in sorted(entries):
            out.append(classify(key, entries[key], facts))
    return out


def telemetry_counts(project_dir: Path, scripts: Iterable[str]) -> dict[str, Any]:
    """Fire counts for lost hooks plus a control that is known to fire.

    Zero rows for a hook prove nothing on their own -- the logger may be dead.
    The control line is what makes the zeros evidence.
    """
    path = project_dir / ".cognitive-os" / "metrics" / "hook-timing.jsonl"
    if not path.is_file():
        return {"available": False, "reason": f"{path} not found"}
    text = path.read_text(encoding="utf-8", errors="replace")
    rows = text.count("\n")
    counts = {name: text.count(name.removesuffix(".sh")) for name in sorted(set(scripts))}
    control = "bash-hot-path-dispatcher"
    return {
        "available": True,
        "rows": rows,
        "control_hook": control,
        "control_firings": text.count(control),
        "counts": counts,
    }


def summarize(verdicts: list[Verdict]) -> dict[str, Any]:
    per_harness: dict[str, dict[str, int]] = {}
    for verdict in verdicts:
        bucket = per_harness.setdefault(verdict.harness, {CLASS_PROJECTED: 0, CLASS_BY_DESIGN: 0, CLASS_LOST: 0})
        bucket[verdict.classification] += 1
    return per_harness


def render_text(verdicts: list[Verdict], telemetry: dict[str, Any] | None) -> str:
    lines = ["HOOK PROJECTION DRIFT AUDIT", ""]
    per_harness = summarize(verdicts)
    entries = len({v.entry for v in verdicts})
    scripts = len({v.script for v in verdicts})
    lines.append(f"declared: {entries} entries naming {scripts} distinct scripts")
    lines.append("")
    header = f"{'harness':<10} {'projected':>10} {'by-design':>10} {'LOST':>6}"
    lines.append(header)
    lines.append("-" * len(header))
    for harness in sorted(per_harness):
        counts = per_harness[harness]
        lines.append(
            f"{harness:<10} {counts[CLASS_PROJECTED]:>10} {counts[CLASS_BY_DESIGN]:>10} {counts[CLASS_LOST]:>6}"
        )
    lost = [v for v in verdicts if v.classification == CLASS_LOST]
    lines.append("")
    if lost:
        lines.append(f"LOST -- declared active and unreachable, with no declaration saying so ({len(lost)}):")
        for verdict in lost:
            matcher = f"[{verdict.matcher}]" if verdict.matcher else ""
            lines.append(f"  {verdict.harness:<9} {verdict.script:<42} {verdict.event}{matcher} scope={verdict.scope}")
    else:
        lines.append("LOST: none")

    by_design = [v for v in verdicts if v.classification == CLASS_BY_DESIGN]
    reasons: dict[str, int] = {}
    for verdict in by_design:
        reasons[verdict.reason] = reasons.get(verdict.reason, 0) + 1
    lines.append("")
    lines.append("omitted-by-design, by declared reason:")
    for reason, count in sorted(reasons.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"  {count:>4}  {reason}")

    if telemetry is not None:
        lines.append("")
        if not telemetry.get("available"):
            lines.append(f"telemetry: unavailable ({telemetry.get('reason')})")
        else:
            lines.append(
                f"telemetry: {telemetry['rows']} rows; control {telemetry['control_hook']} "
                f"fired {telemetry['control_firings']}x (logger is alive, so a zero below means zero)"
            )
            for name, count in telemetry["counts"].items():
                lines.append(f"  {count:>6}  {name}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project-dir", default=str(REPO_ROOT), help="repository root to audit (default: this repo)")
    parser.add_argument(
        "--harness",
        action="append",
        choices=sorted(HARNESSES),
        help="restrict to one harness; repeatable (default: all)",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    parser.add_argument("--with-telemetry", action="store_true", help="report hook-timing fire counts for lost hooks")
    args = parser.parse_args(argv)

    project_dir = Path(args.project_dir).resolve()
    harnesses = args.harness or sorted(HARNESSES)
    try:
        verdicts = build_verdicts(project_dir, harnesses)
    except AuditError as exc:
        print(f"hook-projection-drift-audit: {exc}", file=sys.stderr)
        return 2

    lost = [v for v in verdicts if v.classification == CLASS_LOST]
    telemetry = telemetry_counts(project_dir, [v.script for v in lost]) if args.with_telemetry else None

    if args.json:
        print(
            json.dumps(
                {
                    "summary": summarize(verdicts),
                    "declared_entries": len({v.entry for v in verdicts}),
                    "declared_scripts": len({v.script for v in verdicts}),
                    "lost": [vars(v) for v in lost],
                    "verdicts": [vars(v) for v in verdicts],
                    "telemetry": telemetry,
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(render_text(verdicts, telemetry), end="")
    return 1 if lost else 0


if __name__ == "__main__":
    sys.exit(main())
