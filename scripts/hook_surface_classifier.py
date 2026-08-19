# SCOPE: os-only
"""Classify every hooks/*.sh by DESTINATION, not by name.

Answers one question: of the shell hooks that exist on disk, which ones reach a
runtime path, by which mechanism, and which ones reach none at all.

Deliberately NOT a pruning tool. The output's last bucket (`unclassified`) is a
list of hooks with no discoverable projection path -- that is a finding to hand
to an operator, not a delete list. Telemetry is not consulted on purpose:
`.cognitive-os/metrics/hook-timing.jsonl` is rotated AND sampled, so absence
there proves nothing about whether a hook runs.

Mechanisms checked, in precedence order (a hook can match several; `buckets`
reports every match, `bucket` reports the first):

  registered        basename appears in .claude/settings.json hooks[]
  adr311_dispatch   referenced by hooks/bash-hot-path-dispatcher.sh (ADR-311
                    collapsed the PreToolUse:Bash mesh; these run WITHOUT a
                    settings.json entry)
  delegated         invoked from another hook/script/lib runtime file
  profile_gated     present in scripts/_lib/settings-driver-claude-code.sh or in
                    manifests/harness-hook-projection-policy.yaml under a profile
                    that is not the active one (typically `full`)
  other_harness     materialized in .codex/hooks.json or .opencode/cos-hooks.json
  omitted_reason    cognitive-os.yaml declares *_projection: false and/or a
                    projection_note explaining the omission
  unclassified      none of the above

Read-only. Exit codes: 0 = no unclassified hooks, 1 = unclassified hooks found,
2 = error.

Usage:
    .venv/bin/python scripts/hook_surface_classifier.py [--json] [--bucket NAME]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

SETTINGS = REPO / ".claude" / "settings.json"
YAML_CONFIG = REPO / "cognitive-os.yaml"
DISPATCHER = REPO / "hooks" / "bash-hot-path-dispatcher.sh"
CC_DRIVER = REPO / "scripts" / "_lib" / "settings-driver-claude-code.sh"
POLICY = REPO / "manifests" / "harness-hook-projection-policy.yaml"
ALLOWLIST = REPO / "hooks" / "_lib" / "registration-allowlist.txt"
CLASSIFICATION = REPO / "manifests" / "hook-registration-classification.yaml"
EXCLUDED = REPO / "tests" / "contracts" / "EXCLUDED_HOOKS.txt"
SECURITY_PROFILES = REPO / "templates" / "security-profiles"
CODEX_PROJ = REPO / ".codex" / "hooks.json"
OPENCODE_PROJ = REPO / ".opencode" / "cos-hooks.json"

SH_RE = re.compile(r"[A-Za-z0-9_.-]+\.sh")

# Runtime roots scanned for delegation (a hook invoked by another primitive).
# Tests are excluded here on purpose: a test referencing a hook is a consumer,
# not an invocation path, and is reported separately.
DELEGATION_ROOTS = ("hooks", "scripts", "lib", "cos_lib", "packages")

# A line only counts as delegation when it looks like it EXECUTES the hook.
# Naming a hook in a registry, a comment or a doc string is a mention, and a
# mention is exactly the weak evidence this audit exists to stop accepting.
# Files that LIST hooks for bookkeeping. Naming a hook here is the opposite of
# invoking it, so they must never count as callers or consumers.
REGISTRY_FILES = {
    "hooks/_lib/registration-allowlist.txt",
    "scripts/_lib/settings-driver-claude-code.sh",
    "manifests/harness-hook-projection-policy.yaml",
}

# `\bsh\b` is NOT usable here: `.` is a word boundary, so it matches the `sh`
# inside every `foo.sh`, and every comment mentioning one becomes an
# "invocation". Interpreters must appear as commands -- start of line, or after
# whitespace or a shell separator -- never as a filename suffix.
INVOKE_RE = re.compile(
    r"(?:(?:^|[\s;|&(`])(?:ba)?sh\s|(?:^|[\s;|&(`])exec\s|(?:^|[\s;|&(`])source\s"
    r"|^\s*\.\s|_run_gate|run_hook|subprocess|check_output|Popen"
    r"|\$\{?(?:HOOK_DIR|PROJECT_DIR|SCRIPT_DIR|CLAUDE_PROJECT_DIR))"
)
CONSUMER_ROOTS = ("tests", "docs", "manifests", "rules", "skills", "templates")

BUCKET_ORDER = [
    "registered",
    "adr311_dispatch",
    "profile_gated",
    "security_profile",
    "other_harness",
    "omitted_reason",
    "delegated",
    "unclassified",
]


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(2)


def sh_names(path: Path) -> set[str]:
    """Every `*.sh` basename mentioned in a file. Empty set if absent."""
    if not path.is_file():
        return set()
    return {m.split("/")[-1] for m in SH_RE.findall(path.read_text(errors="replace"))}


def inventory() -> tuple[list[str], dict[str, str]]:
    """Top-level hooks/*.sh basenames, plus basename -> resolved target.

    hooks/_lib/ and hooks/_archived/ are excluded: `_lib` holds sourced shell
    libraries (never registered, never registrable) and `_archived` holds .bak
    files. Counting either as "an unregistered hook" is the arithmetic that
    inflates the unregistered figure.
    """
    d = REPO / "hooks"
    if not d.is_dir():
        fail(f"missing {d}")
    names, resolved = [], {}
    for p in sorted(d.glob("*.sh")):
        names.append(p.name)
        resolved[p.name] = str(p.resolve())
    return names, resolved


def registered_names() -> set[str]:
    if not SETTINGS.is_file():
        fail(f"missing {SETTINGS}")
    try:
        data = json.loads(SETTINGS.read_text())
    except json.JSONDecodeError as exc:
        fail(f"{SETTINGS} is not valid JSON: {exc}")
    out: set[str] = set()
    for groups in (data.get("hooks") or {}).values():
        for group in groups:
            for hook in group.get("hooks") or []:
                for m in SH_RE.findall(hook.get("command") or ""):
                    out.add(m.split("/")[-1])
    return out


def yaml_declarations() -> dict[str, dict]:
    """basename -> declaration entry from cognitive-os.yaml > harness.hooks."""
    try:
        import yaml
    except ImportError:  # pragma: no cover - environment guard
        fail("PyYAML unavailable; run with .venv/bin/python")
    try:
        cfg = yaml.safe_load(YAML_CONFIG.read_text()) or {}
    except Exception as exc:  # noqa: BLE001
        fail(f"cannot parse {YAML_CONFIG}: {exc}")
    out: dict[str, dict] = {}
    for key, entry in ((cfg.get("harness") or {}).get("hooks") or {}).items():
        if not isinstance(entry, dict):
            continue
        script = entry.get("script")
        if script:
            out[str(script).split("/")[-1]] = {"key": key, **entry}
    return out


def policy_non_active_names(active_profile: str) -> set[str]:
    """Hook basenames declared only under a profile other than the active one."""
    if not POLICY.is_file():
        return set()
    try:
        import yaml

        pol = yaml.safe_load(POLICY.read_text()) or {}
    except Exception:  # noqa: BLE001
        return set()
    active: set[str] = set()
    other: set[str] = set()
    profiles = ((pol.get("harnesses") or {}).get("claude-code") or {}).get("profiles") or {}
    for name, body in profiles.items():
        if not isinstance(body, dict):
            continue
        target = active if name == active_profile else other
        for hook in body.get("hooks") or []:
            for script in hook.get("scripts") or []:
                target.add(str(script).split("/")[-1])
    return other - active


def allowlisted() -> set[str]:
    """Hook basenames on the ratchet of intentionally-unregistered hooks.

    hooks/_lib/registration-allowlist.txt is the project's own written answer to
    "why is this hook not registered". Its header states the list can only
    shrink as hooks get wired, which makes stale entries measurable -- see
    `ratchet` in the report.
    """
    if not ALLOWLIST.is_file():
        return set()
    out = set()
    for line in ALLOWLIST.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.add(line)
    return out


def classification_entries() -> set[str]:
    """Basenames covered by manifests/hook-registration-classification.yaml.

    That manifest's own contract line reads: "Every unregistered top-level hook
    must appear here with status, rationale, and next_action." It is therefore
    checkable, and `ledgers` in the report checks it.
    """
    if not CLASSIFICATION.is_file():
        return set()
    try:
        import yaml

        doc = yaml.safe_load(CLASSIFICATION.read_text()) or {}
    except Exception:  # noqa: BLE001
        return set()
    return {
        str(e.get("path", "")).split("/")[-1]
        for e in (doc.get("entries") or [])
        if e.get("path")
    }


def excluded_entries() -> set[str]:
    """Basenames in tests/contracts/EXCLUDED_HOOKS.txt (`<hook.sh> | <reason>`)."""
    if not EXCLUDED.is_file():
        return set()
    out = set()
    for line in EXCLUDED.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.add(line.split("|")[0].strip().split("/")[-1])
    return out


def security_profile_names() -> set[str]:
    """Hook basenames projected by any templates/security-profiles/*.json.

    A hook can reach a runtime path through a security profile without ever
    appearing in the checked-in .claude/settings.json.
    """
    out: set[str] = set()
    if not SECURITY_PROFILES.is_dir():
        return out
    for path in sorted(SECURITY_PROFILES.glob("*.json")):
        out |= sh_names(path)
    return out


def active_profile() -> str:
    try:
        import yaml

        cfg = yaml.safe_load(YAML_CONFIG.read_text()) or {}
    except Exception:  # noqa: BLE001
        return "default"
    prof = ((cfg.get("harness") or {}).get("profile")) or cfg.get("profile") or "default"
    # settings-driver-claude-code.sh maps default -> maintainer.
    return "maintainer" if str(prof) == "default" else str(prof)


def scan_refs(
    names: set[str], roots: tuple[str, ...], invocation_only: bool = False
) -> dict[str, set[str]]:
    """basename -> set of tracked files under `roots` that mention it.

    A file mentioning its own basename is not a caller and is skipped.

    One `git ls-files` plus one pass per file with a single compiled alternation,
    instead of one subprocess (or one grep pattern) per hook.
    """
    if not names:
        return {}
    hits: dict[str, set[str]] = {n: set() for n in names}
    proc = subprocess.run(
        ["git", "ls-files", "--", *roots], cwd=REPO, capture_output=True, text=True
    )
    if proc.returncode != 0:
        fail(f"git ls-files failed: {proc.stderr.strip()}")
    pattern = re.compile("|".join(re.escape(n) for n in sorted(names)))
    for rel in proc.stdout.splitlines():
        if rel in REGISTRY_FILES:
            continue
        path = REPO / rel
        base = Path(rel).name
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 4_000_000:
                continue
            text = path.read_text(errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            for m in set(pattern.findall(line)):
                if m == base:
                    continue
                if invocation_only and not INVOKE_RE.search(line):
                    continue
                hits[m].add(rel)
    return hits


def classify() -> dict:
    names, resolved = inventory()
    reg = registered_names()
    decl = yaml_declarations()
    dispatch = sh_names(DISPATCHER)
    driver = sh_names(CC_DRIVER)
    codex = sh_names(CODEX_PROJ)
    opencode = sh_names(OPENCODE_PROJ)
    profile = active_profile()
    allow = allowlisted()
    classified = classification_entries()
    excluded = excluded_entries()
    secprof = security_profile_names()
    policy_other = policy_non_active_names(profile)

    unregistered = {n for n in names if n not in reg}
    delegation = scan_refs(unregistered, DELEGATION_ROOTS, invocation_only=True)
    consumers = scan_refs(unregistered, CONSUMER_ROOTS)

    rows = []
    for name in names:
        d = decl.get(name, {})
        omitted = bool(
            d.get("claude_projection") is False
            or d.get("default_projection") is False
            or d.get("projection_note")
            or name in allow
            or name in classified
            or name in excluded
        )
        # Delegation callers minus files that are themselves pure registries.
        callers = sorted(
            p
            for p in delegation.get(name, set())
            if not p.endswith(("settings-driver-claude-code.sh",))
        )
        flags = {
            "registered": name in reg,
            "adr311_dispatch": name in dispatch,
            "delegated": bool(callers),
            "profile_gated": (name in driver or name in policy_other) and name not in reg,
            "security_profile": name in secprof and name not in reg,
            "other_harness": name in codex or name in opencode,
            "omitted_reason": omitted,
        }
        matched = [b for b in BUCKET_ORDER[:-1] if flags[b]]
        rows.append(
            {
                "hook": name,
                "resolved": resolved[name],
                "declared_in_yaml": name in decl,
                "ledgers": sorted(
                    n
                    for n, member in (
                        ("registration-allowlist", name in allow),
                        ("hook-registration-classification", name in classified),
                        ("EXCLUDED_HOOKS", name in excluded),
                    )
                    if member
                ),
                "bucket": matched[0] if matched else "unclassified",
                "buckets": matched or ["unclassified"],
                "callers": callers[:8],
                "consumers": sorted(consumers.get(name, set()))[:8],
                "consumer_count": len(consumers.get(name, set())),
            }
        )

    # Ratchet health. The allowlist header promises it only shrinks; entries for
    # hooks that are now registered, or that have no file at all, are slack --
    # a suppressor suppressing nothing, which reads as coverage and is not.
    on_disk = set(names)
    ratchet = {
        "entries": len(allow),
        "stale_now_registered": sorted(allow & reg),
        "stale_no_file": sorted(allow - on_disk),
        "live": sorted(allow & (on_disk - reg)),
    }

    unreg_names = on_disk - reg
    ledgers = {
        "registration-allowlist": len(allow),
        "hook-registration-classification": len(classified),
        "EXCLUDED_HOOKS": len(excluded),
        "unregistered_in_no_ledger": sorted(unreg_names - allow - classified - excluded),
        "unregistered_in_all_three": len(unreg_names & allow & classified & excluded),
    }

    # Reachability under the CONFIGURATION THAT IS ACTIVE RIGHT NOW, which is a
    # different question from "has a destination". `profile_gated` and
    # `security_profile` hooks reach a runtime path only under a profile nobody
    # has selected; counting them as live is how surface gets justified.
    reach = {"active": [], "latent": [], "none": []}
    counts = {b: 0 for b in BUCKET_ORDER}
    for r in rows:
        counts[r["bucket"]] += 1
        if r["bucket"] in ("registered", "adr311_dispatch"):
            reach["active"].append(r["hook"])
        elif r["bucket"] == "unclassified":
            reach["none"].append(r["hook"])
        else:
            reach["latent"].append(r["hook"])
    return {
        "repo": str(REPO),
        "active_profile": profile,
        "totals": {
            "hooks_on_disk": len(names),
            "unique_targets": len(set(resolved.values())),
            "registered": sum(1 for r in rows if r["bucket"] == "registered"),
            "unregistered": len(names) - sum(1 for r in rows if r["bucket"] == "registered"),
            "declared_in_yaml": sum(1 for r in rows if r["declared_in_yaml"]),
            "settings_entries": _settings_entry_count(),
        },
        "buckets": counts,
        "ratchet": ratchet,
        "ledgers": ledgers,
        "reachability": {k: sorted(v) for k, v in reach.items()},
        "rows": rows,
    }


def _settings_entry_count() -> int:
    try:
        data = json.loads(SETTINGS.read_text())
    except Exception:  # noqa: BLE001
        return -1
    return sum(
        len(g.get("hooks") or []) for gs in (data.get("hooks") or {}).values() for g in gs
    )


def _findings_exit(report: dict) -> int:
    """1 when the audit has something an operator must look at, else 0."""
    has = report["buckets"].get("unclassified") or report["ledgers"][
        "unregistered_in_no_ledger"
    ]
    return 1 if has else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true", help="emit the full report as JSON")
    ap.add_argument("--bucket", help="print only the hook names in this bucket")
    args = ap.parse_args()

    report = classify()

    if args.bucket:
        for r in report["rows"]:
            if r["bucket"] == args.bucket:
                print(r["hook"])
        return _findings_exit(report)

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return _findings_exit(report)

    t = report["totals"]
    print(f"hooks/*.sh on disk        {t['hooks_on_disk']:>4}  "
          f"({t['unique_targets']} unique after readlink -f)")
    print(f"registered in settings    {t['registered']:>4}  "
          f"({t['settings_entries']} hook entries)")
    print(f"unregistered              {t['unregistered']:>4}")
    print(f"declared in cognitive-os  {t['declared_in_yaml']:>4}")
    print(f"active claude profile     {report['active_profile']:>4}")
    print()
    print(f"{'bucket':<20} {'count':>6}")
    print("-" * 27)
    for b in BUCKET_ORDER:
        print(f"{b:<20} {report['buckets'][b]:>6}")
    print("-" * 27)
    print(f"{'total':<20} {sum(report['buckets'].values()):>6}")

    rc = report["reachability"]
    print()
    print(f"reachable under the ACTIVE config   {len(rc['active']):>4}  "
          f"(settings.json + ADR-311 dispatcher)")
    print(f"latent: needs another profile       {len(rc['latent']):>4}  "
          f"(full / standard / paranoid, or documented off)")
    print(f"no destination found                {len(rc['none']):>4}")

    lg = report["ledgers"]
    print("\nwritten ledgers covering unregistered hooks:")
    for key in ("registration-allowlist", "hook-registration-classification", "EXCLUDED_HOOKS"):
        print(f"  {key:<36} {lg[key]:>4} entries")
    print(f"  {'in all three':<36} {lg['unregistered_in_all_three']:>4}")
    print(f"  {'unregistered in NO ledger':<36} {len(lg['unregistered_in_no_ledger']):>4}")

    rt = report["ratchet"]
    print(f"\nregistration-allowlist ratchet: {rt['entries']} entries -- "
          f"{len(rt['live'])} live, {len(rt['stale_now_registered'])} already registered, "
          f"{len(rt['stale_no_file'])} with no file on disk")
    if rt["stale_no_file"]:
        print("  no file on disk: " + ", ".join(rt["stale_no_file"]))

    if lg["unregistered_in_no_ledger"]:
        print("\nunregistered and in NO written ledger "
              f"({len(lg['unregistered_in_no_ledger'])}) -- breaches the contract line in "
              "manifests/hook-registration-classification.yaml:")
        for name in lg["unregistered_in_no_ledger"]:
            print(f"  {name}")

    unc = [r for r in report["rows"] if r["bucket"] == "unclassified"]
    if unc:
        print(f"\nunclassified ({len(unc)}) -- no projection path found. "
              f"NOT a prune list; hand to an operator.")
        for r in unc:
            print(f"  {r['hook']:<52} consumers={r['consumer_count']}")
    return 1 if (unc or lg["unregistered_in_no_ledger"]) else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
