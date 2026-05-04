# Primitive Readiness Review — 2026-05-04

> First continuity-cycle review produced after `docs/architecture/primitive-readiness-continuity-plan.md`. This is a working report, not a final readiness sign-off.

## Lifecycle Manifest Surface

| Dimension | Counts |
|---|---|
| Kinds | hook: 126, script: 27, doctor: 1 |
| Distribution | lab: 101, maintainer: 41, core: 8, team: 4 |
| Supported harness declarations | claude: 127, shell: 28, codex: 3 |

## Coverage by Family

| Family | Count | Average score | Statuses | Review verdict |
|---|---:|---:|---|---|
| config | 78 | 48.6 | dormant: 56, partial: 22 | Driver/projection surface is under-scored; separate generated/runtime/reference config. |
| doc | 507 | 54.1 | partial: 128, dormant: 379 | High continuity risk: many docs are dormant and must be claim-mapped or downgraded. |
| hook | 258 | 82.9 | partial: 111, dormant: 15, real: 132 | Strongest runtime surface, but blocking/mutating hooks need ongoing evidence. |
| rule | 112 | 69.0 | partial: 112 | Needs enforcement linkage or explicit context-only classification. |
| script | 139 | 59.4 | dormant: 45, partial: 94 | Medium continuity risk: classify script roles before promoting as agent tools. |
| skill | 165 | 75.0 | partial: 165 | Good agent UX surface; needs package/distribution and harness proof. |

## Automation Loop Scripts

| Loop | Script | What it automates | Current role |
|---|---|---|---|
| Active primitive index | `scripts/active_primitive_index.py` | canonical surface counts from lifecycle manifest | core maintainer readiness |
| Gap snapshot | `scripts/primitive_gap_snapshot.py` | cross-family high-risk snapshot | cycle gate |
| Coverage scanner | `scripts/primitive_coverage.py` | docs/scripts/hooks/rules/skills/config coverage rows | cycle gate |
| Row audit | `scripts/primitive_row_audit.py` | primitive family proof status | cycle evidence |
| Usage map | `scripts/primitive_usage_map.py` | static consumers by family | orphan and promotion triage |
| Surface reduction | `scripts/primitive_surface_reduce.py` | safe demotion/archive candidates | surface control |
| Docs execution audit | `scripts/docs_execution_audit.py` | documentation claims vs evidence | docs claim gate |
| Primitive harvester | `scripts/cos_primitive_harvester.py` | conversation/repeated-workflow proposal classifier | self-evolution propose-only |
| Self-improvement loop | `scripts/cos_self_improvement_loop.py` | audit finding to proposed work item | self-evolution propose-only |
| Doctrine proposer | `scripts/cos_doctrine_proposer.py` | control-plane evidence to proposed doctrine | self-evolution propose-only |
| Harness parity audit | `scripts/harness_parity_audit.py` | driver capability and support gap audit | portability gate |

## Lowest-Scoring Script Rows to Triage First

| Script | Score | Status | Initial role hypothesis |
|---|---:|---|---|
| `scripts/cos_recovery_drill.py` | 15 | dormant | maintainer-tool; needs lifecycle or archive decision |
| `scripts/agentic_mastery_summary.py` | 25 | dormant | maintainer-tool or report-only helper |
| `scripts/cos_doctrine_proposer.py` | 25 | dormant | self-evolution lab/maintainer tool; prove or downgrade claims |
| `scripts/session_event_bus.py` | 30 | dormant | runtime support tool; needs consumer/proof mapping |
| `scripts/align_skill_frontmatter.py` | 40 | dormant | migration-only or maintainer-tool |


## Ledger Implementation Update

ADR-146 adds `scripts/primitive_readiness_ledger.py` as the canonical machine-readable script role ledger. The first generated baseline classifies 310 script files:

| Role | Count |
|---|---:|
| agentic-primitive | 100 |
| maintainer-tool | 175 |
| migration-only | 11 |
| driver-specific | 11 |
| lab | 13 |

The first low-confidence pass is closed through `manifests/primitive-readiness-script-overrides.yaml`; the ledger now reports zero low-confidence rows. The follow-up lifecycle ratchet prioritized protected install/profile/projection scripts and added ADR-126 `candidate` metadata for those surfaces without making them active/default-visible. The lifecycle backlog reports remain active for the remaining agentic script rows that still need lifecycle metadata or downgrade decisions.

The ledger now also reports `consumer_accessibility`. This is required because the SO repository docs are not automatically available inside downstream projects that implement the SO. A script can be documented and useful in this repository while still being `so-local-only` or `skill-referenced-not-projectable` for consumer-project agents.

## Next Review Pass

1. Promote candidate script rows only after package/harness proof, or downgrade/archive rows that should not remain agent-facing.
2. Keep protected install/profile rows tied to settings/profile projection checks before changing distribution or active visibility.
3. Run the same review for hooks, skills, and rules after scripts are classified.
4. Expand harness declarations beyond Claude only where projection proof exists.
5. Keep product wording narrower than implementation evidence.
