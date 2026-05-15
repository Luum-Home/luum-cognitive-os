# COS vs AI Slop Two-Repo Smoke — Latest

Generated: `2026-05-15T13:22:34+00:00`
Status: `pass`
Mode: `non-provider-two-repo-substrate-smoke`
Harness: `codex`

## Probe Results

| Probe | Status | Rationale |
|---|---|---|
| `vanilla_repo_unchanged` | `pass` | Baseline repo remains a clean native-harness fixture. |
| `cos_projection_exists` | `pass` | COS repo has inspectable projected substrate. |
| `driver_boundary_visible` | `pass` | Codex projection does not hide Claude coupling. |
| `status_visible` | `pass` | Status tooling inspects the COS repo without model calls. |
| `public_claim_gate_clean` | `pass` | Public high-risk claims remain bounded by a gate. |
| `manifest_debt_not_hidden` | `pass` | Remaining manifest debt is visible as warn. |
| `benchmark_plan_available` | `pass` | Existing so-vs-vanilla benchmark dry-run is available. |

## Manifest-Tier Debt Visibility

- status: `warn`
- primitive_count: `673`
- finding_count: `854`
- warning_count: `508`

## Limitations

- Does not execute live model tasks.
- Does not prove time-to-merge, defect-rate, or cognitive-load wins.
- Only proves the local substrate needed before the A/B/C falsification benchmark.

