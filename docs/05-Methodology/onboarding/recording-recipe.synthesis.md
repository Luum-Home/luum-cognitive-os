---
type: methodology-synthesis
source: docs/05-Methodology/onboarding/recording-recipe.md
provenance: "Reproducible recipe for recording the M2 onboarding asciicast walkthrough so it stays short, non-interactive, and embeddable in README.md."
---

## What it is
A recipe for non-interactively driving and recording the M2 onboarding walkthrough as an asciicast (`.cast`), so the recording is reproducible, short, and embeddable in `README.md`.

## Key mechanics
- **One-time install:** `brew install asciinema` (or `pip install asciinema`); optional `brew install agg` for `.cast` → `.gif` conversion.
- **Recording command (from a fresh clone):** `asciinema rec docs/05-Methodology/onboarding/walkthrough.cast --title "Cognitive OS — fresh clone walkthrough" --command "bash scripts/cos-record-onboarding.sh"`.
- **Pacing:** the driving script self-paces at 1.5s between steps for a human-like cadence; override via `COS_RECORD_PAUSE=0.5 asciinema rec ...` for a tighter recording. Total runtime ~2 minutes.
- **Publish options:** (1) local-only — keep `walkthrough.cast` in the repo (plaintext, ~30KB) and link it from the README; (2) `asciinema upload docs/05-Methodology/onboarding/walkthrough.cast` and link the resulting URL. For a static GIF fallback: `agg walkthrough.cast walkthrough.gif --speed 1.5 --font-size 16`.
- **What the script demonstrates (8 beats):** `cos-status.sh` install verification; list of available skills under `.claude/skills/`; sample skill content (`verification-before-completion`); hook-chain inventory; destructive-op block demo (`git push --force` gated); readiness-checklist preview; `CONTRIBUTING.md` AI-policy preview; license + FAQ link.
- **Sync requirement:** the recording must match the prose walkthrough in `walkthrough.md`; update `scripts/cos-record-onboarding.sh` whenever the prose changes, and keep both in sync.
- **Acceptance criterion:** played back at 1× speed, the recording must complete under 3 minutes; if any step times out or hangs, fix the underlying primitive before re-recording rather than editing around it — asciinema faithfully reproduces bad UX.

## Relations & where used
- `scripts/cos-record-onboarding.sh` — the driving script this recipe wraps; must stay in sync with `walkthrough.md`.
- `docs/05-Methodology/onboarding/walkthrough.md` — the prose companion this recording must match.
- `docs/05-Methodology/onboarding/walkthrough.cast` / `.gif` — recipe outputs, optionally embedded in `README.md`.
- `.claude/skills/verification-before-completion` — the sample skill shown in the recording.

## Status / caveats
- No explicit last-updated date; an operational recipe rather than a status report. Contains no numeric claims about current suite/system state to flag as stale.
