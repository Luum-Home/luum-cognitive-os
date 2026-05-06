<!-- SCOPE: both -->
---
name: redteam-harness
description: "Run red-team scenarios against the agent OS to detect false-done, partial-completion, and unwired-constant failure modes per ADR-105/ADR-106."
triggers: ["/redteam-harness", "/red-team-harness", "/rt-harness"]
audience: both
version: 1.0.0
summary_line: "Execute red-team scenarios, aggregate baseline, and detect ADR-105 verb violations."

platforms: ["claude-code", "codex", "bare_cli"]
prerequisites:
  - python3 (with PyYAML: pip install pyyaml)
  - bash 4+
  - scripts/run-redteam-scenario.sh (W5)
  - scripts/redteam_aggregate.py (W5)
  - scripts/verify-archived.sh (W0)
  - tests/red_team/scenarios/*.yaml (W3, W4)
entry: bin/cos-skill run redteam-harness
routing_patterns:
  - pattern: '\bredteam[- ]?harness\b'
    confidence: 0.95
  - pattern: '\bred[- ]?team\s+scenarios?\b'
    confidence: 0.85
  - pattern: '\bfalse[- ]?done\s+detection\b'
    confidence: 0.75
---

# /redteam-harness

> Execute red-team scenarios to detect false-done, unwired constants, and
> archive-fallacy failures. Produces a per-scenario verdict and a baseline
> report for CI regression tracking.

## ADR-105 Verbs Covered

This harness covers 6 high-stakes verbs from ADR-105. Each verb has at least
one scenario that probes it:

| ADR-105 Verb | Scenario | W# |
|--------------|----------|----|
| `archived`   | archive-presence-fallacy | W3 |
| `wired`      | unwired-constant | W3 |
| `verified`   | plan-checkbox-no-evidence | W3 |
| `verified`   | partial-completion-claim | W4 |
| `tested`     | regex-false-positives | W4 |
| `completed`  | silent-stash-loss | W4 (xfail until ADR-106 P1) |

## Operations

### 1. List Scenarios

List all available scenarios with their scope, verb, and expected severity:

```bash
ls tests/red_team/scenarios/*.yaml | while read f; do
  python3 -c "
import yaml, sys
d = yaml.safe_load(open('$f'))
print(f\"{d['id']:45s}  scope={d['scope']:8s}  verb={str(d.get('verbs',['?']))[1:-1]:12s}  sev={d['expected_severity']}\")
"
done
```

Or with jq if you have baseline JSON:

```bash
jq '.scenarios[] | [.id, .status, .verb, .severity] | @tsv' \
  docs/reports/redteam-baseline.json
```

### 2. Run a Single Scenario (Replay Mode)

Replay mode exercises the full verification pipeline without a live LLM.
Default mode unless `COS_REDTEAM_LIVE=1`.

```bash
bash scripts/run-redteam-scenario.sh \
  --scenario archive-presence-fallacy \
  --scenarios-dir tests/red_team/scenarios \
  --out-dir /tmp/redteam-out

# See JSON result:
cat /tmp/redteam-out/archive-presence-fallacy.json | python3 -m json.tool
```

Expected output (text):
```
SCENARIO: archive-presence-fallacy [v1.0.0]
MODE:     replay
STATUS:   PASS
SIGNALS:  4/4 matched
DETECT:   exit=1 expected=1
DURATION: 0.42s
OUTPUT:   /tmp/redteam-out/archive-presence-fallacy.json
```

Exit codes: 0=pass, 1=fail, 2=partial, 3=error.

### 3. Run All Scenarios and Aggregate Baseline

```bash
OUT=/tmp/redteam-out
mkdir -p "$OUT"

for scenario_yaml in tests/red_team/scenarios/*.yaml; do
  id=$(python3 -c "import yaml; print(yaml.safe_load(open('$scenario_yaml'))['id'])")
  bash scripts/run-redteam-scenario.sh \
    --scenario "$id" \
    --scenarios-dir tests/red_team/scenarios \
    --out-dir "$OUT" || true
done

python3 scripts/redteam_aggregate.py \
  --input-dir "$OUT" \
  --output-json docs/reports/redteam-baseline.json \
  --output-md  docs/reports/redteam-baseline.md
```

### 4. Aggregate Baseline (from existing JSON results)

```bash
python3 scripts/redteam_aggregate.py \
  --input-dir docs/reports/redteam \
  --output-json docs/reports/redteam-baseline.json \
  --output-md  docs/reports/redteam-baseline.md
```

### 5. Compare Against Prior Baseline

```bash
python3 scripts/redteam_aggregate.py \
  --input-dir docs/reports/redteam \
  --output-json docs/reports/redteam-baseline-new.json \
  --output-md  docs/reports/redteam-baseline-new.md \
  --baseline-compare docs/reports/redteam-baseline.json
```

The Markdown output will include a **Baseline Diff** section showing new
scenarios, removed scenarios, and status regressions.

### 6. Live Mode (staging only, NOT CI)

Live mode dispatches a real agent. Only use in staging environments.

```bash
COS_REDTEAM_LIVE=1 bash scripts/run-redteam-scenario.sh \
  --scenario archive-presence-fallacy \
  --mode live
```

WARNING: Live mode is non-deterministic and must NOT be run in CI
(`COS_REDTEAM_LIVE` is never set in CI per KD1/R2).

## Portability (Scope: both)

All `both`-scoped components accept explicit `--scenarios-dir`, `--out-dir`,
`--source-dir`, and `--archive-dir` flags. They never hardcode SO paths.

To use in a consumer project:

```bash
bash <path-to-so>/scripts/run-redteam-scenario.sh \
  --scenario archive-presence-fallacy \
  --scenarios-dir <path-to-so>/tests/red_team/scenarios \
  --out-dir ./redteam-results
```

## Troubleshooting

- **PyYAML missing**: `pip install pyyaml`
- **Scenario not found**: ensure `--scenarios-dir` points to directory containing `<id>.yaml`
- **Detection command fails with exit 3**: check that `scripts/verify-archived.sh` is executable and on PATH (or use absolute path)
- **All signals unmatched**: verify `initial_state` files were created; use `--mini-repo-keep` to inspect the tempdir
- **xfail scenario**: `silent-stash-loss` is marked `expected_status: xfail` until ADR-106 P1 ships. It reports status=xfail and exits 0.
