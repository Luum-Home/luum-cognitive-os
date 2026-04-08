# Smoke Tests

These tests verify that files exist, have correct format, and contain required fields.
They do NOT test behavior — they are structural integrity checks.

Run separately from behavior tests:

```bash
pytest tests/smoke/ -v          # structural checks only
pytest tests/unit/ tests/hooks/ tests/integration/ -v  # behavior tests
```

These were previously in `tests/behavior/` but were reclassified during
the maturation audit (April 2026) to accurately reflect what they test.

## What belongs here

- File existence checks (`assert path.exists()`)
- Format/field presence checks (`assert "field:" in content`)
- YAML frontmatter validation
- Doc section presence checks (`assert "## Section" in content`)
- Minimum content-length checks

## What does NOT belong here

- Tests that execute hooks via subprocess
- Tests that import and call library functions
- Tests that run git commands or CLI tools
- Tests that verify logic correctness (pure function tests)
- Tests that check runtime behavior (exit codes, output content)
