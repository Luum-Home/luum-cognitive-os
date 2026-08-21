#!/usr/bin/env python3
# SCOPE: os-only
"""Classify every rules/*.md by whether ANY channel can load it, and whether
its ref-key resolves. Read-only. Exit 0 no finding / 1 finding / 2 error."""
from __future__ import annotations
import json, re, sys, collections
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RULES = REPO / "rules"
COMPACT = RULES / "RULES-COMPACT.md"
SETTINGS = REPO / ".claude" / "settings.json"
CONFIG = REPO / "cognitive-os.yaml"
PROJ = REPO / ".claude" / "rules" / "cos"
METRICS = REPO / ".cognitive-os" / "metrics"

rule_files = sorted(p.name for p in RULES.glob("*.md"))
stems = {p[:-3] for p in rule_files}

# --- Channel A: harness-native projection (.claude/rules/cos symlinks) ---
projected = {p.name[:-3] for p in PROJ.glob("*.md")} if PROJ.is_dir() else set()

# --- Channel B: ref-keys in RULES-COMPACT ---
compact_txt = COMPACT.read_text()
refkeys = set(re.findall(r"\[`([a-z0-9][a-z0-9._-]*)`\]", compact_txt))
refkey_resolves = {k for k in refkeys if k in stems}
refkey_dangling = sorted(refkeys - stems)

# --- Channel C: rule_router (the instrument itself, not a reimplementation) ---
sys.path.insert(0, str(REPO))
from cos_lib.rule_router import RuleRouter
_router = RuleRouter()
router_capable = {e.rule_name for e in _router._entries if e.patterns}
# POSITIVE CONTROL: the router must find a rule we know it routes.
# It must name a rule that is CURRENTLY routable. This control pointed at
# acceptance-criteria and started failing the moment that rule was demoted to
# routable:false -- doing exactly its job, so it is repointed, not weakened.
_CONTROL_PROMPT = "check error-learning.jsonl for repeats"
_ctl = _router.top_matches(_CONTROL_PROMPT, n=3, min_confidence=0.70)
assert _ctl and any(m.rule_name == "error-learning" for m in _ctl), (
    f"POSITIVE CONTROL FAILED: router did not match error-learning on "
    f"{_CONTROL_PROMPT!r} (got {[m.rule_name for m in _ctl]!r}) -- the "
    f"instrument is broken, not the corpus")
CONTROL = f"positive control OK: {_CONTROL_PROMPT!r} -> {_ctl[0].rule_name} ({_ctl[0].confidence:.2f})"

# --- Channel D: contextual_triggers in cognitive-os.yaml ---
triggers = set()
in_block = False
for line in CONFIG.read_text().splitlines():
    if re.match(r"^\s+contextual_triggers:\s*(#.*)?$", line.rstrip()):
        in_block = True; continue
    if not in_block: continue
    s = line.rstrip()
    if not s or s.lstrip().startswith("#"): continue
    if len(s) - len(s.lstrip()) <= 4: break
    mm = re.match(r'^\s+([a-z0-9-]+)\s*:\s*"(.+)"\s*$', s)
    if mm: triggers.add(mm.group(1))
trigger_reachable = triggers & stems
loader_registered = "contextual-rule-loader" in SETTINGS.read_text()

# --- Channel E: subagent template (templates/agent-mandatory-rules.md) ---
tmpl = REPO / "templates" / "agent-mandatory-rules.md"
tmpl_named = set()
if tmpl.is_file():
    t = tmpl.read_text()
    tmpl_named = {k for k in re.findall(r"`([a-z0-9][a-z0-9._-]*)`", t) if k in stems}

# --- Observed evidence from metrics ---
observed = collections.Counter()
sug = METRICS / "rule-suggestion.jsonl"
sug_lines = emitted = evaluated = 0
if sug.is_file():
    for ln in sug.read_text().splitlines():
        if not ln.strip(): continue
        sug_lines += 1
        try: d = json.loads(ln)
        except Exception: continue
        # Rows written before the origin suppression carry no "evaluated" key
        # and were all evaluated; rows the hook skipped carry evaluated=false.
        # Counting them in the denominator would make the emission ratio drift
        # downward for a reason that has nothing to do with the rules.
        if d.get("evaluated", True): evaluated += 1
        if d.get("threshold_met"): emitted += 1
        for m in d.get("matches", []):
            if m.get("confidence", 0) >= 0.80:
                observed[m.get("rule")] += 1
ctx = METRICS / "contextual-rules.jsonl"
ctx_observed = collections.Counter(); ctx_lines = 0
if ctx.is_file():
    for ln in ctx.read_text().splitlines():
        if not ln.strip(): continue
        ctx_lines += 1
        try: d = json.loads(ln)
        except Exception: continue
        for k in ("rules", "rules_injected", "matched"):
            v = d.get(k)
            if isinstance(v, list):
                for x in v: ctx_observed[str(x)] += 1

# --- Classify ---
rows = []
for f in rule_files:
    s = f[:-3]
    ch = []
    if s in projected: ch.append("projected")
    if s in refkey_resolves: ch.append("refkey")
    if s in router_capable: ch.append("router")
    if s in trigger_reachable: ch.append("trigger(unreg)")
    if s in tmpl_named: ch.append("subagent-tmpl")
    live = [c for c in ch if c in ("projected", "router", "subagent-tmpl")]
    rows.append((s, ch, live, observed.get(s, 0)))

print("=" * 72)
print("RULE LOAD-CHANNEL AUDIT")
print("=" * 72)
print(f"rules/*.md files            : {len(rule_files)}")
print(f"CHANNEL A projected symlinks: {len(projected)}  {sorted(projected)}")
print(f"CHANNEL B ref-keys in COMPACT: {len(refkeys)} distinct, {len(refkey_resolves)} resolve to a rules/*.md")
print(f"          dangling ref-keys  : {len(refkey_dangling)}")
print(f"CHANNEL C router-capable (routing_patterns frontmatter): {len(router_capable)}")
print(f"CHANNEL D contextual_triggers: {len(triggers)} declared, {len(trigger_reachable)} resolve; hook registered={loader_registered}")
print(f"CHANNEL E subagent template names: {len(tmpl_named)}")
print()
print(f"rule-suggestion.jsonl        : {sug_lines} rows ({evaluated} evaluated, "
      f"{sug_lines - evaluated} skipped as not human-authored), {emitted} emitted "
      f"a suggestion, {len(observed)} distinct rules ever named >=0.80")
print(f"contextual-rules.jsonl       : {ctx_lines} rows, {len(ctx_observed)} distinct rules named")
print()

no_live = [r for r in rows if not r[2]]
never_obs = [r for r in rows if r[3] == 0]
no_refkey = [r for r in rows if "refkey" not in r[1]]
print(f"NO LIVE CHANNEL (not projected, not router-capable, not in subagent tmpl): {len(no_live)}")
print(f"NO REF-KEY in RULES-COMPACT: {len(no_refkey)}")
print(f"NEVER OBSERVED named >=0.80 in rule-suggestion.jsonl: {len(never_obs)}")
print()
print("--- dangling ref-keys (point at no rules/<key>.md) ---")
for k in refkey_dangling: print(f"  {k}")
print()
print("--- per-rule table: name | channels | observed_count ---")
for s, ch, live, o in rows:
    print(f"{s:45s} | {','.join(ch) if ch else 'NONE':45s} | {o}")
sys.exit(1 if no_live or refkey_dangling else 0)
