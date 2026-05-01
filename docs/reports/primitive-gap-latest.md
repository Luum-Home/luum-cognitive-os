# Primitive Gap Snapshot

Generated: `2026-05-01T15:33:32.686936+00:00`

Overall risk: **low**

## Hook Latency

events=12419 p50_ms=194 p95_ms=1164 max_ms=8007

## Family Summary

| Family | Total | Proven signal | Partial signal | Aspirational signal | Severity | Evidence | Next action |
|---|---:|---:|---:|---:|---|---|---|
| hooks | 218 | 75 | 143 | 0 | low | row-audit proven=75 partial_nonblocking=143 actionable_gaps=0 | no actionable gaps; harden weak proof opportunistically |
| skills | 232 | 179 | 53 | 0 | low | row-audit proven=179 partial_nonblocking=53 actionable_gaps=0 | no actionable gaps; harden weak proof opportunistically |
| rules | 112 | 112 | 0 | 0 | low | row-audit proven=112 partial_nonblocking=0 actionable_gaps=0 | no actionable gaps; harden weak proof opportunistically |
| memory | 9 | 9 | 0 | 0 | low | memory-named=9 runtime-or-test-referenced=9; actionable_gaps=0 | row-audit memory primitives when Engram APIs change |
| mcp_tools | 183 | 85 | 98 | 0 | low | mcp-mentioned-files=183 test-mentioned-files=85; actionable_gaps=0 | separate installed/optional/reference-only integrations before promotion |
| config_projection | 2 | 2 | 0 | 0 | low | projection-files=2 test-mentioned=2; actionable_gaps=0 | map config keys to readers and projected driver outputs |
| metrics | 99 | 74 | 25 | 0 | low | row-audit proven=74 partial_nonblocking=25 actionable_gaps=0 | no actionable gaps; harden weak proof opportunistically |
| tests_quality_gates | 614 | 28 | 586 | 0 | low | test_py=614 audit-contract-quality=28; actionable_gaps=0 | keep test-quality audit coverage growing; no actionable primitive gap in this snapshot |
| docs_adrs | 2145 | 395 | 1750 | 0 | low | docs_hard_gaps=0 unmapped_claims=0 done_with_proof=126 mapped_claims=269 | no hard docs gaps; improve weak proof opportunistically |
