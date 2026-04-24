# ADR-061 — Focus Narrative and External Evidence

## Status

**Accepted** — 2026-04-24. Fills the 5 gaps identified during the existential
validation check (ADR-059) that ADR-059 Phase 1-3 does NOT cover.

## Context

ADR-059 addresses internal drift (prune, install timing, core-vs-extensions
split). The 2026-04-24 conversation surfaced 5 additional gaps between the
SO's current state and the master plan doctrine
(`docs/business/durable-product-master-plan.md`):

a. **Focus narrative missing** — README still presents 8 centers of gravity.
b. **No reproducible governance demo** — master plan asks for a "short workflow
   that demos the governance value"; none exists.
c. **No competitive positioning doc** — master plan names Hermes/Agent Zero/
   OpenClaw as comparables; no `docs/vs-alternatives.md` explains differences.
d. **No migration path from vanilla/competitors** — users of Hermes or bare
   Claude Code have no doc showing how to layer the SO on top.
e. **Internal-only reliability evidence** — dogfood-score and aspirational-audit
   are committed to local metrics; no public badge or trend surface.

Master plan wedge (verbatim): *"the governance and operational reliability
layer that makes coding agents safe, portable, and measurable in real
repositories"*. The 5 gaps above are what prevent that wedge from being
legible externally.

## Decision

Ship the 5 artifacts below. Each has an explicit owner agent and verification
step. No item is "documented as future work"; all land in this ADR's scope.

### a) README rewrite (governance-layer-first)

- Rewrite `README.md` to present the SO as a **governance layer for coding
  agents**. Lead with what it prevents (fabricated results, unsafe destructive
  ops, unverified completions) not what it contains.
- Move capability lists (skills/hooks/rules counts) below the fold.
- Explicitly state what the SO is NOT: "not an agent framework, not a skill
  catalog, not a dashboard product".

### b) Reproducible 5-minute demo

- New `scripts/demo-governance.sh` that runs in < 5 min and shows:
  1. Launch a sub-agent that would fabricate output
  2. Trust-score-validator catches the missing trust report
  3. Completion-gate blocks a fake "done" claim
  4. Auto-rollback fires on repeated fail
- Script emits a single-screen summary: what fired, what was prevented.
- Referenced from README top section.

### c) Competitive positioning

- New `docs/vs-alternatives.md` comparing Cognitive OS to Hermes, Agent Zero,
  OpenClaw, pi-mono on: scope, governance depth, verification, portability,
  install complexity, test coverage.
- Honest — where each wins and loses.

### d) Migration paths

- New `docs/migration-from/` directory with at least:
  - `from-vanilla-claude-code.md` — adopt SO as governance layer on existing
    Claude Code project
  - `from-hermes.md` — stack SO on top of Hermes skill catalog
- Each doc is recipe-style: commands, diffs, gotchas.

### e) Public reliability evidence

- README badges for: dogfood-score, aspirational-audit REAL%, harness-portability,
  hook-wiring.
- Weekly GitHub Actions cron that:
  1. Runs `scripts/dogfood-score.py --json`
  2. Runs `scripts/aspirational-audit.py --json`
  3. Commits updated badge values to README
  4. Appends JSONL to `.cognitive-os/metrics/public-trend.jsonl`
- Badges use shields.io dynamic JSON endpoint (no hosted service).

## Verification

- `README.md` lead paragraph mentions "governance layer" before any feature list.
- `bash scripts/demo-governance.sh` runs in < 5 minutes with `exit 0` or emits
  a clear summary of what hook fired.
- `docs/vs-alternatives.md` contains ≥ 3 rows (us + 2 comparables minimum).
- `docs/migration-from/from-vanilla-claude-code.md` exists with at least 1
  copy-pasteable command block.
- README has ≥ 2 dynamic badges sourced from `.cognitive-os/metrics/*.json`.
- Weekly cron workflow lands in `.github/workflows/` or equivalent.

## Consequences

### Positive
- Clear external story. Adopters know what they're getting.
- Demo makes value tangible in minutes, not paragraphs.
- Public evidence means trust is verifiable, not claimed.
- Migration docs lower adoption friction for users of competitors.

### Negative
- Maintenance burden: migration docs drift if SO internals change.
- Public metrics expose real scores — if dogfood drops below 60, it's visible.
  (This is intended: the master plan calls for "visible evidence of
  reliability", which has to include bad weeks.)

### Neutral
- Does not change any runtime behavior. Pure documentation + measurement.

## Related

- ADR-027 — SO slimming
- ADR-058 — Langfuse migration (reference for how to ship a crisp ADR + plan)
- ADR-059 — Existential validation (this ADR is the complement)
- ADR-060 — Local-only policy
- `docs/business/durable-product-master-plan.md` — source doctrine
- `docs/safety-mesh.md` — the governance content the demo showcases

## Open questions

1. **Badge hosting**: shields.io dynamic JSON vs self-hosted GH Pages. Start
   with shields.io for zero-infra; revisit if rate-limited.
2. **Migration doc ownership**: who updates `from-hermes.md` when Hermes
   changes? Rule: stale-unless-touched-in-90-days → review gate, similar
   to ADR-059 sunset policy.
