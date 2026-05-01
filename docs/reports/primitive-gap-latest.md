# Primitive Gap Snapshot

Generated: `2026-05-01T14:42:19.994392+00:00`

Overall risk: **low**

## Hook Latency

events=0 p50_ms=None p95_ms=None max_ms=None

## Family Summary

| Family | Total | Proven signal | Partial signal | Aspirational signal | Severity | Evidence | Next action |
|---|---:|---:|---:|---:|---|---|---|
| hooks | 215 | 72 | 143 | 0 | low | row-audit proven=72 partial_nonblocking=143 actionable_gaps=0 | no actionable gaps; harden weak proof opportunistically |
| skills | 230 | 177 | 53 | 0 | low | row-audit proven=177 partial_nonblocking=53 actionable_gaps=0 | no actionable gaps; harden weak proof opportunistically |
| rules | 112 | 112 | 0 | 0 | low | row-audit proven=112 partial_nonblocking=0 actionable_gaps=0 | no actionable gaps; harden weak proof opportunistically |
| memory | 9 | 9 | 0 | 0 | low | memory-named=9 runtime-or-test-referenced=9; actionable_gaps=0 | row-audit memory primitives when Engram APIs change |
| mcp_tools | 174 | 79 | 95 | 0 | low | mcp-mentioned-files=174 test-mentioned-files=79; actionable_gaps=0 | separate installed/optional/reference-only integrations before promotion |
| config_projection | 2 | 2 | 0 | 0 | low | projection-files=2 test-mentioned=2; actionable_gaps=0 | map config keys to readers and projected driver outputs |
| metrics | 2 | 2 | 0 | 0 | low | row-audit proven=2 partial_nonblocking=0 actionable_gaps=0 | no actionable gaps; harden weak proof opportunistically |
| tests_quality_gates | 600 | 27 | 573 | 0 | low | test_py=600 audit-contract-quality=27; actionable_gaps=0 | keep test-quality audit coverage growing; no actionable primitive gap in this snapshot |
| docs_adrs | 2108 | 387 | 1721 | 0 | low | docs_hard_gaps=0 unmapped_claims=0 done_with_proof=119 mapped_claims=268 | no hard docs gaps; improve weak proof opportunistically |
