# Primitive Readiness Continuity Plan

> Living execution plan for turning Cognitive OS documentation, scripts, hooks, rules, skills, memory, and harness adapters into governed agentic primitives that can evolve the SO itself and travel across supported agent harnesses.

## Purpose

The repository already contains the core ingredients for self-evolution: lifecycle metadata, primitive audits, coverage scanners, hook projection, skills, rules, reports, and harness drivers. The remaining risk is continuity. The same analysis has appeared across ADRs, reports, plans, and scripts; unless every cycle re-runs the same readiness loop, the SO can drift back into aspirational documentation, dormant scripts, or harness-specific behavior hidden behind universal language.

This document is the continuity contract. Every cycle that touches docs, scripts, primitive metadata, self-improvement, or harness portability must move at least one row through this pipeline:

```text
docs claim or repeated workflow
  -> primitive id
  -> implementation path: hook | skill | rule | script | doctor | template | manifest
  -> lifecycle metadata
  -> evidence command
  -> report row
  -> harness support declaration
  -> package/distribution tier: core | team | maintainer | lab
  -> next-cycle action
```

## Current answer

We are close for the self-hosted maintainer runtime, especially Claude Code and the emerging Codex path. We are not yet at the point where every documented capability and every automation script is a universal, packaged, harness-portable primitive for all IDE agents.

| Capability slice | Current posture | Readiness estimate | Main blocker |
|---|---|---:|---|
| Active SO primitive kernel | Strong | 75-80% | Reduce maintainer/lab surface and keep lifecycle metadata current. |
| Runtime hook projection | Strong for Claude, partial for Codex | 85-90% in Claude maintainer runtime | Harness parity and false-positive/latency proof outside Claude. |
| Skills and rules as reusable primitive surface | Medium-high | 65-75% | More explicit package boundaries and harness-specific projection tests. |
| Scripts as agent tools | Medium | 55-60% | Many scripts are referenced but not promoted to governed primitive rows. |
| Docs as executable truth | Medium-low | 45-55% | Too many docs remain dormant or partial against implementation evidence. |
| Multi-IDE/harness portability | Early-medium | 25-35% | Drivers exist for some surfaces, but support claims are not proven across each named IDE. |
| Universal tools for all agents/projects | Not yet | 40-50% global | Need installable shared/project packages plus harness capability matrix. |

The safe product claim today is: Cognitive OS has a governed self-evolution kernel and a growing primitive toolchain. Claude Code is the strongest runtime. Codex has an emerging governed path. Other IDEs/harnesses require explicit adapters, capability declarations, and proof before universal support can be claimed.

## Baseline from 2026-05-04 local audit

Commands used for this pass:

```bash
python3 scripts/active_primitive_index.py --project-dir . --human
python3 scripts/primitive_gap_snapshot.py --project-root . --json
python3 scripts/primitive_coverage.py --project-dir . --adapter cognitive-os --format json
```

Observed baseline:

| Signal | Result |
|---|---:|
| Lifecycle manifest rows | 154 |
| Active primitives | 51 |
| Runtime-active primitives | 24 |
| Default-visible primitives | 11 |
| Runtime coverage for projected hooks | 1.0 |
| Primitive coverage rows scanned | 1259 |
| Coverage average score | 64.3 |
| Coverage actionable gap rows | 0 |
| Current gap snapshot overall risk | high |

Family posture from the same pass:

| Family | Count | Avg score / evidence | Status summary | Next action |
|---|---:|---:|---|---|
| docs | 507 | 54.1 | 128 partial, 379 dormant | Map claims to primitive ids or downgrade/archive stale claims. |
| scripts | 139 | 59.4 | 94 partial, 45 dormant | Classify every script as primitive, maintainer tool, migration, lab, or archive. |
| skills | 165 | 75.0 | 165 partial | Add lifecycle/package metadata and prove harness projection. |
| hooks | 258 | 82.9 | 132 real, 111 partial, 15 dormant | Close high-risk hook rows and keep latency/false-positive evidence fresh. |
| rules | 112 | 69.0 | 112 partial | Connect each rule to hook/skill/script enforcement or mark as context-only. |
| config/projection | 78 | 48.6 | 22 partial, 56 dormant | Separate generated, reference, driver, and runtime config surfaces. |

Gap snapshot rows that make the current risk high:

| Family | Evidence | Severity | Required response |
|---|---|---|---|
| hooks | row-audit proven=99, partial_nonblocking=133, actionable_gaps=2 | high | Close actionable hook rows or demote them from active claims. |
| metrics | row-audit proven=90, partial_nonblocking=25, actionable_gaps=3 | high | Prove, wire, or retire metrics files/claims. |
| docs_adrs | docs_hard_gaps=3, mapped_claims=390, done_with_proof=169 | high | Fix stale or unproved docs claims before expanding new architecture. |

## Primitive families to review every cycle

### Documentation claims

Documentation is a primitive candidate source, not proof by itself. Every durable claim must be `implemented`, `decision-only`, `plan`, or `stale`. Implemented claims link to primitive id and evidence command. Decision-only docs must not imply runtime behavior. Plans need acceptance criteria. Stale docs are updated, archived, or classified through ADR closure policy.

Cycle command:

```bash
python3 scripts/docs_execution_audit.py --project-dir . --fail-hard-gaps
```

### Scripts and CLI tools

Scripts must stop being an unbounded automation drawer. Each script must be classified as `agentic-primitive`, `maintainer-tool`, `migration-only`, `driver-specific`, `lab`, or `archive`.

Cycle commands:

```bash
python3 scripts/primitive_readiness_ledger.py --project-dir .
for family in hooks skills rules; do
  python3 scripts/primitive_family_readiness_ledger.py --project-dir . --target-family "$family"
done
python3 scripts/primitive_usage_map.py --project-dir . --target-family scripts --md-out docs/06-Daily/reports/primitive-usage-map-latest.md --json-out docs/06-Daily/reports/primitive-usage-map-latest.json
python3 scripts/primitive_coverage.py --project-dir . --adapter cognitive-os --format markdown --out docs/06-Daily/reports/primitive-coverage-latest.md
```

The script readiness ledger is the canonical machine-readable script role surface. The family readiness ledger provides first-pass role and consumer-accessibility rows for hooks, skills, and rules. Usage and coverage reports remain supporting evidence.

The ledger must also answer whether a script is reachable from a downstream project that implements the SO. A repository-local document or skill reference is not enough: consumer agents in VS Code/Copilot, Cursor, Windsurf, Google Antigravity, Claude Code, OpenAI Codex, OpenCode, and shell/CI only get a script when an install/profile/projection path exports it. The `consumer_accessibility` field separates:

- `install-profile-managed`: bootstrap/profile/settings/update surfaces that can affect generated consumer projects and require profile projection proof;
- `lifecycle-declared-consumer-candidate`: core/team lifecycle rows that still need package/install proof per harness;
- `lifecycle-declared-maintainer`: lifecycle rows kept for SO maintainers;
- `skill-referenced-not-projectable`: skill-used scripts that are not yet package/project-visible;
- `so-local-only`: scripts that must not be assumed available outside this repository.

First review priority for scripts:

1. `scripts/active_primitive_index.py` and `scripts/primitive_gap_snapshot.py` remain canonical readiness entrypoints.
2. `scripts/primitive_coverage.py`, `scripts/primitive_row_audit.py`, `scripts/primitive_usage_map.py`, and `scripts/primitive_surface_reduce.py` form the primitive audit loop.
3. `scripts/docs_execution_audit.py` signs docs-claim reality.
4. `scripts/cos_primitive_harvester.py`, `scripts/cos_self_improvement_loop.py`, `scripts/cos_doctrine_proposer.py`, and `scripts/self_improvement_discipline_gate.py` form the propose-only self-evolution loop.
5. `scripts/_lib/settings-driver-*.sh`, `scripts/harness_parity_audit.py`, and provider adapters define portability proof; they must not be bypassed by direct Claude-only assumptions.


### Profile-managed install surfaces

Some scripts install or project primitives automatically according to profile/harness. They are protected through `manifests/primitive-readiness-protected-install-surfaces.yaml` and have candidate rows in `manifests/primitive-lifecycle.yaml`. They should be promoted only after profile projection proof. Do not demote, archive, or downgrade these rows without checking profile projection, generated harness settings, install/update/upgrade paths, and any optional-tool installation flows they control.

### Hooks

Hooks are the strongest runtime primitive family today, but they are also the highest risk because they can block, mutate, or slow agent work. Every runtime-projected hook needs lifecycle metadata, supported harness declaration, behavior evidence, repair-first message, latency budget when runtime-facing, metrics declaration, and projection evidence.

Cycle commands:

```bash
python3 scripts/primitive_family_readiness_ledger.py --project-dir . --target-family hooks
python3 scripts/active_primitive_index.py --project-dir . --json
python3 scripts/runtime_hook_reality.py --fail-on-findings
bash -n hooks/*.sh hooks/_lib/*.sh
```

### Skills

Skills are the intended portable agent-facing UX, but they need package boundaries. Each promoted skill must declare whether it is SO-maintainer only, shared for any project, project-specific, lab/experimental, or a compatibility wrapper around a script/hook.

Cycle command:

```bash
python3 scripts/primitive_family_readiness_ledger.py --project-dir . --target-family skills
```

### Rules

Rules should be context rules, hook-enforced rules, documentation-only doctrine, or deprecated/absorbed rules. A rule that claims enforcement must point to the enforcing hook, script, or test.

Cycle command:

```bash
python3 scripts/primitive_family_readiness_ledger.py --project-dir . --target-family rules
```

### Memory and self-knowledge

Engram and filesystem summaries are continuity primitives. Save repository artifacts first; use Engram only when the MCP tool is actually available; keep session summaries tied to paths and next actions.

### Harness and IDE portability

Universal IDE support is not a binary claim. Each harness gets a capability profile.

| Harness / IDE | Current evidence level | Required next proof |
|---|---|---|
| Claude Code | strongest; native hooks/settings/rules path | Keep runtime projection and hook reality green. |
| OpenAI Codex | emerging; settings driver and governed fallback path exist | Expand lifecycle `supported_harnesses: codex` and projection tests. |
| Cursor | provider/adapter evidence exists, runtime parity incomplete | Produce capability manifest and manual/automated projection proof. |
| Windsurf | provider/adapter evidence exists, runtime parity incomplete | Produce capability manifest and manual/automated projection proof. |
| VS Code Copilot | not yet signed | Define available surfaces: instructions, tasks, MCP, extension hooks, wrappers. |
| Google Antigravity | not yet signed | Audit supported skill/rule/tool formats and create adapter plan. |
| OpenCode | mentioned/evaluated, not signed | Define wrapper or native config projection and tests. |
| Shell/CI | partial support through scripts and GitHub Actions style adapters | Keep CLI entrypoints deterministic and non-interactive. |

Cycle command:

```bash
python3 scripts/harness_parity_audit.py
```

No docs or product surface may claim support for a harness unless that harness has a declared capability profile plus at least one proof path.


## Session summary fallback boundary

The local Markdown file pattern under `.cognitive-os/sessions/` is a recovery artifact, not yet a universal automatic guarantee for every agent in every IDE. The implemented memory lifecycle has two layers:

1. **Projected hook evidence** for supported harnesses. Claude Code and Codex drivers project SessionStart/UserPromptSubmit/Stop memory hooks where their event models support them. These hooks write local JSONL/changelog/git/session artifacts and can remind the agent to save durable memory.
2. **Agent MCP/tool behavior** when Engram tools are available. The agent must call `mem_session_summary`, `mem_save`, and related tools according to the active memory protocol. Shell hooks cannot invoke in-process MCP tools on behalf of the model.

Therefore, a manually written file such as `.cognitive-os/sessions/session-summary-*.md` is acceptable as a last-resort repository artifact when Engram tools are not surfaced, but it must not be described as proof that all IDE agents perform the same memory write automatically. Universal memory support requires a harness capability profile, projected lifecycle hooks or equivalent wrappers, and a doctor/manual proof path for that harness.

Canonical verification remains:

```bash
bash scripts/cos-doctor-memory-lifecycle.sh --harness codex
bash scripts/cos-doctor-memory-lifecycle.sh --harness claude
```

Future harnesses must add equivalent proof before they can claim this lifecycle.


## Coordination preflight

Before a session edits primitive readiness ledgers, lifecycle metadata, profile projection manifests, or generated readiness reports, the agent should acquire an expiring task claim so concurrent IDE sessions can see ownership before starting overlapping work:

```bash
python3 scripts/claim_task.py acquire <task_id> \
  --session-id "$COGNITIVE_OS_SESSION_ID" \
  --agent-id <agent-or-harness> \
  --scope primitive-readiness \
  --expected-file manifests/primitive-lifecycle.yaml \
  --expected-file scripts/primitive_readiness_ledger.py \
  --ttl-seconds 7200
```

This is a coordination primitive, not a file lock. It prevents duplicate logical work when all agents follow the SO contract. Same-file mutation safety still belongs to edit/file-lock primitives such as `edit-coop` and `concurrent-write-guard`.

Relevant implementation: `scripts/claim_task.py` and `lib/task_claim_ledger.py`; broader contract: `docs/04-Concepts/architecture/concurrency-safety-core-consumer-contract.md` and ADR-118.

## Repeatable cycle checklist

1. Acquire or check a task claim for the current primitive-readiness scope when concurrent agents/IDEs may be active.
2. Refresh active primitive index.
3. Refresh primitive gap snapshot.
4. Refresh primitive coverage report.
5. Refresh primitive usage map for scripts, then hooks/skills/rules when touched.
6. Run docs execution audit and fix hard gaps before adding new claims.
7. Review lifecycle manifest changes for distribution, supported harnesses, evidence commands, and rollback paths.
8. Update this document if a new family, harness, or automation loop becomes canonical.
9. Link new artifacts from `docs/00-MOCs/entrypoints/README.md` and `docs/08-References/business/master-plan-checklist.md`.
10. Record session summary with accomplished work, next steps, and relevant files.

Acceptance criteria for a cycle:

```text
ACCEPTANCE CRITERIA:
1. active_primitive_index reports no missing projected hooks.
2. primitive_gap_snapshot has no untriaged high-severity family rows.
3. docs_execution_audit has no hard gaps for docs touched in the cycle.
4. every touched script has a role: primitive, maintainer-tool, migration-only, driver-specific, lab, or archive.
5. every new portability claim names supported harnesses and proof commands.
```

## Promotion policy for universal agent tools

A primitive can be called a shared tool for all agents only when it has a stable primitive id, lifecycle metadata, deterministic invocation, tests or manual proof path, supported harness declaration, graceful unsupported-harness behavior, package placement outside project-specific customizations, and runnable acceptance criteria.

Until then, use narrower language: `maintainer tool`, `Claude-supported primitive`, `Codex-supported primitive`, `lab primitive`, or `project-specific extension`.

## Immediate next backlog

1. Use `scripts/primitive_readiness_ledger.py` as the machine-readable script role ledger; low-confidence script rows are now closed through explicit overrides.
2. Continue with the generated lifecycle backlog for the remaining agentic-primitives without ADR-126 metadata, then add touched-script ratchet gates.
3. Expand harness capability profiles beyond Claude/Codex without claiming full parity.
4. Reconcile stale docs rows with ADR closure policy.
5. Promote only repeated automation loops that already have tests and operator value.
6. Demote or archive dormant scripts that have no consumer or only historical docs references.

## Related artifacts

- `manifests/primitive-lifecycle.yaml`
- `docs/02-Decisions/adrs/ADR-120-conversation-to-primitive-harvester.md`
- `docs/02-Decisions/adrs/ADR-124-cos-distribution-boundaries.md`
- `docs/02-Decisions/adrs/ADR-126-agentic-primitive-lifecycle-governor.md`
- `docs/02-Decisions/adrs/ADR-127-active-primitive-index.md`
- `docs/02-Decisions/adrs/ADR-133-expansion-without-monsterization.md`
- `docs/04-Concepts/architecture/primitive-harvester.md`
- `docs/04-Concepts/architecture/headless-self-improvement-proposer.md`
- `docs/04-Concepts/architecture/self-evolving-doctrine-proposals.md`
- `docs/04-Concepts/architecture/harness-engineering.md`
- `docs/04-Concepts/architecture/harness-driver-parity.md`
- `docs/06-Daily/reports/primitive-gap-latest.md`
- `docs/06-Daily/reports/primitive-coverage-latest.md`
- `docs/06-Daily/reports/primitive-usage-map-latest.md`
- `docs/06-Daily/reports/primitive-readiness-ledger-scripts-latest.json`
- `docs/02-Decisions/adrs/ADR-146-primitive-readiness-ledger.md`
- `docs/04-Concepts/architecture/primitive-readiness-ledger-family-extension.md`
- `manifests/primitive-readiness-script-overrides.yaml`
