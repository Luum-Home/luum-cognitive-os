# Primitive Gap Snapshot

Generated: `2026-04-30T17:39:43.137704+00:00`

Overall risk: **high**

## Hook Latency

events=2391 p50_ms=219 p95_ms=1325 max_ms=13332

## Family Summary

| Family | Total | Proven signal | Partial signal | Aspirational signal | Severity | Evidence | Next action |
|---|---:|---:|---:|---:|---|---|---|
| hooks | 165 | 77 | 165 | 0 | high | registered=80 tested=162 both=77 | row-audit hook lifecycle, metrics, consumers, and latency |
| skills | 143 | 77 | 124 | 19 | medium | runtime-mentioned=109 tested=92 both=77 | cluster skills by purpose and identify manual-only or duplicate skills |
| rules | 112 | 97 | 112 | 0 | medium | tier-comment=112 tested-or-mentioned=97 | verify tier/load reality using lib/ref_key_loader.py semantics |
| memory | 9 | 9 | 9 | 0 | high | memory-named=9 runtime-or-test-referenced=9 | prove automatic save/read/consume loop across sessions |
| mcp_tools | 165 | 67 | 165 | 98 | high | mcp-mentioned-files=165 test-mentioned-files=67 | separate installed, optional, reference-only, and missing integrations |
| config_projection | 2 | 2 | 2 | 0 | high | projection-files=2 test-mentioned=2 | map config keys to readers and projected driver outputs |
| metrics | 95 | 73 | 95 | 22 | medium | jsonl=95 nonempty=73 empty=22 | assign owners and consumers to every metric stream |
| tests_quality_gates | 539 | 20 | 539 | 0 | high | test_py=539 audit-contract-quality=20 | run test-quality audit and map theater tests to primitives |
| docs_adrs | 374 | 47 | 58 | 11 | high | docs=374 adrs=58 adr-proof-mentions=47 | map product claims to code, tests, metrics, or manual proof paths |
