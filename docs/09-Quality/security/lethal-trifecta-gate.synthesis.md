---
type: quality-synthesis
source: docs/09-Quality/security/lethal-trifecta-gate.md
provenance: "MVP reference for the lethal-trifecta gate, a deterministic pre-execution classifier that blocks actions combining private-data access, untrusted-content exposure, and outbound side effects in one step."
---

## What it is

A short reference doc for a deterministic, dependency-free gate that runs before tool execution and evaluates whether a single action combines three risk dimensions at once: access to private/sensitive data, exposure to untrusted content, and an outbound communication or side-effecting action.

## Key mechanics

- Decision table combines the three yes/no dimensions: all three "yes" -> block with exit code 2; any two "yes" with the third "no" -> warn; all other combinations -> allow.
- Runtime surfaces: classifier logic in `lib/lethal_trifecta.py`, hook wiring in `hooks/lethal-trifecta-gate.sh`, metrics written to `.cognitive-os/metrics/lethal-trifecta.jsonl`, unit tests in `tests/unit/test_lethal_trifecta.py`, contract tests in `tests/contracts/test_lethal_trifecta_gate.py`.
- Design constraints: no external dependency required on the hot path (keeps the gate fast and always-available); optional third-party scanners may enrich red-team lanes but are never required for the core block decision; every evaluated action writes a canonical MetricEvent row for auditability.
- Status is explicitly "MVP implemented" — described as deterministic and safe to run pre-execution, i.e. already wired in, not just planned.

## Relations & where used

- `hooks/lethal-trifecta-gate.sh` is registered as a security hook (referenced in `cognitive-os-attack-surface-inventory.md` as one of the representative security hooks).
- The underlying risk framing (private data + untrusted content + external communication combining into one dangerous action) is the same pattern discussed at length in `cognitive-os-agent-security-research-2026-05-05.md`, which credits this framing to external research and notes the gate exists but that the current local runtime can still combine all three risk factors if broader shell/network actions are approved outside the hook path.

## Status / caveats

Marked MVP — core logic is implemented and considered production-safe to run, but the doc does not claim full coverage; it explicitly notes optional scanners are supplementary, implying the deterministic classifier alone is the baseline defense, not a complete solution.
