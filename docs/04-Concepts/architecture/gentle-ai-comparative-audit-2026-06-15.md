# Gentle-AI Comparative Audit — 2026-06-15

## Purpose

Evaluate `Gentleman-Programming/gentle-ai` as an external benchmark for Cognitive OS token efficiency, SDD discipline, persistent process state, multi-agent orchestration, and cross-IDE/CLI projection.

This is a source-level audit and adoption plan, not a code import. Adopted work should be reimplemented as Cognitive OS contracts, tests, and primitives unless a future decision explicitly vendors code with license attribution.

## Snapshot and license boundary

| Item | Evidence |
|---|---|
| Repository | `https://github.com/Gentleman-Programming/gentle-ai` |
| Local audit snapshot | `.cognitive-os/external-source-cache/gentle-ai` |
| Commit inspected | `7f3c8103aed1f60651102a35018b9ccd30653e90` |
| Clone command | `git clone --depth 1 https://github.com/Gentleman-Programming/gentle-ai .cognitive-os/external-source-cache/gentle-ai` |
| Repository license | MIT in `LICENSE` |
| Skill frontmatter nuance | Several embedded skills declare `MIT`; several workflow skills declare `Apache-2.0` in frontmatter. Treat text/code reuse as license-sensitive even though the root repo is MIT. |
| Adoption policy | Pattern-only by default; no prompt/code copying without explicit attribution decision. |

## Validation performed

From the external snapshot:

```bash
go test ./internal/sddstatus ./internal/skillregistry ./internal/pipeline ./internal/components/sdd ./internal/components/filemerge ./internal/app ./internal/model ./internal/catalog -count=1
```

Result: all selected packages passed. Re-ran the same focused package set during the deep-code addendum pass; all selected packages passed again.

From Cognitive OS after the addendum update:

```bash
COS_TEST_PYTHON=.venv/bin/python .venv/bin/python -m pytest \
  tests/unit/test_cos_process_loop.py \
  tests/unit/test_cos_loop.py \
  tests/unit/test_sdd_resume.py \
  tests/behavior/test_sdd_transitions.py \
  tests/behavior/test_sdd_governance.py \
  tests/unit/test_skill_router.py \
  tests/unit/test_so_impact_eval_trigger_hook.py \
  tests/unit/test_cos_so_impact_eval.py \
  -q
```

Result: `187 passed in 52.36s`.

Observed scale from the external snapshot:

- 173 Go test files.
- 2175 `func Test...` entries under `internal/` and `e2e/`.
- 23 embedded `SKILL.md` assets under `internal/assets/skills`.
- 12 embedded orchestrator assets.

## What Gentle-AI is doing well

| Capability | External evidence | Why it matters |
|---|---|---|
| SDD as a first-class state machine | `internal/sddstatus/status.go` exposes structured `Status`, `Dependencies`, `ApplyState`, `NextRecommended`, and `BlockedReasons`. | The agent routes by computed state instead of inferring from prose. This reduces repeated context and phase confusion. |
| Orchestrator/executor split | `internal/assets/*/sdd-orchestrator.md` contains coordinator-only rules; SDD phase skills have explicit executor gates. | Keeps parent context thin and prevents one monolithic thread from reading/writing/testing everything. |
| Mandatory delegation triggers | Orchestrator assets define 4-file, multi-file write, PR/fresh-review, incident, long-session, and fresh-review gates. | Turns “delegate when useful” into an operational contract. |
| SDD preflight | Orchestrator assets require pace, artifact store, PR strategy, and review budget before SDD execution. | Prevents accidental auto-runs, unexpected artifacts, and review-size blowups. |
| Strict TDD only when supported | `sdd-init` detects test runner/capabilities; `sdd-apply` loads `strict-tdd.md` only when `strict_tdd` is active and a runner exists. | Avoids always-on TDD token cost while making TDD enforceable when available. |
| TDD verification audits process, not just final tests | `sdd-verify/strict-tdd-verify.md` checks RED/GREEN/triangulation/safety-net/assertion quality/changed-file coverage. | This is stronger than “tests passed”; it detects fake/weak tests and missing TDD evidence. |
| Skill registry is an index, not a context dump | `internal/skillregistry/registry.go` writes `.atl/skill-registry.md` with paths and descriptions, deliberately not copying full rules. | Reduces prompt bloat while preserving skill source-of-truth loading. |
| Startup skill-registry automation | `internal/components/sdd/inject.go` installs Codex/Claude hooks to refresh skill registry with cache. | Keeps routing fresh without spending tokens on every session. |
| Cross-harness SDD projection | `internal/assets/{claude,codex,opencode,cursor,kiro,kimi,...}` and `internal/components/sdd/inject.go`. | Gentle-AI has concrete per-agent SDD assets instead of one generic doc only. |
| Per-phase model/effort assignment | `internal/components/sdd/inject.go`, `internal/model`, OpenCode profiles and Codex phase effort rendering. | Lets cheap/fast phases stay cheap while design/apply/verify use stronger models. |
| Post-injection verification | `internal/components/sdd/inject.go` checks generated OpenCode settings contain expected orchestrator/subagent/profile keys. | Catches silent projection failures immediately. |
| Pipeline/rollback substrate | `internal/pipeline/*` has prepare/apply/rollback stages with progress events. | Install/sync changes have transactional shape and recovery semantics. |
| Review-size economics | `work-unit-commits`, `chained-pr`, and SDD workload forecast require 400-line budget handling. | Reduces review fatigue and failure loops on oversized tasks. |

## What Cognitive OS already has

| Area | Current Cognitive OS evidence | Status |
|---|---|---|
| Agent loop primitives | `scripts/cos-loop-run`, `cos-loop-report`, `cos-loop-guard`, `cos-loop-replay`, `cos-loop-eval`; `docs/04-Concepts/architecture/agent-loop-engineering-runtime.md`. | Strong primitive foundation. |
| Process contract layer | `templates/process-contract.example.yaml`, `scripts/cos-process-loop`, `cos-apply-progress`, `cos-fresh-review`, `cos-verify-report`, `cos-skill-selection-report`. | Strong generic contract, younger than Gentle-AI SDD state. |
| SO-wide impact evaluation | `scripts/cos-so-impact-eval`, `hooks/so-impact-eval-trigger.sh`, `skills/so-impact-eval`. | Better measurement plane than Gentle-AI has in this snapshot. |
| Graph/context optimization | Graphify 8-script suite and `skills/graphify-query`. | Strong context optimization substrate. |
| Token optimization primitives | context budget, preamble budget, context diet, prompt cache, token telemetry/report primitives. | Broad, but real cross-provider telemetry still needs normalization. |
| SDD skills | `skills/sdd-explore`, `sdd-spec`, `sdd-tasks`, `sdd-apply`, `sdd-verify`, `sdd-continue`, `sdd-resume`. | Present, but less state-machine-authoritative than Gentle-AI. |
| Consumer SDD lane | `.cognitive-os/workflows/sdd/` lane and `scripts/demo-consumer-sdd-lane.sh`. | Useful but not yet as orchestrator-native as Gentle-AI SDD. |
| Skill routing | `hooks/skill-router-prompt-suggest.sh`, skill router manifests/benchmarks, generated catalogs. | Strong, but skill registry as runtime path index is different. |
| Cross-harness projection | `.ai` overlay, `.claude`, `.codex`, `.opencode`, harness drivers, lifecycle manifest. | Stronger governance/ACC than Gentle-AI; runtime fidelity varies by harness. |
| Fresh review and adversarial review | `scripts/cos-fresh-review`, `hooks/adversarial-review-gate.sh`, code/pr review skills. | Present, but not yet tied as tightly to SDD dispatcher state. |

## Whole-system functionality comparison

The previous sections call out SDD because that is where the external snapshot is most distinctive, but the adoption question is broader: Cognitive OS should compare the full operating-system surface, not only one workflow. The table below maps complete functional domains.

| Functional domain | Gentle-AI implementation evidence | Cognitive OS implementation evidence | Assessment | Adoption action for COS |
|---|---|---|---|---|
| Installer and sync runtime | `internal/app/app.go`, `internal/cli`, `internal/pipeline`, `internal/installcmd`, `internal/components/*`, `internal/state` | `scripts/cos_init.py`, `scripts/install-cos.sh`, `cmd/cos`, `scripts/cos-install-projection-audit`, install-boundary/lifecycle manifests | Gentle-AI is more cohesive and transactional; COS is broader and consumer-project aware. | Add a reusable transactional install/sync pipeline abstraction with rollback receipts for COS projection writes. |
| Update and self-upgrade | `internal/update`, `internal/update/upgrade`, backup scope by installed agents, checksum/download strategy | release scripts, dependency maintenance hooks, package/version/release gates | Gentle-AI has stronger product-style self-update mechanics; COS has stronger release governance but less end-user self-upgrade UX. | Add an explicit `cos-upgrade-plan` / `cos-upgrade-apply` design with backup scope, checksum verification, and rollback. |
| Cross-agent adapters | `internal/agents/*` for Claude, Codex, OpenCode, Cursor, Kiro, Gemini, Kimi, Qwen, Windsurf, etc. | `.ai/adapters`, `.claude`, `.codex`, `.opencode`, settings drivers, lifecycle support matrices | Both are cross-agent; Gentle-AI is adapter-interface cohesive, COS is manifest/projection cohesive. | Introduce a single typed adapter capability registry for COS so lifecycle claims, settings drivers, and install projection share one source. |
| Asset projection | Embedded `internal/assets/*`, `internal/components/*/inject.go`, post-checks | `.ai/primitives`, `.cognitive-os/skills`, `.claude/skills`, generated settings, primitive lifecycle, projection audits | COS has more surfaces and stronger governance; Gentle-AI has stricter post-injection runtime checks. | Add `cos-projection-postcheck` and require it in primitive closure checklist. |
| Permissions and safety defaults | `internal/components/permissions`, persona/theme injection, agent-specific settings | many hooks: secret, license, protected config, network egress, direct-main, symlink, conflict marker, branch ownership, release guard | COS is substantially stronger as a governance/safety OS. | Keep COS governance mesh; add per-adapter permission summary reports for operator clarity. |
| MCP and persistent memory setup | `internal/components/engram`, `internal/components/mcp`, Engram/context7 injection and verification | memory lifecycle docs/hooks, MCP portability docs, provider/session telemetry, memory governance lib | Gentle-AI gives smoother install/setup for specific MCPs; COS is more policy-oriented and harness-neutral. | Add a `cos-mcp-doctor`/`cos-memory-doctor` user-facing aggregate if current diagnostics stay scattered. |
| Skill delivery | Embedded skills under `internal/assets/skills`, skill presets, `internal/components/skills` | `skills/`, `.cognitive-os/skills`, `.claude/skills`, skill lifecycle, skill router, drift detector, efficacy telemetry | COS has more skill breadth and governance; Gentle-AI has stronger curated workflow bundle. | Keep broad skill set but add curated bundles/presets and a compact path registry. |
| Skill discovery/routing | `.atl/skill-registry.md` path index via `internal/skillregistry` | `lib/skill_router.py`, semantic matcher, router benchmarks, prompt suggestion hooks | COS routing is smarter; Gentle-AI registry is cheaper and simpler. | Add registry as a complement to router, not as replacement. |
| Process and loop engineering | SDD dispatcher, orchestrator assets, pipeline rollback, apply/verify/archive artifacts | `cos-loop-*`, `cos-process-loop`, process contract, fresh review, verify report, loop guard/eval/replay | COS has broader generic loop primitives; Gentle-AI has tighter SDD operationalization. | Extend process-loop to feature-specific dispatchers: SDD, release, bugfix, review, migration, refactor. |
| Testing and TDD | Strict TDD skills, capability detection, verify-phase TDD audit, many Go tests | DoD profiles, stack detection, pytest/behavior/integration suites, consumer smokes, test efficiency targets | COS has broader testing infrastructure; Gentle-AI has clearer TDD workflow enforcement. | Add stack-detected strict TDD primitive and evidence verifier. |
| Review and quality agents | Review personas/assets, Judgment Day agents, fresh-review workflow | adversarial review gate, code review hooks, doc review personas, fresh review script, governance gates | Both strong; Gentle-AI is persona/role polished, COS is gate/policy heavy. | Add review workload forecast and make fresh-review findings first-class process-loop entities. |
| Token/context efficiency | Skill registry, phase prompts, delegation, cached state, model/effort routing | Graphify, context budget, context diet, preamble budget, telemetry, token reports, SO impact eval | COS is stronger on measurement; Gentle-AI is strong on workflow-induced savings. | Measure every adopted workflow pattern with `cos-so-impact-eval`; do not claim unmeasured savings. |
| Product DX / TUI | `internal/tui`, install/sync screens, strict-TDD selection, model/profile controls | CLI/scripts/Make targets, docs, skills, hooks; no equivalent integrated TUI | Gentle-AI has stronger operator UX. | Consider `cos doctor/status` consolidation before a TUI; a TUI is optional after primitives stabilize. |
| Backup/rollback | `internal/backup`, `internal/pipeline/rollback.go`, update backup paths | merge rollback, branch guards, git/stash protection, release freeze | Gentle-AI has install/update rollback shape; COS has git/process safety. | Add rollback receipts for generated projection writes and installer mutations. |
| Release and dependency maintenance | Self-update strategy, version checks, advisory cooldown | release guard, release check, dependency adoption gate, package/dependency maintenance hooks | COS is stronger for repo release governance; Gentle-AI is stronger for installed binary lifecycle. | Add installed-version health report to `cos-doctor` family. |
| Telemetry and impact evaluation | Update/advisory state and workflow state; no controlled SO-wide A/B benchmark found | telemetry libs, token aggregators, SO-impact eval, Graphify benchmarks, skill efficacy reports | COS is ahead for measurement and benchmarks. | Keep COS measurement plane as proof layer for all future adoption. |
| Documentation and decision governance | OpenSpec/skills/docs assets | ADRs, ACC, lifecycle manifests, MOCs, business master plan, projection fidelity | COS is much stronger on durable governance. | Use this advantage to prevent external-pattern adoption from becoming undocumented prompt drift. |

## System-wide adoption backlog

Priority should not be “copy SDD”. It should be “adopt the missing operating-system mechanics across every COS domain”. Ordered backlog:

1. **Typed adapter capability registry**: one COS-owned table for lifecycle events, config paths, subagent support, MCP support, native hooks, projection level, proof level, and postcheck expectations per harness.
2. **Transactional projection pipeline**: prepare/apply/verify/rollback receipts for install/sync/projection operations; use for `.claude`, `.codex`, `.opencode`, `.cognitive-os`, and `.ai` writes.
3. **Projection postcheck primitive**: verify generated assets exist, contain expected keys/commands/hooks, are non-empty, and match lifecycle claims.
4. **Unified `cos status` dispatcher family**: not only SDD. Add status dispatchers for SDD, process-loop, release, dependency maintenance, token budget, Graphify readiness, skill registry freshness, and projection health.
5. **Compact skill registry path index**: cached registry for all projected/user/project skills, integrated with the existing router.
6. **Stack-detected strict TDD plane**: generic testing capabilities detector plus evidence verifier.
7. **Operator UX consolidation**: a single `cos doctor/status` surface before any TUI, summarizing install state, adapters, hooks, MCP/memory, skills, tokens, Graphify, process loops, and release readiness.
8. **Self-upgrade/install health**: backup scope, checksum verification, update advisories, rollback plan, and installed-version report.
9. **Review workload forecast**: line/file/risk estimates before apply/review/release, tied into process-loop and fresh-review.
10. **SO-wide measured adoption loop**: every major adopted pattern gets a `cos-so-impact-eval` ablation before product claims.

## Revised conclusion

The external snapshot is not only a useful SDD reference. It is a compact example of an agent-OS product loop: install/sync, adapter detection, asset injection, memory/MCP setup, skill distribution, workflow dispatch, strict verification, update/rollback, and operator UX live close together. Cognitive OS is broader and more governance-heavy, but the next maturity jump is to make its many primitives feel like one coherent installed operating system. That means transactional projection, typed adapter capabilities, unified status, postchecks, compact registries, and measured adoption across all major features.

## Workflow-specific gaps for Cognitive OS

The system-wide backlog above is the broader adoption plan. The following table keeps the SDD/workflow-specific gaps that originally motivated this audit.

| Gap | Why Gentle-AI is ahead | Recommended COS adoption |
|---|---|---|
| Native SDD status dispatcher | Gentle-AI has one computable status schema with `nextRecommended`, dependencies, blockers, paths, and apply state. | Add `cos-sdd-status` / extend `cos-process-loop status` with a single authoritative JSON schema for SDD and process loops. |
| SDD session preflight | Gentle-AI prevents accidental SDD execution without choices for pace, artifact store, PR strategy, and review budget. | Add `templates/sdd-session-preflight.example.yaml` and a `/sdd-preflight` skill/hook suggestion. |
| Strict TDD mode | Gentle-AI detects capabilities, gates TDD by runner availability, and verifies TDD evidence/weak assertions. | Add `skills/strict-tdd/` plus `cos-testing-capabilities` and `cos-tdd-evidence-verify`. Make it stack-detected and optional. |
| Skill registry as path index | Gentle-AI registry avoids copying full skill rules into context and refreshes via hooks. | Add `cos-skill-registry-refresh` that emits `.cognitive-os/skill-registry.md` as path index, with cache and startup hook. |
| Delegation hard gates | Gentle-AI's orchestrator assets make 4-file/multi-file/test/fresh-review/long-session delegation non-skippable. | Promote COS delegation guidance into `loop-contract.yaml` policies and hook/skill prompts with measurable exceptions. |
| Per-phase model/effort routing | Gentle-AI exposes phase assignments across Codex/OpenCode/Claude/Kiro-like adapters. | Extend COS `lib/execution_profile.py` into a projected per-phase model/effort table in harness adapters. |
| Post-projection self-checks | Gentle-AI verifies generated SDD assets after injection. | Add post-projection checks for generated `.codex`, `.opencode`, `.claude`, and `.cognitive-os` SDD/process assets. |
| Review workload forecast | Gentle-AI's SDD tasks phase gates apply when projected diff size exceeds review budget. | Add `cos-review-workload-forecast` and wire it into `sdd-tasks` and `cos-process-loop`. |
| Phase gatekeeper in auto mode | Gentle-AI validates every phase before launching the next in automatic mode. | Add `cos-phase-gatekeeper` over process-loop/SDD artifacts: contract conformance, artifact existence, no hallucinated paths, no drift, routing coherence. |

## What Cognitive OS does better or more broadly

| Area | COS advantage |
|---|---|
| Primitive lifecycle governance | COS has lifecycle manifest, ACC, registry locks, projection fidelity checks, scope/portability proofs, and DoD gates. |
| Token optimization measurement | COS already has SO-wide eval, Graphify controlled trials, context diet, token savings audit, and telemetry primitives. Gentle-AI is more workflow-disciplined but less measurement-heavy in this snapshot. |
| Consumer-project governance | COS has install scope, consumer projection tests, harness proof levels, and primitive accessibility audits. |
| Hook safety mesh | COS has many deterministic guards: git safety, secret/content/license policy, context budget, duplicate quality, SO impact trigger. |
| External adoption doctrine | COS already has explicit external-tool adoption boundaries and license hygiene. |

## Workflow-specific adoption roadmap

This roadmap covers the SDD/process slice only; system-wide operating-system improvements are tracked in the backlog above.

### Slice 1 — SDD status dispatcher parity

Deliverables:

- `scripts/cos-sdd-status` or `scripts/cos-process-loop status --schema sdd`.
- JSON fields: `schemaName`, `schemaVersion`, `changeName`, `artifactStore`, `planningHome`, `changeRoot`, `artifactPaths`, `contextFiles`, `artifacts`, `taskProgress`, `dependencies`, `applyState`, `actionContext`, `nextRecommended`, `blockedReasons`.
- Tests with no-change, ambiguous-change, missing-change, ready-apply, all-done, verify-ready, archive-ready cases.

### Slice 2 — SDD preflight contract

Deliverables:

- `templates/sdd-session-preflight.example.yaml`.
- `skills/sdd-preflight/SKILL.md` or section in `sdd-continue`.
- Spanish/English localized prompt shapes.
- Store choices in `.cognitive-os/workflows/sdd/session-preflight.json` or process-loop state.

### Slice 3 — Strict TDD portable module

Deliverables:

- `scripts/cos-testing-capabilities` to detect runner/layers/coverage/lint/typecheck/formatter per stack.
- `skills/strict-tdd/SKILL.md` with RED/GREEN/TRIANGULATE/REFACTOR/safety-net evidence contract.
- `scripts/cos-tdd-evidence-verify` to audit evidence, test file existence, current GREEN, assertion quality, and changed-file coverage when available.
- Stack-smoke fixtures for Node, Python, Go, Rust minimal projects.

### Slice 4 — Skill registry path index

Deliverables:

- `scripts/cos-skill-registry-refresh` emitting `.cognitive-os/skill-registry.md` and cache fingerprint.
- Project-first then user/global source order.
- Do not copy full skill rules into registry.
- Hook registrations for Codex/Claude/OpenCode where runtime hooks exist.

### Slice 5 — Phase gatekeeper and review workload forecast

Deliverables:

- `scripts/cos-phase-gatekeeper` over SDD/process-loop phase results.
- `scripts/cos-review-workload-forecast` estimating changed lines/files/risk before apply.
- Wiring into `sdd-tasks`, `sdd-apply`, and `cos-process-loop`.

### Slice 6 — Per-phase model/effort projection

Deliverables:

- Map COS execution profiles to phase assignments.
- Project into supported harness adapters with proof-level caveats.
- Measure token/cost impact using `cos-so-impact-eval` rather than claiming savings from configuration alone.

## Deep source-code comparison addendum

This addendum compares implementation shape, not only feature labels. The external snapshot was refreshed with `git fetch origin main --depth 1` on 2026-06-15; local `HEAD` and `origin/main` both resolved to `7f3c8103aed1f60651102a35018b9ccd30653e90`.

### Codebase shape

| Dimension | Gentle-AI snapshot | Cognitive OS snapshot | Interpretation |
|---|---:|---:|---|
| Primary implementation style | Go CLI plus embedded assets | Python/Bash/Go/TS primitives plus generated projections | Gentle-AI is more cohesive as one binary; COS is broader and more portable, but closure across projections is inherently harder. |
| Files counted for audit | 804 | 21,419 | COS count includes generated/projection-heavy surfaces such as `.cognitive-os`, `.claude`, `.ai`, tests, manifests, and adapters; this explains why primitive changes require more contract closure. |
| Test artifacts | 173 Go test files | 2,074 Python test files plus Go/Bash/TS tests | Gentle-AI has tight Go unit coverage around its core; COS has much broader regression coverage and projection/governance tests. |
| Skills | 29 `SKILL.md` assets | 409 `SKILL.md` surfaces | Gentle-AI keeps fewer phase-focused skills; COS carries generic, projected, and consumer-facing skills. |
| Orchestrator assets | 12 embedded orchestrator assets | 23 orchestrator/process-loop surfaces counted in scripts/docs/assets | Gentle-AI's orchestration is concentrated in SDD; COS has SDD plus loop, process, token, Graphify, and SO-impact planes. |

### Runtime command surface

Gentle-AI exposes a compact native command surface in `internal/app/app.go`: `install`, `sync`, `uninstall`, `doctor`, `skill-registry refresh`, `sdd-status`, and `sdd-continue`. The key design choice is that SDD status and continuation are native CLI commands, not only prompt text.

Cognitive OS exposes many more individual primitives, including `scripts/cos-loop-run`, `scripts/cos-loop-report`, `scripts/cos-loop-guard`, `scripts/cos-loop-replay`, `scripts/cos-loop-eval`, `scripts/cos-process-loop`, `scripts/cos-apply-progress`, `scripts/cos-fresh-review`, `scripts/cos-verify-report`, `scripts/cos-skill-selection-report`, and `scripts/cos-so-impact-eval`. The COS advantage is composability; the gap is that SDD still lacks one native authoritative dispatcher equivalent to Gentle-AI's `sdd-status`.

### SDD state and dispatcher

`internal/sddstatus/status.go` is the strongest transferable design. Its `Status` schema includes `schemaName`, `schemaVersion`, `changeName`, `artifactStore`, `planningHome`, `changeRoot`, `artifactPaths`, `contextFiles`, `artifacts`, `taskProgress`, `dependencies`, `applyState`, `actionContext`, `relationships`, optional `phaseInstructions`, `nextRecommended`, and `blockedReasons`. `resolveNextRecommended` prefers apply over verify while implementation remains, routes to verify when implementation is complete, routes to archive when verification is done, then falls back through missing planning artifacts in dependency order before returning `resolve-blockers`.

COS `scripts/cos_process_loop.py` already computes a generic `next_recommended_action` across source approval, skill selection, apply progress, fresh review, verification, and final verdict. That is broader than SDD, but it is process-contract oriented rather than SDD-artifact authoritative. The adoption should not replace `cos-process-loop`; it should add `cos-sdd-status` or an SDD schema mode that maps SDD artifacts into the same computable process vocabulary.

### Skill registry versus skill router

Gentle-AI's `internal/skillregistry/registry.go` emits `.atl/skill-registry.md`, computes a fingerprint cache at `.atl/.skill-registry.cache.json`, orders project skill directories before user/global directories, and avoids dumping full skill bodies into runtime context. `internal/components/sdd/inject.go` installs Codex/Claude startup automation to refresh that registry quietly.

COS `lib/skill_router.py` is more ambitious: regex triggers, semantic fallback, optional LLM fallback for ambiguous semantic ties, project/profile-aware router cache, prompt suggestions, benchmark fixtures, and tests. The missing piece is the lightweight path-index artifact. A COS skill registry should complement the router: router selects candidate skill; registry gives a compact, current path index; agent still reads the actual `SKILL.md` before acting.

### Projection and post-checks

Gentle-AI's `internal/components/sdd/inject.go` contains dense per-agent projection logic. It injects SDD prompt assets, Strict TDD markers, OpenCode/Kilocode orchestrator prompts, profile orchestrators, phase model/effort assignments, startup skill-registry hooks, plugin files, migration cleanup, and post-checks that fail when required generated keys or SDD skill files are missing. This is narrower than COS but notably strict after generation.

COS projection is stronger in lifecycle metadata and portability accounting: `scripts/cos_init.py`, `scripts/_lib/settings-driver-claude-code.sh`, `scripts/_lib/settings-driver-codex.sh`, `scripts/_lib/settings-driver-opencode.sh`, `.ai/primitives`, `manifests/primitive-lifecycle.yaml`, registry locks, ACC/report artifacts, and consumer projection smokes. The recurring COS risk is partial projection: a primitive can exist as a script while lifecycle, ACC, projection, tests, and generated surfaces lag. The Gentle-AI pattern to adopt is post-projection self-checks for SDD/process primitives, not its exact projection code.

### Strict TDD and verification discipline

Gentle-AI's TDD discipline is capability-gated and evidence-driven: `sdd-init` detects real test runners and test layers; `sdd-apply` loads Strict TDD only when active; `strict-tdd.md` requires RED, GREEN, TRIANGULATE, REFACTOR, and safety-net evidence; `sdd-verify/strict-tdd-verify.md` audits that evidence, changed-file coverage, current GREEN status, and weak or tautological assertions.

COS has stronger stack breadth and DoD culture, but strict TDD is not yet a standalone portable primitive. The correct COS version is stack-detected: `cos-testing-capabilities` should detect runners, lint/typecheck/coverage, and test layers; `skills/strict-tdd/SKILL.md` should be generic across stacks; `cos-tdd-evidence-verify` should audit evidence and avoid requiring TDD when no runner exists.

### Token/context efficiency mechanisms

Gentle-AI optimizes context structurally: smaller orchestrator, skill registry as index, subagent delegation, phase-specific prompts, status dispatcher, cached testing capabilities, and model/effort assignment per phase. The inspected snapshot did not include a controlled A/B token benchmark equivalent to COS SO-impact evaluation.

COS optimizes tokens through explicit measurement and context tooling: Graphify, context budget/preamble budget/context diet, token-savings audit, provider telemetry normalization work, process-loop traces, skill routing, and `cos-so-impact-eval`. COS should measure adoption of each Gentle-AI-inspired pattern with `cos-so-impact-eval` instead of claiming efficiency from architecture alone.

### What to adopt, in COS-owned terms

1. **`cos-sdd-status`**: authoritative SDD artifact/status dispatcher with `nextRecommended`, dependencies, blockers, task progress, verify state, archive readiness, and optional phase instructions.
2. **`cos-skill-registry-refresh`**: path/description registry with fingerprint cache and project-first ordering; never copies full skill bodies.
3. **`cos-testing-capabilities` + `cos-tdd-evidence-verify` + `skills/strict-tdd/`**: stack-detected strict TDD plane with RED/GREEN/TRIANGULATE/REFACTOR evidence.
4. **`cos-projection-postcheck`**: reusable post-projection validator for `.claude`, `.codex`, `.opencode`, `.cognitive-os`, and `.ai` SDD/process assets.
5. **`cos-review-workload-forecast`**: review-size forecast that can split work or require chained PR/process-loop slices before apply.
6. **Per-phase execution profile projection**: map COS execution profiles into SDD/process phases with explicit harness support caveats.

### What not to copy

- Do not vendor prompt text or Go implementation directly in this repo without a separate license/attribution decision.
- Do not collapse COS's lifecycle/ACC/projection governance into a single binary-only mental model; COS's value is portability and consumer-project installability.
- Do not claim token savings from these patterns until `cos-so-impact-eval` or provider telemetry receipts measure them in controlled runs.

### Updated priority

The first implementation slice remains `cos-sdd-status`, but the source audit sharpens its acceptance criteria: it must be able to replace prompt inference with a single machine-readable recommendation for SDD continuation, and it must interoperate with `cos-process-loop` rather than duplicating it.

## Recommended immediate next step

Implement Slice 1 first: a COS-owned SDD/process status dispatcher. It is the smallest high-leverage gap because it makes every later preflight, strict TDD, skill selection, review forecast, and phase gate route from computable state instead of prompt inference.

## Claim boundary

The external repository's public claim of saving context/tokens is plausible from its architecture because it uses delegation, skill-registry indexing, phase routing, cached testing capabilities, and structured state. The audited snapshot does not itself provide a controlled A/B token benchmark comparable to COS `cos-so-impact-eval`. For Cognitive OS, any product claim should remain receipt-backed through SO-wide evals and real provider telemetry.
