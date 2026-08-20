#!/usr/bin/env python3
# SCOPE: os-only
"""Census of the surfaces a hook must appear in, and of where they disagree.

WHY THIS EXISTS, given two audits already run. `hook_projection_drift_audit.py`
walks the registry DOWNWARD (declared in cognitive-os.yaml -> does it reach a
harness artifact?). `hook_surface_classifier.py` walks the disk UPWARD (a
hooks/*.sh exists -> which mechanism, if any, projects it?). Neither one
compares its verdict with the other's, and on HEAD 2026-08-20 they contradict
each other on five entries: the drift audit calls them `lost` (nothing declares
the absence) while the classifier calls them `profile_gated` (something does).
Both cannot be right. This script is the third question -- WHO NAMES THIS HOOK,
SURFACE BY SURFACE -- which is the only way to settle it without trusting
either verdict.

What it reports:

  surfaces      per hook, the registration surfaces that name it, with the
                driver checked on COMMENT-STRIPPED text (the driver header
                documents absences by name; a raw substring test turns that
                documentation into evidence of registration -- this is the trap
                that produced the contradiction above)
  ledgers       the three-way overlap of the "intentionally unregistered"
                ledgers (registration-allowlist.txt,
                hook-registration-classification.yaml, EXCLUDED_HOOKS.txt).
                A hook carrying three independently written reasons is three
                places to update and three places to go stale
  disagreements entries where the two existing audits reach opposite verdicts,
                each annotated with the surfaces that actually name the hook

ENV. `COS_ALLOW_PROTECTED_CONFIG_WRITE` is popped from the environment of the
child audits on purpose: it is inherited, and a measurement taken with a write
permission the normal caller does not have is not the measurement anyone else
will reproduce.

Read-only. Never writes. Exit 0 = no disagreements, 1 = disagreements found,
2 = error.

Usage:
    .venv/bin/python scripts/hook_surface_census.py [--json] [--hook NAME]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

CONFIG = REPO / "cognitive-os.yaml"
CC_DRIVER = REPO / "scripts/_lib/settings-driver-claude-code.sh"
CC_SETTINGS = REPO / ".claude/settings.json"
CODEX_ARTIFACT = REPO / ".codex/hooks.json"
OPENCODE_ARTIFACT = REPO / ".opencode/cos-hooks.json"
DISPATCHER = REPO / "hooks/bash-hot-path-dispatcher.sh"
POLICY = REPO / "manifests/harness-hook-projection-policy.yaml"
ALLOWLIST = REPO / "hooks/_lib/registration-allowlist.txt"
CLASSIFICATION = REPO / "manifests/hook-registration-classification.yaml"
EXCLUDED = REPO / "tests/contracts/EXCLUDED_HOOKS.txt"
SEC_PROFILES = REPO / "templates/security-profiles"

DRIFT_AUDIT = REPO / "scripts/hook_projection_drift_audit.py"
CLASSIFIER = REPO / "scripts/hook_surface_classifier.py"


def fail(msg: str) -> int:
    print(f"ERROR: {msg}", file=sys.stderr)
    return 2


def strip_comments(text: str) -> str:
    return "\n".join(l for l in text.splitlines() if not re.match(r"\s*#", l))


def names_in(path: Path, *, strip: bool = False) -> str:
    if not path.is_file():
        return ""
    text = path.read_text(errors="replace")
    return strip_comments(text) if strip else text


def ledger_names(path: Path) -> set[str]:
    """Basenames in a `<hook.sh> | <reason>` or bare-line ledger."""
    if not path.is_file():
        return set()
    out = set()
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.add(line.split("|")[0].strip().split("/")[-1])
    return out


def classification_names() -> set[str]:
    if not CLASSIFICATION.is_file():
        return set()
    import yaml

    doc = yaml.safe_load(CLASSIFICATION.read_text()) or {}
    return {
        str(e.get("path", "")).split("/")[-1]
        for e in (doc.get("entries") or [])
        if e.get("path")
    }


def security_profile_names() -> set[str]:
    out: set[str] = set()
    if not SEC_PROFILES.is_dir():
        return out
    for f in SEC_PROFILES.glob("*.json"):
        for m in re.finditer(r"hooks/([A-Za-z0-9._-]+\.sh)", f.read_text()):
            out.add(m.group(1))
    return out


def declared() -> dict[str, dict]:
    import yaml

    hooks = (yaml.safe_load(CONFIG.read_text()) or {}).get("harness", {}).get("hooks", {})
    out = {}
    for key, entry in hooks.items():
        if not isinstance(entry, dict):
            continue
        script = entry.get("script")
        if script:
            out.setdefault(str(script).split("/")[-1], {"keys": [], **entry})["keys"].append(key)
    return out


def run_audit(script: Path) -> dict:
    env = dict(os.environ)
    # Inherited write permission would change what the child is allowed to do.
    env.pop("COS_ALLOW_PROTECTED_CONFIG_WRITE", None)
    proc = subprocess.run(
        [sys.executable, str(script), "--json"],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if not proc.stdout.strip():
        raise RuntimeError(f"{script.name} produced no JSON (exit {proc.returncode})")
    return json.loads(proc.stdout)


def census() -> dict:
    decl = declared()
    driver_code = names_in(CC_DRIVER, strip=True)
    driver_raw = names_in(CC_DRIVER)
    settings = names_in(CC_SETTINGS)
    codex = names_in(CODEX_ARTIFACT)
    opencode = names_in(OPENCODE_ARTIFACT)
    dispatcher = names_in(DISPATCHER, strip=True)
    policy = names_in(POLICY, strip=True)
    allow = ledger_names(ALLOWLIST)
    classif = classification_names()
    excl = ledger_names(EXCLUDED)
    secprof = security_profile_names()

    on_disk = sorted(p.name for p in (REPO / "hooks").glob("*.sh"))
    universe = sorted(set(on_disk) | set(decl))

    rows = {}
    for name in universe:
        entry = decl.get(name, {})
        rows[name] = {
            "yaml_registry": name in decl,
            "cc_driver_code": name in driver_code,
            "cc_driver_comment_only": (name in driver_raw) and (name not in driver_code),
            "claude_settings": name in settings,
            "codex_artifact": name in codex,
            "opencode_artifact": name in opencode,
            "dispatcher": name in dispatcher,
            "projection_policy": name in policy,
            "security_profiles": name in secprof,
            "ledger_allowlist": name in allow,
            "ledger_classification": name in classif,
            "ledger_excluded": name in excl,
            "yaml_flags": {
                k: v
                for k, v in entry.items()
                if k
                in (
                    "default_projection",
                    "claude_projection",
                    "codex_projection",
                    "opencode_projection",
                    "projection_note",
                    "profiles",
                )
            },
        }

    drift = run_audit(DRIFT_AUDIT)
    cls = run_audit(CLASSIFIER)
    cls_bucket = {r["hook"]: r["bucket"] for r in cls.get("rows", [])}

    disagreements = []
    for lost in drift.get("lost", []):
        name = str(lost["script"]).split("/")[-1]
        bucket = cls_bucket.get(name)
        if bucket and bucket != "unclassified":
            surfaces = sorted(k for k, v in rows.get(name, {}).items() if v is True)
            disagreements.append(
                {
                    "hook": name,
                    "harness": lost["harness"],
                    "event": lost["event"],
                    "drift_audit": "lost",
                    "classifier": bucket,
                    "surfaces_naming_it": surfaces,
                }
            )

    return {
        "totals": {
            "hooks_on_disk": len(on_disk),
            "declared_scripts": len(decl),
            "universe": len(universe),
            "drift_lost": len(drift.get("lost", [])),
            "drift_summary": drift.get("summary", {}),
        },
        "ledgers": {
            "registration_allowlist": len(allow),
            "hook_registration_classification": len(classif),
            "excluded_hooks": len(excl),
            "in_all_three": len(allow & classif & excl),
            "allowlist_and_excluded": len(allow & excl),
            "allowlist_and_classification": len(allow & classif),
            "classification_and_excluded": len(classif & excl),
            "only_allowlist": len(allow - classif - excl),
            "only_classification": len(classif - allow - excl),
            "only_excluded": len(excl - allow - classif),
        },
        "disagreements": disagreements,
        "rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="emit the full report as JSON")
    ap.add_argument("--hook", help="report the surfaces naming a single hook basename")
    args = ap.parse_args()

    try:
        report = census()
    except Exception as exc:  # noqa: BLE001
        return fail(str(exc))

    if args.hook:
        row = report["rows"].get(args.hook)
        if row is None:
            return fail(f"unknown hook: {args.hook}")
        print(json.dumps({args.hook: row}, indent=2))
        return 0

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1 if report["disagreements"] else 0

    t = report["totals"]
    print(f"hooks on disk: {t['hooks_on_disk']}   declared scripts: {t['declared_scripts']}")
    print(f"drift audit lost entries: {t['drift_lost']}   summary: {json.dumps(t['drift_summary'])}")
    led = report["ledgers"]
    print(
        "unregistered ledgers: allowlist={registration_allowlist} classification="
        "{hook_registration_classification} excluded={excluded_hooks} "
        "in_all_three={in_all_three}".format(**led)
    )
    if not report["disagreements"]:
        print("no verdict disagreements between the drift audit and the surface classifier")
        return 0
    print(f"\nverdict disagreements ({len(report['disagreements'])}):")
    for d in report["disagreements"]:
        print(f"  {d['hook']}  drift=lost  classifier={d['classifier']}")
        print(f"    surfaces naming it: {', '.join(d['surfaces_naming_it']) or '(none)'}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
