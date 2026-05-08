# Onboarding asciicast — recording recipe

This recipe drives the M2 onboarding walkthrough non-interactively so the
recording is reproducible and short enough to embed in `README.md`.

## One-time install

```bash
brew install asciinema   # or: pip install asciinema
brew install agg         # optional: convert .cast → .gif
```

## Record

From a fresh clone of the repo:

```bash
git clone git@github.com:Luum-Home/luum-cognitive-os.git
cd luum-cognitive-os
asciinema rec docs/onboarding/walkthrough.cast \
  --title "Cognitive OS — fresh clone walkthrough" \
  --command "bash scripts/cos-record-onboarding.sh"
```

The script paces itself (1.5s between steps) so the resulting `.cast` looks
like a paced human session. Override the pacing with
`COS_RECORD_PAUSE=0.5 asciinema rec ...` if you want a tighter recording.

Total runtime: ~2 minutes.

## Publish

Two options:

1. **Local-only**: keep `walkthrough.cast` in the repo (it's plaintext, ~30KB).
   The README can embed via:
   ```html
   <a href="docs/onboarding/walkthrough.cast">View walkthrough (.cast)</a>
   ```

2. **asciinema.org**: `asciinema upload docs/onboarding/walkthrough.cast`,
   then link the resulting URL from `README.md`.

For a static GIF (works on any markdown viewer):

```bash
agg docs/onboarding/walkthrough.cast docs/onboarding/walkthrough.gif \
  --speed 1.5 --font-size 16
```

## What the script demonstrates

1. `cos-status.sh` — install verification
2. List of available skills under `.claude/skills/`
3. Sample skill content (`verification-before-completion`)
4. Hook chain inventory
5. Destructive-op block (`git push --force` gets gated)
6. Readiness checklist preview
7. CONTRIBUTING.md AI policy preview
8. License + FAQ link

The recording matches the prose walkthrough in `walkthrough.md`. Update
`scripts/cos-record-onboarding.sh` if the prose walkthrough changes; keep
the two in sync.

## Acceptance criterion

The recording, played back at 1× speed, takes under 3 minutes. If a step
times out or hangs, fix the underlying primitive before re-recording —
asciinema will faithfully reproduce the bad UX.
