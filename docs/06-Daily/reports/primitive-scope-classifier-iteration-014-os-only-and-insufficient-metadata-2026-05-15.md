# Primitive Scope Classifier — Iteration 014: os-only candidates + insufficient metadata split

Date: 2026-05-15

## Goal

Attack both remaining buckets after Iteration 013:

```json
{
  "insufficient-metadata": 344,
  "os-only-semantic-candidate": 41
}
```

## Policy

This iteration intentionally did **not** mass-classify the full `insufficient-metadata` bucket. It split it into safe and unsafe work:

- Safe: rows already declared `os-only`, or rows with strong COS-internal semantic evidence.
- Unsafe: rows declared `both` with insufficient evidence. Those need another manual pass; demoting or confirming them in bulk would repeat the original mistake.

## Actions

### 1. Resolved `os-only-semantic-candidate` completely

- 41 rows were declared `both` but had strong COS-internal evidence.
- They were demoted to `os-only` and given durable metadata.

### 2. Resolved declared-`os-only` rows inside `insufficient-metadata`

- 65 rows already declared `os-only` but lacked lifecycle / consumer-availability evidence.
- They were kept `os-only` and given durable metadata.

## Result

```json
{
  "before_unknown": 385,
  "after_unknown": 279,
  "resolved_total": 106,
  "os_only_semantic_candidate_after": 0,
  "remaining_insufficient_metadata": 279
}
```

Updated classifier summary:

```json
{
  "by_suggested_scope": {
    "both": 176,
    "os-only": 642,
    "project": 91,
    "unknown": 279
  },
  "safe_fallback_os_only_from_unknown": 279
}
```

Updated triage summary:

```json
{
  "by_bucket": {
    "insufficient-metadata": 279
  },
  "by_declared_scope": {
    "both": 279
  }
}
```

## Remaining work

Only one bucket remains, but it is the riskiest one:

- `insufficient-metadata`: 279 rows
- all are declared `both`
- all lack lifecycle / consumer-availability evidence

Prefix distribution:

```json
{
  "hooks": 36,
  "rules": 80,
  "scripts": 115,
  "skills": 40,
  "templates": 8
}
```

These must be reviewed in sub-batches by primitive kind, not mass-edited.

## Next recommended sub-batches

1. `templates` — 8 rows, low risk, likely easy to classify.
2. `skills` — 40 rows, manageable and semantically rich.
3. `rules` — 80 rows, likely many `both`, but should be grouped by governance vs COS-internal.
4. `hooks` — 36 rows, needs care because root regular hooks are often COS runtime internals.
5. `scripts` — 115 rows, highest risk; many may be maintainer-only.
