# ADR-126: Agentic Primitive Lifecycle Governor

## Status

Proposed — 2026-05-02

## Context

ADR-120 defines a conversation-to-primitive harvester that can identify repeated
operator/agent patterns and propose new agentic primitives. ADR-124 defines
distribution boundaries (`core`, `team`, `maintainer`, `lab`). ADR-125 defines a
governance value boundary (`runtime-safety`, `delivery-structure`,
`meta-governance`) and requires low-use or negative-ROI primitives to be
demoted, archived, or moved to lab.

Those ADRs are necessary but not sufficient for self-adjusting behavior. If the
OS can auto-create, auto-adjust, or auto-remove hooks, skills, rules, scripts,
or doctors, the lifecycle itself must be governed. Otherwise the SO will repeat
the historical failure mode from ADR-017: agents add primitives faster than they
can be wired, tested, understood, and retired.

The solo maintainer swarm persona makes this more important, not less. One
operator running Claude Code, Codex, multiple sessions, and multiple agents needs
agentic primitives that push the system toward determinism. Self-improvement must
therefore be treated as a controlled promotion pipeline, not as autonomous code
mutation.

## Decision

Introduce an agentic primitive lifecycle governor. Any primitive created,
modified, promoted, demoted, disabled, archived, or deleted by an agent or
self-improvement workflow must move through explicit lifecycle states and must
carry machine-checkable metadata.

### Lifecycle states

| State | Meaning | Runtime behavior |
|---|---|---|
| `candidate` | Proposed by harvester, user, or agent after a repeated pattern is found. | Not projected, not default-on. |
| `sandbox` | Implemented behind an isolated test/manual path. | May run only in explicit validation or lab profile. |
| `advisory` | Emits warnings/metrics but cannot block. | Allowed in maintainer/team profiles when latency budget is proven. |
| `blocking` | Can stop a tool/action. | Requires runtime-safety class, false-positive tests, repair message, and rollback path. |
| `default-on` | Projected by default for a distribution/profile. | Requires sustained positive ROI and low-noise evidence. |
| `demoted` | Still available but removed from default runtime. | May remain opt-in or move to lab. |
| `archived` | Removed from active projection and active docs indexes. | Restorable from git/archive path; no settings references. |
| `deleted` | Fully removed after archive/retention window. | Requires bilateral absence proof. |

### Required metadata

Each new or changed primitive must declare, eventually in a canonical manifest:

- `id`
- `kind`: `hook | skill | rule | script | doctor | test | template | manifest`
- `owner_adr`
- `lifecycle_state`
- `maturity`: `observe | advisory | blocking`
- `distribution`: `core | team | maintainer | lab`
- `governance_class`: `runtime-safety | delivery-structure | meta-governance`
- `risk_class`: `advisory | blocking | mutating | destructive`
- `supported_harnesses`
- `projection_targets`
- `runtime_projection` when present in generated harness settings
- `behavior_evidence` explaining whether the primitive observes, advises, or blocks
- `latency_budget_ms` when runtime-facing and blocking
- `evidence_commands`
- `rollback_or_repair_command`
- `sunset_criteria`

Metadata may start in a transitional manifest, but runtime projection must not
infer these fields from prose forever.

### Promotion gates

A primitive may be promoted only when the next state has proof:

1. `candidate → sandbox`: ADR or plan exists, owner is declared, and no duplicate
   primitive already owns the same responsibility.
2. `sandbox → advisory`: targeted unit/behavior tests pass and docs explain what
   the primitive observes.
3. `advisory → blocking`: false-positive border tests pass, the block message is
   repair-first, bypass/repair path is documented, and latency budget is met.
4. `blocking → default-on`: ROI dashboard shows positive net value for the target
   distribution/profile, and chaos or multi-session tests cover realistic races.
5. Any promotion that changes projection must regenerate derived artifacts and
   pass projection parity checks.

### Demotion/removal gates

A primitive may be demoted, archived, or deleted when one of these is true:

- ROI is negative for the target tier over the configured window.
- It duplicates a canonical primitive or source of truth.
- It is noisy: repeated false positives or operator bypasses exceed the allowed
  threshold.
- It is stale: no execution, no references, and no maintainer use during the
  retention window.
- It is unsafe: it can mutate, stash, delete, or block without symmetric cleanup
  and tests.

Removal is archive-first unless the file is generated or explicitly disposable.
High-stakes verbs such as `archived`, `deleted`, `removed`, `wired`, and
`default-on` must satisfy ADR-105 claim verification.

### Self-adjustment constraints

Self-adjusting workflows may propose and patch primitives, but they must not
silently land new runtime behavior. They must:

1. classify the change by lifecycle, distribution, and governance class;
2. run the smallest evidence command set that proves the lifecycle transition;
3. publish a session/event-bus event for other sessions;
4. update derived artifacts or fail before commit;
5. avoid changing active projection when the working tree contains unrelated WIP;
6. require human approval or protected merge-queue landing before default-on or
   destructive behavior changes.

For the solo maintainer swarm, this is the safety valve: the SO can learn, but it
cannot silently rewrite its own operating envelope while multiple IDEs and agents
are live.


### 2026-05-03 Runtime hook inventory hardening

`manifests/primitive-lifecycle.yaml` now contains lifecycle metadata for every
hook projected by `.claude/settings.json` at the time of implementation. The
manifest records 116 runtime-projected hooks plus non-hook lifecycle primitives.

The hardening contract is intentionally anti-aspirational:

- every projected hook must have a manifest entry;
- every runtime-projected hook entry must point to an existing hook file;
- `maturity: blocking` must correspond to a hook with an observable `exit 2`
  path and pytest evidence;
- non-blocking maturity cannot claim a blocking/default-on lifecycle state;
- projected hooks cannot be marked archived, demoted, or deleted.

This does not mean every hook is product-core. Many projected hooks remain
`lab`/`sandbox` or advisory because this repository is the maintainer runtime,
not the minimal consumer distribution.

## Consequences

- Primitive creation becomes slower but safer.
- Auto-generated primitives stay in `candidate`/`sandbox` until evidence exists.
- Demotion and archival become normal hardening actions, not admissions of
  failure.
- Distribution/profile projection can become deterministic because every
  primitive carries explicit metadata.
- The primitive harvester remains useful without becoming an uncontrolled source
  of runtime drift.
- The repo needs a future manifest and tests that enforce metadata completeness,
  promotion gates, and bilateral archive/delete claims.

## Alternatives rejected

- **Let agents freely add/remove primitives**: rejected because it recreates
  primitive sprawl and silent runtime drift.
- **Require human approval for every generated candidate**: rejected because it
  prevents useful advisory/sandbox experimentation.
- **Use documentation only**: rejected because agents need machine-checkable
  lifecycle state and projection gates.
- **Ban self-improvement**: rejected because the SO's value includes learning
  from incidents and repeated workflows.

## Verification

Initial documentation-level proof:

```bash
python3 -m pytest tests/audit/test_adr_contracts.py tests/audit/test_adr_locations.py -q
```

Future enforceable proof:

```bash
python3 -m pytest tests/contracts/test_primitive_lifecycle_manifest.py -q
python3 -m pytest tests/behavior/test_primitive_lifecycle_promotion.py -q
python3 -m pytest tests/behavior/test_primitive_lifecycle_archive_claims.py -q
```
