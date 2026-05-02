# ADR-121: Foundation Hardening Program

## Status

Accepted — 2026-05-02

## Context

Cognitive OS is now large enough that reliability failures are no longer caused
only by individual bugs. The recurring instability pattern is systemic:
concurrent agents create WIP while validation is running, full laptop validation
is expensive and exposes cross-hook interactions, new guards sometimes block
legitimate operations, leftover agent branches/worktrees need an explicit
closure protocol, and main still needs a stronger single-writer operational
model.

The system already has the right primitives in partial form: validation capsules,
merge queue, direct-main guard, task claims, resource locks, hook scorecards,
ADR/audit contracts, and chaos tests. The next step is to harden these into
production-style operating invariants so agents cannot rely on memory,
instructions, or polite coordination.

## Decision

Adopt a phased foundation-hardening program with six ordered invariants:

1. **Validation capsules are protected transactions.** A validation run owns an
   immutable HEAD snapshot and no cleanup, reaper, hook, or helper may delete or
   mutate its capsule while its PID/heartbeat indicate liveness.
2. **Main is single-writer.** Main landings must go through a governed merge
   queue or equivalent protected path that revalidates against the current
   remote head immediately before push. Leftover agent branches/worktrees are
   closed through the `branch-worktree-closure` primitive: classify, rebase,
   validate, land through the queue, then remove only after ancestry proves the
   work is in `main`.
3. **WIP has explicit ownership.** Tasks, files, domains, stashes, worktrees, and
   generated projections have claim/lease records with TTL and conflict output.
4. **Guards have maturity levels.** New guards start in `observe` or `warn`, then
   graduate to `block` only after tests cover legitimate production exceptions.
5. **Test lanes express operational intent.** Fast, landing, laptop, full, and
   chaos lanes must have distinct budgets, ownership, and failure semantics.
6. **Chaos validates multi-agent reality.** Swarm tests must exercise concurrent
   agents, validation, cleanup, merge, stash, projection, and reaper races.

This program is not a single feature. It is the acceptance framework for the next
set of ADR-116/118/113/119 hardening slices.

## Consequences

- Validation failures should become attributable to a named invariant instead of
  ad hoc local state.
- Agents can run concurrently with less dependence on conversation discipline.
- New guard rollouts become safer because strict blocking is earned by evidence.
- Laptop validation remains useful but is not the only confidence mechanism.
- More tests will be chaos/edge-case oriented and may increase runtime until lane
  taxonomy and budgets are tuned.

## Alternatives rejected

- **Rely on agent instructions and memory**: rejected because recent failures
  showed agents forget ownership context and can mutate while validation runs.
- **Run only bigger full-suite validation**: rejected because runtime alone does
  not prevent races, stale cleanup, or main-head drift.
- **Disable new guards until perfect**: rejected because guards are necessary;
  they need staged maturity levels and border-case tests instead.
- **Treat multi-agent collisions as operator cleanup**: rejected because the SO
  must make collision/overwrite states explicit and fail safe in production.

## Verification

Each phase must add repository artifacts and executable tests before it is marked
complete:

```bash
python3 -m pytest tests/unit/test_validation_capsule.py -q
python3 -m pytest tests/behavior/test_cos_cleanup_preserved_wip.py -q
python3 -m pytest tests/chaos/test_swarm_stress.py -q
python3 scripts/derived_artifact_gate.py
make test-laptop
```

Phase-level acceptance is tracked in
`.cognitive-os/plans/architecture/foundation-hardening-program.md` and requires
border cases for live/stale/corrupt locks, concurrent WIP, guard false positives,
main-head drift, branch/worktree closure, rollback, and cleanup/reaper races.
