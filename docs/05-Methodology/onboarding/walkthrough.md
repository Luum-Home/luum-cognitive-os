# Onboarding Walkthrough — Fresh Clone to First Useful Skill

> **Goal**: under 10 minutes from `git clone` to a verified, hook-protected
> Cognitive OS install with an audited demo run. A hostile auditor should be
> able to reproduce every step on a clean machine.

This walkthrough is the answer to **"what do I actually do after cloning?"**
It is the canonical path referenced by item M2 of the
[pre-public-readiness checklist](../legal/pre-public-readiness-checklist.md).

A live transcript was captured against the current `main`-equivalent checkout,
then distilled into the public-safe expected-output snippets below. The raw
transcript is intentionally not committed because terminal transcripts can
include local usernames and absolute paths.

---

## Prerequisites

| Tool | Minimum | Why |
|------|---------|-----|
| Git | 2.30+ | clone, worktree |
| Bash | 4+ (macOS users: install via brew, default 3.2 works for most steps) | hooks, scripts |
| Python | 3.10+ | hook libraries, audit tooling |
| Go | 1.21+ | `cmd/cos`, `cmd/cos-test` (optional for first walkthrough) |
| Claude Code | latest | the runtime that hooks attach to |
| `jq` | any | recommended for JSON output |
| `git-filter-repo` | any | only if you run history sanitization |

**You do NOT need** all of these for the walkthrough below — only Git, Bash,
and Python 3.10+ are required to complete steps 1-7. Go and Claude Code
become relevant at step 8.

---

## The 9-Step Walkthrough

Times are wall-clock measurements from the captured transcript on a
2024-class laptop with a warm filesystem cache. Cold-cache will add ~10s
to step 4 (first hook invocation has to load Python).

### Step 1 — Clone (≤ 1 min)

```bash
git clone https://github.com/luum-home/luum-cognitive-os.git
cd luum-cognitive-os
```

**Pre-launch (current state)**: the public URL above is reserved but the
repo has not been published yet. For internal review, clone the local
mirror or operator worktree.

**Expected output**: standard `git clone` progress.
**Troubleshoot**: if clone fails, the repo is not yet public — coordinate
via the contact in `CONTRIBUTING.md`.

---

### Step 2 — Read the front door (≤ 1 min)

Open `README.md`. The two sections that matter:

1. **What it is / is NOT** — sets expectations (governance layer, not an
   agent framework).
2. **5-Minute Demo** — the exact command you will run in step 6.

No command to run here; just read.

---

### Step 3 — (Optional) install into a sample project (≤ 2 min)

Skip this if you only want to *evaluate* the repo. Run it if you want
the hooks active in your own project.

```bash
cd /path/to/your/project
/path/to/luum-cognitive-os/install.sh --harness=claude
```

**Expected output**: installer prints `[install]` lines describing each
copied directory and the resolved profile (`default`).
**Troubleshoot**: if `install.sh` errors with "harness required", pass
`--harness=claude` (or `--harness=codex`).

---

### Step 4 — Verify the install (≤ 1 min)

From the cloned repo (or your installed project, with
`COGNITIVE_OS_PROJECT_DIR` set):

```bash
COGNITIVE_OS_PROJECT_DIR="$PWD" bash scripts/cos-status.sh
```

**Expected output (verbatim from transcript)**:

```
Profile:         default (cognitive-os.yaml)
Skills:          168 exposed -> .claude/skills/  OK
Hooks:           159 wired -> .claude/settings.json
Rules:           0 source -> .cognitive-os/rules/cos/
Packages:        35 installed
Health:          OK all checks pass
```

**Measured time**: 6s.

**Troubleshoot**:
- `Health: FAIL` → run `bash scripts/cos-status.sh --verbose` to see which
  assertion failed; usually a missing `.cognitive-os/` subdir.
- `Rules: 0 source` is expected on a fresh clone — rules live in `rules/`
  and are projected into `.cognitive-os/rules/cos/` only after install.

---

### Step 5 — Inspect what is wired (≤ 1 min)

```bash
bash scripts/cos-status.sh --verbose
```

**Expected output**: same headline as step 4, plus per-event hook lists
and per-skill names. Useful as a **transparency surface** — you can see
exactly which hooks the harness will fire on `PreToolUse`, `PostToolUse`,
`SessionStart`, etc.

**Measured time**: 38s (the verbose path enumerates every skill and hook
file; this is the slowest step in the walkthrough on a cold cache).

**Troubleshoot**: if it hangs >60s, the canonical skills directory has
too many entries — check for stale symlinks under `.claude/skills/`.

---

### Step 6 — See a hook fire (≤ 1 min)

This is the heart of the demo. Four real hooks are invoked with crafted
payloads — no live Claude API calls, no network.

```bash
bash scripts/demo-governance.sh
```

**Expected output (verbatim, last 8 lines of transcript)**:

```
  [OK] trust-score-validator warned — no trust report
  [OK] destructive-git-blocker blocked: git reset --hard HEAD~5 (exit 2)
  [OK] trust-score-validator logged warning — no score in output
  [OK] agent-quota-advisor emitted advisory (pressure ~96%)
  [OK] Fabrication block          — trust-score-validator warned — no trust report
  [OK] Destructive git            — destructive-git-blocker blocked: git reset --hard HEAD~5 (exit 2)
  [OK] Missing trust report       — trust-score-validator logged warning — no score in output
  [OK] Quota advisory             — agent-quota-advisor emitted advisory (pressure ~96%)
```

**Measured time**: 6s. **All 4 governance checks fired and blocked the
expected payload.**

**Troubleshoot**:
- Any `[FAIL]` line means a hook script changed its interface — open the
  named hook in `hooks/` and compare to the payload in
  `scripts/demo-governance.sh`.
- If you get `python3: command not found`, install Python 3.10+.

---

### Step 7 — Dry-run a destructive flow (≤ 1 min)

History-sanitization is the most invasive thing the OS ships. The smoke
test runs without execution and reports what *would* happen:

```bash
DRY_RUN=true bash scripts/cos-history-sanitization-smoke.sh
```

**Expected output (verbatim)**:

```
[smoke] WARN: no sanitization env vars are set; skipping token scan.
[smoke] WARN: discovered 11 value_env entries in manifest:
  - COS_HISTORY_SANITIZE_OPERATOR_EMAIL
  - COS_HISTORY_SANITIZE_HOME_PREFIX
  - COS_HISTORY_SANITIZE_REPO_PATH
  ...
[smoke] PASS (skip-with-warning)
```

**Measured time**: <1s.

**Why this matters**: the smoke test is what gates a real sanitization
run. Seeing `PASS (skip-with-warning)` means the safety check is
operative — the script will NOT run a destructive `git filter-repo` until
you provide explicit env vars matching the manifest.

**Troubleshoot**:
- `git-filter-repo: command not found` (only relevant for `--execute`):
  `brew install git-filter-repo` on macOS, or
  `pip install git-filter-repo`.

---

### Step 8 — Read CONTRIBUTING and CHANGELOG (≤ 1 min)

Two short reads. Both files exist at the repo root.

```bash
less CONTRIBUTING.md   # how to file a PR; license note
less CHANGELOG.md      # what shipped in 0.1.x
```

No expected output — these are reference reads for follow-up.

---

### Step 9 — Where to go next

Pick the path that matches your goal:

| Goal | File |
|------|------|
| Detailed setup, dependency matrix | [`docs/00-MOCs/entrypoints/getting-started.md`](../getting-started.md) |
| Migrating from stock Claude Code | [`docs/08-References/migration-from/from-vanilla-claude-code.md`](../migration-from/from-vanilla-claude-code.md) |
| Architecture decisions | [`docs/02-Decisions/adrs/`](../adrs/) (start with ADR-001, ADR-093, ADR-131) |
| All the demo paths | [`docs/09-Quality/manual-tests/proof-paths.md`](../manual-tests/proof-paths.md) |
| Why-not-X comparison | [`docs/08-References/root/vs-alternatives.md`](../vs-alternatives.md) |
| Public-readiness audit | [`docs/09-Quality/legal/pre-public-readiness-checklist.md`](../legal/pre-public-readiness-checklist.md) |

---

## Total measured time

Steps 4-7 captured live: **52 seconds**, dominated by step 5 (verbose
enumeration). Adding generous estimates for the read-only steps (1-3,
8-9) brings the realistic floor to **~5-7 minutes** for a careful
operator and **<10 minutes** for a hostile auditor who reads every
section in passing.

| Step | Measured | Estimated |
|------|---------:|----------:|
| 1 — clone | — | 30s |
| 2 — read README | — | 60s |
| 3 — install (optional) | — | 90s |
| 4 — cos-status | 6s | — |
| 5 — verbose status | 38s | — |
| 6 — demo-governance | 6s | — |
| 7 — dry-run | <1s | — |
| 8 — read CONTRIBUTING/CHANGELOG | — | 60s |
| 9 — next-steps scan | — | 30s |
| **Total** | — | **~7 min** |

---

## Common failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| `python3: command not found` (step 6) | Python missing | Install Python 3.10+ |
| `Health: FAIL` (step 4) | `.cognitive-os/` partial | Re-run `install.sh` |
| `git-filter-repo: command not found` (step 7 with `--execute`) | dep missing | `brew install git-filter-repo` |
| `Rules: 0 source` (step 4) | fresh clone, no install | Expected; rules project in on install |
| `[FAIL]` in demo-governance (step 6) | hook drift | Diff the named hook against the demo payload |
| Step 5 hangs >60s | stale skill symlinks | `ls -la .claude/skills/` and prune broken links |

---

## Where to ask questions

- `CONTRIBUTING.md` lists the expected channel.
- For audit reproducibility issues, file an issue with the command output
  snippets copied into this walkthrough, not with raw local terminal logs.

## Asciicast

Asciicast / screencast pending for public-release cut. Operator records the live flow once the
public URL goes live. A local terminal transcript was used only to distill the public-safe
command snippets above; raw transcript logs are local-only because they can contain operator
usernames, absolute paths, and machine-specific metadata.
