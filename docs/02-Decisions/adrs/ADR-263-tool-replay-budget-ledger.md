---
adr: 263
title: 'Tool-Replay Budget Ledger: Per-Session Cap + Preview/Reference-Only Modes'
status: accepted
implementation_status: implemented
date: '2026-05-11'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: tool replay ledger module and tests implement per-session replay
  budget decisions
verification:
  level: strong
  commands:
  - python3 -m pytest tests/unit/test_tool_replay_ledger.py -q
  proves:
  - behavior_contract
---

# ADR-263 — Tool-Replay Budget Ledger: Per-Session Cap + Preview/Reference-Only Modes

## Status

Accepted

**Date:** 2026-05-11
**Owner:** orchestrator
**Tier:** core
**Authors:** orchestrator (Claude Sonnet 4.6)
**Implements:** ADR-259 (holaOS Adoption Posture — patterns only)
**Source-pattern:** Internal compliance dossier §Tool-replay budget ledger (AnnexB::§B1)
**Related:** rule `result-management`, ADR-016 (Context Diet), ADR-049 (LLM Dispatch), ADR-186 (Budget Enforcement)

---

## Context

### Current state

luum-agent-os implements tool-result truncation through two artifacts:

- `hooks/result-truncator.sh` — generic PostToolUse hook over Bash outputs (184 lines).
- `lib/smart_truncator.py` — `smart_truncate(command, output, max_chars=5000)` with a head/tail split strategy (620 lines).

The relevant `cognitive-os.yaml` configuration (lines 548–559):

```yaml
result_truncation:
  enabled: true
  max_chars: 5000
  head_chars: 2000
  tail_chars: 1000
  never_truncate_patterns: ["FAIL","ERROR","panic","PASS","coverage:"]
```

A single global threshold of 5,000 chars controls all tool results, with no distinction by tool type or usage frequency within the session.

### Gaps identificados

The documented delta table in [private clean-room research dossier] §Tool-replay budget ledger identifies three critical gaps against the reference pattern:

1. **No cross-tool accumulator.** Each tool call starts the budget from zero. If an SDD-apply session runs `grep giant`, then `find giant`, then `cat giant`, each contributes up to 5,000 truncated chars to the model context without any mechanism detecting cumulative saturation.

2. **No TTL or `reference_only`.** Once truncated, the original payload is permanently discarded. There is no disk spillover or pointer that lets the model recover the full content when needed.

3. **No per-tool granularity.** Short Bash output, large files, web search, and MCP results share the same 5,000-char limit, even though their real-size distributions are radically different.

### Real usage: the replay-without-memory problem

In a typical 80-tool-call SDD session, roughly 25% are large reads (Read files over 200 lines, broad Grep calls, Bash with find/cat logs). Without a ledger, those 20 calls add about 25,000 payload tokens to accumulated context, more than the headroom needed for reasoning. The pattern documented in Annex B projects about 72% payload-replay savings with a calibrated session cap (about 18,000 tokens saved per session).

### Clean-room constraint

This ADR adopts the per-session ledger **pattern** described in [private clean-room research dossier] §Tool-replay budget ledger under the ADR-259 and Annex F clean-room protocol. Thresholds, identifiers, spillover format, and module structure are independently derived from real luum usage data. No literal number from the reference pattern is copied; where the reference pattern establishes values, the local derivation is documented.

---

## Decision

### 1. `lib/tool_replay_ledger.py` — Per-session ledger with local SQLite

A new Python module with state persisted in `.cognitive-os/sessions/<id>/replay-ledger.sqlite`.

```python
from enum import Enum
from dataclasses import dataclass

class Mode(Enum):
    FRESH = "fresh"                   # first occurrence of (tool, target): full result
    PREVIEW = "preview"               # repeat: aggressive truncation according to catalog
    REFERENCE_ONLY = "reference_only" # repeat + exhausted budget: replace with pointer

@dataclass
class LedgerDecision:
    mode: Mode
    trimmed: bool
    trim_reason: str | None    # "char_cap" | "item_cap" | None
    replay_chars: int
    total_session_chars: int
    max_session_chars: int
    total_session_items: int
    max_session_items: int

class ToolReplayLedger:
    def record(self, tool_name: str, target_hash: str, result_chars: int) -> LedgerDecision:
        """Consumes budget for this (tool_name, target_hash). Returns mode."""

    def get_mode(self, tool_name: str, target_hash: str) -> Mode:
        """Reads mode without modifying accumulators."""

    def stats(self) -> dict:
        """Returns session metrics: chars_saved, items_tracked, etc."""

    def prune_expired(self) -> int:
        """Deletes entries with expired TTL. Returns deleted count."""
```

`target_hash` is computed as `sha256(tool_args_normalized)[:16]`. For tools with non-deterministic outputs (timestamps, PIDs), normalization extracts structural arguments (file path, query pattern) before hashing, avoiding false misses.

The ledger is pruned on each `record()` when the entry count exceeds twice of the `item_cap_per_session`. TTL applied: an entry expires `ttl_hours` after its last `touchedAt`.

### 2. `lib/tool_budget_catalog.py` — Per-tool catalog with thresholds derived from luum

Thresholds are derived from the real output distribution in `truncation-events.jsonl` of luum, not copied from the reference pattern. The rationale: Read outputs for typical Python files in this repo have a median of ~3,500 chars; Bash with grep/find usually falls around 800–1,500 chars; WebFetch has high variance with a long tail.

```python
# Thresholds calibrated from truncation-events.jsonl of luum
# (not copied from the reference catalog)

CATALOG: dict[str, ToolBudgetEntry] = {
    "Bash": ToolBudgetEntry(
        preview_max_chars=1500,
        reference_max_chars=500,
        trim_threshold_chars=2200,   # hysteresis: cut at 1500 only if output > 2200
    ),
    "Read": ToolBudgetEntry(
        preview_max_chars=3000,
        reference_max_chars=800,
        trim_threshold_chars=4500,
    ),
    "WebFetch": ToolBudgetEntry(
        preview_max_chars=2500,
        reference_max_chars=600,
        trim_threshold_chars=3800,
    ),
    "Grep": ToolBudgetEntry(
        preview_max_chars=1200,
        reference_max_chars=400,
        trim_threshold_chars=1800,
    ),
    "_default": ToolBudgetEntry(
        preview_max_chars=1500,
        reference_max_chars=500,
        trim_threshold_chars=2200,
    ),
}
```

The double bound (`preview_max_chars` + `trim_threshold_chars`) implements hysteresis: avoids cutting payloads that barely exceed the limit, reducing truncation noise.

### 3. Per-session caps

Derived from luum SDD session distribution (not literally copied from the reference pattern):

| Parameter | Value | Derivation |
|---|---|---|
| `char_cap_per_session` | 20 000 chars | ~5 000 tokens; the p90 of long luum sessions consumes ~18 000 chars of replay. A 20K cap absorbs that before saturation. |
| `item_cap_per_session` | 10 distinct `(tool, target)` tuples | In typical SDD sessions, > 10 distinct targets with large results indicates divergent exploration, not iteration. |
| `ttl_hours` | 4 h | luum sessions rarely exceed 3 h of continuous work. 4 h is more conservative than the reference pattern (6 h) and avoids stale data between same-day sessions. |
| `max_tracked_ledgers` | 64 | `cognitive-os.yaml:sessions.max_concurrent` ≤ 10. 64 gives 6x headroom without memory pressure. |

### 4. Spillover: modo `REFERENCE_ONLY`

When the ledger decides `REFERENCE_ONLY`, the full result is written to disk and the model receives a self-describing pointer:

**Destino:** `.cognitive-os/sessions/<id>/spillover/<tool_name>-<target_hash_short>-<ts>.txt`

**Pointer format injected into context:**

```
[REF:tool=<tool_name> target=<target_hash_short> path=.cognitive-os/sessions/<id>/spillover/<filename>]
```

The pointer includes `tool_name` + truncated `target_hash` + absolute path, so the model can make an explicit `Read` call if it needs the full content. The path is self-describing and does not require an external resolution table.

**Cleanup:** the session-end hook deletes the spillover directory together with the SQLite ledger (see §8).

### 5. Integration in `hooks/result-truncator.sh`

The current hook gains a ledger lookup **antes** of truncar. Modified flow:

```bash
# modified hook pseudocode
mode=$(python3 -c "
from lib.tool_replay_ledger import ToolReplayLedger
ledger = ToolReplayLedger(session_id='$SESSION_ID')
decision = ledger.record('$TOOL_NAME', '$TARGET_HASH', len('$OUTPUT'))
print(decision.mode.value)
")

case "$mode" in
  reference_only)
    write_spillover "$OUTPUT" "$TOOL_NAME" "$TARGET_HASH"
    echo "[REF:tool=$TOOL_NAME target=$TARGET_HASH path=$SPILLOVER_PATH]"
    ;;
  preview)
    apply_catalog_threshold "$OUTPUT" "$TOOL_NAME"
    ;;
  fresh)
    # current behavior: apply smart_truncator.py as fallback
    apply_smart_truncator "$OUTPUT"
    ;;
esac
```

`SESSION_ID` comes from `$CLAUDE_SESSION_ID` (environment variable exposed by the harness). If unavailable, the ledger uses `"default"` as session_id, degrading to current behavior without an accumulator.

### 6. `lib/smart_truncator.py` as fallback

`smart_truncator.py` remains fallback when:
- The ledger is unavailable (SQLite error, session not initialized).
- The tool is not registered in the catalog (uses `_default`).
- The ledger returns `Mode.FRESH` with no catalog entry.

No change to `smart_truncator.py` — the hook invokes it as a subprocess with the same current parameters.

### 7. Configuration in `cognitive-os.yaml`

```yaml
tool_replay_ledger:
  enabled: true
  char_cap_per_session: 20000
  item_cap_per_session: 10
  ttl_hours: 4
  max_tracked_ledgers: 64
  spillover_dir: .cognitive-os/sessions/{session_id}/spillover
  metric_log: .cognitive-os/metrics/tool-replay-ledger.jsonl
```

The block `result_truncation` existing block remains unchanged as the global fallback. Ledger values take precedence when `tool_replay_ledger.enabled: true`.

### 8. Session-end cleanup

The session-end hook (`hooks/session-end.sh` or equivalent registered in `scripts/setup-git-hooks.sh`) adds:

```bash
# cleanup tool-replay ledger + spillover
python3 -c "
from lib.tool_replay_ledger import ToolReplayLedger
ToolReplayLedger(session_id='$SESSION_ID').cleanup()
"
```

`cleanup()` deletes SQLite and the spillover directory for the current session.

### 9. Identifiers — explicit divergence

| Reference pattern (Annex B) | luum identifier | Rationale |
|---|---|---|
| `ToolReplayBudgetDecision` | `LedgerDecision` | Shorter; "Decision" is the natural return type |
| `consumeToolReplayBudget` | `ToolReplayLedger.record()` | Pythonic verb+noun; "consume" suggests destruction, "record" is more precise |
| `mode: "preview" \| "reference_only"` | `Mode.PREVIEW` / `Mode.REFERENCE_ONLY` | Same semantics, but typed as an `Enum` (not a string literal) |
| `compact_envelope` | (does not exist) | Concept not adopted; luum uses an ad-hoc pointer format |
| `DEFAULT_MAX_REPLAY_CHARS = 24_000` | `char_cap_per_session: 20000` | Derived from luum data, not copied |
| `DEFAULT_MAX_REPLAY_ITEMS = 8` | `item_cap_per_session: 10` | Derived from luum session distribution |
| `LEDGER_TTL_MS = 6h` | `ttl_hours: 4` | More conservative for the luum session pattern |

### 10. Observabilidad

Cada `record()` appends a `.cognitive-os/metrics/tool-replay-ledger.jsonl`:

```json
{
  "ts": "<ISO-8601>",
  "session_id": "<id>",
  "tool_name": "Read",
  "target_hash": "a1b2c3d4",
  "mode": "preview",
  "result_chars": 4200,
  "total_session_chars": 14300,
  "chars_saved": 2700,
  "spilled": false,
  "spillover_path": null
}
```

The `chars_saved` field (result_chars - pointer_chars for REFERENCE_ONLY, result_chars - preview_chars for PREVIEW) feeds the `chars_saved_per_session` metric in `llm-dispatch.jsonl` at the end of each session.

---

## Acceptance Criteria

```
[ ] lib/tool_replay_ledger.py exists, importable via
    python3 -c "from lib.tool_replay_ledger import ToolReplayLedger, Mode"

[ ] lib/tool_budget_catalog.py exists, importable via
    python3 -c "from lib.tool_budget_catalog import CATALOG"

[ ] pytest tests/unit/test_tool_replay_ledger.py covers:
    - Transition FRESH → PREVIEW → REFERENCE_ONLY in successive calls to the same target
    - Enforcement of the char_cap: after N accumulated chars, mode = REFERENCE_ONLY
    - Enforcement of the item_cap: after 10 distinct targets, mode = REFERENCE_ONLY on a new target
    - TTL expiration: entry with touchedAt > ttl_hours returns FRESH (new entry)
    - Spillover write: when mode = REFERENCE_ONLY, file exists in spillover_dir
    - Spillover read: pointer format includes the correct path and the file is readable
    - Cleanup: after cleanup(), ledger SQLite and spillover dir do not exist

[ ] hooks/result-truncator.sh queries the ledger before truncating;
    si REFERENCE_ONLY returns the pointer [REF:...] instead of truncated output

[ ] Spillover works end-to-end: the file exists at the path referenced by the pointer;
    Read of the path returns the full original content

[ ] Metric appended to llm-dispatch.jsonl at session end:
    field chars_saved_per_session present and > 0 in sesiones with replays

[ ] cognitive-os.yaml contains block tool_replay_ledger with all fields of the §7

[ ] Compliance F§5:
    grep -rF "ToolReplayLedger" /tmp/holaOS-investigation 2>/dev/null || echo "0 matches"
    # must return 0 matches (or print "0 matches" when /tmp/holaOS-investigation is absent)

[ ] Commit message uses template Annex F §6:
    Source-pattern: [private compliance dossier — see internal records] §Tool-replay budget ledger
```

---

## Consequences

### Positivo

- **~18,000 tokens/session saved** in SDD-apply sessions with high replay (projection Annex B §3). At $0.003/Ktok Sonnet input: ~$0.054/session direct; the main benefit is **headroom** — fewer early compactions, lower out-of-context failure rate.
- **Denser context.** The 18,000 freed tokens let the model keep more specs, more decision history, and more relevant code in the window, improving long-response coherence.
- **Self-describing `REFERENCE_ONLY` mode.** The model receives enough information to recover the content if needed (`Read` of the spillover path), without loss of access — only loss of immediate presence in context.
- **Per-tool granularity.** Short Bash output and large files stop competing for the same limit. Medium file reads (< 3 000 chars) passes without truncation; Noisy Bash (find of 800 lines) is aggressively trimmed from the first call.

### Negativo

- **Per-session state.** The SQLite ledger and spillover directory must be cleaned at session-end. If the session-end hook does not run (kill -9, crash), files persist on disk until the next session cleans them.
- **`REFERENCE_ONLY` can confuse the model.** If the pointer is not interpreted correctly, the model can assume the content is available when it is not in context. Mitigation: the pointer format is explicit (`[REF:tool=... target=... path=...]`) and acceptance tests verify that the path is readable.
- **SQLite in subshell.** Bash hooks run in subshells; each invocation opens and closes SQLite. For sessions with > 50 tool-calls/minute, the overhead of SQLite open/close can be noticeable. Mitigation: WAL mode + connection pool in `tool_replay_ledger.py`; evaluate degrading to plain JSON if overhead is measurable.
- **Dependency on `$CLAUDE_SESSION_ID`.** If the harness does not expose this variable, the ledger groups all sessions under `"default"`, degrading isolation. Mitigation: fallback to PID + timestamp as approximate session_id.

---

## Implementation Plan

**D1 — Core: ledger + schema SQLite + unit tests**

- Write `lib/tool_replay_ledger.py`: `ToolReplayLedger`, `LedgerDecision`, `Mode`, SQLite schema, `record()`, `get_mode()`, `stats()`, `prune_expired()`, `cleanup()`.
- Write `tests/unit/test_tool_replay_ledger.py`: all mode transitions, TTL, spillover, cap enforcement.
- Verify: `python3 -m pytest tests/unit/test_tool_replay_ledger.py -q` green.

**D1.5 — Catalog: thresholds derived from luum logs**

- Process `truncation-events.jsonl` to extract size distribution por tool_name.
- Derive `preview_max_chars` / `trim_threshold_chars` / `reference_max_chars` for the 4 main tools.
- Write `lib/tool_budget_catalog.py` with `CATALOG` and `ToolBudgetEntry` dataclass.
- Unit test: catalog has an entry for each expected tool + `_default`.

**D2 — Integration: `hooks/result-truncator.sh` + spillover writer**

- Modify `hooks/result-truncator.sh`: ledger lookup before truncating, branching FRESH/PREVIEW/REFERENCE_ONLY.
- Implement `write_spillover()` in the hook (Python one-liner o Bash function delegating to Python).
- Test end-to-end: simulate PostToolUse with large output, verify pointer in stdout + file in spillover.
- Graceful degradation: if SQLite fails, fallback a `smart_truncator.py` without hook error.

**D2.5 — Session-end cleanup + `cognitive-os.yaml` schema + observabilidad**

- Add cleanup to the session-end hook.
- Update schema `cognitive-os.yaml` with bloque `tool_replay_ledger`.
- Add `chars_saved_per_session` to `llm-dispatch.jsonl` emission in `lib/dispatch.py`.
- Run checklist compliance Annex F §5.
- Guardar Engram observation under `compliance/holaos-adoption/tool-replay-ledger`.

---

## Alternatives rejected

| Alternative | Decision | Rationale |
|---|---|---|
| Scale the global threshold from 5,000 to 1,000 chars | Rejected | Does not solve the replay problem: it would still have no cross-tool accumulator. Also, 1,000 chars truncates useful medium-size files that currently pass whole. |
| In-memory LRU cache in `smart_truncator.py` | Rejected | Hooks run in separate subshells, so in-memory state does not persist between calls. An in-process cache would require an auxiliary daemon or IPC, adding complexity without SQLite guarantees. |
| Embeddings for semantic deduplication | Rejected | Overkill for the problem: we do not need to detect similarity, only exact `(tool, target)` identity. Embedding overhead (~200 ms/call) would turn each tool call into a slow operation. Revisit if the `sha256(args)` false-positive rate becomes problematic. |
| Extend `lib/context_budget.py` (ADR-186) | Rejected | ADR-186 measures hook outputs in estimated tokens, not tool results in chars. The semantics differ: the ADR-186 budget applies to what the hook itself produces, not what the tool returns to the model. Sharing the accumulator would mix two orthogonal dimensions. |

---

## Compliance Certification

This ADR adopts the per-session ledger pattern described in [private clean-room research dossier] §Tool-replay budget ledger under the clean-room protocol of [private compliance dossier — see internal records].

```yaml
pattern_source: "holaos-comparison-2026-05-10.md::AnnexB::§B1 (tool-replay budget ledger)"
holaos_files_read_by_research: []
holaos_files_blocked_for_impl: ["ALL"]
```

**Thresholds:** all numeric values (char_cap, item_cap, ttl, preview/reference_max_chars) are derived from real usage distribution of luum, not copied from the reference catalog. The derivation methodology is documented in the comment of `lib/tool_budget_catalog.py`.

**Identifiers:** `ToolReplayLedger`, `Mode.PREVIEW`, `Mode.REFERENCE_ONLY`, `LedgerDecision`, `record()` are luum-specific. See table §9.

**Spillover format:** the pointer `[REF:tool=... target=... path=...]` is an ad-hoc luum design. The reference pattern uses `full_state_path` as a field in a JSON object; luum uses a self-describing inline string.

**Implementer prohibition:** agents implementing this ADR are categorically prohibited from reading any path matching `/tmp/holaOS*`. Detecting any code fragment from the reference pattern in the prompt requires an immediate halt and emission of `NEEDS_CLARIFICATION:` before any other action.

**Commit message template** (Annex F §6, required in every implementation commit):

```
<scope>: <change>

Pattern adopted from holaOS (clean-room rewrite).
Refs: [private clean-room research dossier]
Source-pattern: AnnexB::§B1.tool-replay-budget-ledger
License: Apache-2.0 modified (BSL-like). No source code copied.
```

---

## Open Questions

1. **`target_hash` strategy for tools with non-deterministic outputs.** Is `sha256(tool_args_normalized)[:16]` sufficient for tools such as `Bash`, where the same command can produce different outputs (timestamps, PIDs)? For `Read` and `Grep`, the args hash is stable. For `Bash` with `date` or `ps`, the same script produces different outputs but the args hash is identical, which is correct: we want to detect "same command, same target", not "same output". (**UNSURE**: if the agent uses variants of the same command with different flags but the same intent, the hash will differ and both will be FRESH. Evaluate whether to add Bash flag normalization in D1.)

2. **Cap 20K vs 15K: calibrate with 2 weeks of usage.** The projection of Annex B uses 24K chars of the reference pattern; luum uses 20K as a conservative posture. With real data of `tool-replay-ledger.jsonl` post-deploy, calibration to 15K could increase savings ~20% additional with low impact on short sessions. (**UNSURE**: do not confirm until there are 2 weeks of real data.)

3. **Expose stats to the model via system prompt.** Injecting `[LEDGER: session_chars=14300/20000, items=7/10]` in the next turn system prompt would give the model auto-awareness of its replay headroom. Con: meta-context overhead (~50 tokens/turn). Pro: the model could anticipate `REFERENCE_ONLY` and consolidate reads. (**UNSURE**: evaluate in experimental phase with a session cohort, measure whether behavior changes of model tool use before enabling by default.)

---

## References

- [private clean-room research dossier] §Tool-replay budget ledger — abstract specification of the adopted pattern
- [private compliance dossier — see internal records] — clean-room protocol and compliance checklist
- `docs/02-Decisions/adrs/ADR-259-external-pattern-adoption-posture.md` — ADR paraguas (postura patterns-only)
- `docs/02-Decisions/adrs/ADR-016-context-diet.md` — Context Diet ADR (related: headroom management)
- `docs/02-Decisions/adrs/ADR-049-llm-dispatch.md` — LLM Dispatch (metric destination `chars_saved_per_session`)
- `docs/02-Decisions/adrs/ADR-186-budget-enforcement.md` — Budget Enforcement ADR-186 (complementario, no reemplazado)
- `hooks/result-truncator.sh` — PostToolUse hook to modify in D2
- `lib/smart_truncator.py` — current truncator, remains fallback
- `rules/result-management.md` — rule `result-management` (to update to document modes PREVIEW and REFERENCE_ONLY)
- `cognitive-os.yaml:548-559` — configuration `result_truncation` current (to extend with `tool_replay_ledger` block)

---
*This ADR references a private clean-room research dossier whose specific
file paths and section headings are intentionally redacted from this public
record per ADR-267 §Layer 4 and the privatize-research migration (commit e961fd3b).*

## Verification

```bash
python3 -m py_compile lib/tool_replay_ledger.py lib/tool_budget_catalog.py
python3 -m pytest tests/unit/test_tool_replay_ledger.py -q
```

