# Promise Compliance Audit — 2026-05-15

> Status: current repository audit.
> Scope: public/product promises, architecture promises, and default-adoption promises that a developer could reasonably infer from the repo.

## Executive Verdict

Cognitive OS has a real, defensible core: governance, verification, runtime event normalization, safety gates, portability drivers, and durable evidence artifacts. It is not empty overengineering.

The main compliance problem is not absence of substance. The problem is that several public-facing and semi-public documents still mix four different maturity levels as if they were one product surface:

1. **Core, verified runtime behavior**.
2. **Driver-projected behavior with explicit harness limits**.
3. **Maintainer/dogfood behavior that works in this repo but should not be sold as default adoption**.
4. **Aspirational, dormant, or structurally projected surfaces**.

The repo already contains strong anti-maximalist doctrine. What is missing is an explicit **agentic literacy boundary**: Cognitive OS must not replace developers learning PI / prompt-injection defense, Claude Code, Codex, OpenCode, Goose, harness engineering, and SDD directly. COS should encode repeatable operational discipline, not hide the underlying tools.

## Audit Method

This audit uses repository-local evidence only. It does not claim account-backed runtime validation for external IDEs unless the repo already records such a proof.

Commands run on 2026-05-15:

```bash
bash scripts/cos measure harness-profiles --json
scripts/cos-public-claim-gate --json
.venv/bin/python scripts/claim_proof_audit.py --project-dir . --json-out /tmp/claim-proof.json --md-out /tmp/claim-proof.md
python3 scripts/aspirational_audit.py --json
scripts/cos-tier-claim-audit --json
scripts/cos-manifest-tier-claim-audit --json
.venv/bin/python -m pytest tests/contracts/test_harness_engineering_docs.py tests/contracts/test_product_zones.py -q
```

Static counts sampled on 2026-05-15:

| Surface | Current count |
|---|---:|
| `hooks/*.sh` | 244 |
| `.claude/settings.json` hook commands | 153 |
| `.codex/hooks.json` hook commands | 64 |
| `skills/**/SKILL.md` | 176 |
| `rules/*.md` | 120 |
| `scripts/*` files | 561 |

## Current Automated Evidence

| Check | Result | Interpretation |
|---|---:|---|
| Public claim gate | pass, 0 findings | High-risk autonomous/self-improvement language is bounded in the scanned public docs. |
| Claim proof audit | 505 mapped claims, 0 weak/unmapped | Strong textual claims have at least local proof signals. This is lexical/proof-corpus mapping, not semantic runtime truth. |
| Aspirational audit | 1163 total; 201 REAL, 626 ON_DEMAND, 203 DORMANT, 68 ASPIRATIONAL, 65 METADATA; DORMANT+ASPIRATIONAL ratio 23.3% | The repository is mostly real/on-demand, but still has meaningful dormant/aspirational surface. |
| Tier claim audit | pass, 0 findings | Promoted ADR tiers satisfy the current evidence policy. |
| Manifest tier claim audit | warn, 790 findings; 474 warnings | Distribution/lifecycle claims are not yet evidence-complete enough for broad external adoption. |
| Harness profile measure | minimal=3 hooks; full Claude=153; full Codex=64 | The minimal/full distinction is real and necessary; full projection is maintainer-scale. |
| Contract tests | 12 passed | Product zones and harness-engineering docs have executable coverage. |

## Remediation Pass — 2026-05-15

The first remediation pass addressed the highest-risk public documentation fronts:

- `features.md` now uses an 8-core-phase SDD contract with optional init/bootstrap, not conflicting 7/10 phase language.
- Multi-IDE claims now use proof-level vocabulary and separate Claude/Codex native lifecycle, OpenCode governed-wrapper starter slice, structural projections, and planned hosts.
- Developer Experience counts now show current repo inventory and make minimal/core versus maintainer-scale exposure explicit.
- Automation Workflows remains DORMANT and no longer claims turnkey ticket-to-production automation.
- Observability/Cost Control now leads with JSONL/OTel/MCP, synchronous budget gates, retry contracts, and capability routing instead of central Langfuse/LiteLLM claims.
- Manifest-Driven Governance no longer claims every primitive has YAML; the remaining audit debt is tracked in `docs/06-Daily/reports/manifest-tier-warning-backlog-2026-05-15.md`.
- OpenCode projection status is aligned with `manifests/harness-projection.yaml` as `governed-wrapper-enforced` for the signed starter slice.

## What the Repo Promises and Complies With

| Promise | Compliance | Evidence |
|---|---|---|
| COS is a governance/operational layer, not a replacement agent framework | **Complies** | `README.md`, `durable-product-master-plan.md`, `feature-reality-audit.md`, `product-zones.md`. |
| Core should be small and protected | **Complies as doctrine and tests** | `kernel-contract.md`, `product-zones.md`, `manifests/product-zones.yaml`, `tests/contracts/test_product_zones.py`. |
| Harness engineering should be simple, composable, and progressive | **Complies as doctrine and partial implementation** | `harness-engineering.md`, `manifests/harness-profiles.yaml`, `scripts/measure_harness_profiles.py`. |
| Product should be simple by default, rigorous when needed | **Complies as doctrine** | `developer-confidence.md`, `product-messaging.md`, `minimal-context-principle.md`. |
| Public autonomous/self-improvement claims are bounded | **Complies for scanned public docs** | `scripts/cos-public-claim-gate --json` returned pass. |
| Self-improvement is not fully autonomous in v1 | **Complies in current public matrix** | `features.md` labels Self-Improvement as DORMANT/propose-only. |
| SRE/self-healing is not autonomous production mutation | **Complies in current public matrix** | `features.md` labels SRE and Self-Healing as DORMANT and human-approved. |
| Automation workflows are not turnkey default behavior | **Complies after remediation pass** | `features.md` row 17 and section now state DORMANT/template-only behavior. |
| Claude/Codex/native harness differences are tracked | **Complies as internal architecture** | `manifests/harness-driver-capabilities.yaml`, `manifests/harness-projection.yaml`, `harness-driver-parity.md`. |
| Product zones prevent extensions/experiments from silently becoming core | **Complies as doctrine and tests** | `tests/contracts/test_product_zones.py` passed. |
| A minimal harness profile exists | **Complies** | Minimal profile is 3 hooks with explicit files/commands in `manifests/harness-profiles.yaml`. |

## What Partially Complied at Audit Time

| Promise | Current reality | Risk |
|---|---|---|
| Persistent memory is REAL | Engram MCP and protocol are real, and this session used Engram successfully. But hook-level `engram-auto-import.sh` / `engram-auto-sync.sh` are still classified ASPIRATIONAL by the latest audit. | Public docs should distinguish MCP/protocol memory from fully automatic hook sync. |
| SDD is REAL | SDD skills exist and are used as workflow doctrine. The remediation pass standardized public-facing business docs on 8 core phases plus optional init/bootstrap and fast paths. | Older ADR/history docs may still mention prior 7/8/10-phase variants as historical context. |
| Quality control / governance hooks are REAL | Many hooks/rules/tests exist. However, features docs still cite old small counts and example constitutional gates that may read as universal project laws. | Overpromises if a consumer expects all example gates to apply to every stack. |
| Multi-agent orchestration is REAL | Strong dogfood and ADR substrate exist. But the most convincing proof is maintainer-scale/dogfood, not a small default adoption path. | Should be marketed as maintainer/team capability, not default solo-dev core. |
| Replay timeline / restore by checkpoint is REAL | Shadow-git and rollback files exist per features docs. Some chaos/cross-harness hardening remains pending in master plan. | Correct for implemented substrate; overclaim if described as fully parity-tested across all harnesses. |
| Sync cost + retry gate is REAL | Core libraries/manifests exist. Needs continued care that docs do not imply every provider/tool call is currently wrapped in every harness. | Runtime coverage can differ by harness. |
| Security and compliance is REAL | Credential/destructive/license gates exist. Some defense layers such as full identity stack are explicitly “designed,” not shipped. | Security section mixes shipped hooks with designed future identity architecture. |
| Observability and cost control is REAL | JSONL metrics, budgets, OTel/MCP direction, retry contracts, and dispatch gates exist. The remediation pass removed central Langfuse/LiteLLM wording from current business feature surfaces. | Historical docs may still mention evaluated or optional backends. |
| Industry presets are REAL | Presets/templates/configs exist, but the claim should stay “templates/presets,” not implied full compliance automation. | Regulated-domain readers may overread it. |
| OpenCode support exists | OpenCode has a signed starter runtime slice in `opencode-native-primitive-adapter-design.md`; remediation aligned `manifests/harness-projection.yaml` with `governed-wrapper-enforced` for that slice. | Remaining primitives stay structural-advisory until signed smoke evidence exists. |

## What Did Not Comply / Overpromised at Audit Time

| Promise or wording | Why it fails today | Required correction |
|---|---|---|
| `features.md` says “Multi-IDE Portability + MCP Server” is REAL for 7+ IDE adapters | `manifests/harness-projection.yaml` shows Claude/Codex native lifecycle, Cursor/VS Code/AGENTS/OpenCode mostly structural or limited, Windsurf/Google Antigravity planned. | Split into `native-lifecycle`, `runtime-smoke`, `structural`, and `planned`; stop using one REAL label for all 7+. |
| `features.md` Multi-IDE table says Cursor/VS Code/Gemini/OpenCode/Kiro/Windsurf have “Native” skills or “Adapter” hooks | The manifest records structural projection for some and planned/no proof for others. | Replace table cells with proof levels from `manifests/harness-projection.yaml`. |
| `features.md` says Manifest-Driven Governance means “Every primitive declares a schema-versioned YAML” | Aspirational audit sees 1163 components; lifecycle manifest audit covers 607 primitives and warns on 790 evidence/distribution issues. | Reword to “manifest-backed governance is being ratcheted across primitives”; reserve “every” for audited coverage only. |
| Developer Experience section says 27+ skills, 30+ hooks, 22+ rules, 16+ personas; later says 21 hooks and 19 rules | Current counts are 176 skills, 244 hooks, 120 rules, 561 scripts. The old smaller counts may understate size while implying curated default. | Replace raw counts with profile-specific counts: minimal/core/team/maintainer/lab. |
| Automation Workflows section says “End-to-end pipelines from ticket to deployed code” | The same file’s overview correctly labels Automation Workflows DORMANT and says ticket-to-prod is operator-assembled, not pre-wired. | Keep DORMANT label in section heading and say “pipeline templates,” not turnkey E2E automation. |
| Observability section presents Langfuse and LiteLLM as current central architecture | README and newer docs point to Phoenix/OTel/MCP/JSONL direction; ADR-049 rejects LiteLLM as central proxy because of supply-chain/security concerns. | Update feature prose to current stack: JSONL, OTel/MCP semconv, Phoenix optional, direct provider/gateway policy. |
| Open-source core architecture block lists `core/`, `plugins/`, `generators/` as repo layout | Those directories are not the actual root architecture; current repo uses `hooks/`, `lib/`, `scripts/`, `cmd/cos/`, `packages/`, `manifests/`, etc. | Replace conceptual tree with actual product zones or move to “target package shape.” |
| Security section lists a 6-layer identity stack as part of defense layers | It is labelled “designed,” but placement after “Enterprise-grade security built into infrastructure” can read as shipped. | Move identity stack to planned/advanced section or add explicit status per layer. |
| README / product docs still rely on “full OS” framing in places | `feature-reality-audit.md` already says full 13-layer OS framing has low product value and high complexity risk. | Keep first-contact docs focused on operational layer, not total OS. |
| Agentic literacy boundary is missing | No explicit doc says developers must still learn PI/prompt-injection defense, Claude Code, Codex, OpenCode, Goose, harness engineering, and SDD directly. | Add ADR or product doctrine: COS is scaffolding, not a substitute for agentic literacy. |

## Agentic Literacy Boundary

This should become a first-class product rule:

> Cognitive OS encodes repeatable operational discipline. It must not obscure or replace developer literacy in the underlying harnesses, tools, security model, and workflows.

Practical consequences:

1. COS skills should teach the underlying operation and name the harness-specific surface they rely on.
2. First-contact onboarding should include vanilla Claude Code/Codex/OpenCode/Goose literacy paths, not only COS commands.
3. SDD should remain a discipline with fast paths, not ceremony imposed on every task.
4. PI / prompt-injection and tool-permission safety should be taught directly, not hidden behind a “security hook” abstraction.
5. Cross-harness docs should say whether a behavior is native runtime enforcement, governed wrapper enforcement, structural projection, or just planned.

## Feature-by-Feature Compliance Matrix

| Feature from public matrix | Current status label | Audit verdict | Notes |
|---|---|---|---|
| Persistent Memory | REAL | **Partial/mostly true** | MCP/protocol real; automatic hook sync/import not fully wired. |
| Spec-Driven Development | REAL | **Remediated in public business docs** | Public business docs now use 8 core phases plus optional init/bootstrap and fast paths. |
| Quality Control | REAL | **Partial/true** | Many gates real; docs need profile-specific and stack-specific wording. |
| Self-Improvement Loop | DORMANT | **Complies** | Correctly bounded as propose-only/human-gated. |
| Multi-Agent Orchestration | REAL | **Partial/true for maintainer/team** | Strong substrate; should not be default solo-dev promise. |
| Replay Timeline & Restore-by-Checkpoint | REAL | **Partial/mostly true** | Implemented substrate; some hardening remains pending. |
| Sync Cost + Retry Gate | REAL | **Partial/mostly true** | Core exists; harness coverage must stay explicit. |
| Agent-to-Agent Handoff Protocol | REAL | **Mostly true** | Typed envelope/cycle dedup exists; runtime adoption should stay evidence-scoped. |
| Security and Compliance | REAL | **Partial/true** | Hooks real; identity stack/future layers need clearer status. |
| Observability and Cost Control | REAL | **Remediated in current business docs** | Current business docs lead with JSONL/OTel/MCP, sync budget gates, retry contracts, and capability routing. |
| Developer Experience | REAL | **Remediated wording; product risk remains** | Counts now show current inventory and profile-aware default exposure; maintainer-scale surface remains opt-in. |
| Multi-IDE Portability + MCP Server | REAL | **Remediated wording** | Current feature docs use proof-level vocabulary and separate native, wrapper, structural, and planned support. |
| Sandbox Adapter Tiers | REAL | **Mostly true** | Keep opt-in/default tier caveats visible. |
| Detached Agent Daemon | REAL | **Mostly true** | Treat as advanced/local-first agent surface, not core first-run. |
| SRE and Self-Healing | DORMANT | **Complies** | Correctly human-approved/advisory. |
| Industry Presets | REAL | **Partial** | Templates/presets yes; compliance automation should not be implied. |
| Automation Workflows | DORMANT | **Remediated** | Section now says template/procedure surface, not turnkey ticket-to-production automation. |
| Manifest-Driven Governance | REAL | **Remediated wording; backlog remains** | Universal “every primitive” claim removed; remaining evidence debt is tracked in the manifest tier warning backlog. |
| Open-Source Core | REAL | **Remediated layout wording** | Feature docs now use current product zones instead of the old conceptual `core/` tree. |

## Priority Corrections

1. **Use ADR-316 as the agentic literacy boundary.** This closes the exact concern raised on 2026-05-15 at the decision level.
2. **Patch `features.md`** to align every section with its own status table, especially Multi-IDE, Automation, Observability, Manifest-Driven Governance, Developer Experience, SDD, and Open-Source Core layout.
3. **Update `manifests/harness-projection.yaml` or the OpenCode architecture doc** so OpenCode signed-runtime-slice status is not contradictory.
4. **Make feature claims profile-aware.** Replace global “hooks/skills/rules” counts with minimal/core/team/maintainer/lab counts.
5. **Use the manifest tier warning backlog** at `docs/06-Daily/reports/manifest-tier-warning-backlog-2026-05-15.md` to reduce or justify the current 790 findings.
6. **Define canonical SDD phase taxonomy.** Pick one current contract and update AGENTS, ADR-014 references, and `features.md`.

## Acceptance Criteria for Closing This Audit

1. `features.md` no longer has a section whose prose contradicts its status label.
2. `manifests/harness-projection.yaml` and OpenCode docs agree on the signed runtime slice.
3. ADR-316 remains linked from first-contact docs and explicitly states the agentic literacy boundary.
4. `scripts/cos-manifest-tier-claim-audit --json` warning count is either reduced or linked to `docs/06-Daily/reports/manifest-tier-warning-backlog-2026-05-15.md` with target thresholds.
5. Harness claims in public docs use the proof-level vocabulary: `native-lifecycle`, `runtime-smoke`, `governed-wrapper-enforced`, `structural`, `planned`, `unsupported`.
6. A future run of this audit records no stale public counts for hooks/skills/rules/scripts.
