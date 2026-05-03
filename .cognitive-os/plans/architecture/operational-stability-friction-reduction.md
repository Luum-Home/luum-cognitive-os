# Operational Stability and Friction Reduction Program

## Goal

Make Cognitive OS boringly reliable under real multi-agent work while reducing
friction for low-risk flows. The target operator experience is:

```text
SAFE TO WORK: yes
SAFE TO LAUNCH AGENT: yes
SAFE TO PUSH: no
reason: main is ahead of origin by 1 commit
repair: push through protected landing path
```

The SO should protect against WIP loss, main corruption, projection drift, and
concurrent-agent races without treating every hygiene artifact as a critical
incident.

## Operating principles

1. **Risk proportionality**: block only when the risk is data loss, unsafe main
   landing, or known-invalid generated state.
2. **Repair before blame**: every block must explain the safe next action.
3. **Profiles over bypasses**: lower-friction work should use `lean` or
   `observe`, not ad hoc killswitches.
4. **Evidence before strictness**: guards graduate to `block` only after tests
   cover false positives and production exceptions.
5. **One status surface**: agents should not run five diagnostics to understand
   if they can proceed.

## Relationship to ADR-124 distribution tiers

ADR-123 lowers friction by changing behavior; ADR-124 lowers friction by
changing packaging. Profiles (`lean`, `standard`, `strict`) tune how strict an
installed primitive is. Distribution tiers (`core`, `team`, `maintainer`, `lab`)
decide which primitives are installed or projected by default. Both dimensions
are required: a solo project should run `core + lean/standard`, while SO
maintainers may run `maintainer + strict`.

## Phase 1 — Friction audit and blocker telemetry

### Deliverables

- `cos status --json` or equivalent report listing:
  - top blocking hooks;
  - top warning hooks;
  - hook p95 latency by event;
  - manual cleanup frequency;
  - bypass usage;
  - false-positive candidates.
- Metrics normalization for hook outcomes: `observe`, `warn`, `block`,
  `auto_repair`, `bypass`, `latency_ms`.

### Border cases

- Hook exits `2` without structured reason.
- Hook times out or is killed by safe mode.
- Same blocker repeats across sessions.
- A warning produces more operator cost than the work it protects.

### Acceptance

- [ ] A single command prints the current top friction sources.
- [ ] At least 10 recent blocker events can be attributed to hook + reason.
- [ ] Hook latency distinguishes real body latency from wrapper/kill/safe-mode.

### Validation

```bash
python3 -m pytest tests/unit/test_hook_latency_observability.py -q
python3 -m pytest tests/behavior/test_cos_status.py -q
```

## Phase 2 — Guard maturity levels

### Deliverables

- `cognitive-os.yaml` supports per-hook maturity:
  - `observe`
  - `warn`
  - `block`
  - `emergency`
- Hook wrapper passes `COS_GUARD_MATURITY` and `COS_PROFILE` to each hook.
- Contract test fails if a new hook defaults to `block` without exception tests.

### Border cases

- Emergency guard must block even in `lean`.
- `observe` must record evidence without changing exit code.
- `warn` must be visible but not block tool execution.
- Existing killswitches must remain auditable during migration.

### Acceptance

- [ ] Each registered hook has maturity metadata or inherits a documented default.
- [ ] New hooks start `observe`/`warn` unless ADR-approved.
- [ ] Maturity is included in hook-quality manifest/report.

### Validation

```bash
python3 -m pytest tests/contracts/test_hook_quality_manifest.py -q
python3 -m pytest tests/audit/test_guard_maturity.py -q
```

## Phase 3 — Adaptive profiles

### Deliverables

- Profiles: `lean`, `standard`, `strict`.
- Profile resolver computes the active profile from:
  - current branch (`main` is stricter);
  - dirty/staged state;
  - number of worktrees;
  - active task claims/resource leases;
  - stashes/pre-agent markers;
  - landing intent;
  - files changed.
- Operator override is logged.

### Border cases

- Feature branch with one clean file edit should not inherit release strictness.
- Dirty main with active worktrees should become strict.
- Validation capsule should suppress mutating hooks but not blind the status
  report.
- Manual override should expire or be scoped.

### Acceptance

- [ ] `cos profile explain` shows why the profile was selected.
- [ ] `lean` still protects secrets and destructive operations.
- [ ] `strict` is selected for main landing and multi-agent contention.

### Validation

```bash
python3 -m pytest tests/unit/test_profile_resolver.py -q
python3 -m pytest tests/behavior/test_adaptive_profiles.py -q
```

## Phase 4 — Repair CLI and safe reapers

### Deliverables

- `cos repair --dry-run` lists safe repairs with risk class.
- `cos repair --safe --apply` performs only reversible cleanup:
  - stale copy-only markers;
  - expired task claims;
  - dead session markers;
  - clean merged agent worktrees;
  - stale validation capsules after backup.
- Each repair emits backup path or proof that no backup is needed.

### Border cases

- Live PID but stale timestamp.
- Dead PID but dirty worktree.
- Stash with file overlap against current WIP.
- Marker references missing snapshot/stash.
- Worktree branch merged but worktree dirty.

### Acceptance

- [ ] Dry-run is default.
- [ ] No repair deletes uncommitted work without backup and explicit selector.
- [ ] Re-running safe repair is idempotent.

### Validation

```bash
python3 -m pytest tests/behavior/test_cos_cleanup_preserved_wip.py -q
python3 -m pytest tests/behavior/test_branch_worktree_closure.py -q
python3 -m pytest tests/chaos/test_cleanup_reaper_races.py -q
```

## Phase 5 — Unified `cos status`

### Deliverables

`cos status` must answer four operational questions:

```text
SAFE TO WORK: yes/no
SAFE TO LAUNCH AGENT: yes/no
SAFE TO VALIDATE: yes/no
SAFE TO PUSH: yes/no
```

For every `no`, include:

- reason;
- severity;
- owning primitive;
- repair command or skill;
- whether it is hygiene or corruption risk.

### Border cases

- Main ahead but otherwise clean.
- Worktree count > 1 with no stashes or dirty state.
- Active validation capsule.
- Hook projection drift.
- Generated artifact drift.

### Acceptance

- [ ] Agents can use one command before launch and before landing.
- [ ] Output has stable JSON for hooks and human text for operators.
- [ ] Status distinguishes hygiene warnings from blockers.

### Validation

```bash
python3 -m pytest tests/unit/test_cos_status_cli.py -q
python3 -m pytest tests/behavior/test_cos_status_operator_messages.py -q
```

## Phase 6 — Diff-aware validation lanes

### Deliverables

- Lane taxonomy:
  - `fast`: under 1 minute;
  - `landing`: 2–5 minutes;
  - `laptop`: full local confidence;
  - `full`: CI/nightly;
  - `chaos`: multi-agent stress/manual or scheduled.
- Diff classifier recommends lane and targeted tests.
- Landing reports include lane used and why it was sufficient.

### Border cases

- Hook changes require hook + integration lane.
- ADR-only change requires ADR audit and link checks.
- Projection changes require derived-artifact gate.
- Snapshot/stash changes require restore/recovery tests.
- Test-only changes require affected test lane plus audit if contracts changed.

### Acceptance

- [ ] `cos validate --recommend` prints lane + commands.
- [ ] Merge queue records recommended lane and executed lane.
- [ ] `make test-laptop` remains available but is no longer the only trusted
      confidence story.

### Validation

```bash
python3 -m pytest tests/unit/test_validation_lane_recommender.py -q
python3 -m pytest tests/behavior/test_merge_queue_validation_lane.py -q
```

## Phase 7 — Distribution boundary implementation

### Deliverables

- Add `distribution: core | team | maintainer | lab` metadata to hooks, skills,
  scripts, and doctors.
- Build a distribution resolver that can answer: "what runs in core?"
- Project only `core` primitives in the default install path.
- Move primitive harvester, aspirational audit, dogfood scoring, deep scorecards,
  and large chaos tests to `maintainer` or `lab` projection.
- Add docs that present COS as modular safety primitives before presenting the
  full platform.

### Border cases

- A `core` primitive depends on a `maintainer` helper.
- A hook is security-critical but high-friction.
- A maintainer-only contract accidentally blocks a consumer project.
- A lab primitive writes metrics in a default install.

### Acceptance

- [ ] Default install path includes only `core` unless explicitly configured.
- [ ] Every projected primitive has distribution metadata.
- [ ] `cos status` reports active distribution and profile.
- [ ] Maintainer/lab tooling is available but not in the default runtime path.

### Validation

```bash
python3 -m pytest tests/audit/test_distribution_metadata.py -q
python3 -m pytest tests/contracts/test_core_distribution_projection.py -q
python3 -m pytest tests/behavior/test_core_install_is_low_friction.py -q
```

## Phase 8 — Productization threshold

### Exit criteria

Cognitive OS can be considered operationally stable enough for default-on use
when all are true:

- [ ] `cos status` reports safe/unsafe states accurately in fixture repos.
- [ ] False-positive blocker rate is tracked and trending down.
- [ ] Safe repairs are idempotent and covered by race tests.
- [ ] New guards cannot enter `block` without maturity metadata and tests.
- [ ] Merge queue / protected landing is the default path for main.
- [ ] Multi-agent chaos suite covers N=10/20/50 contention without deadlocks.

## Implementation order

1. Friction telemetry.
2. Guard maturity metadata.
3. Repair CLI for safe hygiene cleanup.
4. Unified status CLI.
5. Adaptive profiles.
6. Diff-aware validation lanes.
7. Distribution boundary implementation.
8. Chaos/productization threshold.
