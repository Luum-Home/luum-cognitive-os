# Session Startup Baseline — 2026-04-20

> Captured by Agent D (benchmark harness stream) as part of the 4-stream
> startup-optimisation initiative.  This document records pre-optimisation
> numbers so Agents A/B/C can measure their gains objectively.
>
> Benchmark tool: `scripts/startup-benchmark.sh`
> Metric file: `.cognitive-os/metrics/startup-benchmark.jsonl`
> Regression test: `tests/unit/test_startup_budget.py`

---

## 1. SessionStart Hook Timing (serial wall-clock)

Measured on: 2026-04-20 / 2026-04-21 (two runs averaged)

| # | Hook | Run 1 (ms) | Run 2 (ms) | Avg (ms) | Notes |
|---|------|-----------|-----------|---------|-------|
| 1 | `self-install.sh` | 1346 | 1733 | 1540 | Largest single hook — writes settings, registers hooks |
| 2 | `session-init.sh` | 1149 | 871 | 1010 | Session dir creation, work-queue check, catalog check |
| 3 | `reaper-daemon-launcher.sh` | 53 | 49 | 51 | Fast |
| 4 | `cos-executor-daemon-launcher.sh` | 107 | 130 | 119 | Daemon check |
| 5 | `crash-recovery.sh` | 165 | 160 | 163 | State check |
| 6 | `session-resume.sh` | 41 | 53 | 47 | Fast |
| 7 | `orchestrator-mode-detect.sh` | 250 | 262 | 256 | Python startup cost |
| 8 | `valkey-ensure.sh` | 37 | 64 | 51 | TCP probe |
| 9 | `usage-health-check.sh` | 45 | 192 | 119 | Variable — disk I/O |
| 10 | `ecosystem-check.sh` | 45 | 80 | 63 | Fast |
| 11 | `pattern-check.sh` | 66 | 117 | 92 | Exit 1 (pattern match tool not installed) |
| 12 | `metrics-rotation.sh` | 303 | 401 | 352 | JSONL file rotation scan |
| 13 | `aspirational-audit-weekly.sh` | 44 | 50 | 47 | TTL check, fast |
| 14 | `mcp-scan.sh` | 1818 | 1203 | 1511 | MCP process scan — network/socket probes |
| 15 | `session-start-worktree-nudge.sh` | 51 | 55 | 53 | Fast |
| 16 | `self-knowledge-refresh.sh` | 1997 | 2384 | 2191 | Slowest hook — file I/O + Python |

**Total serial SessionStart: ~7517–7804 ms (~7.5–7.8 s)**

### Key Observations

- **Top 4 offenders** (by avg): `self-knowledge-refresh.sh` (2191 ms), `self-install.sh` (1540 ms), `mcp-scan.sh` (1511 ms), `session-init.sh` (1010 ms)
- These 4 hooks account for **~82%** of total startup time
- 12 of 16 hooks complete in < 350 ms each — these are not the problem
- SLO 1 target is 2 s; current total is **3.75× over budget** serially
- If the top 4 are parallelised or cached, total could drop to ~700 ms (within SLO)

---

## 2. Initial Context Payload Sizes

| Component | Bytes | Est. Tokens | Notes |
|-----------|-------|-------------|-------|
| Global `~/.claude/CLAUDE.md` | 11,125 | 2,781 | User-global orchestrator rules |
| Project `CLAUDE.md` | 0 | 0 | Not present in this project |
| `rules/RULES-COMPACT.md` | 5,933 | 1,483 | Always-active rules index |
| `skills/CATALOG-COMPACT.md` | 12,696 | 3,174 | Skills catalog |
| `cognitive-os.yaml` | 28,125 | 7,031 | Config file (not all loaded into context) |
| Hook text output (4 emitting hooks) | 34,354 | ~8,589 | Stdout from session-init, self-install, etc. |

**Core payload** (CLAUDE.md + RULES-COMPACT + skills catalog): **29,754 bytes (~7,439 tokens)**

**Full rules payload** (CLAUDE.md + all 103 rules/*.md + skills catalog): **410,776 bytes (~102,694 tokens)**

### Key Observations

- Core payload (what's actually injected at startup) is **7,439 tokens** — well within the 50,000-token SLO
- The 103 rules files total 387 KB / ~97K tokens; these are loaded on-demand via `[ref-key]` triggers, NOT all at startup
- Hook stdout output (~8.5K tokens equivalent) is a real contribution to initial context — `self-install.sh` alone is a 23 KB file
- **SLO 10 status: PASS** (7,439 tokens vs 50,000 target)

---

## 3. SLO Status at Baseline

| SLO | Dimension | Target | Baseline | Status | Gap |
|-----|-----------|--------|----------|--------|-----|
| 1 | SessionStart p95 duration | < 2,000 ms | ~7,650 ms | BREACH | 3.8× over |
| 10 | Initial context payload tokens | < 50,000 | ~7,439 tokens | PASS | 85% headroom |

---

## 4. Optimisation Targets for Agents A/B/C

Based on this baseline, the highest-value changes are:

1. **Parallelise top 4 hooks** — `self-knowledge-refresh.sh`, `self-install.sh`, `mcp-scan.sh`, `session-init.sh` can run concurrently. Potential saving: ~5,000 ms → total drops to ~2,500 ms.
2. **Cache `self-install.sh` output** — it rebuilds hook registrations on every session start. A checksum-based cache could reduce it to < 50 ms on cache hits.
3. **Lazy-load `self-knowledge-refresh.sh`** — move to first tool call rather than SessionStart.
4. **Async `mcp-scan.sh`** — MCP socket probes do not block session utility; can be moved to async.

After the above optimisations, SLO 1 (< 2 s) should be achievable.

---

## 5. Measurement Procedure

```bash
# Run benchmark (appends to metrics JSONL, prints markdown to stdout)
bash scripts/startup-benchmark.sh

# Verify JSON output
tail -1 .cognitive-os/metrics/startup-benchmark.jsonl | python3 -m json.tool

# Run regression test
pytest tests/unit/test_startup_budget.py -v

# Check SLO compliance
python3 -c "
import json
rec = json.loads(open('.cognitive-os/metrics/startup-benchmark.jsonl').readlines()[-1])
print('Hook total:', rec['session_start']['total_duration_ms'], 'ms')
print('Payload tokens:', rec['payload']['core_payload_tokens'])
print('SLO 1:', rec['slo']['session_start_status'])
print('SLO 10:', rec['slo']['payload_token_status'])
"
```

---

## 6. TTFT (Time to First Token) — Manual Measurement Procedure

TTFT cannot be measured by the benchmark script alone because it requires the model
to respond. Manual procedure:

1. Open a fresh Claude Code session on this project
2. Note the wall-clock time when the session starts (hook chain begins)
3. Type a simple prompt: `echo hello`
4. Note the wall-clock time when the first output token appears in the UI
5. Subtract: TTFT = (first token time) - (session start time)

Suggested tooling for automated TTFT:
- Instrument `session-init.sh` to write `START_EPOCH=$(date +%s%N)` to a temp file
- Instrument the first `PostToolUse` hook to compute delta and append to `ttft-events.jsonl`
- SLO target (proposed): p95 TTFT < 5 s (includes model latency; hook contribution should be < 2 s)

This integration point is documented but NOT implemented in this stream. Agent A
owns hook execution changes; coordinate there.

---

## 7. Integration with `so-vitals.sh`

The `scripts/so-vitals.sh` system-level dashboard does NOT currently capture
startup hook timing. The benchmark script operates independently and appends to
`startup-benchmark.jsonl`.

**Proposed integration** (for Agent A / post-optimisation):

Add a `startup_ms` field to the `so-vitals.sh` payload by reading the last record
from `startup-benchmark.jsonl`:

```python
# In so-vitals.sh Python block, after disk_bytes calculation:
startup_ms = None
benchmark_path = ROOT / ".cognitive-os" / "metrics" / "startup-benchmark.jsonl"
if benchmark_path.exists():
    try:
        lines = benchmark_path.read_text().strip().splitlines()
        if lines:
            rec = json.loads(lines[-1])
            startup_ms = rec.get("session_start", {}).get("total_duration_ms")
    except Exception:
        pass
# Then add to payload: "startup_ms": startup_ms
```

This is a read-only operation — it does not modify hook execution and can be added
without coordination with other agents.

---

_Captured 2026-04-20. Next measurement: after Agent A/B/C changes land._
