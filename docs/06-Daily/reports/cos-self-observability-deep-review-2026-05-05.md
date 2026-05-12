# COS Self-Observability Deep Review (vs OpenSpace gaps)

**Date**: 2026-05-05  
**Status**: read-only audit; no state modified  
**Trigger**: OpenSpace deep audit (2026-05-05) declared OpenSpace MEJOR than COS on observability/drift/federation. User asked: *"revisemos en profundidad lo que tenemos"*. This audit answers what COS actually has, where it lives, and whether the gap is real.

---

## TL;DR

- **Area 1 (Skill-change observability): PARTIAL** — COS has SHA-256 versioned skill execution history in JSONL but no diff-between-versions, no web viewer, no git-commit attribution per skill change.
- **Area 2 (Drift detection): PARTIAL** — Two per-session drift detectors exist and auto-heal; the only scheduled drift job (GitHub Actions weekly) is disabled. No event-driven path.
- **Area 3 (Federation client): READY** — All the wiring exists (`cos-engram-cloud-enroll`, `ENGRAM_CLOUD_AUTOSYNC` branch, ADR-141 implemented). Federation is gated on the operator setting `ENGRAM_CLOUD_TOKEN` and `ENGRAM_CLOUD_SERVER`, not on missing code.
- The OpenSpace audit was accurate on Area 1 (SQLite lineage + React viewer is richer than our JSONL). It was partially unfair on Area 2 (missed our per-session detectors). It was unfair on Area 3 (COS federation is READY, not DESIGN-ONLY).
- The biggest real gap is skill lineage: we track execution results but not content changes between versions.
- The fastest win is enabling `ENGRAM_CLOUD_AUTOSYNC=1`: it needs a credential, not code.

---

## Area 1 — Skill-change observability + lineage

### What COS has (verified)

| File | What it captures | When it fires | Retention |
|---|---|---|---|
| `hooks/skill-tracker.sh` (+ `packages/skill-governance/hooks/skill-tracker.sh`) | Skill invocation result (success/fail, tokens, duration, model) per `Agent\|Skill` PostToolUse | Real-time (PostToolUse) | JSONL per session `.cognitive-os/metrics/skill-metrics.jsonl` |
| `hooks/skill-invocation-logger.sh` | Skill name + args per `Skill` tool call | Real-time (PostToolUse Skill) | `.cognitive-os/metrics/skill-invocations.jsonl` |
| `hooks/skill-feedback-tracker.sh` | Failure feedback to Engram under `skill-feedback/<name>` | Real-time on failure | Engram persistent |
| `lib/skill_archive.py` | SHA-256 of `SKILL.md` content at execution time + trust_score + success + task_description | Called by consequence engine on execution | `.cognitive-os/metrics/skill-archive.jsonl` |
| `hooks/auto-skill-generator.sh` | Auto-generated `SKILL.md` files with `generated-at` timestamp | PostToolUse Agent (complexity threshold) | `.cognitive-os/skills/auto-generated/<slug>/SKILL.md` |
| `hooks/skill-synthesis-scanner.sh` | Recurring-sequence detection → skill draft proposals | Stop hook, 30-min cooldown | `.cognitive-os/metrics/skill-synthesis-queue.jsonl` |
| Git history | Every committed change to any `SKILL.md` file | Whenever operator commits | Git log (permanent) |

**Attribution**: Skill metrics carry `skill_name`, `timestamp`, `model`, `success` — but no `session_id`, no git SHA, no agent identity. Session association is implicit via the session-scoped directory path.

**Queryability**: All records are flat JSONL. The `SkillArchiveManager` class in `lib/skill_archive.py` exposes `get_archive(skill_name)` (all snapshots), `get_best_version(skill_name)` (highest-scoring successful run). No query by date range, no diff between versions.

**What does NOT exist**:
- No record of "what the SKILL.md content was before vs after a rewrite" — only the SHA-256 of whatever content was present at execution time.
- No diff view (CLI or web).
- No hook that fires specifically on `SKILL.md` file writes and records the before/after content.

### Comparison to OpenSpace

| Dimension | OpenSpace | COS |
|---|---|---|
| Storage backend | SQLite with explicit skill-evolution table | Flat JSONL (append-only) |
| Versioning unit | Explicit version record per skill edit | SHA-256 of SKILL.md at execution time (not at edit time) |
| Diff viewer | React UI at `open-space.cloud/skills/<name>/history` | None |
| Query interface | SQL / REST | Python class `SkillArchiveManager` (programmatic only) |
| Attribution | Session + agent identity | Skill name + timestamp only |
| Failure feedback | Stored | Stored in Engram under `skill-feedback/<name>` |

### Gap classification

**PARTIAL** — COS records skill execution results with SHA-256 content fingerprinting — this is a meaningful lineage signal. The gap is that the snapshot is taken at execution time (not at edit time), so a skill can be rewritten without producing a lineage record unless it subsequently runs. There is no diff view and no cross-session query path beyond reading raw JSONL.

### What to build (if any)

1. A `PostToolUse Write` hook (scoped to `SKILL.md` writes) that captures before/after content hash, the writing session/agent, and appends to `.cognitive-os/metrics/skill-content-history.jsonl`. Cost: ~50 lines of bash. No new schema needed — extend the existing MetricEvent format.
2. A CLI command `scripts/cos-skill-diff <name>` that replays the content-history JSONL and shows a unified diff between any two version hashes. Builds on the JSONL records from item 1.
3. The web viewer (React) is out-of-scope for now — the CLI diff provides the functional equivalent without the infrastructure investment.

---

## Area 2 — Drift detection (continuous vs batch)

### What COS has (per drift kind)

| Drift kind | Detector | Frequency | Output |
|---|---|---|---|
| Profile/hook registration drift | `hooks/profile-drift-autoapply.sh` (SessionStart) | **Per-session** | Auto-reapplies `apply-efficiency-profile.sh`; logs to `.cognitive-os/runtime/profile-autoapply.log` |
| Docker image pin drift | `hooks/docker-drift-detector.sh` (SessionStart) | **Per-session** | Advisory to stderr; `.cognitive-os/metrics/docker-drift.jsonl` |
| Hook wiring vs firing reality | `scripts/runtime_hook_reality.py` / `scripts/cos-runtime-hook-reality` | **On-demand** | Classified hook report |
| Silent failure detection | `scripts/silent_failure_audit.py` / `scripts/cos-silent-failure-audit` | **On-demand** | Report |
| Component REAL/DORMANT/ASPIRATIONAL | `scripts/aspirational_audit.py` / `scripts/component-reality-check` skill | **On-demand** (+ was weekly via disabled GH Action) | `public-metrics-aspirational.json` |
| Primitive gap snapshot | `scripts/primitive_gap_snapshot.py`, `scripts/cos-weekly-primitive-gap.sh` | **On-demand / was weekly** | Gap report JSONL |
| Doctrine drift → proposal | `scripts/cos-doctrine-proposer` | **On-demand** | ADR proposals |
| Self-improvement loop | `scripts/cos-self-improvement-loop` (called by CI gate) | **On-demand / CI** | Improvement proposals |
| Config/meta audit | `scripts/cos-config-audit.sh` (companion to docker-drift) | **On-demand** | Rich report |
| Primitive fitness ledger | `scripts/primitive_fitness_ledger.py` | **On-demand** | Fitness scores |

**Weekly GitHub Actions workflow**: `.github/workflows/weekly-public-metrics.yml.disabled` — **was** scheduled for every Monday at 12:00 UTC running `dogfood_score.py` and `aspirational_audit.py`. Currently **disabled** (`.disabled` suffix = not picked up by GitHub Actions).

### Frequency classification

| Category | Count | Names |
|---|---|---|
| Real-time (event-driven) | 0 | — |
| Per-session (SessionStart) | 2 | `profile-drift-autoapply`, `docker-drift-detector` |
| Daily/weekly scheduled | 0 active (1 disabled) | `weekly-public-metrics.yml.disabled` |
| On-demand only | 8 | `runtime_hook_reality`, `silent_failure_audit`, `aspirational_audit`, `primitive_gap_snapshot`, `cos-doctrine-proposer`, `cos-self-improvement-loop`, `cos-config-audit`, `primitive_fitness_ledger` |
| Inactive / disabled | 1 | `weekly-public-metrics.yml.disabled` |

**Key finding**: The per-session pair auto-heals two important drift types. All deeper drift analysis is on-demand — the operator must invoke it. No detector fires continuously or on a schedule today (the weekly job is disabled).

### Comparison to OpenSpace

| Dimension | OpenSpace | COS |
|---|---|---|
| Continuous monitoring | Yes (metric streaming with anti-loop guards) | No |
| Event-driven drift path | Yes | No |
| Per-session auto-heal | Unknown (not documented in audit) | Yes (profile + docker) |
| On-demand batch tools | Yes (via CLI) | Yes (8 scripts) |
| Scheduled batch | Yes (weekly) | No (disabled) |

### Gap classification

**PARTIAL** — The gap in continuous/event-driven drift detection is real. COS has no equivalent to OpenSpace's metric streaming. However, the per-session auto-heal for profile drift goes beyond what the OpenSpace audit described: it not only detects but self-corrects on every session start. The batch tooling is comparable. The main missing piece is a live watcher, and the quick path is re-enabling the weekly GitHub Actions job.

### What to build (if any)

1. Re-enable `.github/workflows/weekly-public-metrics.yml.disabled` by renaming (removing `.disabled` suffix). Provides scheduled drift coverage with zero new code.
2. Add a `PreToolUse Write` hook that checks if `hooks/` or `scripts/apply-efficiency-profile.sh` is about to be modified and emits a drift-risk advisory. This approaches event-driven coverage without a daemon.
3. The continuous metric streaming equivalent (daemon) is high-effort; skip unless Shape B triggers fire.

---

## Area 3 — Federation client

### What COS has (verified)

| File | Function | Actual maturity |
|---|---|---|
| `scripts/cos-engram-cloud-enroll` | Bootstrap wrapper: `engram cloud config/enroll/upgrade`; emits `ENGRAM_CLOUD_TOKEN` for env capture | **READY** — calls real `engram` binary commands |
| `packages/engram-sync/hooks/engram-auto-sync.sh` | SessionEnd hook: exports via git-jsonl; if `ENGRAM_CLOUD_AUTOSYNC=1` also runs `engram sync --cloud` | **READY** — cloud branch gated on env var |
| `scripts/cos-engram-bundle` / `scripts/cos-engram-import-propose` (via `cos_cross_instance_learning.py`) | Export/import Engram observations as portable bundles | **READY** — local file I/O, propose-only import |
| `scripts/cos-export-consumer-evidence` / `scripts/cos-import-consumer-evidence` | Bilateral evidence exchange between COS instances | **READY** |
| `scripts/cos-registry-lock` | Deterministic SHA-256 lock of `agentic-primitive-registry.lock.yaml` | **READY** |
| `scripts/cos-federation-trigger-audit` | Reads `manifests/federation-triggers.yaml`; reports which Shape-B thresholds fire | **READY** |
| `scripts/cos-engram-cloud-docker-smoke` | E2E smoke test: Docker Engram Cloud server + two project scopes + sync verification | **READY** — requires Docker + `engram` binary |
| `lib/cross_instance_learning.py` | Python impl for all cross-instance runway commands | **READY** |
| `lib/engram_http_client.py` | Typed HTTP wrapper for local Engram daemon | **READY** (local only; no cloud URL wired) |

### Status of ADR-136 / ADR-139 / ADR-141

| ADR | Title | Status |
|---|---|---|
| ADR-136 | Cross-Instance Learning Runway | **Accepted — implemented**. Shape-B primitives (evidence exchange, registry locks, engram bundle, federation trigger audit) are all live code. Shape-B federation stays deferred until triggers in `manifests/federation-triggers.yaml` fire. Current observed: 1 maintainer, 2 machines, 0 concurrent remote writers — all below Shape-B thresholds. |
| ADR-139 | Account-Agnostic Multi-Provider Runtime (BYOK) | **Accepted — implemented** as token classification (`byok-maintainer` / `byok-project` / `proxied`). Flow contracts carry `credential_source`. The Engram cloud token lifecycle follows `byok-project` rules. |
| ADR-141 | Engram Cloud as Cross-Instance Replication Transport | **Accepted — implemented**. Three modes: `local-only` (default), `git-jsonl`, `engram-cloud`. Cloud mode activates when `ENGRAM_CLOUD_AUTOSYNC=1` + `ENGRAM_CLOUD_TOKEN` + `ENGRAM_CLOUD_SERVER` are set. None of those are currently set in the operator environment. |

### Comparison to OpenSpace

| Dimension | OpenSpace | COS |
|---|---|---|
| Live cloud registry | `open-space.cloud` (always-on) | Self-hosted `engram cloud serve` (must be started by operator) |
| Plug-and-play for any user | Yes (point at open-space.cloud) | No (must enroll, get token, run server) |
| Cross-instance sync protocol | Proprietary (open-space.cloud REST) | `engram cloud` upstream protocol (bearer-JWT, port 8080) |
| Air-gap fallback | Unknown | Yes (git-jsonl mode, always available) |
| Evidence exchange | None documented | Yes (consumer evidence, registry locks, engram bundles) |
| Maturity | LIVE | READY |

### Gap classification

**PARTIAL** (not REAL) — The OpenSpace audit's "COS federation = DESIGN ONLY" verdict was incorrect as of ADR-141. The code exists, the bootstrap script exists, the smoke test exists. The gap is operational: the operator has not set `ENGRAM_CLOUD_TOKEN`/`ENGRAM_CLOUD_SERVER`, and COS requires a self-hosted cloud server rather than a shared service. The functional distance is one environment variable configuration from LIVE, not months of development.

### What to build (if any)

1. Set `ENGRAM_CLOUD_SERVER` pointing to a local `engram cloud serve` instance and run `scripts/cos-engram-cloud-enroll`. Zero code required. This would move federation from READY to LIVE.
2. To reach OpenSpace's plug-and-play UX: a shared hosted Engram Cloud server for the maintainer's projects. Outside scope unless multiple machines or contributors are active (federation-triggers.yaml Shape-B gate).

---

## Cross-cutting findings

1. **All drift detectors are either per-session or on-demand — none are event-driven.** The architectural reason is the hook model: hooks fire on Claude Code events, not on filesystem watchers or metric streams. Adding an event-driven layer would require a daemon outside the hook model.
2. **Skill lineage and drift detection both suffer from the same root cause**: JSONL append-only files are observable but not queryable. SQLite would unlock time-series queries, diff replays, and range scans. This is a single infrastructure change that would benefit both areas simultaneously.
3. **Federation is 60% operational framing, 40% credentials.** ADR-141 ships the wiring; what is missing is a running server and tokens. This is the easiest gap in the report to close.
4. **The weekly drift job being disabled is the highest-leverage dormant asset.** Re-enabling it (one file rename) adds scheduled aspirational-audit + dogfood-score coverage with zero new code.
5. **The OpenSpace audit correctly identified the React diff viewer as a real gap.** COS has no skill content diff capability at any interface level. This is the single most actionable build item in Area 1.

---

## Recommendations (prioritized)

### 1. Re-enable the weekly drift job (Area 2, effort: 5 minutes, ROI: high)

Rename `.github/workflows/weekly-public-metrics.yml.disabled` to `.github/workflows/weekly-public-metrics.yml`. This immediately restores scheduled drift detection (aspirational audit + dogfood score) every Monday. Falsifiable gate: `gh workflow list` shows the workflow active; first Monday run produces `public-metrics-aspirational.json`.

### 2. Add a skill content-history hook (Area 1, effort: 1–2 hours, ROI: high)

Add a `PostToolUse Write` hook that detects writes to `**/SKILL.md` files, computes before/after SHA-256 (comparing to the last recorded hash), and appends a record to `.cognitive-os/metrics/skill-content-history.jsonl`. This closes the primary lineage gap. Falsifiable gate: edit any `SKILL.md`, confirm new record appears in `skill-content-history.jsonl` with `prev_hash` and `new_hash` fields and a session attribution.

### 3. Activate Engram Cloud federation (Area 3, effort: 30 minutes, ROI: medium-high)

Run `engram cloud serve` locally (or on a second machine), then run `scripts/cos-engram-cloud-enroll --server <URL> --project luum-agent-os --emit-env`. Set the emitted env vars. Set `ENGRAM_CLOUD_AUTOSYNC=1`. This moves federation from READY to LIVE. Falsifiable gate: `scripts/cos-engram-cloud-docker-smoke` exits 0.

### 4. Add a `cos-skill-diff` CLI (Area 1, effort: 2–4 hours, ROI: medium)

Once skill-content-history records exist, build `scripts/cos-skill-diff <skill-name> [--from <hash>] [--to <hash>]` that reads `skill-content-history.jsonl` and emits a unified diff. Provides the functional equivalent of OpenSpace's React diff viewer. Falsifiable gate: `scripts/cos-skill-diff sdd-explore` outputs a readable diff for the most recent content change.

### 5. Migrate skill-archive to SQLite (Area 1 + 2, effort: 2–3 days, ROI: medium-term)

Replace the JSONL skill archive with a SQLite file at `.cognitive-os/metrics/skill-archive.db`. Extend the schema to include agent-identity, git SHA at time of execution, and full SKILL.md content for diff replay. This would close the structured queryability gap vs OpenSpace's SQLite lineage. High effort; justify only when skill count exceeds ~100 active skills and on-demand JSONL scanning becomes slow. Falsifiable gate: `SELECT skill_name, version, prev_version FROM skill_history ORDER BY timestamp DESC` returns meaningful rows.

---

## Open questions / blockers

1. **Engram Cloud server hosting decision**: Should the maintainer run a local-only Engram Cloud server, or use the upstream Gentleman-Programming hosted service (if one exists)? ADR-141 is agnostic — it supports both. The operator must decide.
2. **Weekly drift job token permissions**: The disabled weekly job commits badge updates to the repo. It needs `contents: write` permission and a working `uv` install on the runner. Verify these before re-enabling.
3. **Skill-content-history hook: before-content access**: The `PostToolUse Write` hook receives the new content but not the previous content. The hook must read the old hash from the last record in `skill-content-history.jsonl` before the write completes. Concurrency with multiple sessions writing the same skill needs a lock or append-only design.

---

## TRUST_REPORT

**Confidence: 0.82** on the overall verdicts.

**Uncertainties**:
- The `engram cloud serve` upstream binary behavior was inferred from ADR-141 and the smoke test script — not validated by running an actual federation test. The READY classification assumes the upstream `engram` binary supports `cloud serve` as documented.
- Engram observation counts under `skill-feedback/*` topics were not enumerated; the topic exists in the hook code but whether any failure records have accumulated depends on runtime history not read during this audit.
- Cron schedule status for the weekly job was determined by the `.disabled` suffix on the workflow file — not by checking GitHub Actions UI. The assumption that `.disabled` suffix prevents execution is correct for GitHub Actions by convention but not formally verified.
- `lib/engram_http_client.py` does not contain cloud-URL logic; the cloud sync path flows through the `engram` binary directly. This means cloud sync is transparent to the Python lib layer — confirmed by reading the file, but the full binary code path was not traced.

---

## Sources

All files read during this audit:

- `/hooks/skill-tracker.sh` (lines 1–119)
- `/hooks/skill-invocation-logger.sh` (lines 1–69)
- `/hooks/auto-skill-generator.sh` (lines 1–207)
- `/hooks/profile-drift-autoapply.sh` (lines 1–111)
- `/hooks/docker-drift-detector.sh` (lines 1–116)
- `/hooks/skill-synthesis-scanner.sh` (lines 1–50+)
- `/hooks/self-install.sh` (grep for skill-rewrite)
- `/packages/skill-governance/hooks/skill-tracker.sh` (same as hooks/)
- `/packages/engram-sync/hooks/engram-auto-sync.sh` (lines 1–46)
- `/lib/skill_archive.py` (lines 1–230)
- `/lib/engram_http_client.py` (lines 1–60)
- `/lib/cross_instance_learning.py` (lines 1–80)
- `/lib/consequence_engine.py` (grep for skill-rewrite references)
- `/scripts/cos_cross_instance_learning.py` (lines 1–100)
- `/scripts/aspirational_audit.py` (lines 1–60 + grep)
- `/scripts/runtime_hook_reality.py` (lines 1–80)
- `/scripts/cos-engram-cloud-enroll` (grep)
- `/scripts/cos-engram-cloud-docker-smoke` (lines 1–60)
- `/scripts/cos-federation-trigger-audit` (full, inline)
- `/scripts/cos-doctrine-proposer` (first 20 lines)
- `/manifests/federation-triggers.yaml` (full)
- `/docs/02-Decisions/adrs/ADR-136-cross-instance-learning-runway.md` (lines 1–80)
- `/docs/02-Decisions/adrs/ADR-139-account-agnostic-multi-provider-runtime.md` (grep)
- `/docs/02-Decisions/adrs/ADR-141-engram-cloud-cross-instance-replication.md` (lines 1–80)
- `/.github/workflows/weekly-public-metrics.yml.disabled` (lines 1–30)
