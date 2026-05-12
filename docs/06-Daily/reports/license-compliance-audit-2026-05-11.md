# Global License-Compliance Audit — Adoption-Debt Ledger

**Date:** 2026-05-11
**Owner:** platform-safety
**Trigger:** `manifests/external-tool-adoption-freeze.yaml::frozen=true` (commercial/SaaS pivot, ADR-267 Gap 1)
**Scope:** Every external tool COS has ever evaluated (radar + scouts + deep evals + private holaOS research).
**Status:** READ-ONLY audit. No artifacts mutated.
**Companion docs:** `manifests/external-tools-adoption.yaml`, `docs/05-Methodology/root/blocked-tools.md`, `rules/license-policy.md`, `docs/02-Decisions/adrs/ADR-259-external-pattern-adoption-posture.md`, `docs/02-Decisions/adrs/ADR-267-license-compliance-enforcement-architecture.md`.

---

## §1. Executive Summary

| Metric | Count |
|---|---:|
| **Total tools evaluated** (deep eval + radar manifest + blocked + private holaOS) | **94** |
| Deep evals on disk (`docs/03-PoCs/research/repo-scout/deep/*.md`) | 72 |
| Adoption-manifest rows (`manifests/external-tools-adoption.yaml`) | 34 |
| Blocked-tools ledger entries (`docs/05-Methodology/root/blocked-tools.md`) | 11 |
| Per-tool Annex-F clean-room dossiers (`docs/03-PoCs/research/*-annex-f-*.md` + private holaOS) | 4 (helixdb, ifixai, megamemory, holaOS) |
| **Adopted with runtime code in `lib/` or `packages/`** | **6 source files, 4 upstream tools** (Hermes ×4, Pi coding-agent ×1, HKUDS/OpenHarness ×1, Sprut Agent Kit ×1) |
| **Adopted as patterns-only (clean-room, no source copied)** | **6 ADRs** (ADR-260..265 — all sourced from holaOS) |
| Tools in radar with TRIAL/ADOPT verdict but **no Annex-F dossier** (= silent debt) | **≈ 30** |
| Tools with `reviewed-by-legal: yes` marker | **0** (zero — marker convention does not yet exist) |
| BLOCKER-licensed tools (AGPL/SSPL/BSL/ELv2/Commons Clause/FSL) | 11 in `blocked-tools.md` + 1 in deep evals (HelixDB AGPL-3.0) + 1 special (holaOS Apache-2.0+BSL-like §1.a) |
| BLOCKER-licensed tools mis-classified as anything other than REJECT | **0** confirmed — HelixDB sits in deep-eval as ASSESS/clean-room-only, holaOS sits in ADR-259 patterns-only |

### 3-line verdict on unfreeze safety

1. **Unfreeze is NOT safe today.** Zero tools carry a `reviewed-by-legal:` marker, and the ADR-267 firewall hook (`hooks/research-to-runtime-firewall.sh`) is present-but-unregistered (untracked in git status), so the **6 existing runtime-code leaks** from Hermes / Pi / HKUDS / Sprut were never gated.
2. The 6 holaOS clean-room adoptions (ADR-260..265) are *posture-defensible* per ADR-259 §1 and 17 USC §102(b), but the upstream license (Apache 2.0 modified with BSL-like §1.a) is a BLOCKER under `rules/license-policy.md` and the per-pattern attribution still cites `.private/holaos-research/*` paths in the public ADR text — a reviewer-discoverable surface that legal must opine on.
3. Pre-existing license tooling (`scripts/agentic-tool-license-matrix.sh`) only audits **5 hand-curated agentic tools** (promptfoo, garak, swe-bench, opencode, lethal-trifecta-policy) — it does **not** scan the 72-file deep-eval corpus, the manifest, or the runtime for ported code. The audit could not be performed by existing scripts and required manual walking.

---

## §2. Full Inventory Table

Risk-band legend:
- **HIGH** = BLOCKER license + non-pattern adoption, OR ADOPT/TRIAL with runtime code + no Annex-F + no legal review
- **MEDIUM** = ASSESS/TRIAL with Annex-F but no legal review; OR Apache-2.0 ported without NOTICE entry
- **LOW** = REJECT documented in `docs/05-Methodology/root/blocked-tools.md`, OR ADOPT with proper attribution + (eventual) legal review

### 2.1 Runtime-vendored code (CRITICAL — highest priority)

| Tool | Source path (deep eval / annex) | License (SPDX) | Policy class | Verdict | Adoption kind | Annex F? | Reviewed by legal? | Code in runtime? | Risk | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| **Hermes Agent (NousResearch)** | `docs/03-PoCs/research/repo-scout/deep/NousResearch__hermes-agent-2026-05-06.md` | MIT | SAFE | ADOPT | vendored (ported verbatim with attribution comments) | **No** | No | **YES** — 6 files: `lib/memory_manager.py`, `lib/context_compressor.py`, `lib/prompt_cache.py`, `lib/error_insights.py`, `lib/review_agent.py`, `packages/agent-lifecycle/lib/review_agent.py`, `packages/verification-audit/lib/error_classifier.py` | **HIGH** | Attribution exists in code comments (`# Ported from Hermes...`) but no NOTICE file, no Annex-F dossier, no SPDX header. Predates the 2026-05-10 clean-room doctrine. |
| **Pi coding-agent** | (not in deep-eval corpus — radar-implicit) | MIT (per code comment) | SAFE | ADOPT | vendored | **No** | No | **YES** — `lib/file_mutation_queue.py` | **HIGH** | TypeScript → Python port. No upstream URL captured, no LICENSE archived, no Annex-F. Silent debt. |
| **HKUDS/OpenHarness** | (related to HKUDS__LightRAG deep eval) | (LightRAG is MIT) — OpenHarness license unverified | UNKNOWN | ADOPT | vendored | **No** | No | **YES** — `lib/hook_types.py` lines 99 & 168, pinned to upstream commit `7873f0d10917...` | **HIGH** | Pinned-by-commit is excellent forensic hygiene but no LICENSE captured, no Annex-F, no NOTICE. The HKUDS org publishes LightRAG (MIT) but OpenHarness is a separate repo — license must be re-verified. |
| **Sprut Agent Kit** | (not in deep-eval corpus) | unknown | UNKNOWN | ADOPT | adapted (pattern + minor code) | **No** | No | **YES** — `packages/verification-audit/lib/research_scoring.py` ("last30days scoring pattern") | **HIGH** | Upstream URL/license not captured anywhere in repo. Silent debt — operator cannot answer "where did this come from?" without re-deriving. |

### 2.2 Patterns-only clean-room adoptions (LOWER risk but still incomplete)

| Tool | Source path | License (SPDX) | Policy class | Verdict | Adoption kind | Annex F? | Reviewed by legal? | Code in runtime? | Risk | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| **holaOS (Holaboss)** | `.private/holaos-research/holaos-comparison-2026-05-10.md` (+ annexes A–G) | Apache-2.0 modified **with BSL-like §1.a + §2.a unilateral tightening** | **BLOCKER** | patterns-only (REJECT for code) | clean-room (ADR-259) | **Yes** (private) | No | No (clean-room rewrite via ADR-260..265) | **MEDIUM** | ADR-259 + Annex F = strongest compliance posture in the repo. BUT: public ADRs leak `.private/holaos-research/...` paths in `Source-pattern:` fields — a reviewer-discoverable trail to BSL-like material. Patent/trademark search still pending per freeze yaml. |
| **HelixDB** | `docs/03-PoCs/research/helixdb-annex-{a,b,c,d,e,f}-2026-05-11.md` | **AGPL-3.0** | **BLOCKER** | ASSESS (clean-room reference only) | reference-only | **Yes** | No | No | LOW | Annex-D specifically documents open-core risk; Annex-F clean-room dossier produced. No code, no manifest row. Clean. |
| **iFixAi** | `docs/03-PoCs/research/ifixai-annex-{a..f}-2026-05-11.md` | Apache-2.0 | SAFE | TRIAL (provider-portable diagnostic) | reference + optional sub-process | **Yes** | No | No | LOW | Apache-2.0 + Annex-F = lowest-risk new adoption candidate. |
| **MegaMemory (0xK3vin)** | `docs/03-PoCs/research/megamemory-annex-{a..f}-2026-05-11.md` + deep eval | MIT | SAFE | TRIAL (algorithm-only port candidate) | reference (port pending) | **Yes** | No | No (port not yet executed) | LOW | Properly gated behind Annex F before any code lands. |

### 2.3 Manifest rows (`manifests/external-tools-adoption.yaml`)

All 34 rows are package-dependency or pattern-only adoptions, not vendored copies. Summary:

| Tool | License | Verdict (manifest) | Adoption | Annex F? | Legal? | Risk | Notes |
|---|---|---|---|---|---|---|---|
| PyYAML | MIT | KEEP | dependency | No | No | LOW | Foundation dep |
| Jinja2 | BSD-3 | KEEP | dependency | No | No | LOW | Foundation dep |
| Rich | MIT | INTEGRATE | dependency | No | No | LOW | |
| FastAPI | MIT | INTEGRATE | dependency | No | No | LOW | |
| Uvicorn | BSD-3 | INTEGRATE | dependency | No | No | LOW | |
| OpenAI SDK | Apache-2.0 | INTEGRATE | dependency | No | No | MEDIUM | Apache-2.0 — NOTICE file gap |
| Claude Agent SDK | MIT | INTEGRATE | dependency | No | No | LOW | |
| pytest | MIT | KEEP | dependency | No | No | LOW | |
| mutmut | BSD-3 | INTEGRATE | dependency | No | No | LOW | |
| pytest-smell | **UNKNOWN** | REMOVE | dependency | No | No | MEDIUM | Cleanup pending — license unknown is a risk |
| testcontainers | MIT | INTEGRATE | dependency | No | No | LOW | |
| redis-py | MIT | DEFER | dependency | No | No | LOW | |
| Opik | Apache-2.0 | INTEGRATE | dependency | No | No | MEDIUM | NOTICE gap |
| Langfuse | MIT | REMOVE | dependency | No | No | LOW | Cleanup pending |
| MLflow | Apache-2.0 | INTEGRATE | dependency | No | No | MEDIUM | NOTICE gap |
| Cognee | Apache-2.0 | INTEGRATE | dependency | No | No | MEDIUM | NOTICE gap |
| memU | **UNKNOWN** | REMOVE | dependency | No | No | MEDIUM | "verify_package_then_cleanup" status |
| NeMo Guardrails | Apache-2.0 | DEFER | dependency | No | No | MEDIUM | NOTICE gap |
| Jupyter | BSD-3 | DEFER | dependency | No | No | LOW | |
| Crawl4AI | Apache-2.0 | INTEGRATE | dependency | No | No | MEDIUM | NOTICE gap |
| LiteLLM | MIT | REMOVE | dependency | No | No | LOW | Cleanup pending |
| DeepEval | Apache-2.0 | ADOPT | dependency | No | No | MEDIUM | NOTICE gap |
| RAGAS | Apache-2.0 | ADOPT | dependency | No | No | MEDIUM | NOTICE gap |
| Enforcement tools (pre-commit, ruff, vulture, import-linter, diff-cover) | MIXED | INTEGRATE | dependency | No | No | LOW | Mixed but all permissive |
| BurntSushi/toml | MIT | KEEP | dependency | No | No | LOW | |
| modernc.org/sqlite | BSD-3 | KEEP | dependency | No | No | LOW | |
| FastMCP | Apache-2.0 | INTEGRATE | dependency + consumer | No | No | MEDIUM | Used in `packages/mcp-server/cos_mcp.py` — NOTICE gap |
| OpenSage ADK | Apache-2.0 | DEFER | pattern-only | No | No | LOW | |
| TaskingAI | Apache-2.0 | DEFER | pattern-only | No | No | LOW | |
| VERSA / dotAIslash | MIT | ASSESS | trial-overlay-standard | No | No | LOW | Spec only |
| Agent Skills ecosystem | MIXED | ASSESS | conformance reference | No | No | LOW | |
| Zed ACP | **UNKNOWN** | ASSESS | adapter-runtime-transport | No | No | MEDIUM | License unknown |
| OpenCode permissions/plugins | **UNKNOWN** | TRIAL | adapter-design | No | No | MEDIUM | License unknown — and TRIAL not ASSESS |
| Open Agent Passport | **UNKNOWN** | MONITOR | ledger-hardening-pattern | No | No | LOW | Research only |

### 2.4 Deep-eval corpus (radar-evaluated, not yet in manifest)

The 72 deep-eval files include many ADOPT/TRIAL verdicts where the operator's intent is "harvest patterns or port small algorithms". Highlights with non-LOW risk:

| Tool | Deep verdict | License | Policy | Annex F? | Risk | Reason |
|---|---|---|---|---|---|---|
| Aider-AI | ADOPT (edit-block + repo-map) | (Apache-2.0 — verified externally) | SAFE | No | MEDIUM | Verdict ADOPT but no Annex F, no port executed yet — silent debt accumulator |
| MemPalace | ADOPT (cross-harness peer) | (unverified — license line empty in deep eval) | UNKNOWN | No | MEDIUM | License field missing from deep eval |
| LightRAG (HKUDS) | ADOPT algorithm-only | MIT | SAFE | No | MEDIUM | Already-vendored sibling lib (`hook_types.py`) suggests creep risk |
| HippoRAG | ADOPT algorithm-only | (license empty in deep eval) | UNKNOWN | No | MEDIUM | License must be re-verified before port |
| SWE-agent | ADOPT (ACI reference) | (academic — license empty) | UNKNOWN | No | MEDIUM | License must be verified — likely MIT but not captured |
| gepa-ai/gepa | ADOPT (reflective text-evolution) | (empty) | UNKNOWN | No | MEDIUM | |
| graphiti (getzep) | ADOPT algorithm-only (bi-temporal edges) | (empty) | UNKNOWN | No | MEDIUM | |
| coder/agentapi | ADOPT (HTTP normalizer) | (empty) | UNKNOWN | No | MEDIUM | |
| praetorian/augustus | ADOPT (red-team corpus) | (empty) | UNKNOWN | No | MEDIUM | |
| simonw/llm | ADOPT (plugin architecture) | (empty) | UNKNOWN | No | MEDIUM | |
| stanfordnlp/dspy | ADOPT (foundational) | (empty) | UNKNOWN | No | MEDIUM | License must be verified |
| snyk/agent-scan | ADOPT | (empty) | UNKNOWN | No | MEDIUM | |
| crawl4ai | ADOPT | Apache-2.0 | SAFE | No | MEDIUM | Already in manifest |
| superpowers (obra) | ADOPT (with caveats) | (empty) | UNKNOWN | No | MEDIUM | |
| affaan-m/everything-claude-code | ADOPT | MIT (per re-verify note) | SAFE | No | LOW | Verified |
| everything-claude-code | (anomalous fork count) | MIT | SAFE | No | LOW | |
| Mibayy/token-savior | TRIAL | (empty — "license clean") | UNKNOWN | No | MEDIUM | Supply-chain audit flagged |
| BeehiveInnovations/pal-mcp-server | ADOPT | Apache-2.0 (manually verified) | SAFE | No | MEDIUM | NOTICE gap |
| OpenHands | pattern-harvest only | MIT (non-enterprise/) **+ proprietary enterprise/** | MIXED | No | MEDIUM | Mixed-license repo — must restrict to `non-enterprise/` paths |
| LiteLLM (cluster monitor-followup) | — | MIT | SAFE | No | LOW | Already REMOVE per manifest |
| Letta | — | (unverified) | UNKNOWN | No | MEDIUM | |
| MetaGPT | — | (unverified) | UNKNOWN | No | MEDIUM | |
| MIRIX-AI | — | (unverified) | UNKNOWN | No | MEDIUM | |
| QwenLM/qwen-code | — | (unverified) | UNKNOWN | No | MEDIUM | Used as dispatch fallback per ADR-049 — license must be verified |
| crewAI | — | (unverified) | UNKNOWN | No | MEDIUM | |
| topoteretes/cognee | — | Apache-2.0 (per manifest) | SAFE | No | MEDIUM | NOTICE gap |
| memvid | — | (unverified) | UNKNOWN | No | LOW | Pattern only |
| BerriAI/litellm | — | MIT | SAFE | No | LOW | Already REMOVE |
| Letta, MetaGPT, MIRIX, crewAI, cline, openai/codex, sigoden/aichat, RooCode, microsoft/graphrag, Mibayy, MiniMax-M2, FoundationAgents, … | various / unverified | varies | UNKNOWN | No | LOW–MEDIUM | Mostly read-only references in monitor-followup; verdicts not ADOPT |
| All "off-theme" deep evals (btop, k9s, bottom, goaccess, lazydocker, gitui, hatoo/oha, dive, jarun/nnn, viddy, soft-serve, etc.) | not adopted | MIT/Apache-2.0/BSD-2 | SAFE | n/a | LOW | No COS surface — no risk |
| All ADR-187 SURFACE-5 gated tools (bubbletea, ratatui, textual, bubbles, lipgloss, glamour, huh, gum, crossterm, gh-dash, lazygit, zellij, superfile, wtf, vhs) | gated, not adopted | MIT/MPL-2.0 | SAFE/CAUTION | n/a | LOW | Source-level proof gate blocks adoption |
| semgrep | reference (already in skill) | LGPL-2.1 | CAUTION | No | LOW | Dynamic-link / sub-process only per deep eval |
| wtfutil/wtf | reference | MPL-2.0 | CAUTION | No | LOW | File-level copyleft — sub-process only |
| openclaw | star-anomaly flag | MIT | SAFE | No | LOW | Not adopted |
| DEEP-PolyU/Awesome-GraphMemory | reading-list | NOASSERTION (all-rights-reserved default) | BLOCKER | No | LOW | Confirmed read-only |

### 2.5 Blocked-tools ledger (REJECT — LOW risk because explicitly rejected)

All 11 entries in `docs/05-Methodology/root/blocked-tools.md` (Daytona, Windmill, QueryWeaver, Auto-Claude, Claude Squad, Claudix, aRustyDev pre-commit-hooks, Context Engineering Kit, Inngest, FalkorDB, Arize Phoenix) are correctly classified as REJECT with documented alternatives. **Risk = LOW.** No mis-classification found.

---

## §3. Compounding-Risk Findings

### 3.1 CRITICAL — Runtime code leaks (the firewall hook was built to prevent these; it isn't deployed)

The ADR-267 research-to-runtime firewall hook (`hooks/research-to-runtime-firewall.sh`) exists on disk but is **untracked in git** and is not registered in `hooks/_lib/registration-allowlist.txt` (the registration-allowlist diff is the *only* unstaged modification). Pre-existing leaks below were therefore never gated:

| File | Upstream | License (claimed) | Annex F? | Attribution form | Compliance status |
|---|---|---|---|---|---|
| `lib/memory_manager.py` (multiple ports) | Hermes Agent / NousResearch | MIT (comment-attested) | NO | inline comment | **LEAK — no NOTICE, no Annex F** |
| `lib/context_compressor.py` | Hermes (`.claude/plugins/hermes-agent/agent/context_compressor.py`) | MIT (implied) | NO | inline comment | **LEAK** |
| `lib/prompt_cache.py` | Hermes `agent/prompt_caching.py` | MIT | NO | inline comment | **LEAK** |
| `lib/error_insights.py` | Hermes `agent/insights.py` | MIT | NO | inline comment | **LEAK** |
| `lib/review_agent.py` & `packages/agent-lifecycle/lib/review_agent.py` | Hermes `_spawn_background_review` | MIT | NO | inline comment | **LEAK** (and duplicated across two paths) |
| `lib/hook_types.py` (lines 99 & 168) | HKUDS/OpenHarness commit `7873f0d10917...` | unverified | NO | commit-pinned comment | **LEAK — license not captured** |
| `lib/file_mutation_queue.py` | Pi coding-agent `file-mutation-queue.ts` | MIT (comment-attested) | NO | inline comment | **LEAK — no upstream URL** |
| `packages/verification-audit/lib/error_classifier.py` | Hermes `agent/error_classifier.py` | MIT | NO | inline comment | **LEAK** |
| `packages/verification-audit/lib/research_scoring.py` | Sprut Agent Kit "last30days scoring pattern" | unverified | NO | inline comment | **LEAK — no upstream URL, no license** |

All 9 source files predate the 2026-05-10 clean-room doctrine (ADR-259). They are *technically defensible* (MIT permits this provided notices are preserved), but they violate the post-2026-05-11 doctrine on three counts: (a) no NOTICE file aggregating attributions, (b) no Annex-F clean-room dossier, (c) no SPDX-License-Identifier header. The ADR-267 firewall hook should have blocked the LATEST of these but is not active.

### 3.2 Adoptions executed before Annex-F existed (silent debt)

The Hermes ports (`memory_manager`, `context_compressor`, `prompt_cache`, `error_insights`, `review_agent`, `error_classifier`) and the Pi / HKUDS / Sprut ports all landed **before 2026-05-10**, the date the Annex-F clean-room protocol was introduced (per ADR-259 Context §). They are retroactively non-conformant. Each needs either: (a) a backfilled Annex-F dossier asserting MIT compatibility, or (b) demotion to "carries-MIT-attribution-only" with a NOTICE file.

### 3.3 Public ADRs leak `.private/holaos-research/...` paths

`docs/02-Decisions/adrs/ADR-260-grant-signed-cosd-api.md` and `docs/02-Decisions/adrs/ADR-264-tool-result-envelope.md` (likely also ADR-261..263, ADR-265 by pattern) contain explicit `Source-pattern: .private/holaos-research/holaos-annex-X.md §N` references. These public, git-tracked ADRs reveal:
1. That `.private/holaos-research/` exists and contains research material.
2. The exact section of the holaOS-derived annex each adoption draws from.
3. (Implicitly) that the operator has read the BSL-like source.

The clean-room defense in *Phoenix Technologies v. NEC* depends on demonstrable wall isolation. Naming the abstract spec is fine; pointing public artifacts at the wall is suboptimal. Legal must opine on whether this constitutes a wall-breach signal.

### 3.4 Upstream license drift (best-effort flag)

The deep-eval corpus dates to 2026-05-06. Tools whose upstream license may have changed and that COS still references with ADOPT/TRIAL verdict:
- **LiteLLM** — already REMOVE per manifest but cluster-monitor file (`monitor-followup/BerriAI__litellm-...`) still shows MIT; verify before the next ADR-049 review.
- **OpenHands** — deep eval notes "mixed license (MIT non-enterprise/, proprietary enterprise/)" — drift risk on the boundary.
- **HelixDB** — captured as AGPL-3.0 in deep eval + Annex-D; verify upstream has not added BSL/SSPL since.
- **qwen-code** — used as dispatch fallback in ADR-049; license never captured in repo. Qwen models have historically used Tongyi-Qianwen License (with named-entity restrictions). MUST verify before any commercial pivot.
- All "(empty)" license rows in §2.4 are unverified — risk that originally-permissive upstream has relicensed.

### 3.5 Manifest license fields containing `UNKNOWN` while still marked TRIAL/ADOPT

- `pytest-smell` (status: cleanup_required) — UNKNOWN + REMOVE = OK
- `memU` (status: verify_package_then_cleanup) — UNKNOWN + REMOVE = OK
- `Zed ACP` — UNKNOWN + ASSESS — **NEEDS RESOLUTION**
- `OpenCode permissions/plugins` — UNKNOWN + **TRIAL** — **NEEDS RESOLUTION before any further trial work**
- `Open Agent Passport / pre-action auth` — UNKNOWN + MONITOR — OK (research only)

### 3.6 NOTICE-file gap (Apache-2.0 obligation)

The repo has **no top-level NOTICE file** aggregating attributions for Apache-2.0 dependencies. Apache-2.0 §4(d) requires retention of NOTICE. Affected dependencies include: OpenAI SDK, Opik, MLflow, Cognee, NeMo Guardrails, Crawl4AI, DeepEval, RAGAS, FastMCP, OpenSage ADK, TaskingAI, BeehiveInnovations/pal-mcp-server, iFixAi, e2b/infra, agentscope, btop, continue, derailed/k9s, microsoft/agent-framework, opensage, semgrep (LGPL — separate obligation), testcontainers-python. **This is a structural gap** affecting ≈ 20 tools, not a per-tool problem.

---

## §4. Recommended Unfreeze Prerequisites (Per HIGH-Risk Tool)

### 4.1 Hermes Agent (6 files in `lib/` and `packages/`)
- Confirm the upstream LICENSE file at the time of each port (need git-blame timestamps cross-referenced against Hermes upstream commits).
- Decide retention strategy: (a) keep with backfilled Annex F + repo-level NOTICE, or (b) rewrite under clean-room. ADR-259 §1 implicitly required (b) for *future* adoption — does it apply retroactively?
- Resolve duplicate `review_agent.py` (lives in both `lib/` and `packages/agent-lifecycle/lib/`).
- Add SPDX-License-Identifier headers to all 6 files.

### 4.2 Pi coding-agent (`lib/file_mutation_queue.py`)
- Identify the upstream repo URL (not captured anywhere — operator must answer "Pi = which project?").
- Verify MIT claim by archiving the upstream LICENSE.
- Decide retain-with-NOTICE vs clean-room rewrite.

### 4.3 HKUDS/OpenHarness (`lib/hook_types.py`)
- Resolve the OpenHarness vs LightRAG license question — HKUDS publishes both and `hook_types.py` cites OpenHarness specifically. If OpenHarness license differs from LightRAG MIT, this could be a higher-tier blocker.
- Pin upstream commit hash + LICENSE file in NOTICE.

### 4.4 Sprut Agent Kit (`packages/verification-audit/lib/research_scoring.py`)
- Identify upstream URL. License unknown.
- Likely-permissive but **assumption** — must be verified before commercial pivot.

### 4.5 holaOS (ADR-260..265, all clean-room)
- Patent search (USPTO) per `external-tool-adoption-freeze.yaml` unfreeze_requires.
- Trademark search (TESS) for "Holaboss" and "holaOS".
- IP counsel opinion on whether public ADRs citing `.private/holaos-research/...` paths weakens the clean-room wall defense.
- IP counsel opinion on whether 17 USC §102(b) shields the 6 adoptions given the §1.a SaaS-prohibition clause in upstream license.

### 4.6 HelixDB
- No code adopted. Legal review can confirm that Annex-F + AGPL-3.0 + no code = compliant.

### 4.7 Manifest tools with UNKNOWN license (Zed ACP, OpenCode plugins)
- Resolve license before any further trial work touches these.

---

## §5. Tooling-Coverage Gap Assessment

### 5.1 `scripts/agentic-tool-license-matrix.sh` — what it does
Reads `.cognitive-os/tests/agentic-tools/license-matrix.json` (5 hand-curated entries: promptfoo, garak, swe-bench, opencode, lethal-trifecta-policy). Emits a PASS/FAIL gate report. Works correctly **but covers 5 of 94 tools = 5.3%**.

### 5.2 `scripts/cos-cross-stack-license-audit` — what it does
(Did not execute in this audit pass — operates against `manifests/cross-stack-license-audit.yaml`. Same architecture: audits a hand-curated manifest, not the deep-eval corpus.)

### 5.3 What the matrix scripts MISS (gaps this audit had to fill manually)

| Gap | Manual workaround used |
|---|---|
| No scanner across `docs/03-PoCs/research/repo-scout/deep/*.md` for License field | grep over all 72 files |
| No scanner across `docs/03-PoCs/research/*-annex-f-*.md` for clean-room dossier presence | manual `ls` |
| No scanner across `lib/`, `packages/`, `scripts/` for `Ported from`, `Adapted from`, `Source: https://github` markers | grep + manual classification |
| No cross-reference between deep-eval verdict (ADOPT/TRIAL) and presence of Annex-F or manifest row | manual join |
| No detection of duplicated ports (`review_agent.py` lives in two paths) | manual diff |
| No NOTICE-file presence check at repo root for Apache-2.0 deps | manual `find` (negative result) |
| No upstream-license-drift watcher (e.g., monthly recheck of LICENSE files for ADOPT-verdict deep evals) | none |
| No SPDX-License-Identifier header enforcement on ported source | none — would be a pre-commit hook |
| No `reviewed-by-legal:` frontmatter scanner | none — convention does not exist yet |
| No public-leak detector for `.private/...` paths in git-tracked files (would catch §3.3) | manual grep |

### 5.4 Recommended tooling additions (out of scope of this audit, follow-up work)
1. `scripts/cos-license-runtime-audit.py` — scan `lib/`, `packages/`, `scripts/` for `Ported from|Adapted from|Source: https?://github` and join to an attribution registry.
2. `scripts/cos-deep-eval-license-extractor.py` — parse `docs/03-PoCs/research/repo-scout/deep/*.md` for SPDX licenses, emit a CSV, flag UNKNOWN/empty rows.
3. `scripts/cos-annex-f-coverage.py` — for every ADOPT/TRIAL verdict, assert presence of `docs/03-PoCs/research/<tool>-annex-f-*.md` OR `.private/<tool>-research/<tool>-annex-f-*.md`.
4. `hooks/research-to-runtime-firewall.sh` (already on disk, **untracked**) — REGISTER IT before unfreeze.
5. NOTICE file generator from `manifests/external-tools-adoption.yaml` for Apache-2.0 / MPL-2.0 entries.
6. `reviewed-by-legal:` frontmatter convention + lint rule, applied to every Annex-F file.

---

## §6. Closing Remarks

The freeze decision was correct. The 6 patterns-only adoptions (ADR-260..265) are the *defendible* layer; the **9 runtime source files** (Hermes ×6 effective files, Pi, HKUDS, Sprut) are the **silent debt** that compounded before the doctrine existed. The firewall hook designed to prevent recurrence sits in the working tree, untracked. Until those 9 files are either Annex-F'd or NOTICE'd, until the holaOS clean-room wall is reviewed by counsel, and until `hooks/research-to-runtime-firewall.sh` is registered, unfreeze is premature.

**Single-line verdict:** Hold the freeze; backfill Annex F or NOTICE for the 9 leaked runtime files first, register the firewall hook second, run patent/trademark searches third, then unfreeze.
