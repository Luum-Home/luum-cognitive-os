---
type: adr-synthesis
source: docs/02-Decisions/adrs/ADR-026-r2-r3-design-review.md
adr: ADR-026
status: accepted
reality_level: PARTIAL
provenance: A Capa-3 functional audit identified two "reader" refactors (R2, R3) deliberately characterized-but-not-fixed by their authoring PRs — commit messages explicitly warned "divergences locked in (NOT fixed)" for R2 and "the two functions are NOT behaviorally equivalent and a naive delegation would silently break cos_mcp's user-facing message" for R3 — leaving both as open human decisions.
---

## Decision

R2 (`cognitive-os.yaml` readers, 3 characterized sites with 5 locked behavioral divergences): adopt Option B — a single `lib/config_loader.py` exposing three variant functions (`read_top_level_int` cheap-regex, `load_structured` full-schema, `find_config_path` shim) so the 3 sites centralize without collapsing their legitimate divergences. R3 (`lib/safe_engram.py` vs `lib/engram_client.py`): adopt Option C — keep both modules as-is, formalize the boundary via docstrings, since they have zero overlapping callers and 5-of-7 non-equivalent contract dimensions.

## Why

R2: three sites read `cognitive-os.yaml` differently — `dispatch_helper.py` and `agent_health_monitor.py` use cheap regex (no PyYAML) because they're on the PreToolUse hot path or a scheduled loop; `dispatch_gate_check.py` uses `yaml.safe_load` because it already imports heavy modules. This produced 5 locked divergences (search-path order, env-var precedence, key-nesting requirements, empty-file handling, error surfacing) — none objectively correct, each reflecting a real operational constraint, confirmed via git forensics that no single commit introduced them. R3: `safe_engram.safe_save` and `engram_client.save_observation` look like duplicate engram-write wrappers but have zero overlapping callers and diverge on CLI shape (`--json` flag), error surface (dataclass with returncode classification vs. `dict | None` collapsing 5 error modes to None), and return type. Concretely, `mcp-server/cos_mcp.py` depends on `safe_save`'s three-way returncode branch (0 / 127 / other) to distinguish "saved," "engram binary missing," and "real failure" — naive delegation to `engram_client` would collapse this and also surface raw JSON to users instead of the current human-readable string. A latent bug was also found and left for separate fixing: `cos_mcp.py:217-219` misclassifies returncode=127 (binary missing) as success.

## Consequences

R2 positive: single import site, bash `grep`/`awk`/`sed` readers (`scripts/cos-update.sh`, `bin/cognitive-os.sh`) remain unaffected since the schema stays grep-friendly; the 43 tests in `test_cos_yaml_readers.py` need only import-path updates. R2 negative: Option B still requires ~9 hours of mechanical porting across sites; 6+ additional adjacent parsers (`queue_drainer.py`, `prompt_builder.py`, `dispatch_model_advisor.py`, and per the follow-up addendum also `rate_limiter.py`, `sdd_pipeline.py`, `queue_advisor.py`, `smart_infra.py`) were found to duplicate the same path-resolution logic but were deliberately scope-limited out (deferred to "R2b") because no characterization tests exist for them yet.

R3 positive: zero behavioral risk, zero code change beyond docstrings; 79 characterization tests (33 + 46) stay green; the audit backlog closes with a valid "investigated, no consolidation needed" verdict. R3 negative: none identified — this was assessed as the correct terminal state, not a compromise.

## Status & current state

Frontmatter marks accepted/partial. R3 portion is explicitly CLOSED (2026-04-17) per ADR-026a: module docstrings added to both files, and the `cos_mcp.py` returncode=127 bug fixed. R2 portion required human decisions (D2.1-D2.4) that ADR-026a (the addendum) answered on the author's behalf with high confidence recommendations (adopt Option B; fix the env-var precedence miss in the same PR; scope-limit rather than absorb adjacent parsers; defer schema validation to a future ADR) — but R2 rollout itself ("Lote 4", ~9h estimated) is not confirmed shipped within this document; `partial_remaining` in frontmatter flags the R2b adjacent-parser absorption as remaining scope.

## Key links

ADR-026a (addendum answering all 7 open decision questions with evidence and a Lote 4/R3-close-out implementation plan), ADR-025 (prior ADR format reference), PR #7 (`540998a`, R3 characterization), PR #8 (`d5f6f12`, R2 characterization), PR #9 (`6ed3e63`, R1 project-dir resolution, a sequencing prerequisite for R2), `lib/safe_engram.py`, `lib/engram_client.py`, `mcp-server/cos_mcp.py`, `tests/unit/test_cos_yaml_readers.py`.
