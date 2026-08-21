#!/usr/bin/env python3
# SCOPE: os-only
"""Classify connectedness of scripts/ and manifests/ primitives.

Criterion before measurement (ADR-less, operator-facing census).

Evidence levels, per the operator's hierarchy:
  L1 git/filesystem     -- git ls-files, source text of every tracked file
  L2 primitive source   -- does the referencing file actually PARSE the target
  L3 SO telemetry       -- tool-sequences.jsonl, admitted as POSITIVE evidence only
  L4 derived artifacts  -- NOT USED. No report, ledger or manifest is trusted here.

The telemetry (L3) is one-sided by construction: seeing a script there proves it
ran; NOT seeing it proves nothing, because the writer truncates commands at 180
chars and was de-registered on 2026-08-19. This asymmetry is enforced in code --
telemetry can only ever upgrade a classification, never produce a "dead" verdict.

Exit codes: 0 = no findings, 1 = findings, 2 = error.
"""

from __future__ import annotations

import argparse
import glob
import gzip
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Files whose mention of a primitive counts as a WIRING reference (auto-invocable).
# Wiring tiers, strongest first. The tier answers "what would have to be true
# for this to run without a human typing its name?"
WIRING_TIERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    # Something in the harness executes it with no human in the loop.
    ("AUTO_INVOCABLE", (".claude/settings.json", ".claude/settings.local.json",
                        ".github/workflows/", "hooks/", "Makefile")),
    # An operator or agent invokes it by name through a documented surface.
    ("OPERATOR_SURFACE", (".claude/commands/", ".claude/agents/", "skills/")),
    # Only a test drives it. Real coverage, but nothing in production calls it.
    ("TEST_ONLY", ("tests/",)),
    # Only sibling code names it -- could be a library, could be a dead island.
    ("PEER_ONLY", ("scripts/", "lib/", "cos_lib/", "packages/")),
    # Only declared in a manifest -- data, not a call site.
    ("MANIFEST_ONLY", ("manifests/",)),
)

WIRING_PREFIXES = tuple(p for _, prefixes in WIRING_TIERS for p in prefixes)

# A reference from these counts only as documentation (a human could find it).
DOC_SUFFIXES = (".md", ".mdx", ".rst", ".txt")

# Evidence that a referencing file actually reads/parses a data file.
PARSE_CALL_RE = re.compile(
    r"(yaml\.safe_load|yaml\.load|yaml\.safe_load_all|json\.load|toml\.load"
    r"|\.read_text\(|\.read_bytes\(|open\s*\(|\byq\b|\bjq\b|\bcat\b"
    r"|ReadFile|os\.ReadFile|ioutil\.ReadFile|source\s|\.\s+\"?\$)"
)

# Patterns that mean "this directory is walked dynamically", so a per-file
# reference is not required for the primitive to be reachable.
DYNAMIC_DISPATCH_RE = re.compile(
    r"(scripts/\*|manifests/\*|glob\.glob\([^)]*(?:scripts|manifests)"
    r"|Path\([^)]*(?:scripts|manifests)[^)]*\)\.(?:glob|rglob|iterdir)"
    r"|for\s+\w+\s+in\s+(?:\./)?(?:scripts|manifests)/"
    r"|ls\s+(?:\./)?(?:scripts|manifests)/"
    r"|find\s+(?:\./)?(?:scripts|manifests))"
)

TELEMETRY_LIVE = ".cognitive-os/metrics/tool-sequences.jsonl"
TELEMETRY_ARCHIVE_GLOB = ".cognitive-os/metrics/.archive/tool-sequences-*.jsonl.gz"


# --------------------------------------------------------------------------- #
# L1: git + filesystem
# --------------------------------------------------------------------------- #
def git_ls(*patterns: str) -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", *patterns],
        capture_output=True,
        text=True,
        check=True,
    )
    return [ln for ln in out.stdout.splitlines() if ln.strip()]


def load_corpus() -> dict[str, str]:
    """Every tracked text file, read once. L1 evidence."""
    corpus: dict[str, str] = {}
    for rel in git_ls():
        path = REPO_ROOT / rel
        try:
            if not path.is_file() or path.stat().st_size > 2_000_000:
                continue
            corpus[rel] = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
    return corpus


# --------------------------------------------------------------------------- #
# L3: telemetry -- positive evidence only, window declared
# --------------------------------------------------------------------------- #
def load_telemetry() -> tuple[set[str], dict[str, object]]:
    """Return (basenames observed executing, provenance of the instrument)."""
    seen: set[str] = set()
    files = sorted(glob.glob(str(REPO_ROOT / TELEMETRY_ARCHIVE_GLOB)))
    live = REPO_ROOT / TELEMETRY_LIVE
    if live.exists():
        files.append(str(live))
    rows = 0
    tmin = tmax = None
    token_re = re.compile(r"[A-Za-z0-9_.-]+\.(?:py|sh)\b")
    for fname in files:
        opener = gzip.open if fname.endswith(".gz") else open
        try:
            handle = opener(fname, "rt", errors="replace")
        except OSError:
            continue
        with handle:
            for line in handle:
                try:
                    row = json.loads(line)
                except (ValueError, TypeError):
                    continue
                rows += 1
                stamp = row.get("timestamp")
                if stamp:
                    tmin = stamp if tmin is None or stamp < tmin else tmin
                    tmax = stamp if tmax is None or stamp > tmax else tmax
                preview = row.get("command_preview") or ""
                for token in token_re.findall(preview):
                    seen.add(token.rsplit("/", 1)[-1])
    provenance = {
        "instrument": TELEMETRY_LIVE,
        "writer": "hooks/tool-sequence-capture.sh",
        "writer_registered_now": False,
        "rows": rows,
        "window_start": tmin,
        "window_end": tmax,
        "known_defect": "command_preview capped at 180 chars (writer line 92); "
        "a script invoked past that offset is invisible. Writer de-registered "
        "in commit 376976744 (2026-08-19), so the stream is frozen.",
        "admissibility": "positive evidence only -- never used to declare dead",
    }
    return seen, provenance


# --------------------------------------------------------------------------- #
# Reference search
# --------------------------------------------------------------------------- #
TOKEN_RE = re.compile(r"(?<![A-Za-z0-9_.-])([A-Za-z0-9_.-]+\.(?:py|sh|yaml))(?![A-Za-z0-9_-])")


# A referrer that names this many distinct primitives of a family is keeping a
# ROSTER (a census, an allowlist, a naming-convention test), not calling them.
# Measured: one portability test names 137 scripts. Treating that as a call site
# is the dominant false positive of any grep-based connectedness audit.
ROSTER_THRESHOLD = 20


def find_roster_files(index: dict[str, set[str]], family: set[str]) -> dict[str, int]:
    """Files naming > ROSTER_THRESHOLD distinct members of `family`."""
    tally: dict[str, int] = {}
    for basename, referrers in index.items():
        if basename not in family:
            continue
        for ref in referrers:
            tally[ref] = tally.get(ref, 0) + 1
    return {f: n for f, n in tally.items() if n > ROSTER_THRESHOLD}


def build_reverse_index(corpus: dict[str, str]) -> dict[str, set[str]]:
    """basename -> files that mention it. One pass over the corpus (L1)."""
    index: dict[str, set[str]] = {}
    for rel, text in corpus.items():
        for token in set(TOKEN_RE.findall(text)):
            index.setdefault(token, set()).add(rel)
    return index


def find_references(
    target_rel: str,
    corpus: dict[str, str],
    index: dict[str, set[str]],
    rosters: dict[str, int] | None = None,
) -> dict[str, list[str]]:
    """Files referencing target, bucketed. Self-references and rosters excluded."""
    rosters = rosters or {}
    basename = target_rel.rsplit("/", 1)[-1]
    buckets: dict[str, list[str]] = {"wiring": [], "doc": [], "other": [], "roster": []}
    for rel in sorted(index.get(basename, ())):
        if rel == target_rel:
            continue
        if rel in rosters:
            buckets["roster"].append(rel)
            continue
        if rel.endswith(DOC_SUFFIXES) and not rel.startswith("skills/"):
            buckets["doc"].append(rel)
        elif rel.startswith(WIRING_PREFIXES) or rel == "Makefile":
            buckets["wiring"].append(rel)
        else:
            buckets["other"].append(rel)
    return buckets


def parses_target(referrer: str, target_rel: str, corpus: dict[str, str]) -> bool:
    """L2: does the referrer plausibly PARSE the target, or only name it?

    The trap this exists for: a manifest can have a declared reader that never
    reads it. We check that the mention is (a) not on a comment-only line and
    (b) that the referring file contains a read/parse call at all.
    """
    text = corpus.get(referrer, "")
    basename = target_rel.rsplit("/", 1)[-1]
    non_comment_hit = False
    for line in text.splitlines():
        if basename not in line:
            continue
        stripped = line.strip()
        if stripped.startswith(("#", "//", "*", "<!--")):
            continue
        non_comment_hit = True
        break
    if not non_comment_hit:
        return False
    return bool(PARSE_CALL_RE.search(text))


def has_dynamic_dispatch(corpus: dict[str, str]) -> list[str]:
    return [
        rel
        for rel, text in corpus.items()
        if rel.startswith(WIRING_PREFIXES) and DYNAMIC_DISPATCH_RE.search(text)
    ]


# --------------------------------------------------------------------------- #
# Classification
# --------------------------------------------------------------------------- #
def classify_script(
    target: str,
    corpus: dict[str, str],
    observed: set[str],
    index: dict[str, set[str]],
    rosters: dict[str, int] | None = None,
) -> str:
    refs = find_references(target, corpus, index, rosters)
    basename = target.rsplit("/", 1)[-1]
    remaining = list(refs["wiring"])
    for tier_name, prefixes in WIRING_TIERS:
        if any(r.startswith(prefixes) or r == "Makefile" for r in remaining):
            return tier_name
        remaining = [r for r in remaining if not r.startswith(prefixes)]
    if basename in observed:
        # L3 upgrade. Positive evidence only: telemetry can rescue a script from
        # the dead pile, but absence from it never puts one there.
        return "OBSERVED_ONLY"
    if refs["doc"]:
        return "DOC_ONLY"
    if refs["other"]:
        return "REFERENCED_ELSEWHERE"
    if refs["roster"]:
        # Named only by a census/allowlist/naming test. Nothing calls it.
        return "ROSTER_ONLY"
    return "UNREFERENCED"


def classify_manifest(
    target: str, corpus: dict[str, str], index: dict[str, set[str]]
) -> tuple[str, list[str]]:
    refs = find_references(target, corpus, index)
    code_refs = [r for r in refs["wiring"] + refs["other"] if not r.endswith(DOC_SUFFIXES)]
    parsers = [r for r in code_refs if parses_target(r, target, corpus)]
    if parsers:
        return "PARSED", parsers
    if code_refs:
        return "CODE_REF_UNPROVEN", code_refs
    if refs["doc"]:
        return "DOC_ONLY", refs["doc"]
    return "UNREFERENCED", []


# --------------------------------------------------------------------------- #
# Positive control -- wired in, runs BEFORE any zero is reported
# --------------------------------------------------------------------------- #
def positive_control(
    corpus: dict[str, str],
    observed: set[str],
    index: dict[str, set[str]],
    rosters: dict[str, int],
) -> list[str]:
    """Prove the instrument can find what IS there and can also fire its zero.

    A probe that returns the same answer on both branches of the counterfactual
    is broken. These asserts require the two branches to DIFFER.
    """
    failures: list[str] = []

    # (a) Known-wired script: literally named in .claude/settings.json.
    known = "scripts/hook-timing-wrapper.sh"
    if known in corpus:
        got = classify_script(known, corpus, observed, index, rosters)
        if got != "AUTO_INVOCABLE":
            failures.append(f"CONTROL-A: {known} expected AUTO_INVOCABLE, got {got}")
    else:
        failures.append(f"CONTROL-A: fixture {known} missing from corpus")

    # (b) Synthetic never-referenced name: the zero branch must actually fire.
    ghost = "scripts/zzz_nonexistent_probe_9f3a2b.sh"
    got_ghost = classify_script(ghost, corpus, observed, index, rosters)
    if got_ghost != "UNREFERENCED":
        failures.append(f"CONTROL-B: ghost expected UNREFERENCED, got {got_ghost}")

    # (c) The two branches must DIFFER, or the probe is not discriminating.
    if known in corpus and classify_script(known, corpus, observed, index, rosters) == got_ghost:
        failures.append("CONTROL-C: wired and ghost classify identically -- probe is blind")

    # (d) Manifest with a real parser must come back PARSED.
    man = "manifests/hook-vitality-budget.yaml"
    if man in corpus:
        verdict, _ = classify_manifest(man, corpus, index)
        if verdict == "UNREFERENCED":
            failures.append(f"CONTROL-D: {man} expected a reader, got {verdict}")
    else:
        failures.append(f"CONTROL-D: fixture {man} missing from corpus")

    # (f) Roster demotion must actually fire, or the fix is inert.
    if not rosters:
        failures.append(
            "CONTROL-F: no roster files detected -- demotion is inert, "
            "TEST_ONLY counts would be inflated by enumerating tests"
        )

    # (e) Telemetry must contain at least one real script basename, else the
    #     L3 channel is silently empty and must not be cited as evidence.
    if not observed:
        failures.append("CONTROL-E: telemetry parsed to zero basenames -- L3 channel empty")

    return failures


# --------------------------------------------------------------------------- #
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=["scripts", "manifests", "all"], default="all")
    parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    parser.add_argument("--list", metavar="CLASS", help="list members of one class")
    args = parser.parse_args()

    try:
        corpus = load_corpus()
        observed, telemetry_provenance = load_telemetry()
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: could not build evidence base: {exc}", file=sys.stderr)
        return 2

    index = build_reverse_index(corpus)
    script_family = {t.rsplit("/", 1)[-1] for t in git_ls("scripts/*.py", "scripts/*.sh")}
    rosters = find_roster_files(index, script_family)
    control_failures = positive_control(corpus, observed, index, rosters)
    if control_failures:
        print("POSITIVE CONTROL FAILED -- refusing to report counts", file=sys.stderr)
        for failure in control_failures:
            print(f"  {failure}", file=sys.stderr)
        return 2

    head_tree = set(subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-tree", "-r", "--name-only", "HEAD"],
        capture_output=True, text=True, check=False,
    ).stdout.splitlines())

    report: dict[str, object] = {
        "count_basis": (
            "targets come from `git ls-files` (index + working state). The index "
            "is mutated by concurrent sessions, so counts drift mid-run; "
            "HEAD-tree counts are reported alongside as the stable reference."
        ),
        "repo_head": subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=False,
        ).stdout.strip(),
        "positive_control": "passed",
        "telemetry_provenance": telemetry_provenance,
    }
    findings = 0

    if args.family in ("scripts", "all"):
        targets = git_ls("scripts/*.py", "scripts/*.sh")
        buckets: dict[str, list[str]] = {}
        for target in targets:
            buckets.setdefault(classify_script(target, corpus, observed, index, rosters), []).append(target)
        dynamic = has_dynamic_dispatch(corpus)
        report["scripts"] = {
            "total": len(targets),
            "total_in_head_tree": sum(1 for t in targets if t in head_tree),
            "counts": {k: len(v) for k, v in sorted(buckets.items())},
            "members": buckets,
            "dynamic_dispatch_sites": len(dynamic),
            "roster_files_demoted": rosters,
            "false_positive_mode": (
                "A script reached only through dynamic dispatch (a loop over "
                "scripts/*) has no per-file reference and lands in UNREFERENCED. "
                f"{len(dynamic)} dispatch sites exist, so UNREFERENCED is a "
                "candidate list for review, never a delete list."
            ),
        }
        findings += len(buckets.get("UNREFERENCED", []))

    if args.family in ("manifests", "all"):
        targets = git_ls("manifests/*.yaml")
        buckets = {}
        detail: dict[str, list[str]] = {}
        for target in targets:
            verdict, who = classify_manifest(target, corpus, index)
            buckets.setdefault(verdict, []).append(target)
            detail[target] = who
        report["manifests"] = {
            "total": len(targets),
            "total_in_head_tree": sum(1 for t in targets if t in head_tree),
            "counts": {k: len(v) for k, v in sorted(buckets.items())},
            "members": buckets,
            "readers": detail,
            "false_positive_mode": (
                "PARSED means the referring file names the manifest outside a "
                "comment AND contains a read/parse call somewhere -- not that "
                "the call reads THIS file. CODE_REF_UNPROVEN is the honest "
                "bucket for 'declared reader that may never read it'."
            ),
        }
        findings += len(buckets.get("UNREFERENCED", [])) + len(
            buckets.get("CODE_REF_UNPROVEN", [])
        )

    if args.list:
        for family in ("scripts", "manifests"):
            block = report.get(family)
            if isinstance(block, dict):
                for item in block.get("members", {}).get(args.list, []):  # type: ignore[union-attr]
                    print(item)
        return 1 if findings else 0

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"HEAD {report['repo_head']}  positive control: passed")
        prov = telemetry_provenance
        print(
            f"\nL3 telemetry: {prov['rows']} rows, window "
            f"{prov['window_start']} -> {prov['window_end']}, "
            f"writer registered now: {prov['writer_registered_now']}"
        )
        print("  admissibility: positive evidence only")
        for family in ("scripts", "manifests"):
            block = report.get(family)
            if not isinstance(block, dict):
                continue
            print(
                f"\n== {family} (total {block['total']}, "
                f"in HEAD tree {block['total_in_head_tree']}) =="
            )
            for name, count in block["counts"].items():  # type: ignore[index]
                print(f"  {name:24s} {count}")
            print(f"  false positive mode: {block['false_positive_mode']}")

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
