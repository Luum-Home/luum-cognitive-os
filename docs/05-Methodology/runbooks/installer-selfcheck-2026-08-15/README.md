# Cognitive OS installer self-check — rescued reconstruction

This directory holds a repair for the Cognitive OS installer at
`luum-agent-os`. It does not belong to this repository's product; it lives here
because it was about to be lost a second time, and a repository is the only
place that survives.

## What this fixes

The installer ships an allowlisted subset of the OS into consumer projects. It
never removes anything, and it never validates that what it ships can satisfy
its own imports. Three defects follow from that, and they are present in every
install on the machine, including fully up-to-date ones:

1. **The confidentiality ruleset never travels.** The template lives under
   `.cognitive-os/`, which the origin's own `.gitignore` excludes as runtime
   state, so no installer path could ever pick it up. Three of the scanner's
   four detection categories are defined entirely by that file, so every scan
   reports "nothing found" while three quarters of it cannot fire. The existing
   template also declares `protected_terms` / `protected_orgs`, which the
   parser does not read — it reads `project_names`, `client_names`,
   `repo_urls`, `org_names` — so a filled-in copy still yields an empty
   ruleset while looking populated.
2. **Modules that shipped code depends on are dropped.** The closure seed is
   built from `hooks/*.sh` only; `hooks/_lib/` is copied wholesale and never
   scanned. A miss is skipped in silence, with the comment "the fail-open
   backstop covers this at runtime". The sharpest consequence:
   `circuit_breaker.py` is installed, but the next line of the same `try` block
   imports `record_completion`, which is not, so the shared `except` swallows
   the whole block and the agent circuit breaker has never run in any consumer.
   Shipping `record_completion` alone does not fix it — it imports
   `learning_pipeline`, which is `os-only`, so the import is deferred to its
   single call site.
3. **`cos-root` cannot ship.** Its header declares `SCOPE: os-only`, and the
   scope projector can never emit an os-only file, while the timing wrapper it
   feeds is re-homed into `hooks/cos/_lib/` without it. `PROJECT_DIR` resolves
   empty and telemetry is written to `/`. The repair removes the dependency
   rather than making it optional.

**The primary deliverable is not those three fixes.** It is
`scripts/cos_install_selfcheck.py`, wired into the install as a step that fails
the install — not an advisory — when a shipped entry point cannot resolve its
imports, when a registered hook path does not exist, or when a shipped file
depends on one that its scope forbids. That check is what would have caught all
three, and its absence is why they survived.

## Provenance, and what is NOT verified here

The original patch was produced and verified by an agent on 2026-08-15: applied
to a fresh clone of the origin, a real install run from the patched tree, and
the self-check demonstrated failing four ways — on the unpatched baseline (12
findings), on a module deleted from a good install, on a module deleted from the
source, and on a ghost hook injected into `settings.json` — with an intact
control returning clean before and after each.

**That verified artifact no longer exists.** It was written to
`/tmp/origin-fix/origin.patch` and `/tmp` was cleared at the date rollover
before anyone moved it into a repository. The warning was given twice and not
acted on, including by the session that gave it.

What is in this directory is a **reconstruction from the agent's own
transcript**: three files recovered from their complete `Write` calls, with the
six later edits to the self-check folded in, and the twelve edits to four
existing files recovered as ordered replace/with pairs in `edits.md`.

Therefore:

- The reconstructed Python compiles and both YAML files parse. That is all that
  has been re-checked.
- **None of the original verification has been re-run against this
  reconstruction.** Treat it as a reviewed proposal, not as a verified patch.
  Anyone applying it should redo the clone-install-sabotage cycle described
  above rather than trusting the earlier result, which was obtained on an
  artifact that can no longer be diffed against this one.
- The origin was recorded at `8602ddc70b8bba77e47300c672a01b24f447d72c`, branch
  `main`. The edits in `edits.md` were written against that tree and may not
  apply cleanly to a later one.

Nothing was ever written to the origin repository: the work was done in a clone
under `/tmp`, by explicit agreement with the session that owns it.

## Known gaps in the self-check itself

Reported by its own author, and worth reading before relying on it:

- For modules that already ship, it flags only **unguarded** module-level
  imports, on the reasoning that a deferred or `try:`-guarded import does not
  break importability. But a guarded import that never resolves is exactly the
  silently-dark-feature class that produced all three defects — so the check is
  blind to the shape that motivated it. A broader intermediate run surfaced
  real cases that were never triaged.
- Only one profile and one harness were exercised (`--default`, `--harness=claude`).
  The `--full` branch has its own duplicate wrapper-copy block that was never run.
- The cost of shipping ~25 additional modules was never measured — install
  size, import time, or whether any drags in a dependency or licence that
  consumer installs previously avoided.

## Applying it

Reinstalling a consumer to pick this up is destructive: `install.sh` does
`rm -rf "$TARGET_DIR"` on both the `--force` and interactive paths, deleting
all of `.cognitive-os/` including metrics, sessions, runtime state and any
local additions. Copy the artifacts file by file, or back the directory up
first. A fleet-wide `--force` would destroy the telemetry that evidences the
defects in the first place.
