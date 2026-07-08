---
type: reference-synthesis
source: docs/08-References/business/install-scope-anti-slop-audit-2026-05-15.md
provenance: "Verifies, against actual installer code and smoke evidence, whether Cognitive OS's three named install scopes (project/both/all) are a real three-tier product surface or a smaller effective surface being over-marketed."
---

## What it is

A dated (2026-05-15) evidence audit that checks the installer's claimed
three-tier scope model (`project` / `both` / `all`) against
`install.sh`/`scripts/cos_init.py` source and install-scope smoke reports, and
issues wording guardrails to prevent overclaiming.

## Key mechanics

- **Verdict**: only two effective installation surfaces exist. `project` and
  `both` are equivalent in installer logic and smoke evidence; `all` is a
  maintainer/full superset that has not demonstrated better developer
  outcomes.
- **Evidence table** joins claim area → code/artifact evidence → assessment:
  installer naming (three accepted CLI values, two effective semantics),
  `scope_allows()` in `scripts/cos_init.py` (treats `project` and `both`
  identically, only `all` disables filtering), smoke evidence (`project` and
  `both` produce identical file counts/primitive signatures; `all` is larger
  but not fully passing its own probes), and protected-config evidence
  (secret detector / destructive-git-blocker pass their probes, but the
  protected-config guard does **not** cover `.env`).
- **Protected config guard clarification**: the guard blocks writes to
  agent control-plane paths (`.claude/**`, `.codex/**`, `.cursor/**`,
  `.continue/**`, `mcp.json`, `.mcp/**`, `hooks/**`, `rules/**`, selected
  `skills/**`/`manifests/**`) — it is explicitly not a general `.env` write
  blocker. The claim "protected-config-write-guard blocks `.env` writes" is
  unsupported by policy and tests.
- Cross-references ADR-093, which already collapsed installer profiles to two
  tiers (sensible default + `--full`), reinforcing the two-surface
  conclusion.
- Gives explicit **allowed vs. avoid wording** examples for product copy, and
  a **required follow-up list**: documentation correction, install CLI
  labeling `both` as an alias/default rather than a distinct tier, an
  explicit `.env` protected-config policy decision, an `all_default_justified`
  outcome-evidence gate before recommending `all` to normal developers, and
  cross-stack smoke closure beyond Python.

## Relations & where used

- Directly informs `master-plan-checklist.md` items under "Product Promise"
  (aligning install-scope product copy with this audit's conclusions) and
  under "Success Signal" (ADR-320 install-scope surface debt entry echoes
  this audit's `project`/`both`-alias and `.env`-not-covered findings
  verbatim).
- Feeds the wording discipline enforced by the broader anti-slop/product-
  claim-evidence pipeline referenced in `product-answer-playbook.md`
  (`manifests/product-claim-evidence.yaml`, `scripts/cos-public-claim-gate`).

## Status / caveats

- This is a dated point-in-time audit (2026-05-15); its verdict should be
  re-checked against current installer code/smoke output if used as ongoing
  proof, since "Required follow-up" items were open recommendations, not
  confirmed completions, as of this document.
- No internal inconsistency found; the document is self-consistent and
  explicitly separates "what the code says" from "what product wording should
  say."
