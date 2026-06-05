# Primitive Contamination Audit — 2026-05-09

## Why this audit exists

A maintenance review flagged that some Cognitive OS source and docs still looked copied from consumer projects instead of describing OS-level agentic primitives. Examples included raw private codenames/service names in a public-readiness checklist, a verification table with domain-specific service rows, and blockchain-specific auditor examples in product docs.

The safety requirement is: **do not delete or rewrite primitives until current consumer projects are checked for local copies/needs.** Project-specific skills should live in the consumer project, package, or plugin layer; OS core should ship generic primitives and configuration contracts.

## Acceptance criteria for this sweep

1. Raw private repository token examples do not appear in OS primitives or public docs outside private external evidence.
2. `skills/`, `hooks/`, `rules/`, `agents/`, `squads/`, and `templates/` do not contain consumer-specific service inventories.
3. Current consumer projects are inventoried before removal decisions.
4. Usage-map tooling is fast enough to audit all primitive families without scanning bundled plugin/vendor payloads.
5. Any remaining domain-specific capability is explicitly optional/package/plugin-oriented, not core SO policy.

## What changed in this pass

- `skills/verification-before-completion/SKILL.md` now uses generic service placeholders instead of a domain-specific verification row.
- `rules/definition-of-done.md` now says “externally irreversible operations” instead of naming a specific domain.
- `docs/08-References/business/open-source-design.md` now uses `regulated-domain-auditor.md` instead of a blockchain-specific plugin example.
- `docs/09-Quality/legal/pre-public-readiness-checklist.md` no longer prints raw private token values; it points to external/private evidence.
- `docs/04-Concepts/root/component-sources.md`, `docs/01-Build-Log/root/roadmap.md`, and `docs/05-Methodology/root/rules.md` were genericized where older prose still contained stack/domain examples.
- `scripts/primitive_usage_map.py` now ignores `.claude/plugins/` and prefilters target literals before regex matching so full primitive audits are practical.

## Consumer project inventory

Scanned local consumers under the local sibling-project workspace (`<consumer-workspace-root>`):

| Consumer project | OS config present | Local skills found | Domain-token hits in `.claude` / `.cognitive-os` |
|---|---:|---|---|
| Private consumer repo | yes | `agent-dashboard`, `auto-refine`, `compose-prompt`, `cos-status`, `exhaustive-prompt`, `paperclip-dashboard`, `plan-feature`, `resource-governor`, `session-backlog`, `verification-before-completion` | only inherited generic “smart contract” wording before this patch |
| `cos-consumer-e2e-drill` | yes | none | only inherited generic “smart contract” wording before this patch |
| `luum-puppy` | no `cognitive-os.yaml` found | none | none |
| `stock-ventas-backend` | no `cognitive-os.yaml` found | none | none |

Interpretation: the currently visible local consumers do **not** appear to rely on local blockchain/web3/wallet skills that would be lost by genericizing the OS core examples. If a private consumer outside this local tree has such needs, those should be preserved as a package/plugin or consumer-local skill before any deletion.

## Primitive usage-map results

Generated reports:

- `docs/06-Daily/reports/primitive-usage-map-skills.md`
- `docs/06-Daily/reports/primitive-usage-map-hooks.md`
- `docs/06-Daily/reports/primitive-usage-map-rules.md`

Summary from the latest run:

| Family | Targets | Without skill consumer | Without any consumer |
|---|---:|---:|---:|
| skills | 170 | 0 | 0 |
| hooks | 290 | 237 | 2 |
| rules | 116 | 80 | 0 |

Interpretation: usage maps are static reachability, not runtime proof. Many hooks/rules have no skill consumer because they are hook-chain or config-driven surfaces. Use this as a triage map, not a deletion list.

## Remaining risk

- Some docs under `docs/03-PoCs/research/` and generated report snapshots can still mention domain terms as historical research examples. This pass excluded those from the public/core contamination gate.
- The Trail of Bits optional security skill source includes specialized protocol audit capabilities. That should remain an optional external package description, not a default OS primitive.
- Current grep checks are lexical. A stronger contract should classify “core vs package vs consumer-local” by frontmatter/tag and fail when raw consumer tokens appear in core paths.

## Recommended next steps

1. Add a test contract, for example `tests/audit/test_no_consumer_domain_leakage.py`, that rejects raw private-token literals and concrete consumer service names in core paths.
2. Add a primitive classifier report with buckets: `CORE`, `PACKAGE`, `CONSUMER_LOCAL`, `RESEARCH_ARCHIVE`, `GENERATED_REPORT`.
3. For any future removal: first run consumer inventory, then archive/package, then delete from core only after tests prove no consumer-local requirement is lost.
