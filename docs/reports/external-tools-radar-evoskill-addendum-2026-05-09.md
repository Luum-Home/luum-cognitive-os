---
report_type: external-tools-radar-targeted-addendum
scope: sentient-agi/EvoSkill
source_index: docs/reports/external-tools-radar-INDEX.md
generated_at: 2026-05-09
status: documentation-before-implementation
source_artifacts:
  - docs/research/repo-scout/deep/sentient-agi__EvoSkill-2026-05-09.md
related_docs:
  - docs/architecture/external-tool-adoption-doctrine.md
  - docs/architecture/external-tool-adapter-taxonomy.md
  - docs/reports/external-tools-radar-full-reassessment-2026-05-08.md
  - docs/reports/external-tools-radar-agno-addendum-2026-05-09.md
---

# External Tools Radar Addendum — EvoSkill 2026-05-09

## Why this addendum exists

The 2026-05-08 reassessment and the first 2026-05-09 targeted addenda did not
include `sentient-agi/EvoSkill`. The user explicitly requested that EvoSkill be
added to the deep-analysis queue and the tech radar, passing through the full
analysis pipeline. This addendum records the radar decision so future work does
not rediscover the same tool or confuse it with generic skill catalogs.

## Executive verdict

| Field | Decision |
|---|---|
| Radar status | **TRIAL-PATTERNS / ASSESS-RUNTIME** |
| Recommendation | Extract the benchmark-driven skill-evolution contract now; run only a bounded adapter lab later |
| Adoption kind | `pattern-only`, possible future `adapter-lab` |
| License | Apache-2.0 |
| Default-install posture | **Do not install by default** |
| Primary value | Failure-driven skill synthesis, held-out validation, frontier selection, cross-harness skill packaging |
| Primary risk | Git branch/tag mutation, generated skills, credential forwarding, remote/Docker execution, and benchmark overfit without COS governance |

EvoSkill is unusually relevant because it targets the exact primitive family COS
cares about: reusable agent skills produced from evidence, not hand-written
intuition. The right move is not wholesale runtime adoption. The right move is
to turn its loop shape into COS-owned contracts, fixtures, and regression gates.

## Current metadata snapshot

| Repository | License | Stars | Last push | Latest release | Radar call |
|---|---:|---:|---|---|---|
| [`sentient-agi/EvoSkill`](https://github.com/sentient-agi/EvoSkill) | Apache-2.0 | 710 | 2026-05-08 | `v1.1.0` on 2026-05-05 | **TRIAL-PATTERNS / ASSESS-RUNTIME** |

Checked on 2026-05-09 through GitHub repository metadata, README, release
metadata, workflow metadata, the arXiv abstract, and a fresh shallow clone at
commit `418a37ca680a1264086df420a96db07dcd064ace`. Star counts are not adoption
proof.

## Full-stage pipeline result

| Stage | Result |
|---|---|
| Discovery | Relevant and missing from prior radar corpus |
| License gate | Apache-2.0, clean for pattern extraction and opt-in lab work |
| Source audit | Staged self-improvement loop, git-backed frontier registry, skill/prompt generators, cache, scorer, and multi-harness executor layer |
| Evidence review | arXiv and README report gains on OfficeQA, SealQA, and transfer to BrowseComp; COS has not reproduced them |
| Bidirectional cross-check | EvoSkill is better at skill-evolution mechanics; COS is better at governance, policy, credentials, and adoption doctrine |
| Adoption decision | Add to radar as EVALUATE; extract patterns first; require manifest before runtime trial |
| Acceptance criteria | See below; no default dependency or workspace mutation without wrappers |

## Bidirectional implementation cross-check

| EvoSkill capability | COS state | Verdict | Action |
|---|---|---|---|
| Base → failure → proposer → generator → evaluator → frontier loop | COS has skills, optimization docs, and regression doctrine but no shipped equivalent loop | **MEJOR_EXTERNO** | Encode as a COS lab contract |
| Held-out validation before skill promotion | COS has postmortem-regression audit direction | **COMPATIBLE / MEJOR_EXTERNO in implementation** | Reuse as fixture pattern |
| `.claude/skills` to `.agents/skills` bridge | COS cares about harness-agnostic projection | **MEJOR_EXTERNO for concrete Codex fixture** | Extract projection tests, not canonical path choice |
| Git program branches and frontier tags | COS has stronger safety requirements for user workspaces | **RISKY** | Only in disposable labs with rollback receipts |
| Docker/Daytona long-running execution | COS has local-first and credential policies | **RISKY** | Data-flow review before any remote run |
| Generated skill promotion | COS has governance and security lanes | **MEJOR_NUESTRO** | COS gates remain authoritative |

## What to extract

1. **Skill-evolution stage contract** — baseline, failure sampling, proposer,
   generator, held-out evaluator, frontier selection, feedback ledger.
2. **Generated-skill evidence schema** — source failures, proposal rationale,
   generated paths, score delta, model/harness/cost, retained/discarded outcome.
3. **Harness projection fixture** — prove skills generated for one path are
   visible through Codex-compatible discovery without deleting real directories.
4. **Frontier semantics** — keep top-N programs as an algorithmic idea, but map
   it to COS manifests/receipts before touching user git state.
5. **Benchmark discipline** — train failures may guide generation; validation
   data decides promotion.

## What not to extract

- No default EvoSkill runtime dependency in COS bootstrap, requirements, hooks,
  packages, or install scripts.
- No automatic mutation of a user's git branches or tags from COS core.
- No generated skill promoted into `skills/` without COS skill-contract,
  security, vocabulary, and regression checks.
- No remote/Docker execution with production data or secrets until credentials,
  data-flow, audit, and rollback are documented.
- No `.claude`-first canonicalization that weakens COS's harness-agnostic
  primitive projection.

## Recommended next action

```text
ACCEPTANCE CRITERIA:
1. EvoSkill remains an EVALUATE radar entry until an adoption manifest row exists.
2. A future trial uses a disposable fixture repo and a toy benchmark with no secrets.
3. The COS wrapper records dirty-tree status, allowed generated paths, source commit, train/validation split, score delta, cost, model, harness, and rollback command.
4. Generated skills pass COS contract/security/regression lanes before any promotion.
5. Default COS install remains unchanged unless a separate ADR approves runtime adoption.
```

## Decision ledger row

| Tool/framework | Recommendation | Adoption kind | Reason | Next action |
|---|---:|---|---|---|
| sentient-agi/EvoSkill | TRIAL-PATTERNS / ASSESS-RUNTIME | pattern-only, possible adapter-lab | Best-fit external reference for benchmark-driven reusable skill synthesis; direct runtime adoption is gated by git, credential, remote, and generated-artifact risks | Keep deep evaluation and design a disposable fixture trial with COS wrappers |

## Source evidence

- Deep evaluation: `docs/research/repo-scout/deep/sentient-agi__EvoSkill-2026-05-09.md`
- GitHub repository: <https://github.com/sentient-agi/EvoSkill>
- arXiv paper: <https://arxiv.org/abs/2603.02766>
