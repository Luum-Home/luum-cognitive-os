#!/usr/bin/env python3
"""Audit repo-scout ADOPT verdicts that point nowhere.

Sibling of scripts/audit_decision_backing.py, different population.  That one
asks "does this implemented decision have a written decision behind it?" over
decision SURFACES (blocking gates, policy manifests, package boundaries).  This
one asks a narrower question over a population that script deliberately excludes
(PoC research documents):

    Does every ADOPT verdict resolve to something a reader can act on?

A deep repo-scout report that says ADOPT and links to nothing is a standing
instruction with no expiry.  A reader landing on it today sees "adopt this" and
has no way to learn that the operator froze all external adoption on
2026-05-11, or that the thing was in fact adopted three days earlier.  Both
outcomes are fine; being unable to tell them apart is not.

--------------------------------------------------------------------------
THE CRITERION
--------------------------------------------------------------------------
Population: files under docs/03-PoCs/research/repo-scout/deep/ whose YAML
frontmatter carries a `deep_verdict:` starting with ADOPT.  Nothing else --
TRIAL, DEFER, and the comparison reports are out of scope, because they do not
read as an instruction to act.

An ADOPT verdict is LINKED when its body resolves the verdict for a reader, by
at least one of:

  L1  FREEZE POINTER    the file names manifests/external-tool-adoption-freeze.yaml
                        (i.e. the reader is told the verdict may be superseded,
                        or that it landed before the freeze).
  L2  ADR NAMES IT      some ADR cites the repo by its org/repo slug -- the ADR
                        corpus itself resolves what happened.

UNLINKED = neither.  That is the census of the hole.

NOT accepted as linkage, on purpose: a bare ADR-NNN mention in the report body.
Every one of these reports name-drops the ADR it would be *relevant to*
("direct ADR-049 reference", "ADR-033 fit").  That is the analyst arguing the
tool matters, not a record of what was decided -- counting it would mark 8 more
files green while a reader still cannot tell adopted from abandoned.  It was
counted in the first draft of this script and removed after inspecting the
matches; the fix has to shrink the problem, not the measurement.

  DANGLING = the file cites ADR-NNN and no such ADR exists.  Worse than silence:
             it reads as backed and is not.  Counted separately, same as the
             sibling script.

Deliberately NOT done here: writing retroactive ADRs.  The motive for these
verdicts is already written once, in the freeze manifest; ten restatements of
one reason invented after the fact would be fiction wearing a record's clothes.
The correct output for an unlinked ADOPT verdict is a pointer, not a new ADR.

Also deliberately NOT done: treating "linked" as "correct".  This script cannot
tell whether a note says the true thing -- only whether a reader has somewhere
to go.  Verifying that the pointer is accurate is a human read.

--------------------------------------------------------------------------
Read-only.  Deterministic.  Exit 0 = within ratchet, 1 = regression, 2 = error.
--------------------------------------------------------------------------
Usage:
  python3 scripts/audit_adopt_verdict_linkage.py           # human table
  python3 scripts/audit_adopt_verdict_linkage.py --json    # machine output
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCOUT_DIR = REPO / "docs" / "03-PoCs" / "research" / "repo-scout" / "deep"
ADR_DIR = REPO / "docs" / "02-Decisions" / "adrs"
FREEZE = "manifests/external-tool-adoption-freeze.yaml"

# Ratchet lives here rather than in a manifest: the population is a closed,
# frozen set of 2026-05-06 reports, so the number only moves when someone adds
# a new deep report or removes a pointer.  Raising it requires editing this
# line with a reason in the commit message.
#
# 8 = measured reality on 2026-08-15, not a cushion.  The 2026-08-15 pass
# audited the 10 verdicts whose payload was checked against the codebase
# case-by-case; the remaining 8 (pal-mcp-server, hermes-agent,
# everything-claude-code, agentapi, superpowers, augustus, simonw/llm,
# agent-scan) were never verified, so they are debt on the record rather than
# green.  Lowering this number is the point; raising it needs a reason here.
RATCHET_UNLINKED = 8
RATCHET_DANGLING = 0

ADR_RE = re.compile(r"ADR-(\d{1,4})")
VERDICT_RE = re.compile(r"^deep_verdict:\s*(ADOPT.*)$", re.MULTILINE)


def die(msg: str) -> int:
    print(f"ERROR: {msg}", file=sys.stderr)
    return 2


def existing_adr_numbers() -> set[int]:
    nums: set[int] = set()
    for p in ADR_DIR.glob("ADR-*.md"):
        m = ADR_RE.match(p.name)
        if m:
            nums.add(int(m.group(1)))
    return nums


def adr_corpus() -> str:
    parts = []
    for p in sorted(ADR_DIR.rglob("*.md")):
        try:
            parts.append(p.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
    return "\n".join(parts)


def slug_for(path: Path) -> str:
    """Aider-AI__aider-2026-05-06.md -> Aider-AI/aider"""
    stem = path.stem
    stem = re.sub(r"-\d{4}-\d{2}-\d{2}$", "", stem)
    return stem.replace("__", "/", 1)


def classify(path: Path, adr_nums: set[int], corpus: str) -> dict | None:
    text = path.read_text(encoding="utf-8", errors="replace")
    m = VERDICT_RE.search(text)
    if not m:
        return None
    verdict = m.group(1).strip()
    slug = slug_for(path)

    cited = {int(n) for n in ADR_RE.findall(text)}
    resolvable = cited & adr_nums
    dangling = sorted(cited - adr_nums)

    l1 = FREEZE in text
    l2 = slug in corpus

    return {
        "file": str(path.relative_to(REPO)),
        "repo": slug,
        "verdict": verdict,
        # informational only -- deliberately NOT a linkage signal, see module docstring
        "body_adr_mentions": sorted(resolvable),
        "freeze_pointer": l1,
        "adr_names_repo": l2,
        "linked": l1 or l2,
        "dangling_adrs": dangling,
    }


def main() -> int:
    as_json = "--json" in sys.argv

    if not SCOUT_DIR.is_dir():
        return die(f"missing population dir: {SCOUT_DIR.relative_to(REPO)}")
    if not ADR_DIR.is_dir():
        return die(f"missing ADR dir: {ADR_DIR.relative_to(REPO)}")

    adr_nums = existing_adr_numbers()
    if not adr_nums:
        return die("no ADR files found — refusing to report everything unlinked")
    corpus = adr_corpus()

    rows = []
    for p in sorted(SCOUT_DIR.glob("*.md")):
        row = classify(p, adr_nums, corpus)
        if row:
            rows.append(row)

    if not rows:
        return die("no ADOPT verdicts found — population empty, criterion likely broken")

    unlinked = [r for r in rows if not r["linked"]]
    dangling = [r for r in rows if r["dangling_adrs"]]

    if as_json:
        print(json.dumps({
            "population": len(rows),
            "unlinked": len(unlinked),
            "dangling": len(dangling),
            "ratchet": {"unlinked": RATCHET_UNLINKED, "dangling": RATCHET_DANGLING},
            "rows": rows,
        }, indent=2, sort_keys=True))
    else:
        print(f"ADOPT verdicts under {SCOUT_DIR.relative_to(REPO)}: {len(rows)}")
        print(f"{'repo':38s} {'~ADR':>10s} {'freeze':>7s} {'named':>6s}  status")
        print("-" * 80)
        for r in sorted(rows, key=lambda x: (x["linked"], x["repo"])):
            adr = ",".join(str(n) for n in r["body_adr_mentions"]) or "-"
            print(
                f"{r['repo'][:38]:38s} {adr:>10s} "
                f"{'yes' if r['freeze_pointer'] else '-':>7s} "
                f"{'yes' if r['adr_names_repo'] else '-':>6s}  "
                f"{'linked' if r['linked'] else 'UNLINKED'}"
            )
        print()
        print(f"unlinked: {len(unlinked)} (ratchet {RATCHET_UNLINKED})")
        print(f"dangling: {len(dangling)} (ratchet {RATCHET_DANGLING})")

    failures = []
    if len(unlinked) > RATCHET_UNLINKED:
        failures.append(f"unlinked {len(unlinked)} > ratchet {RATCHET_UNLINKED}")
    if len(dangling) > RATCHET_DANGLING:
        failures.append(f"dangling {len(dangling)} > ratchet {RATCHET_DANGLING}")

    if failures:
        for f in failures:
            print(f"REGRESSION: {f}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
