# Phoenix Migration Plan — Langfuse → Arize Phoenix

> Canonical ADR: `docs/adrs/ADR-058-observability-migration-langfuse-to-phoenix.md`
> Created: 2026-04-24
> Owner column values: `operator` = human maintainer (decision-making + ops).
> Status values: `pending` | `in-progress` | `done` | `blocked`.

## Context

Langfuse was running as a 6-container stack (~1.34 GiB idle RAM, ~1380 % CPU
aggregate) despite being declared `disabled` in `cognitive-os.yaml`. Root
cause: no profile gate on the compose services. Decision (ADR-058):
deprecate Langfuse, adopt Arize Phoenix (`mode: pip`, no Docker).

## Phase checklist

### Phase 0 — Immediate stop-the-bleeding (2026-04-24) — DONE

| # | Task | Owner | Status | Dependency | Exit criterion |
|---|------|-------|--------|------------|----------------|
| 0.1 | Stop all 6 `cognitive-os-langfuse-*` containers | operator | done | — | `docker ps --filter name=cognitive-os-langfuse` empty |
| 0.2 | Write ADR-058 | operator | done | — | `docs/adrs/ADR-058-observability-migration-langfuse-to-phoenix.md` exists |
| 0.3 | Update `infrastructure-service-catalog.md` (Langfuse deprecated, Phoenix added, decision log) | operator | done | 0.2 | Langfuse row reads `Deprecated (phase 2 removal) — see ADR-058`; phoenix row present |
| 0.4 | Update `cognitive-os.yaml` (Langfuse `status: deprecated`, new `phoenix:` entry) | operator | done | 0.2 | `grep "phoenix:" cognitive-os.yaml` matches; langfuse has `status: deprecated` |
| 0.5 | Append §Decision to `observability-backend-evaluation-2026-04-24.md` | operator | done | 0.2 | §Decision heading present at end of doc |
| 0.6 | Create this plan file | operator | done | — | file exists |
| 0.7 | Verify sunset-policy test still passes | operator | done | 0.4 | `uv run pytest tests/contracts/test_service_sunset_policy.py` passes |

### Phase 1 — Adopt Phoenix (target 2026-05-15)

| # | Task | Owner | Status | Dependency | Exit criterion |
|---|------|-------|--------|------------|----------------|
| 1.1 | Add `arize-phoenix>=7.0` + `opentelemetry-exporter-otlp` to `pyproject.toml` under `[project.optional-dependencies].observability` | operator | pending | 0.* | `uv pip install -e '.[observability]'` succeeds; `python -c "import phoenix"` works |
| 1.2 | Author `skills/phoenix-trace-ui/SKILL.md` (launches `phoenix serve` on-demand) | operator | pending | 1.1 | Skill invocable via `/phoenix-trace-ui`; UI reachable at `localhost:6006` |
| 1.3 | Smoke test: send a manual OTel span, confirm it appears in Phoenix UI | operator | pending | 1.2 | Span visible in UI within 5 s of emission |
| 1.4 | Feature-coverage check vs Langfuse: prompts playground + evaluations | operator | pending | 1.2 | Checklist doc noting which Langfuse features Phoenix covers, gaps flagged |

### Phase 2 — Migrate trace sink (target 2026-05-30)

| # | Task | Owner | Status | Dependency | Exit criterion |
|---|------|-------|--------|------------|----------------|
| 2.1 | Refactor `lib/record_completion.py`: replace `_send_langfuse_trace` → `_send_phoenix_trace` (OTel OTLP) | operator | pending | 1.1, 1.3 | Langfuse import removed from `lib/`; Phoenix spans visible in UI from real completions |
| 2.2 | Update `tests/unit/test_record_completion.py` to mock OTel exporter | operator | pending | 2.1 | Unit test suite passes; coverage of completion-trace path maintained |
| 2.3 | Preserve graceful no-op when Phoenix endpoint absent (try/except) | operator | pending | 2.1 | `COS_PHOENIX_ENABLE=0` or no endpoint → no exception, completion still recorded to JSONL |
| 2.4 | Run `uv run pytest tests/` full suite once | operator | pending | 2.2 | 0 failures |
| 2.5 | Add `tests/integration/test_record_completion_sends_trace_to_phoenix.py` — e2e span round-trip against a live `phoenix serve` subprocess (no Docker). Skips cleanly when `arize-phoenix` not installed. | operator | done (2026-04-24) | 2.1 | File exists; `uv run pytest tests/integration/test_record_completion_sends_trace_to_phoenix.py -v` passes with phoenix installed, skips without. Legacy Langfuse e2e tests removed from `test_e2e_flows.py`. |

### Phase 3 — Remove Langfuse from Compose (target 2026-06-15)

| # | Task | Owner | Status | Dependency | Exit criterion |
|---|------|-------|--------|------------|----------------|
| 3.1 | Delete the 6 `langfuse-*` services from `docker-compose.cognitive-os.yml` | operator | pending | Phase 2 complete | `grep -c "^  langfuse" docker-compose.cognitive-os.yml` = 0 |
| 3.2 | Delete `scripts/setup-langfuse.sh` | operator | pending | 3.1 | file absent |
| 3.3 | Remove Langfuse references from `hooks/infra-health.sh`, `hooks/cognitive-os-health.sh`, `hooks/valkey-ensure.sh` | operator | pending | 3.1 | `grep -riE 'langfuse' hooks/` returns 0 |
| 3.4 | Remove Langfuse entry from `tests/integration/test_service_health.py::SERVICE_CONTRACTS` | operator | pending | 3.1 | Test suite still passes; Phoenix not added to SERVICE_CONTRACTS (pip-mode, no compose) |
| 3.5 | Leave historical note in catalog ("removed in Phase 3, see ADR-058") | operator | pending | 3.3 | Catalog references ADR-058 |

### Phase 4 — Final cleanup (target 2026-06-30)

| # | Task | Owner | Status | Dependency | Exit criterion |
|---|------|-------|--------|------------|----------------|
| 4.1 | `docker volume rm $(docker volume ls -q --filter name=langfuse)` | operator | pending | Phase 3 complete + 30-day stability | No `langfuse*` volumes remain |
| 4.2 | Remove `langfuse` entry entirely from `cognitive-os.yaml` services block | operator | pending | 4.1 | `grep langfuse cognitive-os.yaml` returns 0 |
| 4.3 | Update ADR-058 status to `Implemented` + outcome addendum | operator | pending | 4.2 | ADR-058 shows `Status: Implemented` |

## Rollback triggers (Phase 2+)

If any of these fire within 30 days of Phase 2 cutover:

- Phoenix crashes >1/day on operator workstation
- OTel export drops >5 % of completion spans
- Phoenix UI missing a critical feature discovered post-cutover

Then: `git revert` Phase 2 commit, `docker start` preserved Langfuse
containers, remove `status: deprecated` from Langfuse entry. Volumes
available through Phase 4 (2026-06-30); after that, rollback requires
re-running the historical `scripts/setup-langfuse.sh` manually.

## Cross-references

- ADR-058 — canonical decision and rationale
- ADR-034 — predecessor observability backend selection (now partially superseded)
- `docs/architecture/observability-backend-evaluation-2026-04-24.md` §Decision (2026-04-24 pin)
- `docs/architecture/infrastructure-service-catalog.md` — services table + decision logs
