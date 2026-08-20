# Documentation Truth Audit — Latest

Generated: 2026-08-20T03:26:54+00:00
Status: `block`

## Summary

- rows: `120`
- by_status: `{'block': 1, 'pass': 119}`
- by_claim: `{'claude_code_hook_registration': {'pass': 5, 'block': 1}, 'consumer_projection_harnesses': {'pass': 17}, 'cos_init_flag_surface': {'pass': 11}, 'disk_ceiling_single_source': {'pass': 1}, 'documentation_truth_control': {'pass': 8}, 'payload_canary_determinism': {'pass': 8}, 'primitive_authority_write_effects': {'pass': 16}, 'session_pending_protocol': {'pass': 35}, 'subprocess_timeout_discipline': {'pass': 13}, 'volatile_number_prose': {'pass': 5}}`
- block_count: `1`

## Forbidden-phrase scan surface

- Files checked: `3233` (27326789 bytes)
- Declared phrases: `27`
- Suffixes: `.md, .sh, .py, .yaml, .yml`
- Pruned dirs: `.cognitive-os, .git, .mypy_cache, .pytest_cache, .ruff_cache, .venv, .worktrees, __pycache__, build, dist, htmlcov, node_modules, reference, target, venv`
- required_docs always scanned: `25`

| Files excluded | Reason |
|---|---|
| `11` | **/archive/** :: archived artifacts are a record of what was, not a claim about what is. |
| `1819` | .claude/plugins/** :: third-party plugin cache, vendored, not authored in this repo. |
| `7` | ADR status superseded: superseded decisions keep their original prose |
| `240` | date-anchored filename: historical record, cites old claims on purpose |
| `502` | docs/06-Daily/reports/** :: Session reports (date-anchored) and the generated *-latest ledgers. Historical record and machine output, not asserted current truth. A report that a claim needs scanned anyway is opted back in by naming it in that claim's required_docs, which are always scanned. |
| `1` | manifests/documentation-truth-claims.yaml :: the claims manifest declares the phrases |
| `10` | packages/*/tests/** :: same as tests/**, reached through the package layout instead of the symlink. |
| `1` | rules/session-close-doc-truth.md :: The rule that DEFINES this discipline teaches it by quoting an example forbidden phrase ("no atomic close primitive exists"). Self-reference, same class as the claims manifest and the auditor -- both of which the audit excludes in code rather than by configuration. |
| `1` | scripts/documentation_truth_audit.py :: the auditor itself quotes phrase syntax |
| `2373` | tests/** :: The instrument's own fixtures and assertions. A stale-phrase test must contain the phrase to assert its absence (tests/contracts/test_primitive_authority_docs.py lists three of them). The alternative is deforming test code so the auditor is not confused, which is the tail wagging the dog. |

## Blocking rows

| Claim | Check | Doc | Message | Next action |
|---|---|---|---|---|
| `claude_code_hook_registration` | `forbidden_phrase` | `cos_lib/wiring_validator.py` | Forbidden stale phrase present in 1 place(s), checked against 3233 files: the canonical hook registry is `cognitive-os.yaml > harness.hooks` | remove stale or contradictory prose at the listed file:line |
