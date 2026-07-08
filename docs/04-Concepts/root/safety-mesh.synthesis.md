---
type: concept-synthesis
source: docs/04-Concepts/root/safety-mesh.md
provenance: "A major cloud provider's AI coding tool shipped code with security vulnerabilities and expanded small fixes into large rewrites because it relied on a single-layer quality gate (a single point of failure); the lesson is that safety must be a mesh of independent layers catching different failure modes at different pipeline stages."
---

## What it is
The 14-layer defense-in-depth safety mesh that prevents agent errors from propagating through the COS pipeline, split into pre-launch gates and post-completion validators.

## Key mechanics
- Pre-launch (PreToolUse): [1] `clarification-gate.sh` — blocks (exit 2) if ambiguity score >60 across 7 signals; [2] `blast-radius.sh` — WARN only (exit 0), counts files/dirs/cross-service/bulk keywords, auto-escalates on infra/security keywords; [3] `dry-run-preview.sh` — blocks (exit 2) when `DRY_RUN=true`; [4] `rate-limiter.sh` — blocks (exit 2) on exceeding limits, applies to all tools.
- Post-completion (PostToolUse, all on Agent): [5] `scope-proportionality.sh` — blocks (exit 2) if change scope disproportionate to request; [6] `claim-validator.sh` — blocks (exit 2) in production on hallucination; [7] `assumption-tracker.sh` — WARN if 3+ assumption-language hits (HIGH: "I assume"/"presumably", MEDIUM: "I think"/"probably"); [8] `trust-score-validator.sh` — LOG only, validates Trust Report structure exists; [9] `confidence-gate.sh` — blocks (exit 2) in production if trust score <50; [10] `clarification-interceptor.sh` — LOG + signals orchestrator on `NEEDS_CLARIFICATION:` marker (max 2 rounds); [11] `auto-rollback-trigger.sh` — blocks+reverts after 3 retries exhausted, phase-aware (auto in recon/stabilization, needs approval in prod/maint); [12] `lib/cross_verifier.py` — on-demand library, second model catches first model's hallucinations; [13] `reinvention-check.sh` — WARN + suggest reuse when Engram/skill catalog match found; [14] `lib/memory_scanner.py` — session-start library scan for stale/contradictory Engram memories.
- 3 defense-in-depth properties: Independence (each layer catches a distinct failure mode; removing one leaves a gap), Graceful Degradation (BLOCK layers 1/3/4/7/9, WARN layers 2/5, LOG layers 6/8), Phase Awareness (reconstruction mostly warns, production mostly blocks).
- Each layer logs to its own JSONL in `.cognitive-os/metrics/` (e.g. `clarification-events.jsonl`, `blast-radius.jsonl`, `hallucinations.jsonl`).
- `/pentest-self` actively probes each layer across 6 categories: Prompt Injection, Permission Escalation, Secret Exfiltration, Token Flooding, Scope Escalation, Data Integrity.

## Relations & where used
Cross-references `docs/04-Concepts/root/security-stack.md` for the full security posture (external tools, MCP security, supply chain, red team). Adding a new layer requires: hook in `hooks/`, registration in `settings.local.json`, a metrics file, documentation here, an entry in `rules/RULES-COMPACT.md`, a `/cognitive-os-test` conflict check, and `/pentest-self` coverage.

## Status / caveats
FLAG: the source doc's own numbering is inconsistent — the numbered table lists 14 rows (1-14), but the "Layer Details" subsections skip from "Layer 10: Auto-Rollback Trigger" straight to "Layer 13: Reinvention Check" and "Layer 14: Memory Scanner," with no dedicated ### subsection for the table's row 12 (`lib/cross_verifier.py`, documented only in-table as "N/A, library call") and an off-by-one between some heading numbers and table row numbers. Not resolved here; flagged for operator awareness. Run `/pentest-self` weekly, after safety-mesh changes, and before production transitions.
