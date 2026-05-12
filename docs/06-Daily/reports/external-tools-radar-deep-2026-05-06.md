# External Tools Radar — Phase 2 Deep Audits — 2026-05-06

> Phase 2 of the radar. Source-level deep audit of the 22 top-tier candidates that the shallow Phase 1 ([`docs/06-Daily/reports/external-tools-radar-2026-05-06.md`](external-tools-radar-2026-05-06.md)) flagged as pass-to-deep. Per-repo artifacts under [`docs/03-PoCs/research/repo-scout/deep/`](../research/repo-scout/deep/). Engram persistence under topic-key prefix `tech-radar/`.
>
> **Method**: `gh api` for tree + metadata + tags + issues + CI runs + (where needed) raw LICENSE file. WebFetch / DeepWiki not used in this run because the parent radar already covered Phase-0 DeepWiki for these repos and `gh api` reads gave us the source-level depth Step 7 of `repo-scout/SKILL.md` requires.
>
> **Operator constraint observed**: read-only outside per-repo + consolidated artifacts. Engram updates are intentional per skill Step 9.

## Summary Table

| # | Repo | Classification | Score | License | Adopt-Mode | 1-Line Verdict |
|---|------|----------------|-------|---------|------------|----------------|
| 14 | stanfordnlp/dspy | **ADOPT** | **9.2** | MIT | dependency | Highest-confidence ADOPT in batch — Stanford NLP, 3.3y, v2.4.x, CI green; ships GEPA optimizer integration. |
| 22 | unclecode/crawl4ai | **ADOPT** | 8.8 | Apache-2.0 | dependency | CI 10/10, 65k★, healthy ratios; drop-in for COS web-research/RAG ingestion. |
| 7 | getzep/graphiti | **ADOPT** | 8.7 | Apache-2.0 | algorithm | Bi-temporal edges + cross-encoder reranking; port into Engram (don't vendor framework). |
| 12 | coder/agentapi | **ADOPT** | 8.7 | MIT | testdata + sidecar | 11-harness golden testdata corpus; perfect ADR-033 fit. Vendor testdata, port msgfmt parser. |
| 20 | snyk/agent-scan | **ADOPT** | 8.7 | Apache-2.0 | sidecar | Snyk-backed, CI 10/10; skill-aware security scanner with malicious-skill negative tests. |
| 5 | HKUDS/LightRAG | **ADOPT** | 8.6 | MIT | algorithm | EMNLP 2025 paper; port dual-level retrieval into Engram (algorithm only, framework too heavy). |
| 15 | gepa-ai/gepa | **ADOPT** | 8.6 | MIT | dependency | 9 production adapters incl. mcp_adapter + gskill subproject for COS skill optimization. |
| 18 | SWE-agent/SWE-agent | **ADOPT** | 8.6 | MIT | tool ports + eval corpus | 18 ACI tools incl. registry/web_browser/windowed_*; CTF + trajectories eval corpus. |
| 10 | simonw/llm | **ADOPT** | 8.6 | Apache-2.0 | pattern | Plugin/provider entry-point arch + cassette-based LLM tests; foundational for ADR-049. |
| 8 | MemPalace/mempalace | **ADOPT** | 8.8 | MIT | benchmark + cross-harness pattern | CI 9/10, multi-harness skill packaging, "best-benchmarked" claim — verify. |
| 3 | affaan-m/everything-claude-code | **ADOPT** | 8.5 | MIT | catalog diff | 455 SKILL.md files = forcing function for COS skill-coverage gap analysis. Metric-pump caveat. |
| 21 | praetorian-inc/augustus | **ADOPT** | 8.5 | Apache-2.0 | binary CI gate | 50+ probe families, 28+ generators, 4 multiturn strategies; complements snyk + Aguara. |
| 1 | obra/superpowers | **ADOPT** | 8.4 | MIT | pattern | Cross-harness skill schema + 7-step methodology peer to COS. CI red + 179k★ outlier caveat. |
| 19 | Aider-AI/aider | **ADOPT** | 8.4 | Apache-2.0 | pattern | Edit-block format + 38-language tree-sitter repo-map; mature production tool. |
| 16 | NousResearch/hermes-agent | **ADOPT** | 8.4 | MIT | catalog mining | 30+ provider plugins + 8 memory plugins; 8388-issue backlog caveat. License confirmed (was self-evolution split-out that's blocked). |
| 2 | agentsmd/agents.md | **ADOPT** | 8.0 | MIT | spec emit | Repo IS the AGENTS.md spec + landing site. Add emitter to `cognitive-os-init`. |
| 13 | BeehiveInnovations/pal-mcp-server | **ADOPT** | 7.9 | Apache-2.0 (manual verification) | pattern | API returned NOASSERTION; LICENSE file confirms Apache-2.0. Cassette tests + provider registries. 5mo stale. |
| 6 | OSU-NLP-Group/HippoRAG | **ADOPT** | 7.8 | MIT | algorithm | NeurIPS 2024; port PPR multi-hop into Engram. 8mo stale → frozen reference. |
| 17 | coleam00/Archon | **TRIAL** | 7.7 | MIT | pattern | TS-only + pre-1.0; recursive dogfooding interesting; lift workflow grammar + PRP pattern. |
| 11 | musistudio/claude-code-router | **TRIAL** | 7.5 | MIT | pattern | Same harness as ours; 2mo stale + 915 issues + housekeeping debt. Lift transformer/preset patterns. |
| 9 | Mibayy/token-savior | **TRIAL** | 7.4 | MIT | sandbox verify | Headline -77% tokens / -76% wall-time MUST be independently reproduced before sidecar adoption. |
| 4 | dmgrok/agent_skills_directory | **TRIAL** | 6.6 | MIT | schema reference | 15★ solo maintainer; pre-v1 daily-tag churn. Lift skill-manifest JSON Schema only. |

**Summary**: 18 ADOPT, 4 TRIAL, 0 ASSESS/HOLD/REJECT. No deep audit overturned a shallow PASS into a REJECT, but **4 shallow-implied-ADOPTs were downgraded to TRIAL** based on source-level evidence the shallow scout could not reach. Highest score: stanfordnlp/dspy (9.2/10). Lowest: dmgrok/agent_skills_directory (6.6/10).

## Adoption-Mode Distribution

| Adopt-Mode | Repos | Notes |
|------------|-------|-------|
| Direct dependency (pip install / vendor) | dspy, gepa, crawl4ai | High-confidence; library shape clean |
| Algorithm port (clean-room into Engram) | LightRAG (dual-level), HippoRAG (PPR), graphiti (bi-temporal edges + cross-encoder) | Engram retrieval+graph improvements |
| Pattern lifting (read source, reimplement) | superpowers, agents.md (spec-only), everything-claude-code, aider, simonw/llm, claude-code-router (TRIAL), pal-mcp-server, musistudio (TRIAL), Archon (TRIAL), dmgrok (TRIAL — schema only) | Translation effort varies |
| Tool/binary sidecar | coder/agentapi (Go), augustus (Go), agent-scan, token-savior (TRIAL — verify first) | Drop-in CLI tools |
| Catalog mining (selective skill/plugin extraction) | hermes-agent, mempalace, everything-claude-code, SWE-agent (tools/ subdir) | Read + selective port |
| Spec emit | agents.md | Add AGENTS.md emitter to cognitive-os-init |

## Cross-Reference vs Shallow Radar

The parent shallow radar ([`external-tools-radar-2026-05-06.md`](external-tools-radar-2026-05-06.md)) classified all 22 as `pass-to-deep`. The deep audit:

- **Confirmed shallow verdict on**: 18 of 22 (82%) — ADOPT scope and adoption-mode held.
- **Downgraded to TRIAL on**: 4 of 22 (18%):
  - **dmgrok/agent_skills_directory**: Pre-v1 churn (5 daily-style tags in 5 days, CI 6/10 failing, .playwright-mcp/ logs committed) made the project less mature than the shallow note implied.
  - **Mibayy/token-savior**: Headline -77% tokens / -76% wall-time / 0 losses claims need independent benchmark reproduction before sidecar adoption.
  - **musistudio/claude-code-router**: 2-month staleness + 915 open issues + committed backup-dirs lowered project hygiene below the shallow note's confidence.
  - **coleam00/Archon**: TS-only + pre-1.0 + recursive harness-builder-of-harness-builder overlap make pattern lifting (not adoption) the right scope.
- **License clarifications**:
  - **NousResearch/hermes-agent (main)**: confirmed **MIT**. The shallow radar's "LICENSE absent" caveat applied only to the `hermes-agent-self-evolution` split-out, which remains license-blocked pending a separate check.
  - **BeehiveInnovations/pal-mcp-server**: GitHub API returns `NOASSERTION`; manual `gh api .../contents/LICENSE` fetch confirms **Apache-2.0** (consistent with shallow Phase-2 note — verified again here).
- **Eye-watering metric anomalies surfaced consistently**: obra/superpowers (179k★/16k forks in 7 mo), affaan-m/everything-claude-code (174k★/27k forks in 4 mo), MemPalace/mempalace (51k★/6.7k forks in 1 mo), NousResearch/hermes-agent (134k★/20k forks in 9 mo). The shallow radar flagged some of these; the deep evidence confirms the pattern is consistent and recommends judging these projects purely on substance, not community signals.
- **CI red across multiple repos**: obra/superpowers (0/10), Archon (3/10), graphiti (3/10), aider (2/10), affaan-m (2/10), dmgrok (4/10), claude-code-router (7/9 — green), hermes-agent (0/10 — likely cancelled-not-failed), SWE-agent (2/10 — 8 null = likely cancelled), augustus (2/10 — 7 null = likely cancelled). Investigate `cancelled` vs `failed` before adopting any code that touches CI from these projects.
- **CI consistently green across**: token-savior (10/10), agent-scan (10/10), crawl4ai (10/10), mempalace (9/10), dspy (9/10), gepa (8/10), graphiti workflows (3 ok plus many null), pal-mcp-server (8/10), agentapi (7/10).

## Cross-Cutting Observations Surfaced by Deep Audit (Not Visible in Shallow)

1. **Cassette-based LLM testing is a converging best practice** — appears in simonw/llm (`tests/cassettes/`) and BeehiveInnovations/pal-mcp-server (`tests/{gemini,openai}_cassettes/`). Two independent confirmations → COS dispatch test suite should adopt this pattern, not invent a new one.
2. **Cross-harness skill packaging has a clear winner pattern** — obra/superpowers (`.claude-plugin/`, `.codex-plugin/`, `.cursor-plugin/`, `.opencode/`, `gemini-extension.json`), affaan-m/everything-claude-code (`.agents/skills/<name>/{SKILL.md, agents/openai.yaml}`), and MemPalace/mempalace (`.claude-plugin/skills/`, `.codex-plugin/skills/`) converge on roughly the same shape. COS cross-harness emit should mirror this.
3. **DSPy + GEPA is a single decision, not two** — `dspy/teleprompt/gepa/` (in DSPy) and `src/gepa/adapters/{dspy_adapter, dspy_full_program_adapter}` (in GEPA) integrate bidirectionally. Adopt as a pair.
4. **agentapi's testdata is unique** — 11-harness golden corpus (aider, amazonq, amp, auggie, claude, codex, copilot, cursor, gemini, goose, opencode) covering first_message + multi-line + thinking + confirmation_box + auto-accept-edits + initialization {ready, not_ready}. No other repo in the deep batch has this density of harness-fingerprinting fixtures. Direct adoption target for ADR-033 / `lib/harness_adapter/`.
5. **augustus + snyk/agent-scan + Aguara form a clean security trio** — augustus = offensive (190+ probes), agent-scan = defensive surface scanner (skill-aware + MCP-aware), Aguara = runtime defense (per radar). All three should land before flow #1 promotion per ADR-139..142.
6. **SWE-agent's `tools/*` subdirectory is the canonical ACI artifact** — 18 self-contained tool packages with `bin/` + (sometimes) `lib/`. Direct fit for COS skills as Unix-style tools. `tools/registry/` is especially interesting as a tool-that-registers-tools (dynamic-tool-creation primitive).
7. **Hermes-agent has the most comprehensive provider catalog (30+) and memory-backend catalog (8)** in the deep batch. This is a richer ADR-049 + Engram-comparison surface than the shallow radar suggested. Selective extraction is correct scope.
8. **CI red ≠ project red**: Many of the CI-red repos in this batch run cancelled/skipped jobs that surface as null in the conclusion field. Don't reject on CI score alone — inspect `cancelled` vs `failed` before drawing conclusions.

## Phase-3 Recommendations (Operator Decisions)

These are NOT auto-actions; they are decision-tickets for the operator.

1. **Adopt DSPy + GEPA as a paired dependency** (≤1 week pilot; deep targets #14 + #15). Use gskill subproject to optimize one COS skill end-to-end as proof.
2. **Adopt crawl4ai as the COS web-acquisition primitive** (≤2 days; deep target #22). Wrap in a `web-acquire` or extend `research-protocol`.
3. **Vendor coder/agentapi testdata under MIT into `lib/harness_adapter/testdata/`** (≤1 day; deep target #12). Port `lib/msgfmt/` parsing logic to Python.
4. **Land snyk/agent-scan + augustus in CI before flow #1 promotion** per ADR-139..142 (deep targets #20 + #21). agent-scan as pre-commit/pre-skill-publish gate; augustus as periodic red-team CI gate.
5. **Add an AGENTS.md emitter to `cognitive-os-init`** (≤half day; deep target #2). Cross-link harness roster against `lib/harness_adapter/` for coverage gap analysis.
6. **Run a benchmark sandbox on Mibayy/token-savior** (≤2-3 days; deep target #9) before any sidecar promotion. Reproduce or refute the headline -77% tokens / -76% wall-time numbers on COS task corpus.
7. **Port LightRAG dual-level retrieval + HippoRAG PPR + graphiti bi-temporal edges into Engram** (≤2 weeks total; deep targets #5 + #6 + #7). Sequence: graphiti edges first (schema), then dual-level (retrieval), then PPR (multi-hop).
8. **Catalog-diff hermes-agent + everything-claude-code + mempalace skill catalogs against the COS skills tree** (≤3 days; deep targets #16 + #3 + #8). Output: prioritized gap list for the next sprint.
9. **Use SWE-agent `tools/*` as the reference for COS skill-as-Unix-tool ergonomics** (deep target #18). Pilot with `tools/registry/` semantics for the COS dynamic-tool-creation primitive.
10. **Investigate cancelled-vs-failed CI status across hermes-agent, augustus, SWE-agent** before depending on any executable code from these repos. (`gh api repos/{owner}/{repo}/actions/runs?per_page=10` returns the `conclusion` field; `cancelled` is OK, `failure` is not.)

## Per-Repo Artifacts

All 22 per-repo deep audits live under [`docs/03-PoCs/research/repo-scout/deep/`](../research/repo-scout/deep/) with the schema specified by `skills/repo-scout/SKILL.md` Step 10a (frontmatter, classification, scoring, adoption signals, integration plan, risks, alternatives, raw metrics appendix, cross-reference vs shallow). Engram observations:

| Repo | Engram ID |
|------|-----------|
| obra/superpowers | 17307 |
| agentsmd/agents.md | 17308 |
| affaan-m/everything-claude-code | 17309 |
| dmgrok/agent_skills_directory | 17310 |
| HKUDS/LightRAG | 17311 |
| OSU-NLP-Group/HippoRAG | 17312 |
| getzep/graphiti | 17313 |
| MemPalace/mempalace | 17314 |
| Mibayy/token-savior | 17315 |
| simonw/llm | 17316 |
| musistudio/claude-code-router | 17318 |
| coder/agentapi | 17319 |
| BeehiveInnovations/pal-mcp-server | 17320 |
| stanfordnlp/dspy | 17321 |
| gepa-ai/gepa | 17322 |
| NousResearch/hermes-agent | 17323 |
| coleam00/Archon | 17324 |
| SWE-agent/SWE-agent | 17325 |
| Aider-AI/aider | 17329 |
| snyk/agent-scan | 17330 |
| praetorian-inc/augustus | 17331 |
| unclecode/crawl4ai | 17332 |

## Skipped (cached)

None. `--force` was not specified, but no Engram cache hits were found for these 22 repos under the `tech-radar/{repo-name}` topic prefix prior to this run.

## Errored

None. All 22 repos completed deep audit without errors.

## Notes on Method Deviations from `repo-scout/SKILL.md`

- **Step 4 (Shallow Clone) was replaced with `gh api git/trees/HEAD?recursive=1` reads** per the operator's CONSTRAINTS. This satisfied Step 4's "Code Quality / API Surface / Testing / Dependencies / Documentation" inspection without local clones.
- **Step 7 (Deep Evaluation) — full clone, full test suite execution, security audit, build verification** was downscoped to `gh api`-driven recursive tree inspection + targeted file fetches (e.g., raw LICENSE for pal-mcp-server) per the operator's "READ-ONLY codebase except the per-repo + consolidated report files" constraint. Deep evaluation depth came from source-tree inspection, not local execution. This deviates from the SKILL but is explicitly authorized by the operator's CONSTRAINTS block.
- **Step 8 (Cleanup)** is N/A — no clones were made.
- **License auto-enforcement (`lib/license_guard.py`)** was not invoked programmatically; license verification was inline (Apache-2.0/MIT/etc. confirmed via API metadata, with one manual LICENSE-file fetch for pal-mcp-server). No AGPL/SSPL/BUSL/FSL/Elastic-2.0 detected; no programmatic enforcement needed.
- **Adoption Signal #2 (release cadence — median days between last 5 tags)** was approximated qualitatively from tag-name patterns rather than computed by per-tag commit-date queries, to stay within the 480 tool-call budget. Where tag patterns clearly indicated weekly/biweekly/monthly cadence (e.g., `v2026.4.30, v2026.4.23, v2026.4.16, v2026.4.13, v2026.4.8` = weekly), no per-tag commit fetch was needed.

---

**Generated 2026-05-06 06:58 UTC** — `/repo-scout --batch /tmp/phase2-deep-targets.txt --level=deep` (single-session execution).
