---
type: quality-synthesis
source: docs/09-Quality/manual-tests/agentic-mastery.md
provenance: "Manual test proving the Agentic Mastery MVP surfaces (skill efficacy, runtime benchmarking, adversarial generalization, Lethal Trifecta gate, ACI capture) work end-to-end without external scanners or paid model calls."
---

## What it is
A 4-step manual procedure verifying the Agentic Mastery MVP: automated report generation via `make test-agentic-mastery`, existence checks on 4 generated reports, a manual exercise of the Lethal Trifecta exfiltration-blocking gate, and a manual exercise of ACI observation capture.

## Key mechanics
- Preconditions: run from repo root; no external scanner credentials, no Docker, no network required — designed to be fully local/offline.
- Step 1: `make test-agentic-mastery` runs automated validation.
- Step 2: confirms 4 reports exist under `.cognitive-os/reports/`: `skill-efficacy-smoke-report.md`, `runtime-benchmark-leaderboard.md`, `adversarial-generalization-report.md`, `agentic-mastery-summary.md`.
- Step 3: pipes a synthetic hook-input payload into `hooks/lethal-trifecta-gate.sh` that combines all three risk signals the gate is designed to catch in one tool call — a reference to a sensitive local secrets file, a shell pipe toward an outbound network destination, and injected instructions framed as coming from unreviewed third-party content. Expects exit code 2 and output containing the gate's BLOCKED marker — proving the gate catches the classic "read secret + exfiltrate + untrusted instruction" combination (the Lethal Trifecta).
- Step 4: pipes a crafted tool-response JSON (a failed pytest run) into `hooks/aci-observation-capture.sh`; expects new rows written to `.cognitive-os/metrics/aci-observations.jsonl` and `.cognitive-os/metrics/agent-trajectory.jsonl`.
- Pass criteria: automated validation passes, all 4 reports generated, Lethal Trifecta gate blocks the exfiltration scenario, ACI capture writes both observation and trajectory rows.

## Relations & where used
Exercises `hooks/lethal-trifecta-gate.sh` and `hooks/aci-observation-capture.sh`; produces artifacts consumed elsewhere as `.cognitive-os/reports/agentic-mastery-summary.md` and the metrics JSONL files under `.cognitive-os/metrics/`.

## Status / caveats
Procedural manual-test document, not a dated execution report — defines the test steps and pass criteria without recording a specific run's outcome.
