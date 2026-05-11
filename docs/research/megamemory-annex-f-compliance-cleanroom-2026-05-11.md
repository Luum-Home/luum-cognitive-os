---
title: "MegaMemory Annex F — Compliance & Clean-Room Protocol"
date: 2026-05-11
annex: F
parent: megamemory-comparison-2026-05-11.md
scope: research-only
license_classification: "MIT — direct vendoring legally allowed with copyright preservation; pattern-only or port preferred for runtime independence"
---

# Annex F — Compliance & Clean-Room Protocol for MegaMemory

## 1. License posture
MIT verbatim head quote: "MIT License / Copyright (c) 2026 0xk3vin". Permits use, modification, redistribution with copyright + license preservation. No patent grant. Compare to Apache-2.0 (more explicit patent grant) and AGPL (REJECT).

## 2. What this corpus contains
TypeScript snippets + ONNX-pipeline descriptions from MegaMemory's MCP server. MIT permits with copyright preservation. Per-file headers satisfy this.

## 3. Port-vs-vendor decision per primitive (annex E)
- **In-process ONNX embedder** → PORT to Python via fastembed (Apache-2.0, verified cluster-A Finding 8). Language mismatch (TS → Python). Defer to LightRAG slice (cluster-D verdict).
- **resolve_conflict MCP tool** → PORT-pattern as wrapper over `mem_judge`. <1 day.
- **Concept-kind enum** → REFERENCE only, MIRIX slice may revisit.
- **Append-only timeline** → REFERENCE only, Engram covers.
- **JSONC stripper + MANAGED_FILE_MARKER** → REFERENCE only, candidate for cognitive-os-init.

## 4. If anything vendored directly
- Copy MIT LICENSE text to vendored file header OR dedicated NOTICE/THIRD-PARTY file.
- Preserve `Copyright (c) 2026 0xk3vin` exactly.
- Note modifications inline or in CHANGELOG.
- No NOTICE-file propagation requirement (MIT, unlike Apache, doesn't require NOTICE).

## 5. Why pattern-only is preferred despite MIT permissiveness
- Single-author project (bus factor 1).
- <10k node ceiling.
- Two-MCP fragmentation risk (MegaMemory + Engram).
- fastembed + MiniLM upstream both Apache-2.0 — port stack legally clean.

## 6. Open questions
- If vendoring JSONC stripper, where MIT header lives? Top-of-file pending ADR.
- LightRAG slice SDD: bundle MegaMemory embedder port with attribution OR treat as clean-room (since fastembed is the actual upstream)?
