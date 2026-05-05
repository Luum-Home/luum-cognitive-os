# Proof Drill Registry Manual Test

Date: 2026-05-05  
Scope: Cognitive OS self-build and consumer-project validation boundary

## Goal

Prove that agents can choose between normal tests, smoke opt-ins, and proof
drills without adding provider/Docker/account-backed checks to default lanes.

## Preconditions

- Work from the Cognitive OS repository root.
- Do not set provider credentials unless the operator explicitly asks for a live
  provider smoke.
- Do not run Docker proofs unless the operator explicitly asks for Docker or
  headless runtime evidence.

## Steps

### 1. Validate the registry contract

```bash
python3 -m pytest tests/contracts/test_proof_drill_registry.py -q
```

Expected result: pass.

### 2. Validate the skill contract

```bash
python3 -m pytest tests/audit/test_skills_contracts.py -q
```

Expected result: pass. The new `proof-drill` skill has valid frontmatter,
resolvable references, catalog presence, and no procedural stub markers.

### 3. Inspect opt-in rows without running them

```bash
python3 - <<'PY'
from pathlib import Path
import yaml
registry = yaml.safe_load(Path('manifests/proof-drill-registry.yaml').read_text())
for entry in registry['entries']:
    if entry['class'] in {'smoke-opt-in', 'proof-drill', 'manual-proof'}:
        print(entry['id'], entry['class'], entry['default_lane'], entry['cost_class'])
PY
```

Expected result: every printed row has `default_lane` set to `False`.

### 4. Consumer-project boundary check

Read the `consumer-project-run-tests` row and confirm it points to
`skills/run-tests/SKILL.md`, not an SO-only proof script.

Expected result: consumer-project validation remains project-owned unless a COS
projection manifest explicitly exposes a drill.

### 5. Optional provider smoke

Run this only with explicit operator opt-in and `ALIBABA_QWEN_API_KEY` present:

```bash
bash scripts/smoke-qwen-fallback.sh
```

Expected result: either a successful live smoke or an explicit credential/config
failure. Missing credentials are skipped evidence, not proof that COS provider
fallback is broken.

### 6. Optional Docker/headless proof

Run this only with explicit Docker/headless opt-in:

```bash
scripts/cos-headless-service-drill --json
```

Expected result: local-command task artifacts are produced and the output states
what the drill proves and does not prove.

## Evidence to record

- command;
- working directory;
- exit code;
- artifact paths;
- credential posture;
- cost posture;
- bounded proof claim;
- remaining gaps.
