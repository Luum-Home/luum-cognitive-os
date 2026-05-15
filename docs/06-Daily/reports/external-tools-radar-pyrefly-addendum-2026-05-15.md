---
report_type: external-tools-radar-addendum
date: 2026-05-15
tool: facebook/pyrefly
classification: TRIAL
adoption_kind: advisory-cli-gate
source_urls:
  - https://pyrefly.org/blog/pyrefly-agentic-loop/
  - https://github.com/facebook/pyrefly
related_files:
  - pyproject.toml
  - scripts/cos-pyrefly-pilot
  - .cognitive-os/reports/pyrefly/latest.json
---

# External Tools Radar Addendum — Pyrefly Python Type-Check Pilot

## Verdict

**TRIAL / advisory CLI gate.** Pyrefly is a strong fit for Cognitive OS because
it is a fast Python type checker and language server with an explicit upstream
agentic-loop pattern: run `pyrefly check` as a skill or Stop-hook-style quality
signal before an agent declares Python work complete.

Do **not** promote it to a mandatory Stop hook or default CI blocker yet. The
first local run produced a valuable but noisy baseline, so the correct next
step is measurement and triage, not enforcement.

## Why it belongs in the radar

| Axis | Assessment |
|---|---|
| Capability | Static Python type/API-shape checking for agent-produced code |
| License | MIT |
| Upstream status | Stable; GitHub release v1.0.0 was current during the 2026-05-15 evaluation |
| COS fit | Complements Ruff and pytest; fills the current Python type-check gap |
| Runtime footprint | CLI-only pilot via `uvx pyrefly` or optional `typecheck` extra |
| Default posture | Advisory report, no default dependency, no consumer-project projection |

## Implementation in this SO

The pilot is implemented as:

- `pyproject.toml` — `[tool.pyrefly]` pilot configuration and optional
  `typecheck` extra (`pyrefly>=1.0,<1.1`).
- `scripts/cos-pyrefly-pilot` — advisory runner that records receipts under
  `.cognitive-os/reports/pyrefly/` and only fails when explicitly run with
  `--enforce` or `COS_PYREFLY_ENFORCE=1`.
- `Makefile` — `make typecheck-pyrefly` invokes the pilot lane.

Default config intentionally disables `missing-import` because many COS Python
paths import optional integrations lazily. Strict import probing remains
available through:

```bash
COS_PYREFLY_STRICT_IMPORTS=1 make typecheck-pyrefly
# or
bash scripts/cos-pyrefly-pilot --strict-imports
```

## First local performance receipt

Command:

```bash
make typecheck-pyrefly
```

Observed result on 2026-05-15:

- Pyrefly version: `pyrefly 1.0.0`
- Mode: advisory
- Strict imports: disabled
- Runtime: about 2 seconds after the tool was cached by `uvx`
- Findings: 268 errors after suppressing missing-import noise
- Receipt: `.cognitive-os/reports/pyrefly/latest.json`

The findings are not random lint churn. They cluster around exactly the
classes useful to agents: unsafe `Any | None` JSON payloads, dataclass
reconstruction through imprecise dictionaries, callable-optional checks,
TypedDict value mismatches, and API-shape errors.

## Adoption boundary

Pyrefly is a **tooling primitive**, not a runtime dependency. It should remain:

1. Optional for local maintainers.
2. Advisory until the baseline is triaged.
3. Explicitly configured for COS optional-integration imports.
4. Promoted to blocking only after a ratchet target exists.

## Promotion criteria

Promote from TRIAL to ADOPT when:

1. The advisory baseline is categorized into suppressions vs real defects.
2. At least one high-signal cluster is fixed and covered by tests.
3. `make typecheck-pyrefly` is stable on a clean checkout without requiring
   heavyweight optional dependency lanes.
4. A ratchet exists for new errors, rather than requiring the whole historical
   baseline to go to zero at once.

## Rejected alternatives

| Alternative | Reason not selected now |
|---|---|
| Mandatory Stop hook immediately | Would block all Python work on a noisy historical baseline. |
| Keep only Ruff | Ruff catches syntax/lint issues but not the API-shape/type issues Pyrefly found. |
| Adopt Mypy/Pyright first | Still worth comparing later, but Pyrefly has a current upstream agentic-loop recommendation and very fast initial runtime. |

## Sources

- [Pyrefly agentic-loop guidance](https://pyrefly.org/blog/pyrefly-agentic-loop/)
- [facebook/pyrefly](https://github.com/facebook/pyrefly)
