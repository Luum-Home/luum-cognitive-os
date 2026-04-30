# Stage 2 Expansion Baseline — Tier Filter Validation

**Date**: 2026-04-30  
**Author**: automated harness (`scripts/measure_expansion.py`)  
**Context**: ADR-075 Stage 2 — tier_filter selective expansion. Baseline establishes
token cost and unexpanded-key counts before changing the default `tier_filter` from
`[0, 1]` to `[0]`.

---

## 1. Harness Run Results

### 1.1 `simple-edit.txt` (single-file edit, Tier-0 refs)

```
tier_filter                 bytes   tokens_est    unexpanded_keys
-----------------------------------------------------------------
full (None)                 33895         8474                  2
{0,1,2}                     33895         8474                  2
{0,1}                       33895         8474                  2
{0}                         33895         8474                  2
```

### 1.2 `multi-service-refactor.txt` (cross-service refactor, Tier-1 refs)

```
tier_filter                 bytes   tokens_est    unexpanded_keys
-----------------------------------------------------------------
full (None)                 44364        11091                  2
{0,1,2}                     44364        11091                  2
{0,1}                       38245         9561                  4
{0}                         28901         7225                  7
```

### 1.3 `integration-port.txt` (integration port, Tier-2 refs)

```
tier_filter                 bytes   tokens_est    unexpanded_keys
-----------------------------------------------------------------
full (None)                 36660         9165                  2
{0,1,2}                     36660         9165                  2
{0,1}                       18293         4573                  8
{0}                         14298         3574                  9
```

---

## 2. Interpretation

The results confirm the expected tier-ordering pattern for Tier-1 and Tier-2 fixtures,
with one notable nuance:

**simple-edit.txt** — all four tier_filter settings produce identical byte/token counts.
Every rule referenced directly in this fixture is Tier-0 (`acceptance-criteria`,
`agent-quality`, `trust-score`, `agent-escalation`, `definition-of-done`).  This
means switching the default from `[0,1]` to `[0]` has zero impact on single-file-edit
agent contexts — the most common task type.  The 2 "unexpanded_keys" reported in all
configs are `closed-loop-prompts` and `definition-of-done`, which appear inside the
expanded content of other rules (max_depth=1 prevents recursive expansion) rather than
as direct misses; they are an artefact of max_depth, not missing rules.

**multi-service-refactor.txt** — Tier-1 markers (`blast-radius`, `scope-proportionality`,
`decomposition`, `impact-analysis`, `adversarial-review`) resolve with `{0,1}` but remain
literal with `{0}`.  The `{0}` column drops from 9,561 tokens to 7,225 tokens (−25%) and
leaves 7 markers unexpanded.  An agent running with `tier_filter: [0]` on a cross-service
refactor task will see those markers as literal text, not expanded rules — which is the
regression risk being measured.

**integration-port.txt** — Tier-2 markers (`aguara-integration`, `parry-integration`,
`repomix-integration`, `e2b-integration`, `tero-integration`) are only expanded by
`full (None)` and `{0,1,2}`.  Both `{0,1}` and `{0}` leave them unexpanded.  The
token drop from full (9,165) to `{0}` (3,574) is −61%, but 9 out of 11 markers remain
literal.  For integration-porting tasks, `[0]` would be a significant context gap.

**Conclusion**: `tier_filter: [0]` is safe for Tier-0-heavy workloads (simple edits,
single-file fixes) but leaves Tier-1 and Tier-2 rule content unexpanded for complex
multi-service or integration tasks.  The offline measurement cannot predict whether
agents will _escalate_ more often as a result — that requires live observation.

---

## 3. Pre-change Baseline (2026-04-30)

Source: `.cognitive-os/metrics/session-learnings.jsonl`  
Window: last 7 days (2026-04-23 to 2026-04-30)

| Metric                            | Value   |
|-----------------------------------|---------|
| Sessions recorded                 | 256     |
| Total `skills_failed` events      | 114     |
| Failure rate per session          | 0.445   |

**Note**: `session_errors` is 0 for all sessions — the `skills_failed` field is
the operative escalation proxy.  `error-learning.jsonl` has only 47 entries total
(below the 50-entry threshold); `session-learnings.jsonl` with 835 entries and 256
in the last 7 days is the richer data source.

Compare this rate after running 1+ session with `tier_filter: [0]` to detect
behavioural regression.  **Threshold for revert: >2× baseline escalation rate**
(i.e. `skills_failed / sessions > 0.89`).

---

## 4. How to Validate Live

1. Set `expansion.tier_filter: [0]` in `cognitive-os.yaml`.
2. Run a normal coding session for 30+ minutes (mix of simple edits and at least
   one multi-file task so both Tier-0 and Tier-1 workloads are exercised).
3. Re-run the historical escalation analysis below.
4. If rate > 2× baseline (0.89), revert `tier_filter` to `[0, 1]`.
   If rate ≤ baseline (0.445), the aggressive default is safe to keep.

**One-liner to re-run analysis and print PASS/FAIL**:

```bash
python3 -c "
import json, datetime, sys
cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)).isoformat()
sessions, failures = 0, 0
log = '.cognitive-os/metrics/session-learnings.jsonl'
for line in open(log):
    try:
        o = json.loads(line)
    except Exception:
        continue
    if o.get('timestamp', '') >= cutoff:
        sessions += 1
        failures += o.get('skills_failed', 0)
rate = failures / sessions if sessions else 0
baseline, threshold = 0.445, 0.890
print(f'Sessions={sessions} failures={failures} rate={rate:.3f} baseline={baseline} threshold={threshold}')
print('PASS' if rate <= threshold else 'FAIL — escalation rate exceeds 2x baseline; revert tier_filter')
sys.exit(0 if rate <= threshold else 1)
"
```

---

## 5. Re-run Instructions

To regenerate these measurements at any time:

```bash
python3 scripts/measure_expansion.py tests/fixtures/expansion/simple-edit.txt
python3 scripts/measure_expansion.py tests/fixtures/expansion/multi-service-refactor.txt
python3 scripts/measure_expansion.py tests/fixtures/expansion/integration-port.txt
```

Results are also appended to `.cognitive-os/metrics/expansion-measurements.jsonl`
for longitudinal tracking.
