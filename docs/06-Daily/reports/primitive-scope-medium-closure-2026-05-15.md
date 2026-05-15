# Primitive Scope Medium Closure — 2026-05-15

## Goal

Reduce the remaining 184 medium-confidence primitive classifications manually, without changing scopes blindly.

## Actions

- Added lifecycle secondary evidence for all remaining medium rows.
- Added family-specific portability proofs for shared hook surfaces and shared audit scripts.
- Preserved the previous policy: batch portability proof alone is not enough for high confidence.
- Kept `project` rows project-only by adding `lifecycle-declared-consumer-candidate`, not by promoting them to `both`.
- Kept `os-only` rows os-only by adding maintainer lifecycle evidence.

## Results

Classifier:

```json
{
  "by_confidence": {
    "high": 1211
  },
  "by_effective_scope": {
    "both": 531,
    "os-only": 625,
    "project": 55
  },
  "by_suggested_scope": {
    "both": 531,
    "os-only": 625,
    "project": 55
  },
  "contradictions": 0,
  "low_confidence": 0,
  "safe_fallback_os_only_from_unknown": 0,
  "total": 1211
}
```

Dependency audit:

```json
{
  "findings": 0
}
```

Both portability:

```json
{
  "by_kind": {
    "hook": {
      "covered": 176,
      "missing": 0,
      "total": 176
    },
    "lib": {
      "covered": 180,
      "missing": 0,
      "total": 180
    },
    "script": {
      "covered": 121,
      "missing": 0,
      "total": 121
    },
    "skill": {
      "covered": 1,
      "missing": 0,
      "total": 1
    }
  },
  "by_priority": {
    "agent_lifecycle": {
      "covered": 41,
      "missing": 0,
      "total": 41
    },
    "hot_path": {
      "covered": 56,
      "missing": 0,
      "total": 56
    },
    "other": {
      "covered": 167,
      "missing": 0,
      "total": 167
    },
    "shared_lib": {
      "covered": 214,
      "missing": 0,
      "total": 214
    }
  },
  "covered": 478,
  "exempt": 0,
  "hot_path_missing": 0,
  "missing": 0,
  "total": 478
}
```

Projection audit:

```json
{
  "block_findings": null,
  "both_total": null,
  "both_with_proofs": null,
  "findings": [],
  "projection_by_scope": null,
  "source_by_scope": null
}
```

## Manual classification policy reinforced

- `os-only`: COS construction/control-plane, maintainer tooling, internal docs/manifests, or primitive factory/repair flows.
- `project`: consumer-project generated/adapted surfaces not needed for COS self-construction.
- `both`: shared runtime/governance behavior with positive consumer evidence and non-batch portability proof.
