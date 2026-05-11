---
title: "iFixAi Annex F — Compliance & Clean-Room Protocol"
date: 2026-05-11
annex: F
parent: ifixai-comparison-2026-05-11.md
scope: research-only
license_classification: "Apache-2.0 — vendoring legally allowed with attribution; pattern-only recommended per addendum"
---

# Annex F — Compliance & Clean-Room Protocol for iFixAi

## 1. License posture

iFixAi v1.0.0 is published under the Apache License 2.0 (Copyright 2026 iMe). Full license text at: https://github.com/ifixai-ai/iFixAi/blob/main/LICENSE.

Apache-2.0 requirements relevant to this corpus:

- **§4.b — Attribution**: reproductions must carry the original copyright notice and attribution. Satisfied here via per-file attribution headers and per-block source path lines.
- **§4.c — NOTICE file**: if upstream ships a `NOTICE` file, any vendored distribution must preserve it. Status: not independently verified at eval time (2026-05-11, commit `2e56c4f`). **Required check before any vendoring**: verify presence of `NOTICE` in the upstream tree and include it.
- **§4.d — Derivative works**: modified files must carry prominent modification notices. Satisfied by "Original work © 2026 iMe, modified by Cognitive OS" in any vendored derivative.

Despite legal permissibility, this corpus adopts **pattern-only** over direct vendoring. Reasons are documented in Annex E §7: uncalibrated thresholds (upstream-disclosed), iMe open-core split risk (Annex D), and v1.0.0 being approximately one week old at evaluation time.

## 2. What this corpus contains

This research corpus (Annexes A–F plus the radar addendum and repo-scout deep evaluation) quotes Python from the following iFixAi subdirectories:

| Annex | Source paths quoted |
|---|---|
| B | `ifixai/judge/config.py`, `ifixai/providers/resolver.py`, `ifixai/cli/orchestrator.py`, `ifixai/evaluation/analytic_judge.py` |
| C | `ifixai/evaluation/manifest.py`, `ifixai/utils/fixture_digest.py` |
| D | `ifixai/providers/resolver.py`, `ifixai/reporting/scorecard.py`, `ifixai/cli/_imecore_prompt.py` |
| E | Function-signature sketch (pseudocode, not verbatim) |

All verbatim or near-verbatim Python excerpts carry a `*Source: ifixai/<path>.py:Lx-Ly (Apache-2.0)*` line immediately above the code fence. Structural sketches carry `*Pseudocode sketch / structural description — not verbatim iFixAi source.*`.

Apache-2.0 §4.b is satisfied at three levels: this annex F (corpus-wide), per-file attribution headers (each annex frontmatter block), and per-block source path lines.

## 3. Pattern-only adoption protocol

For each primitive in Annex E, the adoption path is:

- **Step 1**: Read Annexes B, C, D, E to extract the behavioral pattern (contract, algorithm, convention). Do not copy code.
- **Step 2**: Choose one of:
  - **(a) Clean-room re-implement** from the extracted spec. Own the resulting code outright. Add a comment citing iFixAi as the source of the design pattern (not the implementation). This is the recommended path for all five primitives per Annex E.
  - **(b) Vendor with full Apache attribution** (only if clean-room cost is prohibitive): include Apache-2.0 header in every vendored file, preserve any upstream `NOTICE`, add "Original work © 2026 iMe, modified by Cognitive OS" to modified files.
- **Step 3**: The mandatory-minimum inspection cap mechanic (Annex E §6a.1) is **blocked** from adoption until [ADR-265 — Mandatory-minimum inspection caps for COS eval surfaces](../adrs/ADR-265-mandatory-minimum-inspection-caps.md) moves from Proposed to Accepted. Do not implement the cap until the ADR is resolved.
- **Step 4**: If vendoring, the output artifact MUST include: (a) Apache-2.0 license header, (b) "Original work © 2026 iMe, modified by Cognitive OS", (c) preserved upstream `NOTICE` if one exists.

## 4. iMe open-core split risk

iFixAi is positioned as a funnel for the proprietary iMe runtime (see Annex D §2). The OSS package ships a `_IME_FOOTER` in every scorecard and a `print_imecore_conclusion` prompt in every CLI run. The README explicitly warns (L44-48) that the demo GIF shows a custom client build whose fixtures, scoring policy, and UI differ from the OSS version.

Implications for compliance:

- **Fixture divergence**: scoring numbers produced by the OSS scorecard may differ from the iMe client scorecard, by design. Any COS report citing iFixAi numbers MUST label them "iFixAi OSS v1.0.0, default thresholds (uncalibrated per upstream)".
- **Drift risk**: future OSS commits may be steered by funnel conversion priorities rather than technical defensibility. Mitigate by pinning to a specific release tag (`v1.0.0`, commit `2e56c4f`) and re-evaluating on each upstream minor version.
- **Vendoring inherits drift**: if COS vendors iFixAi code, each upstream release must be independently audited for open-core scope changes before the pin is updated. Reference: ADR-247 version-pin discipline.

## 5. Pre-commit gate recommendation

A `hooks/ifixai-cleanroom-gate.sh` check (analogous to `hooks/external-pattern-cleanroom-gate.sh` if present) should verify:

1. No file in `lib/`, `scripts/`, or `skills/` contains the string `ifixai` as an import path without a corresponding compliance comment citing this annex.
2. Any eval-run manifest under `runs/` that references iFixAi numbers carries the "drift-signal, not certified score" label.
3. The `IFIXAI_NO_PROMPT=1` environment variable is set in any COS adapter that shells out to `ifixai run`, so the iMe marketing footer is suppressed from CI logs (Annex D §3.1).

This gate is recommended, not yet implemented. Tracked as a follow-up to the CLI-adapter trial (Phase B in the parent document §6).

## 6. Open questions

The following questions must be resolved before any vendoring (as opposed to pattern-only adoption) proceeds:

1. **Fair-use threshold for code quotation in research annexes**: the excerpts in this corpus are brief (5–15 lines each) and serve a commentary/analysis purpose. This is consistent with standard research fair-use norms under Apache-2.0, but a formal legal review is recommended before any external publication of this corpus.
2. **Apache §4.d NOTICE propagation**: upstream NOTICE file presence must be verified at commit `2e56c4f` before any vendoring. If a NOTICE file exists, it must be preserved verbatim in any distributed derivative.
3. **Calibration status of copied thresholds**: upstream explicitly disclaims thresholds as uncalibrated policy defaults (README L35-L42). Vendoring threshold values without this disclaimer would misrepresent their provenance. Any COS artifact that references specific numeric thresholds from iFixAi MUST include the "uncalibrated per upstream" qualifier.
4. **iMe-scope boundary**: the OSS license covers the `ifixai/` package. Any iMe-proprietary components referenced from the OSS code (e.g., the `https://ifixai.ai/ime` runtime) are NOT covered by Apache-2.0 and MUST NOT be reverse-engineered or vendored.
