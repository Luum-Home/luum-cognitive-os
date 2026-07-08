---
type: methodology-synthesis
source: docs/05-Methodology/runbooks/legal-review-workflow.md
provenance: "Operator runbook for unfreezing external-tool adoption after IP counsel review — the 8-step legal review workflow, state-inspection commands, and the manual-vs-automated boundary for each step."
---

## What it is

An operator-audience runbook for clearing a specific external tool through IP/legal review so it can be unfrozen from `manifests/external-tool-adoption-freeze.yaml`. Scoped to any tool with a non-trivial license (BSL, AGPL, Apache, proprietary) — trivial MIT/BSD deps skip steps 1-3.

## Key mechanics

- **Preconditions**: the tool's Annex F clean-room compliance dossier must exist at `docs/03-PoCs/research/<tool>-annex-f-*.md` (or under `.private/` for BSL-restricted material) with `reviewed-by-legal: pending`, and the tool must have a primary adoption ADR in `Accepted` status.
- **The 8-step workflow**: (1) USPTO patent search via `cos-uspto-patent-search`, (2) USPTO trademark search per candidate mark via `cos-uspto-trademark-search`, (3) generate a structured counsel packet zip (`cos-counsel-packet`) bundling the ADR, Annex F, USPTO reports, license snapshot, attributed clean-room `lib/` files, and related ADRs, (4) optionally draft (never send) outreach email via `cos-counsel-outreach-draft` with three templates, (5) manually send the packet to IP counsel (3-10 business day turnaround), (6) store the returned memo in gitignored `.private/legal-memos/`, (7) record the decision (`approved` / `approved-with-conditions` / `rejected`) via `cos-legal-approve`, which updates Annex F frontmatter with counsel metadata + memo SHA-256 and appends to `manifests/legal-review-ledger.yaml`, (8) per-tool unfreeze via `cos-adoption-unfreeze`, gated on 5 pre-flight checks (USPTO patent/TM reports exist, Annex F approved, ledger decision approved, conditions acknowledged if applicable).
- **Rejected tools** move to `docs/05-Methodology/root/blocked-tools.md`.
- **Unfreeze is per-tool, not global**: passing all 5 gates adds the tool to `unfrozen_tools` in the freeze manifest, but the global `frozen: true` flag stays set — flipping it is called out separately as a strategic decision reserved for after N tools are unfrozen.
- **5 documented bypass env vars** (all audit-logged to `.cognitive-os/logs/*.jsonl`): `COS_ALLOW_FREEZE_TOGGLE`, `COS_ALLOW_ADOPTION_FREEZE_BYPASS`, `COS_ALLOW_PRE_LEGAL_REVIEW_IMPORT`, `COS_ALLOW_UNDOCUMENTED_REWRITES`, `COS_ALLOW_NETWORK_EGRESS`.
- **Explicit non-automation boundary**: email send (step 5), counsel memo receipt (step 6), counsel's legal judgment within step 7, risk-acceptance for conditional approvals, and the global freeze flip are all called out as requiring a human because the deliverable is authorization, tracking, or legal interpretation — not something a script can produce.

## Relations & where used

References ADR-259 (clean-room posture), ADR-267 (commit-time license enforcement), ADR-269 (mandatory ADR reference for history rewrites), ADR-270 (this workflow's automation), and ADR-271 (Tier-2 AST clean-room detector), plus `rules/license-policy.md` for the SPDX classification table.

## Status / caveats

Includes a dated "Pending state (2026-05-11 snapshot)" table listing 8 tools awaiting legal review (holaOS, Hermes Agent, Pi coding-agent, HKUDS/OpenHarness, Sprut Agent Kit, HelixDB, iFixAi, MegaMemory) — this table is a point-in-time snapshot and should be treated as stale; the live status must be read from `manifests/legal-review-ledger.yaml` directly (per the "State inspection commands" section of the same doc) rather than from this synthesis or the source table.
