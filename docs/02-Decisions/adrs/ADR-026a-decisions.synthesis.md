---
type: adr-synthesis
source: docs/02-Decisions/adrs/ADR-026a-decisions.md
adr: ADR-026a
status: accepted
reality_level: PARTIAL
provenance: ADR-026 left 7 open decision questions (D2.1-D2.4 for the config-reader consolidation, D3.1-D3.3 for the engram-module question) explicitly unresolved for human review; this addendum is an auto-generated, evidence-grounded answer to each, written by an architect agent from code inspection at HEAD=80e3262.
---

## Decision

Answers all 7 open questions from ADR-026 with evidence and explicit confidence levels: D2.1 YES adopt Option B (multi-variant `lib/config_loader.py`) — HIGH confidence; D2.2 YES fix the env-var precedence miss in the same PR — HIGH; D2.3 SCOPE-LIMIT rather than absorb 6+ adjacent YAML parsers (defer to follow-up "R2b") — MEDIUM; D2.4 YES defer schema validation to a future ADR — HIGH; D3.1 YES adopt Option C (keep `safe_engram`/`engram_client` separate, document the boundary) — HIGH; D3.2 YES fix the `cos_mcp.py:217-219` returncode=127 misclassification bug in the same work — HIGH; D3.3 YES retire the "R3 consolidation" audit-backlog label as resolved — HIGH.

## Why

Each answer is grounded in direct code evidence, not preference: D2.1/D2.2 — the three R2 sites have genuinely different cost profiles (hot-path regex vs. schema-aware `safe_load`) confirmed by inline code comments explicitly rejecting PyYAML's cold-start cost, and no test locks site 3's single-env-var behavior so adding a second env var is a strict superset that can't break anything. D2.3 — grep confirmed at least 6 additional files (later found to be 9, see spot-check below) duplicate the same path-resolution logic, but none have characterization tests, so absorbing them now would violate the project's own "characterize-first" discipline. D3.1/D3.2 — `grep -rn "from cos_lib.safe_engram|from cos_lib.engram_client"` confirmed zero production files import both modules, and the `cos_mcp.py:213-219` code was read directly, confirming returncode=127 (engram binary missing) falls through to being reported as a success string to users — a real, reproducible, user-visible defect.

## Consequences

The addendum's spot-checks found the parent ADR's own claims were only partially accurate: Claim 1 (zero overlapping callers) and Claim 2 (the cos_mcp misclassification) were both CONFIRMED by direct grep/code inspection. Claim 3 (the 5 R2 divergences are exhaustive) was judged PARTIALLY ACCURATE — the divergence categories are exhaustive for the 3 characterized sites, but the adjacent-parser footprint was understated: 4 files (`rate_limiter.py`, `sdd_pipeline.py`, `queue_advisor.py`, `smart_infra.py`) duplicating the same YAML-reading pattern were not listed in the parent ADR at all, bringing the true adjacent-parser count to at least 9 rather than the parent's implied 6. This produced two new unresolved items (U4: lock the canonical adjacent-parser list before Option B ships; U5: decide whether `lib/smart_access.SmartAccess.get_config_value()`, an existing pseudo-unified reader, should be replaced/wrapped/coexist with the new `config_loader.py`).

## Status & current state

R3 decisions (D3.1-D3.3) are marked CLOSED and implemented as of 2026-04-17 — the same day as this addendum. R2 decisions (D2.1-D2.4) are answered with recommendations but implementation ("Lote 4", ~9 hours estimated, sequenced after Lote 3's `lib/paths.py::project_root` consolidation lands first) is a forward plan in this document, not confirmed shipped. Frontmatter's `partial_remaining` flags the deferred "R2b" adjacent-parser absorption (~6h additional, gated on characterization tests existing first) as the concrete remaining scope. Two items from the parent ADR remain genuinely open, not resolved by this addendum: U1 (should `lib/memory.py::mem_save` route all writes through the scanner by default — judged a product/security decision requiring human input, not resolvable from code alone) and U3 (bash-side YAML consolidation, explicitly out of R2 scope by author intent, since Option B preserves grep-friendliness).

## Key links

ADR-026 (parent ADR, not modified by this addendum — intended to be read alongside it), PR #7 (`540998a`), PR #8 (`d5f6f12`), PR #9 (`6ed3e63`, R1 project-dir resolution — a hard sequencing prerequisite: "do NOT parallelize R1 + R2 on the same modules"), `lib/config_loader.py` (proposed), `lib/smart_access.py` (existing pseudo-unified reader, disposition undecided), `mcp-server/cos_mcp.py:213-219` (bug fix target), `tests/unit/test_cos_yaml_readers.py` (43 tests).
