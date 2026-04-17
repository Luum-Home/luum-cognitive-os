# ADR-026: R2 and R3 Consolidation — Design Review

**Date:** 2026-04-17
**Status:** CLOSED (R3 portion) / Partially accepted

> **R3 audit item — CLOSED 2026-04-17**: Investigated in ADR-026; modules have
> zero overlapping callers and different contracts — see ADR-026a for evidence.
> Module-level docstrings added to `lib/safe_engram.py` and `lib/engram_client.py`
> per D3.1. Bug fix for `cos_mcp.py` returncode=127 applied per D3.2.
> Reference: `docs/architecture/adrs/026a-decisions.md`.
**Related:** commit `540998a` (R3 characterization, PR #7), `d5f6f12` (R2 characterization, PR #8), `6ed3e63` (R1 characterization, PR #9)

## Context

The Capa-3 functional audit identified three overlapping "reader" refactors, labeled R1/R2/R3:

- **R1** — env-var → `project_dir` resolution (4 patterns across 13 sites). Characterized by PR #9 (`6ed3e63`). A separate `lib/paths.py::project_root` consolidation is pending and out of scope for this ADR.
- **R2** — `cognitive-os.yaml` readers (3 divergent sites). Characterized by PR #8 (`d5f6f12`). This ADR proposes options.
- **R3** — `lib/safe_engram.py` ↔ `lib/engram_client.py` (two overlapping modules that look delegatable but aren't). Characterized by PR #7 (`540998a`). This ADR proposes options.

Each refactor was **deliberately deferred**: the PR author added characterization tests that lock in current behavior (including the divergences) and explicitly left reconciliation to a human decision. This ADR is that decision document.

The authors' explicit warnings:
- R2 commit message (`d5f6f12`): *"Divergences locked in (NOT fixed — to be reconciled by R2 design review)"*.
- R3 commit message (`540998a`): *"The two functions are NOT behaviorally equivalent and a naive delegation would silently break cos_mcp's user-facing message"*.

---

## R2 findings — `cognitive-os.yaml` readers

### Scope (Q2.3)

`grep -rn "cognitive-os.yaml"` finds **89 Python files** and **42 shell files** referencing the path. Only a small subset actually *parses* it. The rest either (a) write to the path, (b) print a diagnostic, or (c) pass it as a default argument.

Python parsers fall into two groups:
- **Characterized by PR #8** (the three R2 sites): `lib/dispatch_helper.py`, `lib/agent_health_monitor.py`, `hooks/_lib/dispatch_gate_check.py`.
- **Adjacent parsers not covered by PR #8**: `lib/queue_drainer.py:62` (regex, same pattern as dispatch_helper), `lib/singularity.py:532` (reads phase), `lib/consequence_engine.py:146` (default path arg), `lib/dispatch_model_advisor.py:93` (find-path helper), `lib/prompt_builder.py:64` (find-path helper), `lib/context_diet.py` (loads via `ContextDiet.from_yaml`), plus various `packages/*/lib/` modules.

Shell scripts reach into the YAML via `grep`/`awk`. Two examples:
- `scripts/cos-update.sh:348-354` — *"Read profile from cognitive-os.yaml; default to 'standard' if absent. Use grep+awk for bash 3.2 compatibility (no yq/python dependency here)."*
- `bin/cognitive-os.sh:808-811` — uses `sed` to update the `level:` key in place.

**Implication**: any R2 consolidation that changes the YAML *schema interpretation* (e.g. requires nesting under `resources.compute.*`) risks desynchronising the bash readers that key off loose `grep` patterns.

### The 5 locked divergences (from `tests/unit/test_cos_yaml_readers.py`)

Each row quotes the test that pins the behavior.

| # | Divergence | Site A behavior | Site B behavior | Locked by test |
|---|---|---|---|---|
| 1 | **Search-path order** | `dispatch_helper._find_config_path()`: cwd `cognitive-os.yaml` → cwd `.cognitive-os/cognitive-os.yaml`, with `CLAUDE_PROJECT_DIR` *prepended* at index 0 (lines 41-56). | `agent_health_monitor._read_timeout_seconds()`: `PROJECT_DIR/cognitive-os.yaml` *first*, then explicit `config_path` arg, then cwd `cognitive-os.yaml` (lines 93-117). | `TestFindConfigPath::test_claude_project_dir_takes_precedence_over_cwd` (lines 116-127), `TestReadTimeoutSeconds::test_project_dir_yaml_takes_precedence_over_explicit_arg` (lines 305-316). |
| 2 | **Env-var precedence** | Sites 1+2 both honor `CLAUDE_PROJECT_DIR` **then** `COGNITIVE_OS_PROJECT_DIR`. | Site 3 (`dispatch_gate_check.py:22`) reads **only** `CLAUDE_PROJECT_DIR`. | `test_cognitive_os_project_dir_used_when_claude_unset` (lines 129-137 for site 1; lines 318-326 for site 2). Site 3 has no equivalent — it's a constant at import time. |
| 3 | **Key precedence / nesting** | Regex sites (1a, 1b, 2) grab the **first line** matching `^\s*KEY:\s*(\d+)` anywhere in the file, ignoring YAML nesting. Top-level *and* deeply nested keys are equally valid. | `safe_load` site (3) requires the exact nested path `resources.compute.max_parallel_agents`. A top-level `max_parallel_agents: 17` is **silently ignored**. | `test_nested_under_resources_compute_still_matches_first` (lines 204-215), `test_top_level_key_is_ignored` (lines 422-427). |
| 4 | **Empty file handling** | Regex sites return their hard-coded default (5 or 300). | `safe_load` returns `None`; the consumer's `or {}` coercion falls through to `.get(..., 5)`. No error is logged. | `test_empty_file_returns_default` (lines 239-241 and 376-381), `test_empty_file_returns_default_no_error` (lines 480-486). |
| 5 | **Error surface** | Regex sites swallow `OSError` silently and return default. | `safe_load` site wraps parse errors in `result["error"] += "config:<e>;"` — visible to the dispatch-gate consumer. | `test_malformed_yaml_records_error_and_keeps_default` (lines 518-527). |

### Why the divergences exist (git forensics)

No single commit introduced them. Git log shows the three sites grew independently:
- `dispatch_helper.py` — written for the dispatch-gate hook with an explicit "no heavy imports at module level" constraint (lines 5-10). PyYAML was rejected because it would double cold-start latency on every `PreToolUse`.
- `agent_health_monitor.py` — written for the standalone health-monitor tool that can afford config lookups but still opts for regex "without PyYAML" (line 94 docstring).
- `dispatch_gate_check.py` — a newer "single-pass dispatch gate check" (docstring: "consolidates all python3 invocations from dispatch-gate.sh"). Imports `yaml` because it already pays the cold-start cost for other reasons (imports `ConsequenceEngine`, `CircuitBreaker`, `dispatch_model_advisor`).

**None of the divergences is objectively correct.** They encode three legitimate operational constraints:

- **Site 1 (dispatch_helper)**: ultra-cheap, called on every PreToolUse. Regex wins on cold-start.
- **Site 2 (agent_health_monitor)**: medium-cost, called from a scheduled drain loop. Regex is chosen for consistency with site 1, not for perf.
- **Site 3 (dispatch_gate_check)**: already-heavy, needs schema-aware lookup because nested keys matter for other gates. `safe_load` is appropriate.

The env-var divergence in row 2 is likely a miss, not a choice. Sites 1/2 were updated to honor both env names during the ADR-007 rebrand; site 3 was not.

### Specific questions

**Q2.1 — Canonical reader?**
None. Site 3 (`dispatch_gate_check.py`) has the widest feature surface (reads nested structure, logs errors) but is the *most expensive* — wrong choice for a PreToolUse-hot reader. Site 1 (`dispatch_helper.py`) has the most recent touches (see `dispatch-gate.sh` consolidation). Site 2 is the oldest unchanged code path.

**Q2.2 — Validation?**
None of the three does schema validation. Site 3 is closest — it would surface a YAML syntax error via `result["error"]`, but it does not validate *types* (e.g. `max_parallel_agents: "five"` would fail at `int()` silently in site 1 and return default).

**Q2.3 — Bash readers?**
Yes — `scripts/cos-update.sh`, `bin/cognitive-os.sh`, `scripts/apply-efficiency-profile.sh` read the YAML via `grep`/`awk`/`sed`. These CANNOT be migrated to call Python without adding a `python3` dependency to the install path (currently bash-only in the cold-start install phase). A sibling bash reader is required; any R2 design must keep the schema *grep-friendly* (top-level keys) or provide an alternative bash API.

**Q2.4 — Test churn?**
`tests/unit/test_cos_yaml_readers.py` has **43 tests** pinning current behavior. `tests/unit/test_dispatch_helper.py`, `tests/unit/test_agent_health_monitor.py`, `tests/unit/test_agent_timeout.py`, `tests/unit/test_dispatch_gate.py` exercise the readers transitively. Any option that changes semantics will force rewrites of 10-20 tests. Option A needs the most rewrites; Options B and C need the fewest.

### R2 options

#### Option A — Single unified `lib/config_loader.py`

All three sites delegate to one `load_config(path: str | None = None) -> dict` that returns the full parsed YAML (via `safe_load`). Each reader pulls its value from the returned dict via a nested-path lookup.

- **Effort**: High. ~6 files touched (3 current sites + queue_drainer + singularity + prompt_builder). ~15-20 tests to rewrite.
- **Risk**: High — silent behavior change. The 5 divergences collapse; code that relied on regex-first-match or regex-ignore-nesting breaks quietly. Empty-file handling becomes `{}` everywhere, which drops the error-surfacing at site 3.
- **Bash impact**: Breaks bash readers that grep for top-level keys if the schema migration puts values under `resources.compute.*`. Requires coordinated bash rewrite.
- **Verdict**: Not recommended. The divergences are legitimate, not accidental.

#### Option B — `lib/config_loader.py` with explicit reader variants (**recommended**)

One module, three public functions:

```python
# cheap, regex, PreToolUse-safe — no PyYAML import
def read_top_level_int(path, key, default): ...

# full schema, PyYAML, suitable for heavy gates
def load_structured(path) -> dict: ...

# legacy-compat shim for external scripts
def find_config_path(project_dir_env_order: tuple[str, ...] = ("CLAUDE_PROJECT_DIR", "COGNITIVE_OS_PROJECT_DIR")) -> Optional[str]: ...
```

Each current site migrates to the appropriate variant. Divergences become *documented* (in docstrings) rather than *accidental* (scattered across files).

- **Effort**: Medium. ~6 files touched, but each change is mechanical (import + call-site swap). Characterization tests stay green with minor import changes.
- **Risk**: Low. No semantic change; the 5 divergences are preserved, just centralised. One env-var precedence fix for site 3 (align with sites 1+2) can be a follow-up with its own test.
- **Bash impact**: None. Bash readers keep grep-ing top-level keys because `read_top_level_int` still accepts them.
- **Verdict**: Strong recommendation. Pays the consolidation cost without losing the legitimate variation.

#### Option C — Split by concern

Two modules:
- `lib/config_fast.py` — regex-based, stdlib-only, for hot paths (sites 1, 2, queue_drainer).
- `lib/config_schema.py` — PyYAML + type validation (via `pydantic` or `attrs`), for heavy gates and future CLI commands (`cognitive-os validate`).

- **Effort**: High. Requires designing a schema first (none exists today). ~10 files touched.
- **Risk**: Medium. Schema validation may reject today's configs that the regex readers tolerate. Useful for future work but not for R2's narrow scope.
- **Bash impact**: Same as Option B.
- **Verdict**: Good long-term shape, but premature. Option B first; promote `config_schema.py` later when a schema actually exists.

**Author preference: B > C > A.**

---

## R3 findings — `safe_engram` ↔ `engram_client`

### Files

- `lib/safe_engram.py` — **171 lines**, real file (not a symlink), committed 2025-11-17 (scanner integration). Public API: `safe_save()`, `scan_only_check()`, `SafeEngramResult` dataclass.
- `lib/engram_client.py` — **169 lines**, real file. Public API: `search_observations()`, `get_observation()`, `save_observation()`. Docstring: *"Primary consumers: hooks/inject-phase-context.sh, hooks/subagent-context-injector.sh"*.

### Callers (Q3.1, Q3.2)

`grep -rn "from lib\.safe_engram\|from lib\.engram_client\|import safe_engram\|import engram_client"` found:

**safe_engram callers (3 production + tests):**
- `mcp-server/cos_mcp.py:204` — `safe_save` in `_engram_save()`.
- `hooks/user-prompt-capture.sh:41` — inline `scan_only_check` (bash-embedded Python).
- `lib/anchored_summarizer.py:274` — string reference (not an import — embedded in a prompt template).

**engram_client callers (2 production + 1 indirect):**
- `hooks/inject-phase-context.sh:163` — `search_observations`.
- `hooks/subagent-context-injector.sh:77` — `search_observations`.
- `lib/memory.py:19` — imports all three `engram_client` functions; `mem_search`/`mem_get`/`mem_save` delegate to them.

**Callers using both:** None. The two modules are consumed by disjoint caller sets. This is the key finding: **they are NOT overlapping implementations — they are two different modules with different contracts.**

### Contract diff

| Concern | `safe_engram.safe_save` | `engram_client.save_observation` | Equivalent? |
|---|---|---|---|
| **Auth / binary** | `ENGRAM_BIN` env var OR `engram_bin=` kwarg (per-call override) — lines 133, 117 | `ENGRAM_BIN` env var only, resolved at module load — line 20 | NO (safe_engram allows per-call override; contract test `TestEngramBinOverride::test_explicit_engram_bin_wins_over_env` locks this) |
| **Pre-save scanning** | ALWAYS scans `title + content` via `MemoryScanner`; returns `blocked=True` without invoking CLI when a threat is found (lines 127-130) | No scanning. Docstring explicitly directs callers to `safe_engram` for untrusted input (lines 129-131) | NO (fundamental purpose of safe_engram) |
| **CLI command shape** | `engram save --title ... --content ... --type ...` (NO `--json`) — lines 134-144 | `engram save --json --title ... --content ...` — lines 133-138 | NO (contract test `TestCliCommandShape::test_cli_does_not_include_json_flag` locks this) |
| **Error surface** | `SafeEngramResult` dataclass with `blocked`, `reasons`, `engram_output`, `returncode` (lines 52-66). Swallows `FileNotFoundError` → `returncode=127`; `TimeoutExpired` → `returncode=-1`; CLI failure returns the non-zero code verbatim. | Returns `dict | None`. `None` on any error (FileNotFound / timeout / non-zero / JSON decode / generic) — lines 73-81. No error classification. | NO (engram_client collapses 5 error modes to `None`; safe_engram surfaces each) |
| **User-facing output** | `engram_output` is the stdout of engram CLI verbatim (human text) — line 156 | `save_observation` returns parsed JSON dict or None | NO (fundamentally different return types) |
| **Retry / timeout** | `timeout=10s` default, per-call kwarg — line 106 | `timeout=10s` default, per-call kwarg — line 125 | YES |
| **Return type** | `SafeEngramResult` (always; never None) | `dict | None` | NO |

### The cos_mcp message that naive delegation would break (Q3.4)

Yes, `cos_mcp` is in-repo at `mcp-server/cos_mcp.py`. The consumer code at lines 217-219 (quoted from file):

```python
if result.returncode is not None and result.returncode not in (0, 127):
    return json.dumps({"error": "Engram CLI not available. Install engram."})
return result.engram_output or "Saved successfully."
```

And line 213-216 for the blocked path:

```python
if result.blocked:
    return json.dumps({
        "error": "Content blocked by memory scanner.",
        "reasons": result.reasons,
    })
```

MCP clients receive **three distinct user-facing strings**:
1. On success: `result.engram_output` verbatim (e.g. `"Saved with id=42."` — human readable, not JSON).
2. On scanner block: a JSON error object with `reasons`.
3. On real CLI failure: a JSON error object with a fixed message.

If `safe_save` were delegated to `save_observation`:
- The `--json` flag would be added → `engram_output` would be a JSON dict string, not `"Saved with id=42."`. MCP clients would display raw JSON to the user.
- The returncode dichotomy (0 vs 127 vs other) would collapse to `dict | None` → the three branches in `cos_mcp` merge into two, losing the "binary missing is graceful" semantic (locked by `TestConsumerClassificationDichotomy::test_returncode_127_is_passthrough_not_real_error`).

There's also a **latent bug** locked (not fixed) by PR #7: `cos_mcp.py:218` treats `returncode=127` (binary missing) as success, returning `"engram binary not found; save skipped."` as if it were a save confirmation. This is a UX gap flagged in the commit message; it should be fixed *separately* from R3.

### Specific questions

**Q3.1 — Blast radius?** 3 safe_engram callers, 3 engram_client callers. Small surfaces, zero overlap.
**Q3.2 — Callers using both?** None. Confirms the modules have separate purposes.
**Q3.3 — Which contract tests would stay green under Option A?** Only the `blocked=True` scanner path (tests in `TestScanBlockContract`). All CLI-shape tests (`TestCliCommandShape`), returncode classification tests (`TestConsumerClassificationDichotomy`), success-output string tests (`TestSuccessPathContract`), and binary-missing tests (`TestBinaryMissingContract`) would fail. Roughly 25 of 33 contract tests are *contract* (lock consumer behavior); 8 are *implementation* (test the dataclass mechanics).
**Q3.4 — cos_mcp location?** In-repo. Quoted above.

### R3 options

#### Option A — `safe_engram` becomes a thin wrapper delegating to `engram_client`

Replace the subprocess call in `safe_save` with `save_observation()`; preserve the scanner gate. Convert the returned dict back into `SafeEngramResult`.

- **Effort**: Low code churn (~30 lines in `safe_engram.py`).
- **Risk**: **BLOCKING**. Requires either (a) removing `--json` from `engram_client.save_observation` (which breaks its own consumers in `lib/memory.py` that expect a dict) or (b) synthesizing a human-readable string from the dict on the safe_engram side, replicating CLI output. (b) is fragile — the CLI's output format is not versioned.
- **Migration**: Would need to preserve the `returncode` classification artificially (safe_engram catches FileNotFoundError locally before delegating, sets returncode=127 manually, etc.). Most of the existing logic stays; only the subprocess call moves.
- **Verdict**: Not recommended. The characterization tests were specifically added to prevent this.

#### Option B — Merge: `engram_client` absorbs `safe_engram`

`engram_client.save_observation` gains an optional `scan_content: bool = False` parameter and returns `SafeEngramResult` when scanning is on (or raises differently).

- **Effort**: Medium. Touches the two hook callers + `lib/memory.py`. ~6 files.
- **Risk**: High. `engram_client`'s current `dict | None` contract is depended on by `lib/memory.py::mem_save`. Changing the return type would cascade through memory_first consumers.
- **Migration**: Gradual deprecation of the separate module possible over 2 releases.
- **Verdict**: Not recommended. `engram_client` is the "machine-readable" path and `safe_engram` is the "user-facing" path. Merging them violates that separation.

#### Option C — Keep both, formalise the distinction via docstrings + ADR (**recommended**)

Add explicit cross-references in each module docstring:

- `safe_engram.py` — *"Use this for user-facing writes (returns `SafeEngramResult` with human-readable `engram_output`). For programmatic writes, use `engram_client.save_observation`."*
- `engram_client.py` — strengthen the existing line 129 note ("Prefer `lib.safe_engram.safe_save` when content may be untrusted") and add: *"Returns `dict | None` with parsed JSON. For user-facing strings and scanner gating, use `safe_engram.safe_save`."*

Fix the latent bug in `cos_mcp.py:217-219` (returncode=127 is classified as success) as a *separate commit* with its own test.

- **Effort**: Tiny (~10 lines of docstring updates + 1 bug fix + 1 test).
- **Risk**: Negligible. No behavior change; tests stay green.
- **Migration**: None.
- **Verdict**: Strong recommendation. The modules are NOT duplicates — they have different callers, different contracts, and different purposes. Documenting that is the correct outcome.

**Author preference: C > A > B.** (B is ranked last because it forces coupling on unrelated consumers.)

---

## Decision needed from human

To unblock R2:

- **D2.1** — Adopt Option B (multi-variant `lib/config_loader.py`)? `yes / no`
- **D2.2** — If yes: should the env-var precedence divergence (row 2) be reconciled in the same PR (site 3 gains `COGNITIVE_OS_PROJECT_DIR` support)? `yes / no`
- **D2.3** — Should R2 also absorb the adjacent parsers (`queue_drainer.py:62`, `prompt_builder.py:64`, `dispatch_model_advisor.py:93`), or scope-limit to the three characterized sites? `absorb / scope-limit`
- **D2.4** — Defer schema validation (Option C components) to a future ADR? `yes / no`

To unblock R3:

- **D3.1** — Adopt Option C (keep both modules, document the boundary)? `yes / no`
- **D3.2** — Fix the `cos_mcp.py:217-219` returncode=127 misclassification as part of this work? `yes / no`
- **D3.3** — If yes to C: retire the "R3 consolidation" label in the audit backlog (classify it as *investigated, no consolidation needed*)? `yes / no`

---

## Consequences

### If D2 adopts Option B
- Single import site for YAML reads. New readers in the future MUST choose one of the three variants — enforced by lint (no direct `open("cognitive-os.yaml")` except in `config_loader.py`).
- Bash readers unchanged. The schema remains grep-friendly.
- 43 characterization tests stay green (possibly with import path updates).
- Small perf win: site 3 can keep `safe_load` but import it lazily through the module, avoiding duplicate imports across related hooks.
- Follow-up work: write schema validation (`config_schema.py`) as Option C later when there's a real schema to enforce.

### If D3 adopts Option C
- No code risk. 113 engram-related tests stay green.
- Module boundary becomes explicit. Future callers know which API to pick without reading both source files.
- The audit backlog entry "R3 consolidation" closes with *"investigated, determined to be legitimate separation"* — a valid audit outcome.
- Latent bug (if D3.2 is yes): one additional commit fixes `cos_mcp.py:217-219` + adds a regression test. Keeps the blast radius minimal.

### Unresolved (not decided by this ADR)

- **U1** — Whether `lib/memory.py`'s `mem_save` should route through `safe_engram` by default for untrusted content. Currently it uses `engram_client.save_observation` unconditionally. This is a separate SDD change, not part of R3.
- **U2** — Whether R1 (`lib/paths.py::project_root`) should land before R2 so that `config_loader.py` can use the unified `project_root()` helper. Sequencing decision; doesn't affect the options themselves.
- **U3** — Bash consolidation. `scripts/cos-update.sh`, `bin/cognitive-os.sh` etc. use grep/awk/sed on the YAML. An eventual `cognitive-os-cfg` bash helper could share logic, but that's out of R2 scope.

---

## References

- PR #7 (`540998a`) — R3 characterization: `tests/unit/test_safe_engram_contract.py` (33 tests) + `tests/unit/test_engram_client.py` (46 tests).
- PR #8 (`d5f6f12`) — R2 characterization: `tests/unit/test_cos_yaml_readers.py` (43 tests).
- PR #9 (`6ed3e63`) — R1 characterization: `tests/unit/test_project_dir_resolution.py` (43 tests).
- `lib/safe_engram.py` — current safe-save implementation.
- `lib/engram_client.py` — current engram-client implementation.
- `lib/dispatch_helper.py:41-78` — site 1 YAML reader.
- `lib/agent_health_monitor.py:93-117` — site 2 YAML reader.
- `hooks/_lib/dispatch_gate_check.py:52-66` — site 3 YAML reader.
- `mcp-server/cos_mcp.py:195-219` — `_engram_save` consumer that locks the contract.
- ADR-025 (`025-install-update-loop.md`) — prior ADR format reference.
