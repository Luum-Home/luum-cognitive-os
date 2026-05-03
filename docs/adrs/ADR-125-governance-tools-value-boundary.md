# ADR-125: Governance Tools Value Boundary

## Status

Proposed — 2026-05-02

## Context

Cognitive OS intentionally adds governance on top of vanilla Claude Code and
other harnesses: memory, SDD workflows, claim verification, audit trails,
preflight gates, snapshots, coverage reports, scorecards, and many hook-driven
checks. This governance is not universally good. It has to earn its runtime
cost.

A session review produced useful evidence:

| Governance primitive | Observed value |
|---|---|
| Engram persistent memory | Vanilla harnesses do not replicate cross-session recall. Being able to resume an SDD proposal/design/tasks thread later without re-explaining context is real value. |
| SDD pipeline | For medium+ changes, `propose → design → tasks → apply → verify` reduces scope creep and preserves design intent. |
| Model routing | Routing cheap/repetitive work away from the most expensive model can preserve quota and reduce cost. |
| Audit trail | Knowing which agent changed what matters when WIP loss, false-done reports, or rebase damage occurs. |

The same session also exposed governance failure modes:

| Failure mode | Evidence | Cost |
|---|---|---|
| False-positive gates | ADR-116 preflight blocked multiple times, including self-collision and validation-capsule cases. | Work time shifted from building to fighting gates. |
| Orphaned snapshots/stashes | Runtime accumulated pre-agent markers and an auto-pre-agent stash preserved edits without restoring them. | Silent WIP loss risk. |
| Overlapping subsystems | Multiple task-claim implementations existed with different file paths and schemas. | Double truth and maintainability risk. |
| Inconsistent path resolution | Hook project-dir resolution and inventory `--project-dir` did not always agree. | Bypasses and diagnostics can inspect different roots. |
| Discovery overload | Agents see large skill/hook surfaces without a clear active/living subset. | Cognitive load and wrong primitive selection. |
| Auto-stash on every sub-agent | Defensive snapshotting before every agent/skill launch created residue when restore was not symmetrical. | Safety primitive became a source of corruption risk. |

The conclusion is not to remove governance. The conclusion is to apply a value
boundary: keep governance that prevents real damage or improves medium+ delivery;
make everything else opt-in, tiered, or maintainer-only. For most solo projects,
vanilla Claude Code plus Engram and a short project instruction file may deliver
most of the value with a fraction of the complexity.

This does **not** apply to the solo maintainer swarm persona: one operator using
multiple IDEs/harnesses, multiple sessions, and multiple agents across the OS and
consumer projects. That workload has team-scale concurrency and platform-scale
blast radius even with one human. For that case, governance must be evaluated as
an operational safety layer, not as optional process ceremony. Cognitive OS earns
default use when its net productivity ROI is positive, and for solo swarms the
prevented-damage side of that ROI is materially higher than for ordinary solo
projects.

## Decision

Adopt a governance value boundary with three classes:

| Class | Runtime default | Criteria | Examples |
|---|---|---|---|
| `runtime-safety` | Default in `core`/`team` | Prevents WIP loss, unsafe main landing, secret leakage, or concurrent edit damage. | claim verification, concurrent-write guard, stash auto-reapply, FS reaper, branch/worktree closure, protected landing. |
| `delivery-structure` | Default only when task complexity warrants it | Improves medium+ work quality but should not block trivial work. | SDD pipeline, model routing, audit trail, validation lane recommendation. |
| `meta-governance` | Maintainer/lab only by default | Helps build or audit the SO itself, but does not directly protect consumer work. | primitive harvester, aspirational audit, dogfood scoring, deep scorecards, capability coverage meta-analysis. |

### Boundary rules

1. A governance primitive MUST state which class it belongs to.
2. `runtime-safety` primitives must be low-noise, repair-oriented, and tested for
   false positives before blocking.
3. `delivery-structure` primitives should trigger by complexity, not on every
   trivial change.
4. `meta-governance` primitives must not run in default `core` installs.
5. Duplicate truth sources are not allowed: task claims, project roots, and WIP
   ownership must each have one canonical schema/API.
6. Any auto-snapshot/stash primitive must prove symmetric cleanup in tests before
   it can run by default.
7. Governance must have an ROI dashboard: time saved, incidents prevented, and
   recovery value must be compared against maintenance/debugging/friction cost.
8. Low-use or negative-ROI primitives should be demoted, archived, or moved to
   `lab`; absence should be tested by whether operators miss them over time.

## Consequences

- Governance becomes easier to defend because each primitive has a value class.
- Consumer installs get less meta-infrastructure by default.
- SO maintainer tooling remains available but is no longer confused with runtime
  product value.
- Some existing systems must be consolidated: claim ledgers, path resolution,
  active skill discovery, and snapshot lifecycle.
- Hooks that cannot explain repair intent should not be allowed to block outside
  emergency/security cases.
- Governance can now be removed on evidence, not only added. Archiving unused
  primitives is an accepted hardening action.

## Alternatives rejected

- **Use vanilla Claude Code only**: rejected for multi-session work because
  vanilla primitives do not provide persistent memory, cross-session claims,
  protected landing, or WIP recovery.
- **Keep all governance default-on**: rejected because false positives and
  discovery overload create real velocity loss.
- **Keep duplicate claim/path systems and document them**: rejected because
  documentation does not prevent double-truth bugs.
- **Disable snapshots/stashes entirely**: rejected because WIP recovery is
  valuable; the fix is symmetric lifecycle proof and risk-based triggering.
- **Assume self-use metrics imply productivity**: rejected because dogfooding and
  coverage scores can be positive while net developer productivity is negative.
  The accepted metric is net ROI, not self-reference.

## Verification

Initial verification is documentation-level:

```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
python3 -m pytest tests/audit/test_adr_locations.py -q
```

Future enforcement is tracked in
`.cognitive-os/plans/architecture/governance-tools-consolidation.md`:

```bash
python3 -m pytest tests/audit/test_governance_value_metadata.py -q
python3 -m pytest tests/contracts/test_claim_ledger_single_source.py -q
python3 -m pytest tests/contracts/test_project_root_resolution_contract.py -q
python3 -m pytest tests/integration/test_agent_snapshot_lifecycle_symmetry.py -q
```
