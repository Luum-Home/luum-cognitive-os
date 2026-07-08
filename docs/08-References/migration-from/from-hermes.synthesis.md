---
type: reference-synthesis
source: docs/08-References/migration-from/from-hermes.md
provenance: "Migration/compatibility guide for Hermes-agent (Nous Research) users who want to layer Cognitive OS governance on top of an existing Hermes setup without conflict."
---

## What it is

A guide explaining how Cognitive OS coexists with Hermes-agent: both systems' hook points don't overlap, so installing COS adds verification/safety gates around Hermes skill output without altering how Hermes itself runs.

## Key mechanics

- **Compatibility model**: COS hooks fire at Claude Code harness lifecycle points (`PreToolUse`, `PostToolUse`, `SessionStart`, `Stop`); Hermes runs its own skill scheduler at the application layer, below those lifecycle points — the two don't share a hook chain and don't conflict.
- **Install**: same recipe as the vanilla Claude Code guide — `curl | bash install.sh --harness=claude` from inside the Hermes project directory, then verify with `cos-status.sh`.
- **What Hermes skills gain after install**: Trust Report requirement (`trust-score-validator.sh`, Layer 8) blocking "done" claims without a scored report; claim validation (`claim-validator.sh`, Layer 6) blocking fabricated file/test claims in production mode; blast-radius warnings (`blast-radius.sh`, Layer 2) before large-scope Hermes skill actions; error learning capturing failures to `.cognitive-os/metrics/error-learning.jsonl` and surfacing warnings after 3+ repeats.
- **Three known interactions**, all advisory (non-blocking, exit 0 in default profile): (1) Hermes's self-evaluation skill doesn't emit a COS `TRUST_REPORT:` header, so `trust-score-validator.sh` logs a "no trust report found" warning; (2) Hermes skill-creation may trigger a `reinvention-check.sh` (Layer 13) warning if an existing COS skill overlaps — the two skill systems coexist rather than replace each other; (3) Hermes's cron scheduler is still subject to `rate-limiter.sh` (Layer 4) per-minute/cost caps when scheduled tasks run inside a Claude Code session — long batch jobs should raise `resources.budget.hourly_cap_usd` in `cognitive-os.yaml` (default $5/hr).
- **Opt-out mechanism**: add skill names to `governance.skill_bypass_list` in `cognitive-os.yaml` to suppress COS hooks for specific Hermes skills. The doc flags this key as **planned, not guaranteed wired** — if absent, use `apply-efficiency-profile.sh minimal` as an interim full-session suppression.
- **Explicit non-interference boundary**: COS does not touch Hermes model selection, Hermes's messaging gateways (Telegram/Discord/Slack), Hermes's Honcho user model, or Hermes's skill storage (`~/.hermes/skills/`, read-only from COS's perspective).

## Relations & where used

Directly builds on `from-vanilla-claude-code.md` for full install-option details (local clone, force overwrite, git-hook auto-update, uninstall). References the hook layer numbering scheme (Layer 2/4/6/8/13) used across the COS hook system.

## Status / caveats

The document itself flags one internal inconsistency worth preserving verbatim: `skill_bypass_list` is described as "a planned configuration key" that "may not appear in your installed `cognitive-os.yaml`" — i.e., the opt-out mechanism this guide documents is not confirmed to be wired in all installs. No other inconsistencies were found; the rest of the guide describes stable, already-shipped hook behavior (Layers 2/6/8/13) rather than aspirational features.
