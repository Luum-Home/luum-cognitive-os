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
  - `lib/memory_manager.py`
  - `lib/context_compressor.py`
  - `lib/prompt_cache.py`
  - `lib/error_insights.py`
  - `lib/review_agent.py`
  - `packages/agent-lifecycle/lib/review_agent.py`
  - `packages/verification-audit/lib/error_classifier.py`
- **Annex F**: `docs/research/hermes-annex-f-compliance-cleanroom-2026-05-11.md`  

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
  - `lib/hook_types.py`
- **Annex F**: `docs/research/openharness-annex-f-compliance-cleanroom-2026-05-11.md`  

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
  - `lib/file_mutation_queue.py`
- **Annex F**: `docs/research/pi-coding-agent-annex-f-compliance-cleanroom-2026-05-11.md`  

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
- **Annex F**: `docs/research/sprut-agent-kit-annex-f-compliance-cleanroom-2026-05-11.md`  

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
- **Annex F**: `docs/research/helixdb-annex-f-compliance-cleanroom-2026-05-11.md`  

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
- **Annex F**: `docs/research/ifixai-annex-f-compliance-cleanroom-2026-05-11.md`  

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
- **Annex F**: `docs/research/megamemory-annex-f-compliance-cleanroom-2026-05-11.md`  

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

---

## §2 — Transitive Python Dependencies

> Transitive scan was skipped (pip-licenses not installed). Run `pip install pip-licenses` and regenerate to populate this section.

---

## §3 — License Families Summary

| SPDX / License | Count |
| -------------- | ----- |
| `MIT` | 5 |
| `AGPL-3.0` | 1 |
| `Apache-2.0` | 1 |
| `PROPRIETARY` | 1 |

---

_Generated by `scripts/cos-generate-notices.py` on 2026-05-11_
