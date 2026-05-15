# Consumer SDD Lane Surgical Review Plan

> Plan to review and correct the product/workflow gaps surfaced by the comparison with `betta-tech/harness-sdd`.

## Purpose

This plan turns the SDD harness workflow audit into a surgical review program. It does not assume that Cognitive OS needs a new large subsystem. The goal is to determine which existing surfaces already solve the problem, which ones need tightening, and which small missing pieces would make the consumer workflow obvious.

The review target is narrow:

> A consumer project should understand how to move one task from intent to verified completion without first understanding the whole Cognitive OS architecture.

## Current Read From The Repo

A quick local read shows that Cognitive OS already has many ingredients, but they are distributed:

| Concern | Existing evidence | Initial interpretation |
|---|---|---|
| SDD phases | `.cognitive-os/skills/cos/sdd-spec`, `sdd-tasks`, `sdd-apply`, `sdd-verify`; `.cognitive-os/workflows/feature-pipeline.yaml`; `.cognitive-os/workflows/bugfix-pipeline.yaml` | The SDD capability exists, but the consumer-facing lane is not as obvious as `harness-sdd`. |
| Executable evidence | `docs/05-Methodology/root/executable-acceptance-specification.md`, `templates/eas.md`, `scripts/eas_validate.py`, ADR-317 | EAS is a strong internal answer for evidence, but it may feel heavier than a first-contact `requirements/design/tasks` lane. |
| Traceability | `.cognitive-os/skills/traceability-check/SKILL.md`, `lib/traceability_checker.py`, EAS gap matrix | Requirement-to-test traceability exists conceptually, but it is not yet the simple SDD reviewer gate for one feature. |
| Workflow substrate | `.cognitive-os/workflows/*.yaml`; workflow-engine plan tombstoned by coexistence with existing lightweight substrate | Do not build a new workflow engine before proving the lane with simple files and gates. |
| Proportionality | ADR-014 SDD fast path; Definition of Done by task size; EAS optional for significant work | There is a potential tension: model-based fast path can skip durable specs even when task risk warrants them. |
| Center-of-gravity compression | product zones, feature reality audit, dashboard demotion, squads tombstone | Some competing centers are already demoted, but first-contact workflow docs can still look architecture-heavy. |
| Cross-harness portability | `rules/cross-harness-authoring.md`, harness projection tests, product zones | Any SDD lane must be canonical and projected; `.claude/agents/*.md` cannot be the source of truth. |

## Surgical Questions

The review answers these questions in order. Do not implement before the corresponding answer is evidenced.

1. **Center of gravity** — Which product-facing surfaces still make Cognitive OS feel like many products instead of one operational layer?
2. **Happy path** — Can a new consumer see one obvious task flow in five minutes?
3. **Vocabulary** — Where do internal terms hide operator value?
4. **Proportionality** — When should SDD/EAS be required, recommended, optional, or bypassed?
5. **Spec durability** — Where should `requirements.md`, `design.md`, `tasks.md`, traceability, and review artifacts live for consumer projects?
6. **State memory** — What is the smallest task-state adapter that works locally before Linear/GitHub/Jira?
7. **Traceability gate** — What exactly must fail when `R<n>` has no test or proof?
8. **Reviewer boundary** — How do we prove the reviewer is independent, narrow, and non-mutating?
9. **Cross-harness projection** — What can Claude do natively, what can Codex do natively, and what must be structural/advisory?
10. **Evidence path** — What demo/test proves the lane without reviving a dashboard or workflow engine?

## Review Workstreams

### WS1 — Center-of-Gravity Inventory

**Goal:** identify which surfaces still compete with the wedge in first-contact material.

Inspect:

- `README.md`
- `docs/00-MOCs/entrypoints/README.md`
- `docs/08-References/business/durable-product-master-plan.md`
- `docs/08-References/business/feature-reality-audit.md`
- `docs/04-Concepts/root/product-zones.md`
- `manifests/product-zones.yaml`
- dashboard, squads, auto-repair, observability, package-manager, and agent-service docs that are linked from first-contact pages

Output:

- table of surfaces: `core`, `compatibility`, `extension`, `experimental`, `archived`, `tombstone`
- list of first-contact docs where optional/experimental surfaces still receive product-center weight
- proposed wording changes that replace architecture terms with operator outcomes

Acceptance criteria:

```bash
python3 -m pytest tests/contracts/test_product_zones.py -q
```

Manual criteria:

- a cold reader can state the product wedge in one sentence;
- dashboards, squads, auto-repair, observability, and agent service are not presented as required adoption path;
- every optional surface has either a proof path or an explicit optional/experimental label.

### WS2 — Consumer Happy Path Audit

**Goal:** compare the current consumer journey to the desired simple flow.

Desired flow:

```text
find task -> generate spec -> approve -> implement -> review against spec -> save evidence
```

Inspect:

- `docs/05-Methodology/getting-started/core-30-minute-onboarding.md`
- `docs/09-Quality/manual-tests/five-minute-demo.md`
- `docs/09-Quality/manual-tests/proof-paths.md`
- `docs/00-MOCs/workflow.md`
- generated consumer instruction surfaces for Claude and Codex
- installer output and `cos-status` output

Output:

- current consumer journey map
- desired journey map
- gap list with exact missing command/artifact/proof
- decision on whether the command should be `cos sdd next`, a skill invocation, or both

Acceptance criteria:

- the lane can be explained without naming kernel, driver, control plane, or primitive;
- the first command and the next artifact are explicit;
- the demo does not require external services.

### WS3 — Existing SDD/EAS Reconciliation

**Goal:** avoid building a duplicate SDD system.

Inspect:

- `.cognitive-os/skills/cos/sdd-*`
- `.cognitive-os/workflows/feature-pipeline.yaml`
- `.cognitive-os/workflows/bugfix-pipeline.yaml`
- `lib/sdd_pipeline.py`
- ADR-014 SDD fast path
- ADR-317 EAS
- `templates/eas.md`
- `scripts/eas_validate.py`

Key issue:

ADR-014 allows a model-based fast path that skips spec/design/tasks. The new consumer SDD lane should not be governed by model capability alone. It needs a risk/task-size policy:

| Work class | Default |
|---|---|
| Trivial | No SDD; direct change plus minimal verification. |
| Small | No full SDD; existing tests or focused checks. |
| Medium | Lightweight SDD: requirements/design/tasks/review. |
| Large | SDD plus EAS recommended or required by policy. |
| Critical | SDD plus EAS, human approval, audit trail, rollback/security/idempotency checks. |

Output:

- compatibility matrix between current SDD phases, EAS, and proposed lightweight consumer lane
- decision whether `requirements/design/tasks` are a lightweight SDD profile or a subset of EAS
- list of docs/skills that need wording updates

Acceptance criteria:

- no duplicate workflow engine;
- EAS remains the stronger artifact for large/critical work;
- lightweight SDD remains legible for medium work;
- fast path cannot skip durable spec artifacts when task risk requires them.

### WS4 — Task-State Adapter Design

**Goal:** define the smallest task memory surface before integrating external systems.

Start with local-only:

```text
.cognitive-os/workflows/sdd/state.json
.cognitive-os/workflows/sdd/<feature>/requirements.md
.cognitive-os/workflows/sdd/<feature>/design.md
.cognitive-os/workflows/sdd/<feature>/tasks.md
.cognitive-os/workflows/sdd/<feature>/traceability.md
.cognitive-os/workflows/sdd/<feature>/review.md
.cognitive-os/workflows/sdd/progress/current.md
.cognitive-os/workflows/sdd/progress/history.md
```

Canonical states:

```text
pending
spec_drafting
spec_ready
approved
in_progress
review_ready
done
rejected
```

Adapter ladder:

1. local JSON/Markdown
2. GitHub Issues
3. Linear
4. Jira

Output:

- task-state schema
- state-transition rules
- local filesystem layout
- adapter interface contract
- external adapter deferral criteria

Acceptance criteria:

- one feature at a time can be enforced for simple projects;
- interrupted sessions can resume from state file plus artifacts;
- external adapters are not required for the first proof.

### WS5 — Traceability and Reviewer Gate

**Goal:** make review objective and narrow.

Reviewer must check:

- every requirement has a test or accepted non-test proof;
- every task is complete or explicitly deferred/rejected;
- implementation follows design or records an approved design change;
- prohibited files and boundaries were not touched;
- spec, code, tests, and review do not drift;
- test commands were actually run or residual risk is explicit.

Output:

- traceability artifact format
- reviewer checklist
- fail/pass/partial verdict schema
- test fixture with an intentionally missing requirement-to-test mapping

Acceptance criteria:

```text
R1 -> tests/test_x.py::test_y -> PASS evidence
R2 -> MANUAL-PROOF accepted by human -> residual risk named
R3 -> MISSING -> reviewer FAIL
```

The reviewer gate should fail on missing mappings by default for medium+ SDD work.

### WS6 — Cross-Harness Projection Review

**Goal:** keep the lane canonical while projecting to supported harnesses.

Inspect:

- `scripts/cos_init.py`
- `scripts/generate-project-settings.sh`
- `scripts/_lib/settings-driver*.sh`
- `.codex/` projection tests
- `.claude/` projection tests
- `rules/cross-harness-authoring.md`

Projection policy:

```text
canonical SDD lane contract
  -> harness capability matrix
  -> Claude native agent projection where available
  -> Codex AGENTS/protocol/hook projection where available
  -> structural advisory projection where native lifecycle hooks are missing
  -> runtime evidence per harness
```

Output:

- projection capability matrix for the SDD lane
- required tests for Claude and Codex
- list of claims that must be worded as structural/advisory rather than enforced

Acceptance criteria:

- no `.claude/` file is the canonical source;
- Claude and Codex both receive usable instructions;
- docs label any lifecycle parity gap honestly.

### WS7 — Demo and Proof Path

**Goal:** prove the lane with a five-minute consumer workflow, not a dashboard.

Demo shape:

```bash
cos sdd next --store local --feature example
cos sdd approve example
cos sdd apply example
cos sdd review example
```

If CLI implementation is deferred, the first proof may be a script or documented manual path, but it must still write the same artifacts.

Output:

- manual proof path
- fixture project
- smoke command or script
- before/after artifact tree

Acceptance criteria:

- demo runs without Linear/Jira/GitHub API;
- demo writes requirements/design/tasks/traceability/review/history;
- demo proves at least one failing traceability case and one passing case.

## Sequenced Plan

### Phase 0 — Audit Only

- Run WS1 through WS6 as read-only reviews.
- Produce a findings table with `keep`, `demote`, `reuse`, `change`, `build` decisions.
- Do not add a new runtime surface yet.

Exit criteria:

- exact overlap with SDD/EAS/traceability is known;
- the risk of duplicate workflow machinery is closed;
- the minimum lane shape is agreed.

### Phase 1 — ADR and Contract

- Write an ADR for the consumer SDD lane.
- Define task-state schema and artifact names.
- Define proportionality policy by work class.
- Define reviewer non-mutation and no-self-approval rules.

Exit criteria:

- ADR accepted or explicitly rejected;
- no implementation without contract.

### Phase 2 — Local Filesystem Proof

- Implement or script the local JSON/Markdown adapter.
- Add templates for requirements/design/tasks/traceability/review.
- Add one-feature-at-a-time guard for local mode.
- Add resumability from state file.

Exit criteria:

- disposable project can run one local SDD flow;
- interrupted state can resume;
- history is append-only.

### Phase 3 — Traceability/Reviewer Gate

- Implement requirement-to-test/proof validation for lane artifacts.
- Add failing and passing fixtures.
- Wire reviewer output to Trust Report/evidence conventions.

Exit criteria:

- missing `R<n> -> test/proof` fails;
- reviewer cannot mutate implementation artifacts;
- partial verdict requires explicit residual risk.

### Phase 4 — Cross-Harness Projection

- Project lane instructions to Claude and Codex.
- Add projection tests.
- Label unsupported native lifecycle behavior as advisory.

Exit criteria:

- Claude and Codex fresh installs receive the lane contract;
- tests prove no Claude-only source of truth leaked.

### Phase 5 — Product Demo and Documentation Compression

- Add a five-minute consumer SDD demo.
- Update first-contact docs to say “work this way tomorrow”.
- Demote or remove links that distract from the lane in first-contact material.

Exit criteria:

- cold reader can run the demo;
- optional systems remain optional;
- product docs lead with operator outcomes.

### Phase 6 — External Task Adapters

Only after local proof:

- GitHub Issues adapter;
- Linear adapter;
- Jira adapter.

Exit criteria:

- adapters implement the same state transition contract;
- no external adapter changes the canonical artifact semantics.

## Non-Goals

- Do not revive the tombstoned workflow engine plan.
- Do not make dashboards part of the proof path.
- Do not make squads the consumer workflow model.
- Do not require EAS for trivial or small work.
- Do not make Claude Code subagents the canonical architecture.
- Do not introduce Linear/Jira/GitHub API dependencies before local mode works.

## Findings To Verify During The Review

These are hypotheses, not yet final decisions:

1. Existing EAS is strong enough for large/critical work, but too heavy as the first visible medium-task artifact.
2. Existing SDD skills can be reused if their output contracts are aligned with `requirements/design/tasks/traceability/review` artifacts.
3. ADR-014 fast path should be constrained by task risk, not only model capability.
4. `traceability-check` likely needs a lane-specific mode rather than only generic docs/feature scanning.
5. Dashboard and squads are already formally demoted, so the bigger issue is first-contact narrative, not runtime removal.
6. Auto-repair and control-plane docs may still need wording demotion where they imply autonomous product-center behavior.

## Acceptance Criteria For The Whole Review

1. A table exists for every cited concern: center-of-gravity, happy path, vocabulary, proportionality, durable spec, task state, traceability, reviewer, and cross-harness projection.
2. Each concern has a decision: `reuse`, `tighten`, `demote`, `build`, or `defer`.
3. The plan identifies exact files to change before any implementation starts.
4. The first implementation slice, if approved, is local-only and testable without external services.
5. The outcome improves the consumer workflow without expanding the product center.

## Suggested First Command Set For The Audit

```bash
python3 -m pytest tests/contracts/test_product_zones.py -q
python3 -m pytest tests/contracts/test_eas_docs_contract.py tests/contracts/test_eas_manifest_and_sdd_wiring.py tests/unit/test_eas_validate.py -q
python3 -m pytest tests/behavior/test_consumer_project_projection.py tests/integration/test_installer.py -q
```

Add targeted commands after WS0 identifies the exact files touched.

## Trust Report

`TRUST_REPORT: SCORE=84 STATUS=HIGH EVIDENCE=5 UNCERTAINTIES=2`

Evidence:

1. Existing SDD skills and workflow YAMLs were inspected.
2. Existing EAS docs, ADR, validator, and integration points were inspected.
3. Product-zone and demotion/tombstone docs show several competing centers are already classified.
4. Onboarding/proof-path docs show the current first-contact path is install/governance-oriented, not consumer SDD-flow-oriented.
5. The prior `harness-sdd` audit provides the reference flow and artifact shape.

Uncertainties:

1. The exact CLI shape should be validated against current `cmd/cos` conventions before implementation.
2. External adapters should wait for consumer demand and connector availability rather than being built speculatively.
