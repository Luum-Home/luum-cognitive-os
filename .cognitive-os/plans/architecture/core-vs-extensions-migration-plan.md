# Core vs Extensions Migration Plan — v0.14.0 → v1.0

> Companion to `core-vs-extensions-audit-2026-04-20.md`. Sequences the extraction from today's monolithic `hooks/` + `lib/` + `rules/` + `skills/` into `packages/cos-{name}/` waves, each shippable independently.

## Principles

1. **One pack per wave.** Each minor release moves exactly one extension pack to `packages/`. Smaller blast radius, easier rollback. Audit identified 15 packs → 15 waves minimum.
2. **Backwards-compat shim for one minor version.** When a hook moves from `hooks/x.sh` to `packages/cos-{pack}/hooks/x.sh`, leave a symlink at the old path for one release cycle (N→N+1). Remove in N+2. A pre-release grep test ensures no `hooks/<moved>.sh` references remain in source before the shim is removed.
3. **Profile as delegation point.** `scripts/apply-efficiency-profile.sh` becomes a dispatcher. It asks each enabled pack for its hook registrations (via `packages/*/cos-package.yaml` `hook_registrations:` key). The profile script merges them.
4. **Extensions opt-in.** A new `cognitive-os.yaml` key `extensions:` lists enabled packs. Default install enables: `cos-advisory-llm` (if API creds present), `cos-git-safety`, `cos-security-tools` (advisory only), `cos-observability` (if Langfuse/MLflow present). Everything else explicit.
5. **Zero new functionality.** This is pure extraction. Every test that passed at v0.13 passes at v1.0. If a refactor is needed to decouple, defer that refactor to a dedicated post-v1.0 PR.

## API contract — extension registration

### Package manifest schema addition

```yaml
# packages/cos-{pack}/cos-package.yaml
name: "@cos/{pack}"
version: "1.0.0"
cos_version: ">=0.14.0"
description: "…"

# NEW: hook registrations — consumed by apply-efficiency-profile.sh
hook_registrations:
  - event: SessionStart
    matcher: "*"
    script: "hooks/engram-auto-import.sh"
    profile: [default, full]    # which profiles include this hook
  - event: Stop
    matcher: "*"
    script: "hooks/engram-auto-sync.sh"
    profile: [default, full]
  - event: PreToolUse
    matcher: "Agent"
    script: "hooks/prompt-quality-llm.sh"
    profile: [full]              # LLM hooks stay opt-in
    requires_env: []
    skip_if_missing: true

# NEW: rule contributions
rule_contributions:
  - path: "rules/advisory-llm.md"
    trigger: always_active       # or: contextual
    compact_summary: "Haiku evaluates prompts/completions when API key present."

# NEW: skill contributions
skill_contributions:
  - path: "skills/advisor-consult/"
    tier: L3                     # tier label from CATALOG-COMPACT
```

### Dispatcher pattern in `apply-efficiency-profile.sh`

```bash
# Pseudocode — new section after CORE hook registration
for pack_yaml in packages/cos-*/cos-package.yaml; do
  pack_name=$(yaml_get "$pack_yaml" .name)
  pack_enabled=$(is_extension_enabled "$pack_name" "$PROFILE")
  [ "$pack_enabled" = "true" ] || continue
  yaml_each "$pack_yaml" .hook_registrations | while read reg; do
    # Merge into settings.json via hook_entry / hook_group helpers
    append_hook "$reg"
  done
done
```

This replaces hard-coded hook paths in the profile script with dynamic package discovery. No new file formats — YAML keys added to the existing package manifest.

### Backwards-compat shim

Symlink at old path, detected by wiring-check:

```
hooks/engram-auto-sync.sh -> ../packages/cos-memory-engram/hooks/engram-auto-sync.sh
```

`hooks/registration-check.sh` resolves symlinks before checking file presence. `scripts/check_hook_registration.py` logs a DEPRECATION warning whenever it sees a symlink. At v1.0+2, the `check-upstream-changes.sh` pipeline fails the build if any shim remains.

---

## Wave schedule

Each wave = one minor version, ~0.5–1 session of work (pure move + test).

| Wave | Version | Pack | Files moved | Risk | Notes |
|---|---|---|---|---|---|
| 1 | v0.14.0 | **cos-advisory-llm** | 3 hooks + 2 libs | LOW | POC in this session. Proves dispatcher pattern. |
| 2 | v0.14.1 | **cos-claude-code-integration** | 1 hook + 2 libs (recap, claude_usage_reader, claude_executor stays dual-home for now) | LOW | Claude-Code-specific per D43. |
| 3 | v0.15.0 | **cos-memory-engram** | 3 hooks + 5 libs | MED | engram-sync already wired; shim critical. |
| 4 | v0.15.1 | **cos-git-safety** | 4 hooks + 1 lib (pre-commit-gate.sh symlink stays in .githooks) | LOW | Pure move; destructive-blockers stay CORE. |
| 5 | v0.15.2 | **cos-security-tools** | 5 hooks + 4 libs + 5 install scripts | MED | Aguara/Parry/Semgrep/mcp-scan. Security profile redefined on top. |
| 7 | v0.16.1 | **cos-task-bridge** | 6 hooks + 3 libs | MED | External task system; double-check ADR-024 references. |
| 8 | v0.16.2 | **cos-infra-lifecycle** | 5 hooks + 2 libs | LOW | Docker-only. |
| 9 | v0.17.0 | **cos-agent-coordination** | 4 hooks + 4 libs | MED | Agent-bus migration; requires dual-home during transition. |
| 10 | v0.17.1 | **cos-auto-repair** | 4 hooks + 2 libs | LOW | Heavy but isolated. |
| 11 | v0.17.2 | **cos-skill-governance** | 5 hooks + 6 libs | MED | Touches skill lifecycle; requires dogfood test. |
| 12 | v0.18.0 | **cos-performance-intelligence** | 3 hooks + 7 libs | HIGH | MAPE-K loop; rollback plan mandatory. |
| 13 | v0.18.1 | **cos-scope-governance** | 6 hooks + 1 lib | LOW | Rules + hooks move together. |
| 14 | v0.18.2 | **cos-audit-trail** | 7 hooks + 2 libs | MED | Compliance-sensitive; keep shim for two minors instead of one. |
| 15 | v0.19.0 | **cos-verification-audit** | 7 hooks + 3 libs | MED | assumption-tracker, claim-validator, trust-score-validator all move. |
| 16 | v0.19.1 | **cos-context-optimization** | 3 hooks + 6 libs | MED | Token-economy-adjacent but not CORE. |
| 17 | v0.19.2 | **cos-sdd** | ~30 skills + 2 libs + 0 hooks | LOW | Biggest skill pack; pure skill move. |
| 18 | v0.19.3 | **cos-ecosystem-integrations** | per-tool split | LOW | Last sweep: e2b, tero, parry, repomix, hcom, context7, trailofbits, nemo, ragas, opik, promptfoo, deepeval, strands. |
| 19 | v0.20.0 | **cos-privacy-mode**, **cos-prompt-quality-gate**, **cos-release-automation** | Remaining small packs | LOW | Batch minor packs. |
| 20 | v0.21.0 | **REMOVE dead code** | task-panel-sync, _archived, ghost skills | LOW | Delete shims from v0.14–v0.20 that have aged out. |
| 21 | v0.22.0–RC | **Shim cleanup** | Remove any surviving compatibility symlinks | LOW | Last mile. |
| 22 | **v1.0.0** | Tag & freeze | No code change | — | Release. |

Total: **21 code waves + 1 release**. Comfortably fits in 2026 Q2/Q3.

### Why 21 waves, not 3?

Larger waves mean bigger blast radius. At ~130 hooks and 150 libs, batching 5 packs per wave loses the incremental safety net. Each wave must end green: all tests pass, `apply-efficiency-profile.sh default` and `…full` both produce valid `settings.json`, `wiring-check.sh` reports zero missing hooks.

---

## Backwards-compat shim policy

| State | Action |
|---|---|
| Pack lives in `hooks/`, `lib/`, `rules/`, `skills/` | v0.13 and earlier (current). |
| Pack moves to `packages/cos-{name}/` | Wave N: files moved; symlinks left at old paths. Shim also includes a line in the hook script: `>&2 echo "DEPRECATED: loaded via compatibility shim — update your references."` (once per session — gated by a stamp file in `.cognitive-os/shim-notice-stamp`). |
| Shim lives | Waves N → N+1 inclusive. |
| Shim removed | Wave N+2. `scripts/check-upstream-changes.sh` fails the build if any grep finds the old path in source or docs. |
| Downstream project broke | `cos doctor` detects missing path and prints migration command. |

Exceptions:
- `cos-audit-trail` keeps its shim for two extra minor versions because compliance consumers need longer notice.
- `cos-sdd` (skills only) skips the shim — skills are looked up via the skill registry which resolves new paths automatically.

---

## CORE feasibility — does it fit the targets?

| Surface | Target | Audit result | Verdict |
|---|---|---|---|
| Hooks | <40 | 38 | Tight but achievable. 2 more if `global-verify` + `error-pipeline` reclassified. |
| Libs | <25 | 24 | Achievable. |
| Rules | <30 | 28 | Achievable. |
| Skills | <20 | 20 | At limit. Every new skill must go in a pack. Enforce in CI via `scripts/cos-core-skills-check.sh`. |

**Red flag:** Skills is at exactly the limit. Recommend adding a CI gate that rejects any PR adding a top-level `skills/*/` directory without a corresponding `packages/*` home. Skill graveyard (`packages/_archived`) can be pruned to create headroom if needed, but the structural rule should be "CORE skills are frozen at 20 — additions go to packs".

---

## Wave 1 execution (this session — POC)

**Target:** `cos-advisory-llm`. Scope:
- Move `hooks/prompt-quality-llm.sh`, `hooks/completeness-check-llm.sh`, `hooks/confidence-gate-llm.sh` → `packages/cos-advisory-llm/hooks/`.
- Move `lib/dispatch_model_advisor.py` if exclusively used by advisor flow (otherwise leave CORE).
- Create `packages/cos-advisory-llm/cos-package.yaml` with `hook_registrations:` stub.
- Leave symlinks at `hooks/<moved>.sh`.
- Smoke test: `bash scripts/apply-efficiency-profile.sh default` exits 0 and produces valid JSON.
- Acceptance criteria #3 (`ls packages/cos-advisory-llm/hooks/` ≥ 1 file) and #4 (profile generation green).

**Deliberately descoped for Wave 1:**
- Rewriting `apply-efficiency-profile.sh` to read `hook_registrations:` dynamically. That happens in Wave 2 once a second pack exists to motivate the generalization. Today the profile script keeps referencing the old hook paths (which resolve via symlink).

---

## Open questions for v1.0 RC review

1. Does `cos-advisory-llm` ship enabled-by-default when the API key is present? (Recommendation: yes, with `skip_if_missing: true` keeping it silent otherwise.)
2. Does `cos-sdd` ship enabled-by-default? (Recommendation: yes — SDD is a 1st-class methodology in the project DNA.)
3. Should `cos-audit-trail` be two packs (compliance-lite vs full)? Defer decision to Wave 14.
4. How do we surface "12 optional packs available" to new users? (Recommendation: `cos extensions list` command in Wave 2.)

---

## Acceptance criteria satisfied

- AC1 (audit exhaustive): `docs/04-Concepts/architecture/core-vs-extensions-audit-2026-04-20.md` classifies all 581 agentic primitives (22% CORE, 78% EXTENSIONS+REMOVE).
- AC2 (≥3 waves): 21 waves defined above.
- AC3 (≥1 hook in `packages/cos-advisory-llm/hooks/`): see Wave 1 execution in this session.
- AC4 (`apply-efficiency-profile.sh default` still succeeds): verified in this session's smoke test.
- AC5 (D43 marked PARTIAL): debt register updated in this session.
- AC6 (FROZEN-BACKLOG P1 row updated): FROZEN-BACKLOG updated in this session.
