---
title: "Hermes Agent (NousResearch) Annex F — Compliance & Clean-Room Protocol"
date: 2026-05-11
annex: F
parent: null # backfill — original adoption predates Annex F convention
scope: research-only
license_classification: "MIT — direct vendoring allowed with attribution; backfill of pre-2026-05-10 adoption"
reviewed-by-legal: no
---

# Annex F — Compliance & Clean-Room Protocol for Hermes Agent (NousResearch)

## §1 License Posture

**Upstream repository:** https://github.com/NousResearch/Hermes-Function-Calling
(verified via WebFetch 2026-05-11; repository is public, 1.3k stars, Python/Jupyter)

**SPDX identifier:** MIT

MIT verbatim head (paraphrased from standard MIT text, as NousResearch repo holds a
standard MIT LICENSE file): "Permission is hereby granted, free of charge, to any
person obtaining a copy of this software and associated documentation files … to
deal in the Software without restriction … subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software."

**Copyright holder:** NousResearch (organization owner of the GitHub repository).
Exact copyright line from upstream LICENSE file: _upstream URL verified — exact
copyright line not extracted in single fetch; must confirm precise wording against
`https://github.com/NousResearch/Hermes-Function-Calling/blob/main/LICENSE` before
legal review closes._

**Permissiveness assessment:** MIT is a permissive license. Direct vendoring,
adaptation, and distribution (including SaaS/commercial) are allowed provided that
the copyright notice and the license text are preserved in copies or substantial
portions. No patent grant (unlike Apache-2.0), no copyleft (unlike AGPL). Risk
rating: **LOW** for runtime inclusion with proper attribution.

---

## §2 What This Corpus Contains

This Annex F documents a **backfill**. The seven ports listed below were adopted
into Cognitive OS before the Annex F + NOTICE-file doctrine was established on
2026-05-10 (ADR-259, ADR-267). The ports were governed at the time solely by
inline `# Ported from Hermes …` comment headers, which was the prevailing
attribution discipline. This document adds the Annex F layer and the corresponding
NOTICE-file entry (§4) without altering any ported logic.

All seven files carry inline attribution at the locations listed below. No file is
missing the upstream project name. Two files reference `.cognitive-os/adoption-registry.yaml`
as the canonical license record; that registry path is a phantom (real file lives at
`./adoption-registry.yaml` at the repository root) — that path fix is **out of scope**
for this Annex F and is tracked separately.

| # | COS file | Attribution location |
|---|----------|---------------------|
| 1 | `lib/memory_manager.py` | line 5: `Ported from: Hermes Agent agent/memory_manager.py (MIT license)` |
| 2 | `lib/context_compressor.py` | lines 3–4: `Ported from Hermes … MIT-licensed. Attribution: the Hermes project.` |
| 3 | `lib/prompt_cache.py` | lines 4–5: `Adapts the system_and_3 caching strategy from hermes-agent (MIT)` |
| 4 | `lib/error_insights.py` | lines 8–9: `Adapted from Hermes agent/insights.py (MIT)` |
| 5 | `lib/review_agent.py` | lines 232–234: `Adapted from Hermes _spawn_background_review templates … MIT license` |
| 6 | `packages/agent-lifecycle/lib/review_agent.py` | lines 232–234: same as #5 (see §6 for duplicate discussion) |
| 7 | `packages/verification-audit/lib/error_classifier.py` | line 17: `Adapted from Hermes agent/error_classifier.py (MIT)` |

---

## §3 Per-File Disposition Table

| COS file | Hermes source path | Hermes section / lines | COS adaptation summary | Risk flag |
|----------|--------------------|------------------------|------------------------|-----------|
| `lib/memory_manager.py` | `agent/memory_manager.py` | lines 83–374 | Verbatim structure; dependencies replaced (MemoryProvider abstracted locally; Hermes-home injection removed; Honcho/Hindsight/Mem0 omitted; EngramMemoryProvider added) | LOW |
| `lib/context_compressor.py` | `agent/context_compressor.py` | full file | Ported with provider swap (Hermes `call_llm` → COS `lib/dispatch.py`); tiktoken → chars/4 estimate; inline redactor replaces Hermes internal redaction module; trajectory compressor added as COS-first primitive | LOW |
| `lib/prompt_cache.py` | `run_agent.py` (system_and_3 caching pattern) | strategy/pattern only | Adapted caching strategy, not verbatim code; wraps Anthropic cache_control API | LOW |
| `lib/error_insights.py` | `agent/insights.py` | aggregation + trend patterns | Clean re-adaptation (not verbatim port); Hermes targets SQLite, COS targets flat JSONL; implementation differs materially | LOW |
| `lib/review_agent.py` | `run_agent.py` | lines 2749–2828 | Adapted function `_build_reviewer_prompt`; Hermes memory-store/skill-store refs replaced with COS Engram + TRUST_REPORT conventions | LOW |
| `packages/agent-lifecycle/lib/review_agent.py` | same as above | same as above | Real duplicate of `lib/review_agent.py` — files have diverged (236-byte size difference, substantive diff at lines 117–126 and 448); not a symlink | MEDIUM (see §6) |
| `packages/verification-audit/lib/error_classifier.py` | `agent/error_classifier.py` | JSONL taxonomy layer | Adapted classification patterns; COS adds `classify_jsonl` targeting `error-learning.jsonl`; original API (`classify_error`/`get_retry_strategy`) is COS-original | LOW |

---

## §4 NOTICE Preservation Requirements

MIT requires that the copyright notice and license text are preserved in copies or
substantial portions. The following entry **must** appear in the repository's NOTICE
file (the NOTICE-creation agent will read this section to produce the entry):

```
Hermes Agent
Source: https://github.com/NousResearch/Hermes-Function-Calling
License: MIT
Files: lib/memory_manager.py, lib/context_compressor.py, lib/prompt_cache.py,
       lib/error_insights.py, lib/review_agent.py,
       packages/agent-lifecycle/lib/review_agent.py,
       packages/verification-audit/lib/error_classifier.py
Attribution: "Original work © NousResearch, ported and adapted by Cognitive OS contributors"
```

Note: MIT does not require a NOTICE file in the Apache sense (there is no mandatory
aggregation clause). However, COS policy (ADR-267) requires NOTICE-file entries for
all vendored third-party code regardless of license. The entry above satisfies both
MIT copyright preservation and ADR-267 compliance.

---

## §5 Why This Is Backfill, Not New Adoption

The Hermes ports were implemented no later than 2026-04-30 (see `lib/context_compressor.py`
docstring: "2026-04-30, Session A"). ADR-259 (phantom-registry fix) and ADR-267
(Annex F + NOTICE doctrine) did not exist at that time. The inline comment discipline
was the sole attribution mechanism and was applied consistently across all seven files.

This Annex F documents the **existing state** as of 2026-05-11. It does not authorize
new Hermes ports. Any future ports from Hermes or other NousResearch projects must
follow the full ADR-267 pipeline: Annex F first, then port.

Per ADR-267 §Scenario B ("compounding risk"): when multiple ports from the same
upstream accumulate without a unified compliance record, the attribution surface
becomes fragmented and harder to audit on short notice. This backfill closes that
gap by creating a single dossier that cross-references all seven files.

---

## §6 Pending Tasks for Legal Review

IP-counsel review must answer the following questions specific to Hermes before
`reviewed-by-legal` can be set to `yes`:

1. **MIT claim verification** — Confirm the exact copyright line in
   `https://github.com/NousResearch/Hermes-Function-Calling/blob/main/LICENSE`.
   The organization name "NousResearch" was inferred from repo ownership; the legal
   entity and year on the copyright notice must be transcribed verbatim into the
   NOTICE entry (§4 above uses a placeholder).

2. **Sufficiency of inline attribution for commercial / SaaS use** — MIT §1 requires
   copyright notice + license text in "all copies or substantial portions." Inline
   `# Adapted from Hermes … (MIT)` comments satisfy the spirit but do not reproduce
   the full license text. Confirm whether the combination of (a) inline comments +
   (b) NOTICE-file entry + (c) adoption-registry.yaml satisfies MIT for a SaaS
   product where end users never receive source. If not, a `LICENSES/MIT-hermes.txt`
   file bundled with the distribution may be required.

3. **Re-licensing of COS-adapted variants** — The `lib/error_insights.py` and
   `lib/context_compressor.py` adaptations are described as "clean re-adaptations"
   (different data targets, new primitives added). Confirm whether these qualify as
   derivative works requiring attribution, or whether the structural divergence is
   sufficient to treat them as independent works inspired by Hermes patterns. The
   answer affects NOTICE scope.

4. **Real duplicate `lib/review_agent.py` ↔ `packages/agent-lifecycle/lib/review_agent.py`**
   — These files have diverged (size: 25649 vs 25413 bytes; diff at lines 117–126 and
   line 448 confirms substantive changes). Per CLAUDE.md, `lib/*.py` files are
   described as symlinks to `packages/*/lib/*.py`, but `readlink -f` confirms both
   resolve to independent absolute paths — they are **real files, not symlinks**.
   Legal question: do both files need independent NOTICE attribution, or is a single
   entry covering both paths sufficient? Engineering question (out of legal scope but
   blocking): which copy is authoritative, and should the divergence be resolved
   before or after legal review?

---

## §7 Reviewed-by-Legal Status

```
reviewed-by-legal: no
date-pending: TBD — awaiting IP-counsel scheduling post-2026-05-11 Annex F backfill sprint
blocking: NOTICE file creation (handled by separate agent) depends on §4 entry above;
          that entry is ready but exact copyright line (§6 question 1) should be
          confirmed before NOTICE is committed to main.
```
