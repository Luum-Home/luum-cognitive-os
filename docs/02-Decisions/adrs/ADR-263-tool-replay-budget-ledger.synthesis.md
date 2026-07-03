---
type: adr-synthesis
source: docs/02-Decisions/adrs/ADR-263-tool-replay-budget-ledger.md
adr: ADR-263
status: accepted
reality_level: REAL
provenance: A single global 5,000-char truncation threshold applied to every tool result regardless of type or repetition, so a typical 80-tool-call SDD session where ~25% of calls are large reads could add ~25,000 payload tokens to accumulated context with no cross-tool accumulator ever detecting cumulative saturation — more context than the headroom needed for reasoning.
---

## Decision

New module `lib/tool_replay_ledger.py` with a per-session SQLite-backed ledger tracking `(tool_name, target_hash)` tuples through three modes: FRESH (first occurrence, full result), PREVIEW (repeat occurrence, aggressive per-tool-catalog truncation), REFERENCE_ONLY (repeat + exhausted session budget, result replaced with a self-describing `[REF:tool=... target=... path=...]` pointer to a spillover file on disk). A companion `lib/tool_budget_catalog.py` gives per-tool thresholds (Bash/Read/WebFetch/Grep/_default) with hysteresis (a `trim_threshold_chars` gap above `preview_max_chars` to avoid cutting payloads that barely exceed the limit). `hooks/result-truncator.sh` queries the ledger before truncating; `lib/smart_truncator.py` remains the fallback when the ledger is unavailable or the tool isn't cataloged.

## Why

Three gaps identified against a private clean-room research pattern this ADR adopts under the ADR-259 protocol: no cross-tool accumulator (each call's budget starts from zero, so repeated large reads never trip a cumulative-saturation signal), no TTL or reference-only spillover (once truncated, content was permanently discarded with no recovery path), and no per-tool granularity (short Bash output and large file reads shared the same flat 5,000-char cap despite radically different real-size distributions). All numeric thresholds (20,000-char session cap, 10-item cap, 4-hour TTL, per-tool preview/reference limits) were independently derived from luum's own `truncation-events.jsonl` distribution rather than copied from the reference pattern's values — the reference pattern's 24K-char/8-item/6-hour defaults were explicitly not reused, per the clean-room constraint.

## Consequences

Positive: projected ~18,000 tokens/session saved in high-replay SDD-apply sessions, worth roughly $0.054/session directly at Sonnet input pricing but more valuably reducing early-compaction frequency and out-of-context failure rate; freed tokens let the model retain more specs/decision-history/code in context; the REFERENCE_ONLY pointer is self-describing so the model can recover full content via an explicit `Read` call rather than losing access entirely — only losing immediate presence in context; per-tool granularity means medium file reads under ~3,000 chars pass untruncated while noisy Bash output gets aggressively trimmed from its first call.

Negative/trade-offs: SQLite ledger and spillover files persist on disk if the session-end cleanup hook doesn't run (crash, `kill -9`) until the next session's cleanup catches them; a misinterpreted REFERENCE_ONLY pointer could make the model assume content is present when it isn't (mitigated by an explicit, tested pointer format); Bash hooks running in subshells mean each invocation opens/closes SQLite fresh, with unmeasured overhead risk at >50 tool-calls/minute (mitigation path: WAL mode + connection pooling, or degrade to plain JSON if overhead proves measurable); if the harness doesn't expose `$CLAUDE_SESSION_ID`, sessions degrade to grouping under a shared `"default"` bucket, losing isolation.

## Status & current state

Accepted 2026-05-11, implementation_status "implemented" with strong verification (`tests/unit/test_tool_replay_ledger.py`). Three open questions flagged as UNSURE at acceptance, none blocking: whether `sha256(tool_args_normalized)[:16]` target-hashing needs Bash-flag normalization for commands with the same intent but different flags (currently these would both register as FRESH); whether the 20K char cap should be recalibrated to 15K after two weeks of real usage data (projected ~20% additional savings with low impact on short sessions); whether exposing ledger stats to the model via system prompt (e.g. `[LEDGER: session_chars=14300/20000]`) would usefully let the model anticipate REFERENCE_ONLY and consolidate reads, against a ~50 token/turn meta-context cost — explicitly deferred to an experimental cohort measurement before enabling by default.

## Key links

ADR-259 (holaOS Adoption Posture, umbrella clean-room policy), ADR-016 (Context Diet), ADR-049 (LLM Dispatch — destination for the `chars_saved_per_session` metric), ADR-186 (Budget Enforcement — explicitly complementary not replaced, since ADR-186 measures hook-output tokens while this ADR measures tool-result chars, judged orthogonal dimensions not to be merged), `rules/result-management.md`, `hooks/result-truncator.sh`, `lib/smart_truncator.py` (remains fallback), `lib/tool_replay_ledger.py`, `lib/tool_budget_catalog.py`.
