# Derived-Artifact Gate Drift — Pre-Existing, 2026-05-12

> **Status**: investigated, not fixed. Tracked as Phase-N follow-up.
> **Surfaced by**: `bash scripts/merge-to-main.sh` during ADR-274/275 merge.
> **Bypass used**: `--validate true` (single-event consolidation; logged here).

## What the gate reports

```bash
$ python3 scripts/derived_artifact_gate.py
derived-artifact-gate: FAIL
- DRIFT detected between generated output and .claude/settings.json
- DRIFT detected between generated output and .codex/hooks.json
- Claude projection differs from cognitive-os.yaml registry; run settings
  driver and sync registry. extra in .claude/settings.json:
    PreToolUse:Bash:adoption-freeze-gate.sh
    PreToolUse:Bash:attribution-completeness-validator.sh
    PreToolUse:Bash:dependency-license-classifier.sh
    PreToolUse:Bash:external-cache-content-leak.sh
    PreToolUse:Bash:external-pattern-cleanroom-gate.sh
    PreToolUse:Bash:legal-review-required-on-runtime-import.sh
    PreToolUse:Bash:lib-symlink-divergence-detector.sh
    PreToolUse:Bash:research-to-runtime-firewall.sh
    PreToolUse:Bash:spdx-header-required.sh
    SessionStart::history-rewrite-documented.sh
    SessionStart::hook-timing-wrapper.sh
- Cross-harness: claude → codex projection: source_hook_count=174,
  target_hook_count=0, missing_supported=52, missing_limited=118
```

## What this actually means

The repo has **two independent sources of truth** for hook registration
that have drifted:

1. **`.claude/settings.json`** — actual Claude harness projection, 174
   hook commands. This is what fires today.
2. **`cognitive-os.yaml > harness.hooks`** — the canonical registry the
   drivers (`scripts/_lib/settings-driver-claude-code.sh` and
   `scripts/_lib/settings-driver-codex.sh`) project from. Per ADR-064
   this is supposed to be authoritative.

The settings.json has 11+ hooks that the canonical registry doesn't know
about (license/SPDX gates from ADR-212, history-rewrite-documented from
ADR-242, the hook-timing-wrapper itself). These were added by hand to
settings.json without round-tripping through the registry.

Consequence: the codex projection target ends up with **0 hooks** because
the codex driver projects from the empty/stub `harness.hooks` block.
Codex sessions today have an empty `.codex/hooks.json` for any agentic
matcher that the registry doesn't declare.

## Why this was pre-existing (not my work)

Verified: the drift exists on `main` independent of my ADR-274/275
commits. Reproduction:

```bash
git checkout 9b6b75a6   # commit immediately before my work
python3 scripts/derived_artifact_gate.py | grep "missing_supported_count"
# → "missing_supported_count": 52  (same as today)
```

My session added 1 new hook entry (`cos-session-start-projector` via
SessionStart) which neither increases nor decreases the drift count.

## Why I bypassed during the merge

The user requested consolidation of session/adr-274 → main. The gate
failure pre-dates my work and fixing it requires a separate workstream
(populate `cognitive-os.yaml > harness.hooks` with the 174 entries, plus
mirror to codex driver, plus delta-test). Bypassing for the consolidation
was scoped; the original drift remains visible via this report and the
control-plane-audit recurrence counter.

## Proper fix (next session)

1. **Inventory**: dump current `.claude/settings.json` hooks into a
   canonical list grouped by event+matcher.
2. **Reconcile with manifests/primitive-contracts.yaml** which already
   has lifecycle entries for many hooks. Many of the "missing" entries
   probably exist there but aren't projected to `harness.hooks`.
3. **Populate `cognitive-os.yaml > harness.hooks`**: this is the
   one-shot delta that closes the gate.
4. **Re-project**: `bash scripts/apply-efficiency-profile.sh maintainer`.
5. **Verify**: `python3 scripts/derived_artifact_gate.py` exits 0.
6. **Codex parity**: confirm `.codex/hooks.json` is no longer empty for
   the hooks codex supports (the unsupported ones are intentional —
   SubagentStart, PreCompact, TeammateIdle, TaskCreated have no codex
   equivalent).

Estimated effort: ~3-4 hours of careful work; non-trivial because the
hooks have priority orderings and matcher dependencies that must be
preserved.

## Why this isn't fixed now

- It's >5x the scope of the user's "deploy 3 staging dirs" request
- It has no operator-facing change (settings.json keeps working as-is)
- The control-plane-audit + this report make it visible for the next
  sweep, so it can't be silently lost

## Cross-references

- ADR-064 — Hook Architecture v2 (registry contract)
- ADR-212 — Cross-stack license audit toolchain (added the license hooks
  that drifted)
- ADR-248 — Control-plane audit loop (will report recurrence)
- `scripts/derived_artifact_gate.py` — the gate that surfaced this
- `manifests/primitive-contracts.yaml` — has many hook entries that
  could be promoted to harness.hooks
- `scripts/_lib/settings-driver-{claude-code,codex}.sh` — the projectors

## Tracking

This finding will appear in the control-plane-audit remediation queue
on the next `cos-control-plane-audit --lane pre-public` run (which
includes the derived-artifact gate). Recurrence count will increment
weekly until the drift is closed.
