# ADR-059 — SO Existential Validation: Prune, Install Timing, Core-vs-Extensions Split

## Status

**Proposed** — 2026-04-24. 3-phase plan with measurable exit criteria,
tracked in `.cognitive-os/plans/features/so-existential-validation-2026-04-24.md`.

## Context

The SO has grown to 578 classified components (hooks, lib, scripts, skills).
Aspirational-audit 2026-04-24 baseline:

- **REAL 27.8%** — observable runtime use
- **ON_DEMAND 26.4%** — dormant window but test-covered OR @on-demand marker
- **DORMANT 25.9%** — no use, no test, no marker
- **ASPIRATIONAL 12.2%** — refs missing deps or FUTURE
- **METADATA 7.7%** — legit non-behavioral shims

`dormant_aspirational_ratio: 0.381` (target <0.40 — passing after ON_DEMAND
extension, but barely).

dogfood-score: **65.66 / 100**. Worst dimensions:
- `skill_coverage: 16.79` — 114 of 137 skills have NO behavioral test
- `hook_wiring: 43.23` — 88 of 155 hooks unregistered OR untested
- `harness_portability: 54.65` — 205/452 files reference `.claude/` directly

Three existential questions the operator posed:

1. **"Qué tanto es humo?"** — Answered: ~38% (not 64% as initial metric
   suggested before ON_DEMAND distinction).
2. **"Vale más que vanilla Claude Code / Codex?"** — Partially proven (governance,
   memory, dispatch cascade, cross-harness), but ~38% of surface is dead
   weight that burns adoption.
3. **"¿Las promesas (plug-and-play install, auto-improve, DX genial) se cumplen?"**
   — **Not measured** today. Zero empirical test runs. Answering this is the
   point of Phase 2 below.

## Decision

Adopt a 3-phase validation plan with hard exit criteria. If Phase 2 shows
install time > 5 min OR > 3 manual steps, the "plug-and-play" claim gets
demoted publicly (not silently maintained). If Phase 1 fails to hit
ratio <0.25, we either accept the SO as "mid-weight" OR split it further.

### Phase 1 — Aggressive Prune (target: 2 weeks)

**Goal**: `dormant_aspirational_ratio < 0.25` (baseline 0.381).

**Method**:
- Every **DORMANT >180 days** without test, without `@on-demand` marker,
  without reference in any ADR/plan → issue "remove or prove" tagged with
  14-day deadline.
- Every **ASPIRATIONAL** item → either implement the missing dep (with PR)
  OR remove the reference (with PR). No "leave as aspirational" allowed.
- Day 14 cutoff: unresolved items auto-archived via `git mv → docs/archive/`.

**Exit criteria**:
- `dormant_aspirational_ratio < 0.25` (measured by aspirational-audit.py).
- Zero ASPIRATIONAL items in the audit (resolved or removed).
- `docs/archive/` receives the pruned items (not deletion — history preserved).

**Risk**: legitimate low-frequency hooks might get wrongly archived. Mitigation:
the 180-day window + test-coverage check already filter legit sleepers.
Any archived item can be restored from git.

### Phase 2 — Install Timing Test (target: 1 week)

**Goal**: measure the "plug-and-play" claim with data.

**Tool**: `scripts/install-timing-test.sh` (NEW):

```bash
#!/usr/bin/env bash
# Runs a clean install of the SO in a tmp dir, times end-to-end, counts
# manual steps required. Emits JSONL to .cognitive-os/metrics/install-timing.jsonl.
set -euo pipefail
tmp=$(mktemp -d -t cos-install-XXXX)
cd "$tmp"
start=$(date +%s)
git clone <repo-url> fresh-cos
cd fresh-cos
time_setup=$(time bash scripts/setup.sh 2>&1)
end=$(date +%s)
elapsed=$((end - start))
echo "{\"timestamp\": \"$(date -u +%FT%TZ)\", \"elapsed_s\": $elapsed, \"setup_output_lines\": $(wc -l <<<"$time_setup")}" \
  >> .cognitive-os/metrics/install-timing.jsonl
```

**Measurements** (per run):
- `elapsed_s`: end-to-end wall clock.
- `manual_steps`: number of times user had to type/confirm/paste.
- `errors`: stderr lines containing `ERROR|FAIL|fatal`.
- `docker_required`: 0 or 1.
- `final_hook_count`: hooks registered after install.

**Exit criteria** (must all hold):
- `elapsed_s < 300` (5 minutes).
- `manual_steps <= 3`.
- `errors == 0`.
- No required Docker container for first-run completion.

If any criterion fails: the "plug-and-play" claim is **demoted** in `README.md`
to "scripted install" with honest time + step count.

### Phase 3 — Core vs Extensions Split (target: 3 weeks)

**Goal**: split the SO into minimal core + opt-in extensions. Default install
is small and digestible.

**Splits**:
- `hooks/core/` — the ~67 hooks currently registered + tested. Default.
- `hooks/extensions/` — the ~88 remaining. Opt-in via `/install-hook <name>`.
- `skills/core/` — the ~23 skills with behavioral tests. Default.
- `skills/extensions/` — the ~114 remaining. Opt-in via `/install-skill <name>`.

**Migration rules**:
- A hook/skill graduates from `extensions/` → `core/` when it has:
  - Registered in `apply-efficiency-profile.sh` (default profile)
  - ≥1 behavioral test
  - ≥1 observable run in 7d (per aspirational-audit)
- Demotion `core/` → `extensions/` if any criterion drops for >30 days.

**Install experience**:
- Default `bash scripts/setup.sh` installs core only (target: <3 min).
- `bash scripts/setup.sh --full` installs everything (current behavior).
- `/install-skill <name>` from any core session pulls one extension on-demand
  with dep resolution.

**Exit criteria**:
- `scripts/install-timing-test.sh` under default mode: <3 min, 0 manual steps.
- `tests/contracts/test_core_extensions_split.py` asserts:
  - Every file in `hooks/core/` is registered in default profile.
  - Every file in `skills/core/` has a test that asserts behavior.
  - No file in `hooks/extensions/` or `skills/extensions/` is referenced by
    default profile or by any `core/` component.

## Consequences

### Positive
- SO goes from "heavy blob" to "lean kernel + modular extensions" — matches
  the operator's stated direction.
- Adoption friction drops: new user sees 23 skills + 67 hooks, not 137 + 155.
- Measurement replaces intuition: phase 2 tells us whether to keep the PnP
  claim or demote it.
- Prune pressure (Phase 1) prevents future bloat via a documented cycle.

### Negative
- Migration work: 114 skills + 88 hooks to classify and potentially move.
  ~20-30 hours of human+agent effort distributed over 3 weeks.
- Risk of archiving legitimate rarely-used components (mitigated by 180-day
  window + test-coverage filter).
- Extensions on-demand install adds UX complexity. Users must know which
  skill they need.

### Neutral
- The 38% "humo" number is a snapshot. It moves as the repo changes. Phase 1
  pushes the number down; Phase 3 redefines the denominator (core only).

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Keep status quo + add a "featured skills" doc | Doesn't reduce install size, doesn't change the measurable ratio. Cosmetic only. |
| Rewrite SO from scratch as minimal kernel | Destroys 160 REAL components that work today. Throwing the baby out. |
| Only do Phase 1 (prune) | Misses the install-timing reality check. Can't answer "vale vs vanilla" without Phase 2+3. |
| Only do Phase 3 (split) | Doesn't address ASPIRATIONAL items. They need prune (Phase 1) even after split. |

## Verification

See plan file `.cognitive-os/plans/features/so-existential-validation-2026-04-24.md`
for the day-by-day execution ledger with KPI snapshots per milestone.

Primary metrics (queryable any time):
- `scripts/aspirational_audit.py --json | jq .dormant_aspirational_ratio`
- `scripts/dogfood_score.py --json | jq .overall`
- `.cognitive-os/metrics/install-timing.jsonl` (after Phase 2)

## Rollback

- Phase 1: each archived item is restorable via `git mv docs/archive/... original/path`.
- Phase 2: install-timing script is additive — no rollback needed.
- Phase 3: `hooks/core/` and `hooks/extensions/` can re-merge into flat `hooks/`
  via `mv hooks/core/* hooks/ && mv hooks/extensions/* hooks/`. Same for skills.

## Related

- ADR-027 — SO Slimming (predecessor, WS1-WS3 shipped)
- ADR-028 — SO Reliability & Observability
- ADR-031 / ADR-041 — Continuous classifier (underlying measurement)
- ADR-054 — Project docs convention (adopters; this ADR is about the SO itself)
- ADR-058 — Langfuse migration (recent prune precedent; sets pattern)
- `.cognitive-os/plans/features/stabilization-mega-plan.md` — superseded
  predecessor (earlier attempt at same problem, without hard phases)

## Open questions

1. **Extensions distribution**: should `/install-skill <name>` pull from this
   repo (central) or support arbitrary Git URLs? Central keeps auditable;
   arbitrary enables community contributions. Defer to Phase 3 week 2.
2. **Scope creep during prune**: Phase 1 may reveal that some DORMANT items
   block an aspirational feature the operator wants. Rule: if operator names
   the feature by day 14, resolve via Phase 4 (new ADR per feature). Otherwise
   archive.
3. **Non-interactive install**: `scripts/install-timing-test.sh` assumes no
   prompts. If current `setup.sh` has interactive prompts, Phase 2 requires
   first making install headless. Count that as Phase 2 prerequisite.
