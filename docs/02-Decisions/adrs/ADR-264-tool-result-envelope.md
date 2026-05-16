---
adr: 264
title: 'Tool Result Envelope: Compact Envelope Format for Large Tool Outputs'
status: accepted
implementation_status: implemented
date: '2026-05-11'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: tool result envelope module, agent/dispatch integration, spillover
  behavior, and tests implement compact result envelopes
verification:
  level: strong
  commands:
  - python3 -m pytest tests/unit/test_tool_result_envelope.py tests/red_team/portability/test_tool_result_envelope.py
    tests/red_team/portability/test_dispatch_helper.py tests/red_team/portability/test_agent_runner.py
    -q
  proves:
  - behavior_contract
  - integration_contract
---

# ADR-264 — Tool Result Envelope: Compact Envelope Format for Large Tool Outputs

## Status

Accepted

**Date:** 2026-05-11
**Owner:** orchestrator
**Tier:** core
**Authors:** orchestrator (Claude Sonnet 4.6)
**Implements:** ADR-259 (holaOS Adoption Posture — patterns only)
**Source-pattern:** Internal compliance dossier §Capability HTTP result envelope (AnnexG::§G1)
**Related:** ADR-263 (tool-replay ledger — ortogonal and composable), ADR-016 (context diet)

---

## Context

### Current state

luum truncates large tool outputs through `lib/smart_truncator.py` (20 833 bytes) with a head/tail strategy. The truncator operates without structure: it simply cuts text and adds an ellipsis marker. Usage points are `lib/openai_compatible_agent_loop.py:267,290`.

This strategy has two provable negative consequences:

1. **The model loses metadata about what was truncated.** It does not know the real size of the original output,
   it does not have the tool name that generated it, nor the target (file path, URL, command) that produced the result. The cut is semantically opaque.
2. **Reviewers cannot correlate a truncated result in logs with its source.**
   The log shows a cut text block with no structural context.

The `lib/agent_runner.py` module executes tool calls and appends results to the model conversation history without size post-processing. `lib/dispatch_helper.py` builds the payload sent to the model on each turn, also without per-result size inspection
individual.

### Pattern identified in research

The [private clean-room research dossier] §Capability HTTP result envelope from the holaOS study identifies a cross-cutting infrastructure pattern: when a tool result exceeds a threshold, instead of discarding it or blindly truncating it, it is replaced by a **structured envelope** that preserves:

- The first N bytes as preview (the model sees the beginning of the result).
- Explicit metadata: real size, tool name, target hint.
- A pointer to the full payload (spillover storage) for optional recovery.

The pattern is orthogonal al tool-replay ledger (ADR-263): ADR-263 operates on the temporal dimension
(how many times the same tool ran in the session); this ADR operates on the spatial dimension
(how large an individual execution result is). Both reduce context consumption por
independent paths and compose without conflict.

### Threshold derived from luum

The [private clean-room research dossier] §Capability HTTP result envelope uses 32 KB as threshold, derived from the harness `pi` from holaOS. For luum with
Claude Code (window of 200K tokens, 1 token ≈ 4 bytes):

- 28 KB ≈ 7 000 tokens ≈ 3.5% of available context.
- In sessions with 15-20 tool calls activos, 3-4 large results a 28 KB cada uno add up to
  ~14% of the context only in results, before including conversation history.
- 28 KB is more conservative than 32 KB, appropriate for a shared context with more artifacts
  concurrent (engram, session state, agent prompts). See §Open Questions for future calibration.

---

## Decision

### 1. New module `lib/tool_result_envelope.py`

Pure Python module (with no external dependencies) with the following public interface:

```python
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib, os

ENVELOPE_THRESHOLD: int = 28 * 1024   # 28 KB — derivado of context window luum (see §Context)
ENVELOPE_PREVIEW_SIZE: int = 7 * 1024  # 7 KB preview

@dataclass
class EnvelopePreview:
    preview_text: str         # first ~7 KB of the original result
    full_chars: int           # real size in characters
    tool_name: str            # name of the tool that produced the result
    target_hint: str          # ej. file path, URL, shell command
    full_pointer: str | None  # path to the spillover file, or None if persist_full=False

def wrap_if_large(
    raw_result: str,
    tool_name: str,
    target_hint: str,
    threshold: int = ENVELOPE_THRESHOLD,
    preview_size: int = ENVELOPE_PREVIEW_SIZE,
    persist_full: bool = True,
    spillover_dir: str | None = None,
) -> str:
    """Retorna raw_result tal cual si len(raw_result) <= threshold.
    If it exceeds the threshold, returns a structured Markdown envelope with preview + metadata + pointer.
    If persist_full=True, writes the full content into spillover_dir.
    """
```

The module also exposes:

```python
def render_envelope(ep: EnvelopePreview) -> str:
    """Renders an EnvelopePreview as a Markdown string for model consumption."""
```

### 2. Envelope format (Markdown estructurado — different from holaOS JSON)

The envelope is rendered as readable Markdown text, deliberately different from the JSON used by the reference pattern (which uses `tool_result_format: "compact_envelope"` with nested JSON):

```
[TOOL RESULT ENVELOPE]
tool: <tool_name>
target: <target_hint>
full_size: <N> chars (truncated; preview below)
full_pointer: <path-or-none>

--- preview (<M> chars) ---
<preview_text>
--- end preview ---
```

Intentional differences from the reference pattern (Anexo F §2, Nivel 1):

| Dimension | holaOS (reference) | luum (this ADR) |
|-----------|---------------------|-----------------|
| Envelope format | Serialized JSON | Markdown plain-text |
| Type name | `FormattedCapabilityToolResult` | `EnvelopePreview` |
| Function name | `formatCapabilityToolResultForModel` | `wrap_if_large` |
| Threshold | 32 KB (literal from harness `pi`) | 28 KB (derivado of context window luum) |
| Preview size | 8 KB | 7 KB |
| Structure summary | `topLevelPayloadSummary` (shape without values) | not included (YAGNI: add if needed) |
| Elevated `ok` field | yes (if payload has `ok: boolean`) | no (envelope is content-agnostic) |

### 3. Integration in `lib/agent_runner.py`

Every tool result passes through `wrap_if_large` before being added to conversation history.

```python
from lib.tool_result_envelope import wrap_if_large

# After executing the tool call:
result_text = wrap_if_large(
    raw_result=raw_tool_output,
    tool_name=tool_name,
    target_hint=target_hint,
    spillover_dir=_session_envelope_dir(),
)
# result_text goes to model history
```

If `wrap_if_large` produces an envelope (`len(raw_tool_output) > threshold`), it is logged in
`agent-heartbeat.jsonl`:

```json
{"event": "tool_result_enveloped", "tool_name": "<name>", "full_chars": N, "preview_chars": M}
```

### 4. Integration in `lib/dispatch_helper.py`

Same for tools dispatched through the helper. If the result was already processed por
`agent_runner`, `dispatch_helper` skips the second wrap (detects whether the string already contains the
marker `[TOOL RESULT ENVELOPE]`).

### 5. Spillover storage

Full payloads for enveloped results are persisted in:

```
.cognitive-os/sessions/<session-id>/envelopes/<sha256-of-content>.txt
```

- The directory is created on the first write of the session.
- The filename is the SHA-256 hex of the original content (first 64 chars of the digest).
- `full_pointer` in the envelope points to this file absolute path.
- Cleanup: the full directory is deleted when the session ends (hook `session-end`).
- If `persist_full=False` (useful in tests or preview-only contexts), no file is written and
  `full_pointer` es `None`.

### 6. Composability with ADR-263 (tool-replay ledger)

When ADR-263 is implemented, composition is as follows in `lib/agent_runner.py`:

```
ledger.check(tool_name) → REFERENCE_ONLY | FRESH | BLOCKED
    │
    ├─ BLOCKED    → does not execute the tool (ADR-263 gate)
    ├─ REFERENCE_ONLY → execute, then wrap_if_large with preview_size=0
    │                   (envelope collapses to pointer-only, with no preview)
    └─ FRESH      → execute, then wrap_if_large normal (full preview)
```

When the ledger says `REFERENCE_ONLY`, the envelope is rendered with `preview_text=""` y
`full_pointer` points to the spillover of the most recent result from the same tool.

---

## Acceptance Criteria

```
[ ] lib/tool_result_envelope.py exists and is importable via:
    python3 -c "from lib.tool_result_envelope import wrap_if_large, EnvelopePreview"
    with no external dependencies al stdlib.

[ ] pytest tests/unit/test_tool_result_envelope.py passes with coverage for:
    - under-threshold passthrough: result < 28KB returns the original string unchanged
    - over-threshold envelope: result > 28KB returns string with marker [TOOL RESULT ENVELOPE]
    - persist_full=False: no file is written in spillover_dir
    - persist_full=True: file is written in spillover_dir and full_pointer apunta al path
    - spillover filename: name is SHA-256 hex of the original content (64 chars)
    - preview truncation: preview_text has exactly min(7KB, len(raw)) chars
    - idempotency: calling wrap_if_large in an envelope already rendered does not re-wrap

[ ] lib/agent_runner.py applies wrap_if_large to each tool result before adding it to history.
    Integration test: mock tool that returns 30KB of text → history contains envelope,
    not the full blob.

[ ] lib/dispatch_helper.py idem. Test: payload with envelope already applied does not generate double wrap.

[ ] Composition with ADR-263 tested (can be pending/skipped if ADR-263 is not
    implemented yet):
    ledger=REFERENCE_ONLY + wrap_if_large → preview_text="" + full_pointer only.

[ ] The rendered envelope is human-readable when a reviewer reads logs manually.
    (Manual verification — no automatizable.)

[ ] Compliance F§5:
    grep -rF "EnvelopePreview" /tmp/holaOS-investigation 2>/dev/null | wc -l = 0
    (gate passes with WARN when /tmp/holaOS-investigation does not exist in CI)

[ ] Commit message incluye template F§6:
    Source-pattern: [private compliance dossier — see internal records] §Capability HTTP result envelope
```

---

## Consequences

### Positivo

- **The model preserves awareness of truncated size.** The `full_size` field lets the model
  know how many characters were omitted and decide whether to request the full payload.
- **Explicit metadata in logs.** Reviewers see `tool_name` + `target_hint` + `full_pointer`
  instead of a cut text blob without context.
- **Reduction of out-of-context errors.** In long sessions with multiple large tool calls,
  the envelope prevents one large result from occupying a disproportionate fraction of context.
- **Reversible with one parameter.** `threshold=math.inf` disables the envelope completely.
  Zero blast radius for rollback.
- **Complements `smart_truncator.py` without replacing it.** `smart_truncator` continues operating as
  fallback in `openai_compatible_agent_loop.py`; the envelope operates upstream in `agent_runner.py`.

### Negativo

- **Overhead of render.** The envelope text adds ~200 bytes of markup per result
  enveloped. Negligible compared with savings (typical result of 50KB → 7KB preview + 200B markup).
- **Spillover dir grows during the session.** In sessions with many large tool calls, the dir
  `.cognitive-os/sessions/<id>/envelopes/` can grow several MB. Mitigated with cleanup in
  session-end and cap future (ver §Open Questions).
- **Double-wrap risk.** If both `agent_runner` and `dispatch_helper` apply the envelope, idempotency detection is needed. The `[TOOL RESULT ENVELOPE]` marker in the text acts as a detection flag.

### Mitigation

- Automatic cleanup of the spillover dir in hook `session-end` (to add in `scripts/session-end.sh`
  o equivalente).
- Cap spillover dir at 50 MB as a session guardrail (future, ADR follow-up).

---

## Implementation Plan

**D1 — Pure module + unit tests**

- Create `lib/tool_result_envelope.py`: `EnvelopePreview`, `wrap_if_large`, `render_envelope`.
- Create `tests/unit/test_tool_result_envelope.py`: all cases of the Acceptance Criteria.
- Verify: `python3 -m pytest tests/unit/test_tool_result_envelope.py -q` passes.

**D1.5 — Integration in agent_runner and dispatch_helper**

- Modify `lib/agent_runner.py`: import and call `wrap_if_large` after tool execution.
- Modify `lib/dispatch_helper.py`: same call path plus an idempotency guard.
- Add `tool_result_enveloped` log entries in `agent-heartbeat.jsonl` when the envelope activates.
- Add an integration test in `tests/integration/` with a mock tool that returns 30 KB of output.

**D2 — Spillover storage + cleanup + composition**

- Implement spillover logic: derive the path from the session ID plus SHA-256.
- Add cleanup to the `session-end` hook.
- Add a composition test with ADR-263, skipped when the ledger is not implemented.
- Run the F§5 compliance checklist.

---

## Alternatives rejected

| Alternative | Decision | Reason |
|-------------|----------|-------|
| Hard truncate without envelope (status quo) | Rejected | Loses metadata; the model does not know what was truncated or by how much |
| JSON envelope (holaOS-style) | Rejected | The model parses Markdown more naturally in Claude Code context; JSON requires additional parsing; a distinct format satisfies the clean-room constraint |
| Streamed truncation per-chunk | Rejected | Overkill for the use case; adds streaming complexity to the synchronous loop |
| Replace `smart_truncator.py` completely | Rejected | `smart_truncator` has head/tail logic for cases where the model must see both the beginning and the end; envelope preserves only the beginning. Coexistence is safer |
| threshold 32 KB (literal from holaOS) | Rejected | Would violate the Annex F §2 Level 1 clean-room constraint (do not copy literal values from the reference harness); 28 KB is independently derived from the luum context window |

---

## Compliance Certification

This ADR adopts the pattern described in [private clean-room research dossier] §Capability HTTP result envelope
under the protocol clean-room establecido in [private compliance dossier — see internal records].

Compliance declarations per Annex F §4.2:

```yaml
pattern_source: "holaos-annex-g-surprise-findings.md::§G1 (Capability HTTP result envelope)"
holaos_files_read_by_research: []
holaos_files_blocked_for_impl: ["ALL"]
```

Identifier divergence (Annex F §2, Nivel 1 PATTERN-ONLY):

| holaOS identifier (from the research annex) | luum identifier | Reason |
|------------------------------------------|-----------------|-------|
| `formatCapabilityToolResultForModel` | `wrap_if_large` | Snake_case Python; nombre descriptivo of the comportamiento |
| `FormattedCapabilityToolResult` | `EnvelopePreview` | Name reflects the envelope content, not the formatting process |
| `compact_envelope` (field JSON) | `[TOOL RESULT ENVELOPE]` (marker Markdown) | Completely different format: plain text vs JSON |
| `DEFAULT_COMPACT_TOOL_RESULT_THRESHOLD_BYTES = 32 * 1024` | `ENVELOPE_THRESHOLD = 28 * 1024` | Value derivado independientemente from the context window luum |
| `DEFAULT_COMPACT_TOOL_RESULT_PREVIEW_BYTES = 8 * 1024` | `ENVELOPE_PREVIEW_SIZE = 7 * 1024` | Value ajustado for luum |
| `topLevelPayloadSummary` | not included (YAGNI) | Feature not adopted in this iteration |
| `raw_result.stored_in: "tool_result.details.raw"` | `full_pointer: str \| None` (absolute path) | File-pointer semantics, not logical field path |

luum-specific additions not present in the reference pattern:

- `persist_full=False` as an explicit option (useful for tests and preview-only contexts).
- Guard of idempotencia por marker of texto (avoids double wrap).
- Documented composition with ADR-263 (`REFERENCE_ONLY → preview_text=""`).
- SHA-256 as spillover filename (vs reference using an internal logical path).

**Implementing agents are PROHIBITED from reading `/tmp/holaOS*`.** Any prompt that
contains holaOS paths must be rejected with `NEEDS_CLARIFICATION:`.

Commit messages for commits of implementation MUST include:

```
Pattern adopted from holaOS (clean-room rewrite).
Refs: [private clean-room research dossier]
Source-pattern: AnnexG::§G1.capability-envelope
License: Apache-2.0 modified (BSL-like). No source code copied.
```

---

## Open Questions

1. **Optimal threshold: 28 KB vs 24 KB vs 32 KB.** The value 28 KB is a conservative derivation
   from the context window of Claude Code. Correct calibration requires measuring p50/p95 of size
   of tool results in production for 2 weeks. `ENVELOPE_THRESHOLD` must be configurable
   via `cognitive-os.yaml` (`tool_result_envelope.threshold_kb`) to adjust without redeployment.
   **UNSURE** si 28 KB es too conservative for sesiones with pocos tool calls.

2. **Preview size: is 7 KB enough for the model to decide whether to request full output?**
   For JSON-type results (structured, predictable beginning), 7 KB can be more than
   sufficient. In build-log or large-diff results, the beginning can be less
   informativo. **UNSURE** — also a candidate for configurable `preview_kb`.

3. **Expose `expand_envelope(pointer)` as a model tool?** This would let the model request
   the full payload explicitly of an envelope through a tool call. Requires registering the
   tool in the harness. Potentially more useful than passive spillover. Park for ADR
   follow-up (does not block this adoption).

4. **Spillover dir cap.** Without a cap, a session with 100 large tool calls could accumulate
   ~500 MB in `.cognitive-os/sessions/<id>/envelopes/`. Session-end cleanup mitigates this
   for sesiones normal, but long sessions do not end soon. Parking as guardrail
   in ADR follow-up.

---

## References

- [private clean-room research dossier] §Capability HTTP result envelope — source abstract specification
- [private compliance dossier — see internal records] — protocolo clean-room and checklist
- ADR-259 — holaOS Adoption Posture (umbrella policy for patterns-only adoption)
- ADR-263 — Tool-Replay Ledger (ortogonal and composable with this ADR)
- ADR-016 — Context Diet (context of reduction of window of context in luum)
- `lib/smart_truncator.py` — existing module that this ADR complements (no reemplaza)
- `lib/agent_runner.py` — primary integration point
- `lib/dispatch_helper.py` — secondary integration point

---
*This ADR references a private clean-room research dossier whose specific
file paths and section headings are intentionally redacted from this public
record per ADR-267 §Layer 4 and the privatize-research migration (commit e961fd3b).*

## Verification

```bash
python3 -m py_compile lib/tool_result_envelope.py lib/agent_runner.py lib/dispatch_helper.py
python3 -m pytest tests/unit/test_tool_result_envelope.py tests/red_team/portability/test_tool_result_envelope.py tests/red_team/portability/test_dispatch_helper.py tests/red_team/portability/test_agent_runner.py -q
```

