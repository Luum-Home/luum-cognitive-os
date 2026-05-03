# ADR-133: Expansion Without Monsterization

## Status

Accepted — 2026-05-03

## Context

Cognitive OS is designed to expand across more PCs, IDE harnesses, concurrent
sessions, and semi-autonomous agents. The current architecture already has the
right expansion seams: adoption layers, harness drivers, Engram memory,
multi-provider dispatch, boring reliability dashboards, maturity labels, and the
ADR-126 lifecycle governor.

The honest expandability score today is **6/10**. With three focused hardening
sprints it can reach **8.5/10**. The blocker is not lack of features. The blocker
is uncontrolled multiplication: every new harness, machine, primitive, or agent
can duplicate state, increase Claude-Code coupling, add brittle string matching,
or promote lab features into the default path without earned evidence.

This ADR turns that diagnosis into an operating rule: expansion is allowed only
when it makes the core smaller, more deterministic, or more portable. Otherwise
the work starts in `lab` and must earn promotion.

## Decision

Adopt an expansion discipline with four non-negotiable controls.

### 1. Lab-first is enforced, not aspirational

Every new agentic primitive starts in `lab`/`sandbox` unless it carries promotion
evidence. Promotion to `core`, `team`, `blocking`, or `default-on` requires a
machine-readable evidence block linked to the control plane, especially
`cos-boring-reliability` output.

The first executable control is `scripts/cos-lab-first-gate`, wired into
architecture readiness as `lab-first-promotion-gate`. It is delta-based: existing
ADR-126 inventory is grandfathered, but new or promoted primitives must prove why
they are not lab-only.

### 2. Portability tax must be visible

Claude Code can remain the richest driver, but it cannot remain an implicit
universal runtime. Any harness-specific primitive must declare its supported
harnesses and projection targets in `manifests/primitive-lifecycle.yaml` and must
remain visible through `manifests/harness-driver-capabilities.yaml` and parity
audits.

Adding a new harness is product work, not a search-and-replace task. A new driver
requires capability manifest entries, settings projection, payload parsing,
portability tests, and honest unsupported/limited gaps.

### 3. Text-matching governance must move toward semantic matching

Guards that scan arbitrary command text or payload JSON are allowed only as a
transitional mechanism. The failure mode is proven: commit bodies, filenames, and
telemetry payloads can accidentally look like operator intent.

The target shape is parser-backed or scoped-field matching:

- Git guards parse argv/subcommands instead of commit-body prose.
- JSONL ledgers inspect scoped keys instead of serializing entire payloads.
- Claim gates validate structured claim fields instead of broad prose snippets.
- Direct-main and destructive-operation guards distinguish local branch context,
  remote operations, and explicit operator intent.

### 4. Federation is a separate product frontier

Single-maintainer, multi-session operation can survive with file locks and local
Engram. Multi-PC and multi-maintainer operation cannot. Federation must become a
first-class project before claiming cluster-grade autonomy:

- Engram sync protocol with conflict handling, not manual rsync.
- Versioned `skills/REGISTRY.lock` so skill catalogs are deterministic across
  machines.
- External lock backend, such as Redis/Valkey, for branch/task/session leases
  when more than one machine writes concurrently.
- Runtime markers that include machine/session identity and have reaper coverage.

## Expansion scorecard

| Vector | Current score | First break point | Required next control |
|---|---:|---|---|
| N PCs | 4/10 | Memory and locks fragment per machine. | Engram federation + external lock backend. |
| N IDEs | 5/10 | New harnesses become driver rewrites. | Driver capability tests and harness-specific ratio budget. |
| N concurrent sessions | 6/10 | Race conditions and WIP ownership drift. | Branch leases, task claims, WIP safety score, merge queue. |
| Autonomous agents | 5/10 | Agents skip readiness and learn to bypass noisy gates. | Mandatory boring-reliability checkpoints. |
| Stronger models | 7/10 | Governance theatre costs more than it helps. | Default-visible gates must be real, measured, reversible. |

## Three-sprint plan

### Sprint 1 — Expansion discipline

- Enforce lab-first promotion for new/promoted primitives.
- Add expansion readiness reporting to architecture readiness.
- Keep core/team surfaces small and evidence-backed.
- Continue replacing substring gates with scoped/semantic matching where incidents
  prove brittleness.

### Sprint 2 — Portability tax visibility

- Add per-primitive harness-specific classification where missing.
- Fail parity when a supported driver event lacks projection.
- Keep limited/unsupported harness gaps visible but non-failing.
- Create driver work packages for Cursor, Continue, and OpenCode only after the
  capability matrix and parser contracts are ready.

### Sprint 3 — Federation foundation

- Harden Engram sync with concurrent-write tests.
- Add deterministic skill registry lockfile.
- Add an external lock-service adapter for multi-machine branch/task leases.
- Add autonomous-agent checkpoints: agents running unsupervised must run the
  control plane every N actions and escalate on non-pass.

## Consequences

- Expansion becomes slower but safer.
- New ideas can still be implemented quickly in `lab`.
- `core` and `team` stop growing by accident.
- The maintainer runtime can remain rich without presenting all richness as the
  product default.
- Claude Code coupling remains allowed when declared, but invisible coupling is a
  readiness finding.
- Demotion is a real lifecycle transition: `hooks/task-completed.sh` is preserved
  but removed from default projection as the first proof that the governor can
  shrink active surface without deleting primitives.

## Verification

```bash
scripts/cos-lab-first-gate --json
python3 -m pytest tests/contracts/test_lab_first_promotion_gate.py -q
python3 scripts/cos_architecture_readiness.py --json
```
