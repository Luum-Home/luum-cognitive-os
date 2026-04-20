<!-- SCOPE: both -->
# Content Policy — Automated Enforcement

## Purpose

Prevents prohibited terms, patterns, and attributions from appearing in any file written by agents or committed by humans. Enforcement is automatic -- not dependent on memory.

## Always Enforced

- **PostToolUse hook** `content-policy.sh` (on Edit|Write): scans every modified file for prohibited terms and patterns. BLOCKS the write (exit 2) if any violation is found.
- **Pre-commit gate**: `pre-commit-gate.sh` scans all staged files for prohibited terms before every commit. BLOCKS the commit (exit 1) if any violation is found.
- **Agent preamble**: every sub-agent receives the prohibited terms list in `templates/agent-preamble.md` so violations are prevented at generation time.

## Configuration

Edit `.cognitive-os/content-policy.yaml` to manage:

| Section | Purpose |
|---------|---------|
| `prohibited_terms` | Exact terms that must never appear (case-insensitive) |
| `prohibited_patterns` | Regex patterns that must never match |
| `required_values` | Fields that must have specific values in specific files |
| `content_rules` | General rules for agent behavior |

## Adding a New Prohibited Term

1. Edit `.cognitive-os/content-policy.yaml`
2. Add under `prohibited_terms`:
   ```yaml
   - term: "the-term"
     reason: "Why it is prohibited"
   ```
3. Run a codebase search to find existing occurrences
4. Fix all occurrences before committing

## Metrics

Violations are logged to `.cognitive-os/metrics/content-policy.jsonl`:
```json
{"timestamp":"ISO-8601","file":"path/to/file","violations":1}
```

## Hook Details

- **Hook**: `hooks/content-policy.sh`
- **Type**: PostToolUse
- **Matcher**: Edit|Write
- **Exit code**: 0 (clean) or 2 (BLOCK on violation)

## Integration

| System | Integration |
|--------|-------------|
| Pre-commit | `pre-commit-gate.sh` checks staged files |
| Agent preamble | Prohibited terms listed in preamble template |
| Adversarial review | Complements "no LGTM" rule |
| Secret detector | Complements credential scanning |
