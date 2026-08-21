#!/usr/bin/env python3
# SCOPE: os-only
"""Replay real prompts through cos_lib.rule_router and report precision.

Answers, with a command instead of an opinion: if N rules are routable, on what
FRACTION of real prompts does the router emit a suggestion, and which rules
dominate? A router that fires on most prompts is wallpaper -- the operator
learns to skip it, and the mechanism is lost along with the rules it names.

Corpus: real Claude Code transcripts from this machine.

**The corpus is not one population.** The same UserPromptSubmit event carries
text a person typed, background-agent completion reports, the compaction
preamble, cross-session relays and slash-command echoes. Their emission rates
differ by an order of magnitude, so a single average describes none of them.
Worse, several of those classes never reach the hook at all -- they show up in
transcripts but produce no telemetry row -- and counting them inflates or
deflates a rate that no live hook ever produced.

So this script:

1. classifies every prompt with ``cos_lib.prompt_origin`` (the same classifier
   the hook uses to decide what to skip);
2. cross-checks each class against LIVE hook telemetry by ``prompt_hash``,
   restricted to the transcripts telemetry actually covers, and reports how
   many payloads of that class reached the hook;
3. drops from the evaluated set only the classes with **zero observed reach**
   -- the justification is "the hook never sees it", never "it emits a lot";
4. prints the composition it used, and three emission rates over three named
   denominators, so a reader can see exactly which population each describes.

Read-only. Never writes to .cognitive-os/. Exit 0 = under ceiling,
1 = a rule exceeds --max-hit-rate (noise finding), 2 = error.
"""
from __future__ import annotations

import argparse
import collections
import glob
import hashlib
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from cos_lib.prompt_origin import (  # noqa: E402
    MACHINE_ORIGINS,
    MIN_PROMPT_CHARS,
    classify_origin,
)

TELEMETRY = REPO / ".cognitive-os" / "metrics" / "rule-suggestion.jsonl"

# The hook hashes the prompt this way; see hooks/rule-router-prompt-suggest.sh.
def prompt_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def default_transcript_glob() -> str:
    """Derived from where the repo actually is -- never hardcoded.

    A hardcoded project slug makes the glob empty on any other checkout, and an
    empty corpus reports "0 rules named" indistinguishably from "looked and
    found none". Claude Code replaces BOTH slashes and dots with hyphens.
    """
    slug = str(REPO).replace("/", "-").replace(".", "-")
    return f"~/.claude/projects/{slug}/*.jsonl"


def load_prompts(pattern: str, kind: str = "user") -> tuple[dict[str, list[str]], int]:
    """Extract the replay corpus, keyed by transcript file.

    Keyed by file because the telemetry cross-check needs it: a class with zero
    telemetry hits inside transcripts telemetry never covered has not been shown
    unreachable, it has been shown to predate the log.

    kind="user"  -> real USER prompts (type=user, string content). This is the
                    population the hook actually sees: rule-router-prompt-suggest
                    runs on UserPromptSubmit.
    kind="agent" -> Agent/Task tool_input.prompt (sub-agent briefs). A DIFFERENT
                    population; the hook never sees these. Useful only as a
                    contrast, and it overstates hit rates because briefs are long
                    and vocabulary-dense.
    """
    by_file: dict[str, list[str]] = {}
    files = sorted(glob.glob(os.path.expanduser(pattern)))
    for path in files:
        got: list[str] = []
        try:
            with open(path, errors="ignore") as fh:
                for line in fh:
                    if kind == "agent":
                        got.extend(_agent_prompts_from_line(line))
                    else:
                        got.extend(_user_prompts_from_line(line))
        except OSError:
            continue
        if got:
            by_file[os.path.basename(path)] = got
    return by_file, len(files)


def _user_prompts_from_line(line: str) -> list[str]:
    if '"type": "user"' not in line and '"type":"user"' not in line:
        return []
    try:
        rec = json.loads(line)
    except (ValueError, TypeError):
        return []
    if rec.get("type") != "user":
        return []
    content = (rec.get("message") or {}).get("content")
    return [content] if isinstance(content, str) and content.strip() else []


def _agent_prompts_from_line(line: str) -> list[str]:
    if '"Agent"' not in line and '"Task"' not in line:
        return []
    try:
        rec = json.loads(line)
    except (ValueError, TypeError):
        return []
    content = (rec.get("message") or {}).get("content")
    if not isinstance(content, list):
        return []
    out = []
    for block in content:
        if not isinstance(block, dict) or block.get("type") != "tool_use":
            continue
        if block.get("name") not in ("Agent", "Task"):
            continue
        p = (block.get("input") or {}).get("prompt")
        if p:
            out.append(p)
    return out


def live_rows() -> list[dict]:
    """Every row the hook has actually written. Empty list if no telemetry."""
    if not TELEMETRY.is_file():
        return []
    out = []
    for line in TELEMETRY.read_text(errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def live_prompt_hashes(rows: list[dict] | None = None) -> set[str]:
    """Every prompt_hash the hook has actually logged. Empty set if no telemetry."""
    return {r["prompt_hash"] for r in (rows if rows is not None else live_rows())
            if r.get("prompt_hash")}


def live_report(rows: list[dict], by_file: dict[str, list[str]]) -> dict:
    """What the hook REALLY did, attributed to the origin of each prompt.

    The replay estimates what today's rule set would do to a corpus. This reads
    what the hook actually emitted, row by row, and joins each row back to the
    prompt that produced it via prompt_hash. When the two disagree the replay is
    the one describing a hypothetical: the rule set changes, the log does not.

    Rows whose prompt is not in the local corpus (rotated or trimmed
    transcripts) are reported as their own bucket rather than dropped -- an
    unattributable row is a limit of the join, not a zero.
    """
    origin_of = {prompt_hash(p): classify_origin(p)
                 for ps in by_file.values() for p in ps}
    tot: collections.Counter = collections.Counter()
    emit: collections.Counter = collections.Counter()
    for r in rows:
        o = origin_of.get(r.get("prompt_hash"), "unattributable")
        tot[o] += 1
        if r.get("threshold_met"):
            emit[o] += 1
    total_rows = sum(tot.values())
    total_emit = sum(emit.values())
    machine_emit = sum(emit[o] for o in tot if o in MACHINE_ORIGINS)
    return {
        "rows": total_rows,
        "emitted": total_emit,
        "emission_rate": round(total_emit / total_rows, 4) if total_rows else 0.0,
        "by_origin": {o: {"rows": tot[o], "emitted": emit[o],
                          "emission_rate": round(emit[o] / tot[o], 4)}
                      for o in sorted(tot, key=lambda x: -tot[x])},
        "suggestions_to_machine_authored": machine_emit,
        "share_of_suggestions_wasted": (round(machine_emit / total_emit, 4)
                                        if total_emit else 0.0),
        "first_ts": min((r.get("ts", "") for r in rows), default=""),
        "last_ts": max((r.get("ts", "") for r in rows), default=""),
    }


def reach_table(by_file: dict[str, list[str]],
                live: set[str]) -> dict[str, tuple[int, int]]:
    """origin -> (n_in_covered_transcripts, n_that_reached_the_hook).

    Restricted to transcripts with at least one telemetry hit. Outside that
    window the log simply does not exist yet, and "0 reached" would be an
    artefact of the window, not a fact about the hook.
    """
    covered = [f for f, ps in by_file.items()
               if any(prompt_hash(p) in live for p in ps)]
    tot: collections.Counter = collections.Counter()
    hit: collections.Counter = collections.Counter()
    for f in covered:
        for p in by_file[f]:
            o = classify_origin(p)
            tot[o] += 1
            if prompt_hash(p) in live:
                hit[o] += 1
    return {o: (tot[o], hit[o]) for o in tot}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--transcripts", default=default_transcript_glob())
    ap.add_argument("--threshold", type=float, default=0.80,
                    help="confidence floor the hook uses (default 0.80)")
    ap.add_argument("--max-hit-rate", type=float, default=0.25,
                    help="a single rule matching more than this fraction of "
                         "real prompts is a false-positive finding")
    ap.add_argument("--corpus", choices=("user", "agent"), default="user",
                    help="user = UserPromptSubmit population the hook really "
                         "sees (default); agent = sub-agent briefs (contrast)")
    ap.add_argument("--shadow", action="store_true",
                    help="DARK LAUNCH: score every LOADED rule, including those "
                         "declared routable:false, without any of them reaching "
                         "the operator. Measures noise before granting emission.")
    ap.add_argument("--live", action="store_true",
                    help="report what the hook REALLY emitted, from "
                         ".cognitive-os/metrics/rule-suggestion.jsonl, attributed "
                         "to the origin of each prompt. The replay says what "
                         "today's rule set WOULD do; this says what happened.")
    ap.add_argument("--keep-unreached", action="store_true",
                    help="do NOT drop origin classes with zero observed reach. "
                         "Reproduces the pre-segmentation number for comparison.")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    try:
        from cos_lib.rule_router import RuleRouter
    except Exception as exc:  # pragma: no cover - import guard
        print(f"ERROR: cannot import RuleRouter: {exc}", file=sys.stderr)
        return 2

    router = RuleRouter()

    # Positive control, wired in: if the router stops finding a rule it has
    # demonstrably matched in real telemetry, this script must CRASH rather
    # than publish a false zero. A probe that returns the same answer on both
    # branches of the counterfactual is broken, not informative.
    # The control must name a rule that is CURRENTLY routable. It first fired
    # for real on 2026-08-20 when acceptance-criteria was demoted to
    # routable:false -- doing exactly its job, so it is kept and repointed.
    ctrl = [m.rule_name for m in router.top_matches(
        "check error-learning.jsonl for repeats", n=3, min_confidence=0.70)]
    assert "error-learning" in ctrl, (
        f"positive control FAILED: router did not match error-learning "
        f"({ctrl!r}) -- the probe is broken, not the corpus")
    neg = router.top_matches("zzzqqq unrelated lorem ipsum filler", n=3,
                             min_confidence=0.70)
    assert not neg, f"negative control FAILED: matched {neg!r} on filler text"

    by_file, nfiles = load_prompts(args.transcripts, args.corpus)
    prompts = [p for ps in by_file.values() for p in ps]
    if not prompts:
        print(f"ERROR: empty replay corpus from {args.transcripts} "
              f"({nfiles} files) -- refusing to report a zero", file=sys.stderr)
        return 2

    rows = live_rows()
    live = live_prompt_hashes(rows)
    reach = reach_table(by_file, live) if live else {}
    live_summary = live_report(rows, by_file) if rows else None

    if args.live:
        if live_summary is None:
            print(f"ERROR: no telemetry at {TELEMETRY} -- nothing to report",
                  file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(live_summary, indent=2, sort_keys=True))
        else:
            print(f"live telemetry    : {live_summary['rows']} rows "
                  f"({live_summary['first_ts'][:10]} .. "
                  f"{live_summary['last_ts'][:10]})")
            print(f"  {'origin of the prompt':26} {'rows':>5} {'emitted':>8} {'rate':>8}")
            for o, d in live_summary["by_origin"].items():
                print(f"  {o:26} {d['rows']:5d} {d['emitted']:8d} "
                      f"{d['emission_rate']:8.1%}")
            print(f"  {'TOTAL':26} {live_summary['rows']:5d} "
                  f"{live_summary['emitted']:8d} "
                  f"{live_summary['emission_rate']:8.1%}")
            print()
            print(f"suggestions delivered to text no person typed: "
                  f"{live_summary['suggestions_to_machine_authored']} of "
                  f"{live_summary['emitted']} "
                  f"({live_summary['share_of_suggestions_wasted']:.1%})")
        return 0

    # A class is dropped ONLY when the hook demonstrably never saw it. Emission
    # rate plays no part in this decision -- that is the difference between
    # segmenting a corpus and trimming it until the number looks good.
    unreached = sorted(o for o, (n, hits) in reach.items() if n and hits == 0)
    dropped_classes = [] if args.keep_unreached else unreached

    def _score(text: str) -> set:
        if args.shadow:
            return {m.rule_name for m in
                    router.shadow_match(text, min_confidence=args.threshold)}
        return {m.rule_name for m in
                router.top_matches(text, n=3, min_confidence=args.threshold)}

    per_class_total: collections.Counter = collections.Counter()
    per_class_emit: collections.Counter = collections.Counter()
    per_rule: collections.Counter = collections.Counter()

    # Three named denominators. Printing all three is the point: one number
    # cannot be both "what the router does to the corpus" and "what the hook
    # costs the operator".
    all_total = all_emit = 0            # every prompt, no gate at all
    pop_total = pop_emit = 0            # payloads that reach the hook today
    post_total = post_emit = 0          # same, with the origin suppression on

    for p in prompts:
        origin = classify_origin(p)
        names = _score(p)
        fires = bool(names)

        per_class_total[origin] += 1
        if fires:
            per_class_emit[origin] += 1

        all_total += 1
        all_emit += fires

        # The hook's own pre-existing gates: too short, or a class it never sees.
        if len(p.lstrip()) < MIN_PROMPT_CHARS or origin in dropped_classes:
            continue
        pop_total += 1
        pop_emit += fires
        per_rule.update(names)

        # The change under measurement.
        post_total += 1
        if origin in MACHINE_ORIGINS:
            continue  # suppressed at the hook: no rules named, no context spent
        post_emit += fires

    noisy = {r: c for r, c in per_rule.items()
             if pop_total and c / pop_total > args.max_hit_rate}

    def _rate(num: int, den: int) -> float:
        return round(num / den, 4) if den else 0.0

    composition = {}
    for o in sorted(per_class_total, key=lambda x: -per_class_total[x]):
        n_cov, n_hit = reach.get(o, (0, 0))
        composition[o] = {
            "corpus_n": per_class_total[o],
            "emitting": per_class_emit[o],
            "emission_rate": _rate(per_class_emit[o], per_class_total[o]),
            "in_covered_transcripts": n_cov,
            "reached_hook": n_hit,
            "suppressed_at_hook": o in MACHINE_ORIGINS,
            "dropped_from_corpus": o in dropped_classes,
        }

    result = {
        "corpus_prompts": all_total,
        "corpus_transcripts": nfiles,
        "corpus_kind": args.corpus,
        "shadow": args.shadow,
        "scored_rules": (router.loaded_rule_count if args.shadow
                         else router.routable_rule_count),
        "routable_rules": router.routable_rule_count,
        "loaded_rules": router.loaded_rule_count,
        "threshold": args.threshold,
        "telemetry_rows_seen": len(live),
        "composition": composition,
        "dropped_classes": dropped_classes,
        "denominators": {
            "all_payloads": all_total,
            "hook_population": pop_total,
            "hook_population_after_suppression": post_total,
        },
        "emission_rate_all_payloads": _rate(all_emit, all_total),
        "emission_rate_before_suppression": _rate(pop_emit, pop_total),
        "emission_rate_after_suppression": _rate(post_emit, post_total),
        "prompts_emitting_all_payloads": all_emit,
        "prompts_emitting_before_suppression": pop_emit,
        "prompts_emitting_after_suppression": post_emit,
        "distinct_rules_named": len(per_rule),
        "per_rule_hit_rate": {r: _rate(c, pop_total)
                              for r, c in per_rule.most_common()},
        "noisy_rules": {r: _rate(c, pop_total) for r, c in noisy.items()},
        "max_hit_rate": args.max_hit_rate,
    }

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"corpus            : {all_total} prompts / {nfiles} transcripts")
        print(f"routable rules    : {router.routable_rule_count} "
              f"(of {router.loaded_rule_count} loaded)")
        print(f"telemetry          : {len(live)} distinct prompt_hash in "
              f"{TELEMETRY.name}" if live else
              "telemetry          : none found -- reach column is blank and "
              "NO class is dropped")
        print()
        print("--- corpus composition (origin x reach x emission) ---")
        print(f"  {'origin':20} {'n':>5} {'emit':>5} {'rate':>7} "
              f"{'covered':>8} {'reached':>8}  note")
        for o, c in composition.items():
            note = []
            if c["dropped_from_corpus"]:
                note.append("DROPPED: never reached the hook")
            elif c["suppressed_at_hook"]:
                note.append("suppressed at hook")
            print(f"  {o:20} {c['corpus_n']:5d} {c['emitting']:5d} "
                  f"{c['emission_rate']:6.2%} {c['in_covered_transcripts']:8d} "
                  f"{c['reached_hook']:8d}  {'; '.join(note)}")
        print()
        print("--- emission rate, by denominator ---")
        print(f"  every payload in the corpus       : {all_emit}/{all_total} = "
              f"{_rate(all_emit, all_total):.2%}")
        print(f"  payloads the hook evaluates today : {pop_emit}/{pop_total} = "
              f"{_rate(pop_emit, pop_total):.2%}   <-- BEFORE")
        print(f"  same, with origin suppression on  : {post_emit}/{post_total} = "
              f"{_rate(post_emit, post_total):.2%}   <-- AFTER")
        print()
        print(f"distinct named    : {len(per_rule)}")
        print("--- per-rule hit rate (over the hook population) ---")
        for r, c in per_rule.most_common():
            flag = "  <== NOISY" if r in noisy else ""
            print(f"  {_rate(c, pop_total):7.2%}  {c:5d}  {r}{flag}")
        if noisy:
            print(f"\nFINDING: {len(noisy)} rule(s) above "
                  f"--max-hit-rate={args.max_hit_rate}")
    return 1 if noisy else 0


if __name__ == "__main__":
    sys.exit(main())
