---
type: concept-synthesis
source: docs/04-Concepts/architecture/primitive-readiness-continuity-plan.md
provenance: "The same primitive-readiness analysis kept reappearing across ADRs/reports/plans/scripts; without a repeated loop the SO can drift back into aspirational docs, dormant scripts, or hidden harness-specific behavior."
---

## What it is
Living execution/continuity plan for turning COS docs, scripts, hooks, rules, skills, memory, and harness adapters into governed agentic primitives that evolve the SO and travel across harnesses. Every cycle touching docs/scripts/primitive metadata/self-improvement/portability must move ≥1 row through: docs claim/workflow -> primitive id -> implementation path -> lifecycle metadata -> evidence command -> report row -> harness support declaration -> package tier (core|team|maintainer|lab) -> next-cycle action.

## Key mechanics
- Readiness estimates by capability slice: Active SO primitive kernel 75-80%; Runtime hook projection 85-90% (Claude)/partial Codex; Skills/rules as reusable surface 65-75%; Scripts as agent tools 55-60%; Docs as executable truth 45-55%; Multi-IDE/harness portability 25-35%; Universal tools for all agents/projects 40-50%.
- 2026-05-04 baseline: lifecycle manifest rows 154; active primitives 51; runtime-active 24; default-visible 11; runtime coverage for projected hooks 1.0; coverage rows scanned 1259; coverage avg score 64.3; gap snapshot overall risk `high`. Family posture: docs 507 rows (54.1 avg, 128 partial/379 dormant), scripts 139 (59.4, 94 partial/45 dormant), skills 165 (75.0, all partial), hooks 258 (82.9, 132 real/111 partial/15 dormant), rules 112 (69.0, all partial), config/projection 78 (48.6, 22 partial/56 dormant).
- Per-family cycle commands: docs (`scripts/docs_execution_audit.py --fail-hard-gaps`), scripts (`scripts/primitive_readiness_ledger.py`, `scripts/primitive_family_readiness_ledger.py --target-family {hooks,skills,rules}`, `scripts/primitive_usage_map.py`, `scripts/primitive_coverage.py`), hooks (`scripts/runtime_hook_reality.py --fail-on-findings`, `bash -n hooks/*.sh`), harness (`scripts/harness_parity_audit.py`).
- `consumer_accessibility` classification for scripts: `install-profile-managed`, `lifecycle-declared-consumer-candidate`, `lifecycle-declared-maintainer`, `skill-referenced-not-projectable`, `so-local-only`. Profile-managed install surfaces protected via `manifests/primitive-readiness-protected-install-surfaces.yaml`.
- Harness capability table: Claude Code strongest (native hooks/settings/rules); Codex emerging (settings driver + governed fallback); Cursor/Devin adapter evidence exists but runtime parity incomplete; VS Code Copilot, Google Antigravity, OpenCode not yet signed; Shell/CI partial via deterministic non-interactive CLI entrypoints. No harness may be claimed supported without a capability profile + ≥1 proof path.
- Coordination preflight before editing readiness ledgers/lifecycle metadata/profile manifests: `python3 scripts/claim_task.py acquire <task_id> --session-id ... --agent-id ... --scope primitive-readiness --expected-file manifests/primitive-lifecycle.yaml --expected-file scripts/primitive_readiness_ledger.py --ttl-seconds 7200` (coordination primitive, not a file lock — same-file mutation safety is `edit-coop`/`concurrent-write-guard`'s job).
- Promotion policy: a primitive is a "shared tool for all agents" only with stable id, lifecycle metadata, deterministic invocation, tests/manual proof, supported-harness declaration, graceful unsupported-harness behavior, package placement outside project-specific customization, and runnable acceptance criteria; otherwise use narrower language (maintainer tool, Claude-supported, lab primitive).

## Relations & where used
ADR-120, ADR-124, ADR-126, ADR-127, ADR-133, ADR-146, ADR-118; `manifests/primitive-lifecycle.yaml`; `manifests/primitive-readiness-script-overrides.yaml`; `lib/task_claim_ledger.py`; `docs/04-Concepts/architecture/concurrency-safety-core-consumer-contract.md`, `primitive-harvester.md`, `headless-self-improvement-proposer.md`, `self-evolving-doctrine-proposals.md`, `harness-engineering.md`, `harness-driver-parity.md`, `primitive-readiness-ledger-family-extension.md`.

## Status / caveats
Gap snapshot flags 3 high-risk families at baseline time: hooks (2 actionable gaps), metrics (3 actionable gaps), docs_adrs (3 hard gaps, 390 mapped claims, 169 done-with-proof). Session summary Markdown files under `.cognitive-os/sessions/` are a last-resort recovery artifact, not proof of universal automatic memory writes across all IDE agents.
