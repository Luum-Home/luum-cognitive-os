---
adr: 279
title: Orphan Repo-Scan Process Audit
status: accepted
implementation_status: implemented
classification_basis: 'implemented: ADR-279 ships a dry-run-first audit primitive, explicit opt-in kill path, JSONL evidence, and behavior tests for PPID=1 Claude/zsh/grep-style repo scans.'
date: 2026-05-12
supersedes: []
superseded_by: null
extends: [ADR-028, ADR-047, ADR-219, ADR-278]
implementation_files:
  - lib/orphan_process_audit.py
  - scripts/cos-orphan-process-audit.py
  - tests/behavior/test_orphan_process_audit.py
tier: maintainer
tags: [process-lifecycle, orphan-processes, reaper, watchdog, hang-prevention, postmortem-2026-05-12]
---
# ADR-279: Orphan Repo-Scan Process Audit

## Status

Accepted and implemented — 2026-05-12.

<!-- SCOPE: OS -->

**Date**: 2026-05-12

## Context

During the May 12 dispersed-test repair session, several old Claude/zsh search
pipelines were still running after the sessions that launched them had ended.
The visible pattern was:

- `/bin/zsh -c source ~/.claude/shell-snapshots/snapshot-zsh-...` wrappers
  running repo scans for `holaos-cleanroom` and `docs/architecture/adrs`.
- Child `ugrep` processes scanning `.cognitive-os/` and `.codex/`.
- Some processes already had `PPID=1`, proving their original parent exited
  without reaping them.
- Killing the zsh wrappers reparented two `ugrep` children to PID 1, requiring a
  second explicit kill pass.

The existing ADR-028 process registry is intentionally conservative. It safely
kills only PIDs registered through `lib/process_registry.py` / `_register_bg`.
Arbitrary Claude shell commands are not registered, so the reaper can log nearby
hook orphans but cannot safely terminate unregistered grep/find pipelines.

ADR-278 bounds Python `subprocess.run(...)` hangs, but it does not cover host
harness shell commands already launched outside Python or child processes left
behind by a dead shell wrapper.

## Decision

Add a separate orphan repo-scan audit primitive:

```bash
python3 scripts/cos-orphan-process-audit.py
python3 scripts/cos-orphan-process-audit.py --kill --older-than-seconds 3600
```

The primitive is dry-run-first and only classifies a process as kill-eligible
when all of these are true:

1. `PPID == 1` — the process is already orphaned/reparented.
2. elapsed runtime is at least `--older-than-seconds` (default: 3600).
3. command shape is a conservative repo scan:
   - `ugrep`, `grep`, `find`, or `rg` scanning `.cognitive-os`, `.codex`,
     `docs/architecture`, `docs/archive`, or `docs/archived`; or
   - a Claude shell-snapshot wrapper containing a grep/find-style repo scan.
4. the current audit process is never eligible.

The primitive emits JSON with schema `orphan-process-audit/v1` and appends
metrics to `.cognitive-os/metrics/orphan-processes.jsonl` unless
`--no-metric` is provided.

## Non-goals

- Do not turn `so-reaper.sh` into a broad process killer.
- Do not kill unregistered arbitrary Python, Node, server, test, database, or
  app processes based on age alone.
- Do not infer ownership from command text without the PPID=1 orphan signal.
- Do not replace `lib/process_registry.py`; registered background jobs remain
  the preferred lifecycle primitive.

## Safety Model

| Guard | Why it exists |
|---|---|
| Dry-run default | Operators can inspect exact PIDs and commands before signaling. |
| `--kill` explicit flag | No accidental kill from a read-only diagnostic run. |
| `PPID=1` requirement | Avoids killing active child work still owned by a live harness/session. |
| Age threshold | Avoids racing recently detached process trees. |
| Safe scan tokens | Limits scope to repo-scan commands that caused the incident class. |
| Metrics append | Leaves an audit trail of candidates and kill actions. |

## Implementation

- `lib/orphan_process_audit.py` owns parsing, classification, report building,
  metrics, and signal delivery.
- `scripts/cos-orphan-process-audit.py` is the operator-facing primitive.
- `tests/behavior/test_orphan_process_audit.py` proves:
  - BSD `ps` elapsed-time parsing;
  - old `PPID=1` `ugrep` scans are detected;
  - young, non-orphan, non-repo, and non-scan processes are ignored;
  - Claude shell-snapshot grep wrappers are detected;
  - signal delivery requires the explicit terminate path;
  - JSON reports carry stable ADR-279 IDs.

## Operational Guide

Inspect candidates:

```bash
python3 scripts/cos-orphan-process-audit.py --older-than-seconds 3600
```

Terminate only classified candidates:

```bash
python3 scripts/cos-orphan-process-audit.py --kill --older-than-seconds 3600
```

Use a shorter threshold only when actively debugging a known incident:

```bash
python3 scripts/cos-orphan-process-audit.py --older-than-seconds 300
```

Use fixture mode in tests or forensic replay:

```bash
python3 scripts/cos-orphan-process-audit.py --ps-fixture /tmp/ps.txt --no-metric
```

## Consequences

- The existing reaper safety invariant remains intact: `so-reaper.sh` does not
  become a broad unregistered-process killer.
- Operators get a purpose-built primitive for the precise orphan class observed
  in the incident.
- The behavior is testable without spawning real orphan processes by injecting
  parsed `ps` rows and mocking signal delivery.
- The primitive is intentionally narrow; new orphan classes require explicit
  expansion of the classifier and tests.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| Teach `so-reaper.sh` to kill any old `PPID=1` process | Too broad; risks killing unrelated user/system work. |
| Auto-register every shell command launched by Claude | Not available from this repo boundary; harness-owned commands may not pass through COS wrappers. |
| Only rely on ADR-278 subprocess timeouts | Does not cover host shell pipelines or child processes already orphaned outside Python. |
| Manual `ps | grep | kill` runbooks only | Works once, but leaves no reusable primitive, no tests, and no metrics trail. |

## Verification

```bash
python3 -m pytest tests/behavior/test_orphan_process_audit.py -q
python3 scripts/cos-orphan-process-audit.py --no-metric
```

## Related

- ADR-028 — SO Reliability & Observability Framework; owns process registry and
  safe reaper concepts.
- ADR-047 — Session lifecycle watchdog.
- ADR-219 — Work ownership liveness preflight.
- ADR-278 — `subprocess.run` timeout discipline.
