# Paperclip Integration Audit — 2026-05-05

**Auditor:** Claude Sonnet 4.6 (read-only audit, sub-agent)
**Date:** 2026-05-05
**Trigger:** Decision pending — complete Paperclip integration vs resurrect abandoned `dashboard/`. Doctrine (ADR-133, ADR-148, ADR-149, `cognitive-prosthesis.md`) requires evidence-based promotion before duplicating UI surface. The 2026-03-27 decision in `docs/paperclip-integration.md` declared the dashboard deprecated in favour of Paperclip; this audit verifies whether that decision still holds.
**Reference docs:** [`docs/paperclip-integration.md`](../paperclip-integration.md), [ADR-043](../adrs/ADR-043-paperclip-local-daemon.md).

## Documented vision (the 8 mappings)

The architecture diagram in `docs/paperclip-integration.md` enumerates eight mappings from Cognitive OS sources to Paperclip targets:

| # | COS Source | Paperclip Target |
|---|-----------|-----------------|
| 1 | SDD pipeline | `projects` + `issues` |
| 2 | Agent Bus | agent heartbeats |
| 3 | Metrics JSONL | spend tracking |
| 4 | Squads YAML | org chart |
| 5 | cos packages | skills marketplace |
| 6 | Singularity events | inbox |
| 7 | Safety mesh blocks | blocked status |
| 8 | Error recovery | retry queue |

The doc's "Wired" sub-table uses gap numbers 1–8 mapping to a slightly different surface (SDD/heartbeat/singularity/squads/safety/tasks/cost/retry-queue). Mapping #5 (cos packages → skills marketplace) appears in the architecture diagram but **not** in the wiring table — it is extra claimed scope without an implementation slot.

## Implementation inventory

| Path | Lines | Last modified |
|------|------:|---------------|
| `packages/ecosystem-tools/lib/paperclip_client.py` | 584 | active |
| `packages/paperclip-integration/hooks/paperclip-sync.sh` | 185 | 2026-04-20 |
| `packages/paperclip-integration/hooks/paperclip-sdd-sync.sh` | 119 | 2026-03-29 |
| `packages/paperclip-integration/hooks/paperclip-agent-status.sh` | 82 | 2026-04-20 |
| `packages/paperclip-integration/hooks/paperclip-cost-stream.sh` | 92 | 2026-04-20 |
| `packages/paperclip-integration/hooks/paperclip-squad-sync.sh` | 122 | 2026-04-20 |
| `packages/paperclip-integration/hooks/paperclip-task-sync.sh` | 68 | 2026-03-29 |
| `hooks/_lib/paperclip-notify.sh` | 148 | 2026-04-20 |
| `packages/paperclip-integration/cos-package.yaml` | 14 | 2026-04-20 |
| `packages/paperclip-integration/skills/paperclip-dashboard/SKILL.md` | present | — |
| `scripts/cos-paperclip-local.sh` | present | — |
| `infra/paperclip/init-config.sh` | 5 KB | 2026-03-29 |
| `tests/behavior/test_paperclip_integration_complete.py` | 235 | — |
| `tests/unit/test_paperclip_client.py` | present | — |
| `tests/integration/test_paperclip_local_daemon.py` | present | — |

**Symlink note:** `lib/paperclip_client.py` does not exist as a top-level path. The behavior tests inject `PROJECT_ROOT/lib` into `sys.path`; the import resolves at runtime through the symlink convention documented in `templates/project-gotchas.md`. 35 unit tests pass in 13.44s, confirming the resolution works.

## Mapping status table

| # | Mapping | Status | Evidence |
|---|---------|--------|----------|
| 1 | SDD pipeline → projects/issues | **PARTIAL** | `paperclip-sdd-sync.sh` (119L) present + executable; `test_hook_handles_empty_stdin` passes; **not registered** in `.claude/settings.json` PostToolUse Agent chain |
| 2 | Agent Bus → heartbeats | **PARTIAL** | `paperclip-agent-status.sh` (82L) executable; `test_paperclip_agent_status_hook_is_executable` passes; not registered in settings.json |
| 3 | Metrics JSONL → spend | **PARTIAL** | `paperclip-cost-stream.sh` (92L) referenced in `cognitive-os.yaml:446`; not in PostToolUse chain |
| 4 | Squads YAML → org chart | **PARTIAL** | `paperclip-squad-sync.sh` (122L) executable; `test_squad_sync_hook_is_executable` passes; not registered |
| 5 | cos packages → skills marketplace | **MISSING** | No `/api/skills` endpoint in client; no hook; no test; only present in the architecture ASCII diagram |
| 6 | Singularity events → inbox | **REAL** | `lib/singularity.py:_push_singularity_to_paperclip()` calls `client.push_notification()`; `test_singularity_calls_push_in_record_knowledge` and `test_push_function_uses_push_notification` pass; inline Python so settings.json wiring is irrelevant |
| 7 | Safety mesh blocks → blocked status | **REAL** | `hooks/claim-validator.sh:186-187` and `hooks/confidence-gate.sh:153-154` source `_lib/paperclip-notify.sh` and call `paperclip_notify()` on `exit 2`; **wired** in PreToolUse chain |
| 8 | Error recovery → retry queue | **REAL** | `_RetryQueue` class in `paperclip_client.py:41-81`; six tests pass: `test_retry_queue_enqueue_and_drain`, `test_retry_queue_bounded_at_100`, `test_client_queues_on_connection_failure`, `test_client_does_not_queue_health_checks` |

**Counts: REAL = 3 / 8, PARTIAL = 4 / 8, MISSING = 1 / 8.**

## Live smoke test results

```text
$ scripts/cos-paperclip-local.sh --status
[cos-paperclip-local] STOPPED      (exit 0 — daemon not running, no binary in PATH)

$ scripts/cos-paperclip-local.sh --help
Usage: cos-paperclip-local.sh [--start|--stop|--status]   (exit 0)

$ python3 -c "from packages.ecosystem_tools.lib import paperclip_client; ..."
PaperclipClient methods present:
  _request, create_issue, create_project,
  flush_retry_queue, is_available, push_cost_events,
  push_error_stats, push_kpis, push_metrics,
  push_notification, push_session_summary, push_spend,
  retry_queue_size, sync_org_chart,
  update_agent_status, update_issue_status

  No `push_skills` / `push_skills_marketplace` method  → mapping #5 confirmed MISSING.

$ python3 -m pytest tests/behavior/test_paperclip_integration_complete.py -q
15 passed in 0.29s

$ python3 -m pytest tests/unit/test_paperclip_client.py -q
35 passed in 13.44s

$ docker compose -f docker-compose.cognitive-os.yml config | grep -A1 paperclip
   paperclip-pg:  profiles: [legacy]
   paperclip:     profiles: [legacy]
   # Will not start without --profile legacy

$ grep -c "paperclip" .claude/settings.json
0     # Zero hook entries — none of the 5 package hooks are registered
```

**Runtime artefacts (none present):**

- `.cognitive-os/runtime/paperclip.port` — does not exist (daemon never started here)
- `metrics/.paperclip-cost-last-push` — does not exist (cost-stream hook never fired)

## Gap analysis: dashboard vs Paperclip

| Feature | `dashboard/` (abandoned 2026-03-29) | Paperclip (current state) | Assessment |
|---------|-------------------------------------|---------------------------|------------|
| Rules browser (list + path) | YES — `app/rules/page.tsx` reads `rules/*.md` | NO — no Paperclip mapping | Dashboard covers; Paperclip does not |
| Skills browser (list + description) | YES — `app/skills/page.tsx` reads `skills/*/SKILL.md` | MISSING (mapping #5) | Dashboard covers; Paperclip does not |
| Stat cards (rules/hooks/skills/packages count) | YES — `app/page.tsx` with 4 stat cards | NO | Dashboard covers; Paperclip does not |
| SDD project / issue tracking | NO | PARTIAL (hook unwired) | Paperclip covers once wired |
| Agent heartbeats | NO | PARTIAL (hook unwired) | Paperclip covers once wired |
| Spend tracking | NO | PARTIAL (hook unwired) | Paperclip covers once wired |
| Squad org chart | NO | PARTIAL (hook unwired) | Paperclip covers once wired |
| Singularity inbox | NO | REAL | Paperclip covers |
| Safety-mesh block status | NO | REAL | Paperclip covers |
| Retry queue resilience | NO | REAL | Paperclip covers |
| COS instance admin (lifecycle / phase) | PARTIAL (read-only of `cognitive-os.yaml`) | NO — Paperclip has no write-back to COS | Dashboard partial; Paperclip cannot cover |
| Demotion approvals / write-back | NO (not built) | NO by design (push-only, no webhooks) | Neither covers; gap documented in `paperclip-integration.md:100` |

**Critical finding.** Four of the eight documented mappings are PARTIAL only because the hooks are not registered in `.claude/settings.json`. The hook scripts are complete, executable, and pass their behavior tests, but they fire zero times per session as wired. The integration is delivering 3/8 of its documented value.

**Dashboard's unique territory.** The dashboard's `rules/`, `skills/`, and stat-card views read the local filesystem directly. Paperclip has no endpoint for primitive inventory and cannot receive these via REST push under the current architecture.

## Live UI test (Playwright) — blocked

A Playwright walkthrough of the Paperclip UI is **not currently viable**:

- Local daemon: STOPPED (no binary in PATH).
- Docker path: services `paperclip-pg` and `paperclip` are gated behind `profiles: [legacy]` and will not start without explicit `--profile legacy`.
- ADR-043 confirms the local-daemon path is preferred over Docker; the binary needs installation before the UI is reachable on `localhost:3200`.

**Two unblocking options before Playwright is meaningful:**

1. Install the Paperclip binary on the host and run `cos-paperclip-local.sh --start`.
2. Run `docker compose -f docker-compose.cognitive-os.yml --profile legacy up -d` to bring up the legacy stack (`paperclip-pg` + `paperclip`).

Either path takes 5–10 minutes. Until one of them runs, there is no UI to walk through.

## Recommendation

**Path B — bounded gap exists, but does not justify dashboard resurrection.**

The 2026-03-27 decision (Paperclip deprecates the dashboard) is **conditionally correct but not yet enacted**. The integration is architecturally sound and 3/8 mappings are live. The 4/8 PARTIAL mappings are a wiring problem, not a design problem: the hooks are written, tested, and ready — they just need entries in `.claude/settings.json`. Mapping #5 (skills marketplace) needs a `push_skills()` method and a hook.

The dashboard's unique territory (rules / skills / stat-card views over `cognitive-os.yaml` and the primitive inventory) is real but small. It can be addressed by extending Paperclip with one new mapping plus an `/api/skills` endpoint, or accepted as a residual gap covered in-session by the existing `paperclip-dashboard/SKILL.md`.

**Recommended order:**

1. **Wire the 4 unregistered hooks** in `scripts/apply-efficiency-profile.sh` (the source of `.claude/settings.json`). Estimated: 1–2 hours, no new features. Until this lands, the integration is operating at 37.5% of documented value.
2. **Decide mapping #5** (skills marketplace). If Paperclip's API supports a custom endpoint, add `push_skills()` + a hook; otherwise mark mapping #5 as deferred and remove it from the architecture diagram.
3. **Activate Paperclip locally** (binary or Docker `legacy` profile) and run a Playwright walkthrough of the resulting UI to verify the wired hooks deliver visible state.
4. **Formally demote `dashboard/`** with an ADR after step 3 confirms Paperclip covers the documented surface. Move `dashboard/` to `dashboard/.archived/` or delete with the ADR linking the rationale.
5. **Skip dashboard resurrection.** It is net-new surface area that competes with an integration that is 7/8 of the way to its documented vision.

## Falsifiable claim

If any of the following hold after the recommended path is enacted, the integration is broken and the dashboard decision must be revisited:

1. **Hook-dead signal.** Fourteen consecutive days of sessions in which no `paperclip-cost-stream`, `paperclip-agent-status`, `paperclip-sdd-sync`, or `paperclip-squad-sync` invocation appears in observable artefacts (`metrics/.paperclip-cost-last-push`, equivalent state files, or the session log).
2. **Daemon-absent signal.** Thirty consecutive days in which `.cognitive-os/runtime/paperclip.port` is never created and the Docker `legacy` profile is never activated. Either the daemon is unreachable or the integration is silently degraded.
3. **Mapping-5-frozen signal.** Three months without either implementing `push_skills()` or removing the skills-marketplace claim from the architecture diagram. The doc would be falsifying its own scope.

If none of the above conditions hold over a one-month window, the decision to keep `dashboard/` deprecated remains correct.

## Cross-references

- [`docs/paperclip-integration.md`](../paperclip-integration.md) — the 2026-03-27 architecture decision this audit verifies.
- [ADR-043](../adrs/ADR-043-paperclip-local-daemon.md) — local-daemon path.
- `packages/paperclip-integration/cos-package.yaml` — only exports `paperclip-sync.sh` (Stop event); the four other hooks are not exported.
- `packages/ecosystem-tools/lib/paperclip_client.py` — current REST client.
- `tests/behavior/test_paperclip_integration_complete.py` — 15 passing behavior tests.
- `tests/unit/test_paperclip_client.py` — 35 passing unit tests.
- `templates/project-gotchas.md` — documents the `lib/*.py` symlink convention used by this package.
