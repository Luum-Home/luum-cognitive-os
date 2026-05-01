# Install Timing Baseline — 2026-05-01

> ADR-059 §Phase 2 Day 9-10 baseline runs.
> Script: `scripts/install-timing-test.sh` | Profile: `--standard`
> Source: `file://` clone of local repo (avoids SSH key dependency in CI-free environment)

## Run Results

| run | elapsed_s | errors | manual_steps | exit_code | budget (<300s) |
|-----|-----------|--------|--------------|-----------|----------------|
| 1   | 43        | 0      | 0            | 0         | PASS           |
| 2   | 35        | 0      | 0            | 0         | PASS           |
| 3   | 39        | 0      | 0            | 0         | PASS           |
| 4   | 38        | 0      | 0            | 0         | PASS           |
| 5   | 39        | 0      | 0            | 0         | PASS           |

## Statistics

| metric | value |
|--------|-------|
| count  | 5     |
| mean   | 38.8s |
| p95    | 43s   |
| max    | 43s   |
| budget | 300s  |
| headroom | 257s (86%) |

## Verdict

All 5 runs completed within the ADR-059 budget of 300s with 0 errors and 0 manual steps.
The `--standard` profile installs in ~39s mean on this machine (macOS, local clone).

**"Plug-and-play" claim in README is supported by these numbers.**

## Notes

- Runs used `file://` URL (local clone) rather than `git@github.com` to avoid
  SSH key availability in test environments. Real remote runs may add 5-20s
  depending on network conditions and repo size.
- A minor bug in `count_errors()` (`grep -c` returning exit 1 on zero matches,
  causing `|| echo 0` to double-print) was fixed in commit during this batch.
- The cleanup `trap` emits a benign "unbound variable: tmp_dir" on some Bash
  versions due to `set -u` interacting with EXIT traps; the record is written
  before the trap fires so data integrity is not affected.

## Raw JSONL location

`.cognitive-os/metrics/install-timing.jsonl` — 5 records appended.
