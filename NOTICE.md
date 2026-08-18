<!-- This file is auto-generated. Run scripts/cos-generate-notices.py to regenerate. -->

# NOTICE — Third-Party Attributions

> This file lists upstream tools and Python dependencies used in Cognitive OS (COS). It is auto-generated from `manifests/external-tool-licenses.yaml` and the installed Python environment. Do not edit manually.

---

## §1 — Curated Upstream Tools

These tools have been vendored, ported, or adapted into COS source files. Each entry is governed by the corresponding Annex F compliance dossier.

### Hermes Agent

- **Status**: ![ALLOWED](https://img.shields.io/badge/status-ALLOWED-green)  
- **License (SPDX)**: `MIT`  
- **Upstream**: https://github.com/NousResearch/Hermes-Function-Calling  
- **Copyright**: Copyright (c) NousResearch  
- **Attribution**: Original work © NousResearch, ported and adapted by Cognitive OS contributors  
- **COS files**:
  - `cos_lib/memory_manager.py`
  - `cos_lib/context_compressor.py`
  - `cos_lib/prompt_cache.py`
  - `cos_lib/error_insights.py`
  - `cos_lib/review_agent.py`
  - `packages/agent-lifecycle/lib/review_agent.py`
  - `packages/verification-audit/lib/error_classifier.py`
- **Annex F**: `docs/03-PoCs/research/hermes-annex-f-compliance-cleanroom-2026-05-11.md`  

<details><summary>Compliance notes</summary>

Backfill: ports predate ADR-259/ADR-267. Exact copyright line from upstream LICENSE not extracted
(confirmed MIT, copyright holder NousResearch). Precise copyright year and wording must be confirmed
against https://github.com/NousResearch/Hermes-Function-Calling/blob/main/LICENSE before legal
review closes. lib/review_agent.py has a substantive duplicate in packages/agent-
lifecycle/lib/review_agent.py — tracked separately.

</details>

### HKUDS/OpenHarness

- **Status**: ![ALLOWED](https://img.shields.io/badge/status-ALLOWED-green)  
- **License (SPDX)**: `MIT`  
- **Upstream**: https://github.com/HKUDS/OpenHarness  
- **Copyright**: Copyright (c) 2025 OpenHarness Contributors  
- **Attribution**: Ports HttpHookDefinition and PromptHookDefinition from HKUDS/OpenHarness (MIT), adapted to COS conventions.  
- **COS files**:
  - `cos_lib/hook_types.py`
- **Annex F**: `docs/03-PoCs/research/openharness-annex-f-compliance-cleanroom-2026-05-11.md`  

<details><summary>Compliance notes</summary>

Commit hash recorded at source: 7873f0d109174a57b3b1af7aa5397a6b3b0bd551. Source path:
src/openharness/hooks/schemas.py. MIT confirmed via WebFetch 2026-05-11. Attribution is complete
inline at lib/hook_types.py lines 4-6.

</details>

### Pi coding-agent

- **Status**: ![HOLD](https://img.shields.io/badge/status-HOLD-orange)  
- **License (SPDX)**: `MIT`  
- **Upstream**: UNKNOWN  
- **Copyright**: MISSING — upstream not identifiable  
- **Attribution**: PENDING — upstream URL and copyright holder must be supplied before attribution can be authored  
- **COS files**:
  - `cos_lib/file_mutation_queue.py`
- **Annex F**: `docs/03-PoCs/research/pi-coding-agent-annex-f-compliance-cleanroom-2026-05-11.md`  

<details><summary>Compliance notes</summary>

BLOCKED pending upstream identification. MIT claimed inline only. Two GitHub searches returned zero
matching repositories. No upstream URL, commit hash, or copyright holder recorded in source file.
Author of original port must supply: (1) canonical upstream URL, (2) exact copyright line, (3)
commit hash. Do NOT distribute until resolved.

</details>

### Sprut Agent Kit

- **Status**: ![BLOCKED](https://img.shields.io/badge/status-BLOCKED-red)  
- **License (SPDX)**: `MIT`  
- **Upstream**: https://github.com/AlekseiUL/sprut-agent-kit  
- **Copyright**: MISSING — LICENSE file returned HTTP 404; copyright holder unknown  
- **Attribution**: PENDING — cannot be authored; copyright holder and license file unverifiable  
- **COS files**:
  - `packages/verification-audit/lib/research_scoring.py`
- **Annex F**: `docs/03-PoCs/research/sprut-agent-kit-annex-f-compliance-cleanroom-2026-05-11.md`  

<details><summary>Compliance notes</summary>

Worst-case attribution profile: COS source file contains only bare name reference with no URL,
commit, license, or copyright. Upstream MIT claimed in README but LICENSE file returned 404.
Copyright holder and year unknown. HOLD — cannot distribute until attribution gap is closed.

</details>

### HelixDB

- **Status**: ![TRIAL-PATTERNS](https://img.shields.io/badge/status-TRIAL--PATTERNS-yellow)  
- **License (SPDX)**: `AGPL-3.0`  
- **Upstream**: https://github.com/HelixDB/helix-db  
- **Copyright**: Copyright (c) HelixDB contributors (GNU AGPL-3.0)  
- **Attribution**: Clean-room derived from behavioral spec; no helix-db source referenced. Design patterns documented in Annex F.  
- **Annex F**: `docs/03-PoCs/research/helixdb-annex-f-compliance-cleanroom-2026-05-11.md`  

> **OSS MODE WARNING**: This entry has a copyleft license (`AGPL-3.0`). Runtime inclusion is blocked per `rules/license-policy.md`.

<details><summary>Compliance notes</summary>

REJECT runtime / TRIAL-PATTERNS pattern-only. AGPL-3.0 §13 triggers copyleft on any network
interaction. Three authorised TRIAL-PATTERNS primitives: typed-ADT agent-call surface, reranker
fusion (RRF+MMR), hoisted-embedding/IO-continuation. Clean-room two-engineer protocol required. No
upstream code vendored.

</details>

### iFixAi

- **Status**: ![PATTERN-ONLY](https://img.shields.io/badge/status-PATTERN--ONLY-blue)  
- **License (SPDX)**: `Apache-2.0`  
- **Upstream**: https://github.com/ifixai-ai/iFixAi  
- **Copyright**: Copyright 2026 iMe  
- **Attribution**: Original work © 2026 iMe (Apache-2.0). Pattern-only adoption. Modified by Cognitive OS contributors.  
- **Annex F**: `docs/03-PoCs/research/ifixai-annex-f-compliance-cleanroom-2026-05-11.md`  

<details><summary>Compliance notes</summary>

Apache-2.0. Pattern-only preferred over vendoring (uncalibrated thresholds, iMe open-core split
risk, project age ~1 week at eval). Pinned to v1.0.0 commit 2e56c4f. Upstream NOTICE file presence
not independently verified — required check before any vendoring. Mandatory-minimum inspection cap
mechanic blocked pending ADR-265.

</details>

### MegaMemory

- **Status**: ![PATTERN-ONLY](https://img.shields.io/badge/status-PATTERN--ONLY-blue)  
- **License (SPDX)**: `MIT`  
- **Upstream**: UNKNOWN — upstream repository URL not recorded  
- **Copyright**: Copyright (c) 2026 0xk3vin  
- **Attribution**: Original work © 2026 0xk3vin (MIT). Port/pattern adoption by Cognitive OS contributors.  
- **Annex F**: `docs/03-PoCs/research/megamemory-annex-f-compliance-cleanroom-2026-05-11.md`  

<details><summary>Compliance notes</summary>

MIT confirmed verbatim. Copyright: "MIT License / Copyright (c) 2026 0xk3vin". Pattern-only
preferred (single-author bus factor, <10k node ceiling, MCP fragmentation risk). Planned ports:
resolve_conflict MCP tool wrapper over mem_judge; ONNX embedder deferred to LightRAG slice. Upstream
repository URL not recorded — gap flagged.

</details>

### holaOS

- **Status**: ![HOLD](https://img.shields.io/badge/status-HOLD-orange)  
- **License (SPDX)**: `PROPRIETARY`  
- **Upstream**: CONFIDENTIAL  
- **Copyright**: CONFIDENTIAL — see internal compliance dossier  
- **Attribution**: Reference: internal compliance dossier (Apache-2.0 modified BSL-like terms; distribution restricted)  
- **Annex F**: `internal compliance dossier`  

<details><summary>Compliance notes</summary>

License classification: Apache-2.0 with BSL-like additional restrictions. Distribution status under
review. Upstream URL and compliance details available in internal compliance dossier only — do NOT
include private repository paths in this manifest. Treat as HOLD until legal review closes.

</details>

### Pyrefly

- **Status**: ![ALLOWED](https://img.shields.io/badge/status-ALLOWED-green)  
- **License (SPDX)**: `MIT`  
- **Upstream**: https://github.com/facebook/pyrefly  
- **Copyright**: Copyright (c) Meta Platforms, Inc. and affiliates  
- **Attribution**: Pyrefly © Meta Platforms, Inc. and affiliates (MIT); invoked as optional CLI tooling only.  
- **COS files**:
  - `pyproject.toml`
  - `scripts/cos-pyrefly-pilot`
- **Annex F**: `docs/06-Daily/reports/external-tools-radar-pyrefly-addendum-2026-05-15.md`  

<details><summary>Compliance notes</summary>

TRIAL advisory CLI gate. No source vendored and no runtime import; optional installation through the
typecheck extra or uvx. Verify exact LICENSE copyright line before any vendoring, though current
adoption is subprocess tooling only.

</details>

### Aider

- **Status**: ![INVENTORIED-PENDING-REVIEW](https://img.shields.io/badge/status-INVENTORIED--PENDING--REVIEW-lightgrey)  
- **License (SPDX)**: `Apache-2.0`  
- **Upstream**: https://github.com/Aider-AI/aider  
- **Copyright**: MISSING — upstream LICENSE.txt is the unmodified Apache-2.0 body; the copyright line exists only as the unfilled template in the appendix  
- **Attribution**: Repo-map concept referenced from Aider-AI/aider (Apache-2.0). Implementation is first-party; no upstream source present.  
- **COS files**:
  - `cos_lib/repo_map.py`
  - `scripts/cos-repo-map`
- **Annex F**: `NONE — no Annex F dossier was written for this adoption`  

<details><summary>Compliance notes</summary>

Form evidence, verbatim from the cos_lib/repo_map.py module docstring (lines 4-6): "Pattern-port of
Aider's repo-map idea: build a compact, token-budgeted map of relevant repository files/symbols,
then overlay COS governance context. This is first-party code; no Aider runtime dependency is
required." Corroborated mechanically: `grep -rnE '^\s*(import|from)\s+aider\b' --include='*.py' .`
returns zero rows, and `grep -in aider requirements.txt pyproject.toml` returns zero rows — aider is
neither imported nor declared as a dependency. scripts/cos-repo-map is a 23-line argparse wrapper
that calls cos_lib.repo_map.build_repo_map; it contains no upstream-derived logic. SEPARATE
RELATIONSHIP, deliberately not listed in cos_files because no code is adopted:
cos_lib/harness_adapter/aider.py (registered in cos_lib/compatibility_layer.py:97-98) parses aider's
chat-transcript FORMAT (.aider.chat.history.md) so COS can ingest sessions produced by the tool.
That is interoperability with an output format, a different relationship from porting an idea, and
it is recorded here so a reviewer sees both and can tell them apart. install.sh also lists "aider"
as a supported harness target (line 25). NOT ASSESSED by this entry: whether the reimplementation is
substantively independent of upstream's algorithm. This entry records that the docstring declares a
pattern-port and that no upstream source is present; it does not compare the two implementations.

</details>

### DSPy

- **Status**: ![INVENTORIED-PENDING-REVIEW](https://img.shields.io/badge/status-INVENTORIED--PENDING--REVIEW-lightgrey)  
- **License (SPDX)**: `MIT`  
- **Upstream**: https://github.com/stanfordnlp/dspy  
- **Copyright**: Copyright (c) 2023 Stanford Future Data Systems  
- **Attribution**: Optional integration seam for stanfordnlp/dspy (MIT). No upstream source present; the package is probed for, never imported.  
- **COS files**:
  - `cos_lib/dspy_pilot.py`
  - `scripts/cos-dspy-pilot`
- **Annex F**: `NONE — no Annex F dossier was written for this adoption`  

<details><summary>Compliance notes</summary>

Weakest form of contact in this manifest. cos_lib/dspy_pilot.py is 46 lines and the only reference
to upstream is a capability probe: `importlib.util.find_spec("dspy") is not None`. It never imports
dspy; the dataclass (DspyPilotReport) and the input/output signature it emits are written in-repo.
`grep -rnE '^\s*(import|from)\s+dspy\b' --include='*.py' .` returns zero rows, and dspy appears in
neither requirements.txt nor pyproject.toml — so the probe reports status "dependency-missing" on a
default install. What IS borrowed is vocabulary: "signature" with inputs/outputs is DSPy's term of
art, here a plain dict returned by sdd_verify_signature(). Already recorded elsewhere, though not as
a license entry: manifests/feature-tool-due-diligence.yaml:23-26 carries tool_id dspy with the same
upstream link. That is a due-diligence row, not an attribution row; this entry does not duplicate
it, it closes the license-manifest gap.

</details>

### LightRAG

- **Status**: ![INVENTORIED-PENDING-REVIEW](https://img.shields.io/badge/status-INVENTORIED--PENDING--REVIEW-lightgrey)  
- **License (SPDX)**: `MIT`  
- **Upstream**: https://github.com/HKUDS/LightRAG  
- **Copyright**: Copyright (c) 2025 LightRAG Team  
- **Attribution**: Retrieval concept referenced from HKUDS/LightRAG (MIT). No upstream source present.  
- **COS files**:
  - `cos_lib/memory_retrieval_benchmark.py`
- **Annex F**: `NONE — no Annex F dossier was written for this adoption`  

<details><summary>Compliance notes</summary>

CORRECTS A STANDING CLAIM. manifests/external-tool-adoption-freeze.yaml (line 79-81) states LightRAG
is "recorded in NOTICE.md and manifests/external-tool-licenses.yaml". It was in neither. Before this
entry, `grep -in lightrag manifests/external-tool-licenses.yaml NOTICE NOTICE.md` returned exactly
two rows, both the phrase "ONNX embedder deferred to LightRAG slice" inside the MegaMemory notes — a
forward-looking mention of a different project, not an entry for this one. Root NOTICE had zero
LightRAG rows. Form evidence: the sole reference in code is the comment at
cos_lib/memory_retrieval_benchmark.py:139, verbatim: "# LightRAG-inspired dual-level local proxy:
precise title/entity". Landed 2026-05-08 in commit e6b41fd43 "feat(memory): add retrieval benchmark
Slice 0" (`git log --follow --diff-filter=A -- cos_lib/memory_retrieval_benchmark.py`). No import,
no dependency declaration.

</details>

### Crawl4AI

- **Status**: ![INVENTORIED-PENDING-REVIEW](https://img.shields.io/badge/status-INVENTORIED--PENDING--REVIEW-lightgrey)  
- **License (SPDX)**: `Apache-2.0`  
- **Upstream**: https://github.com/unclecode/crawl4ai  
- **Copyright**: MISSING — upstream LICENSE is the unmodified Apache-2.0 body with no filled-in copyright line. Upstream adds a MANDATORY attribution clause, quoted verbatim in notes.  
- **Attribution**: This product includes software developed by UncleCode (https://x.com/unclecode) as part of the Crawl4AI project (https://github.com/unclecode/crawl4ai).  
- **COS files**:
  - `requirements.txt`
  - `packages/ecosystem-tools/lib/web_crawler.py`
- **Annex F**: `NONE — no Annex F dossier was written for this adoption`  

<details><summary>Compliance notes</summary>

Strongest form of contact among the four backfilled entries, and the only one that is an actual
dependency: requirements.txt:31 pins `crawl4ai>=0.8.0`, and packages/ecosystem-
tools/lib/web_crawler.py imports it directly at lines 23 and 179 (`from crawl4ai import
AsyncWebCrawler, BrowserConfig, CrawlerRunConfig`; `from crawl4ai.extraction_strategy import
JsonCssExtractionStrategy`), degrading to a urllib+regex fallback when absent. No upstream source is
vendored into this repo. ATTRIBUTION DEFECT FOUND, now fixed in the root NOTICE. The upstream
LICENSE requires this exact sentence in distributions: "This product includes software developed by
UncleCode (https://x.com/unclecode) as part of the Crawl4AI project
(https://github.com/unclecode/crawl4ai)." The root NOTICE carried a paraphrase that dropped both
URLs. Verified 2026-08-15 by fetching the raw upstream LICENSE; the two URLs were added to NOTICE on
the same date. Crawl4AI was present in the root NOTICE but absent from this manifest and from
NOTICE.md before this entry. It is separately recorded in manifests/external-tools-
adoption.yaml:214-216 with verdict INTEGRATE.

</details>

---

## §2 — Transitive Python Dependencies

> Transitive scan was skipped (pip-licenses not installed). Run `pip install pip-licenses` and regenerate to populate this section.

---

## §3 — License Families Summary

| SPDX / License | Count |
| -------------- | ----- |
| `MIT` | 8 |
| `Apache-2.0` | 3 |
| `AGPL-3.0` | 1 |
| `PROPRIETARY` | 1 |

---

_Generated by `scripts/cos-generate-notices.py` on 2026-08-18_
