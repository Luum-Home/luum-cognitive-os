# Dry-Run Manifest: `lib` -> `cos_lib` Package Rename

- **Date:** 2026-07-08
- **Repo:** luum-cognitive-os (SOURCE)
- **Tool:** `scripts/cos_lib_rename_codemod.py` (dry-run; no source mutated this session)
- **Decision:** Resolves risk **U1** (namespace collision — a consumer's own top-level
  `lib/` shadowing the projected COS `lib/`). Supersedes the *deferred* note in
  `docs/02-Decisions/designs/hook-lib-projection-contract.md` §7.
- **Reproduce:** `python3 scripts/cos_lib_rename_codemod.py --json`

> **DO NOT COMMIT** this report (git-tracked path, but leave uncommitted per task).

## 1. Totals

| Metric | Count |
|---|---|
| Total files to change | **902** |
| Total import lines to change | **1854** |
| Unguarded files | 808 |
| Unguarded lines | 1705 |
| **GUARDED files** (need env-session) | **94** |
| GUARDED lines | 149 |
| RISKY / unsafe-to-auto edge cases | **47** |
| String/path refs (higher-risk, enumerated only) | **125** |
| Symlinks in `lib/` | 73 |

> **Guarded count note:** the codemod reports **94** guarded hook files vs. the operator's
> earlier **82** grep estimate. The delta is real, not a false positive: the codemod also
> catches split-token invocations such as `ARGS=("-m" "lib.session_lifecycle")` and
> package-level `from lib import X` that a `-m lib.` / `from lib.` grep misses. All 94 were
> verified to contain a genuine `lib` package reference.

## 2. Per-directory breakdown (importers, measured)

| Directory | Python importer files |
|---|---|
| `tests` | 480 |
| `scripts` | 153 |
| `lib` | 134 |
| `packages` | 42 |
| `workflows` | 14 |
| `hooks (.sh)` | 82 |
| `mcp-server` | 1 |

(`lib/` self-imports and `packages/*/lib/` symlink-target module bodies are included; the
codemod rewrites those too since they are unguarded.)

## 3. GUARDED files — REQUIRE a `COS_ALLOW_PROTECTED_CONFIG_WRITE=1` env-session

These live under `hooks/` (protected-config guard). The codemod **refuses** to write them
in a normal `--apply`; it lists them so a guarded session runs them in the SAME atomic pass.
A partial apply (these skipped) leaves the repo **BROKEN**. Count: **94**.

```
hooks/_lib/common.sh
hooks/_lib/context_budget_lib.sh
hooks/_lib/dispatch_gate_check.py
hooks/_lib/recap_adapter.py
hooks/_lib/register-bg.sh
hooks/_lib/session-fs-reap.sh
hooks/_lib/session_init_helper.py
hooks/_lib/task_panel_adapter.py
hooks/_lib/timing.sh
hooks/aci-observation-capture.sh
hooks/adr-detector.sh
hooks/adr-relevance-suggest.sh
hooks/agent-control-inbound-guard.sh
hooks/agent-launch-confirmed.sh
hooks/agent-message-inbox-context.sh
hooks/agent-prelaunch.sh
hooks/agent-quota-advisor.sh
hooks/agent-quota-redirect.sh
hooks/agent-qwen-bridge.sh
hooks/audit-id-enricher.sh
hooks/auto-repair-dispatcher.sh
hooks/auto-skill-generator.sh
hooks/branch-ownership-lock.sh
hooks/claim-validator.sh
hooks/code-review-on-commit.sh
hooks/completion-gate.sh
hooks/confidentiality-enforcer.sh
hooks/consequence-evaluator.sh
hooks/context-budget-meter.sh
hooks/context-diet.sh
hooks/cosd-auth-guard.sh
hooks/crash-recovery.sh
hooks/cross-session-event-emit.sh
hooks/cross-session-peer-context.sh
hooks/dispatch-gate.sh
hooks/ecosystem-check.sh
hooks/engram-crystallize-on-session-end.sh
hooks/engram-reinforce-on-access.sh
hooks/error-pattern-detector.sh
hooks/git-context-capture.sh
hooks/global-verify.sh
hooks/goal-stop-gate.sh
hooks/guardrails-validator.sh
hooks/history-rewrite-documented.sh
hooks/inject-phase-context.sh
hooks/lethal-trifecta-gate.sh
hooks/memory-prefetch.sh
hooks/mlflow-sync.sh
hooks/native-agent-heartbeat.sh
hooks/notify.sh
hooks/orchestrator-mode-detect.sh
hooks/orchestrator-skill-invocation-gate.sh
hooks/pre-agent-snapshot.sh
hooks/pre-compaction-flush.sh
hooks/predev-completeness-check.sh
hooks/protected-config-write-guard.sh
hooks/quality-duplicates.sh
hooks/query-tailored-context-inject.sh
hooks/rate-limit-detector.sh
hooks/rate-limit-drain.sh
hooks/rate-limit-precheck.sh
hooks/rate-limiter.sh
hooks/registration-check.sh
hooks/reinvention-check.sh
hooks/research-quality-validator.sh
hooks/review-spawner.sh
hooks/rule-router-prompt-suggest.sh
hooks/session-changelog.sh
hooks/session-hygiene.sh
hooks/session-init.sh
hooks/session-start-stack-recommend.sh
hooks/session-start-stash-reapply.sh
hooks/session-state-save.sh
hooks/session-wrapup-trigger.sh
hooks/singularity-check.sh
hooks/skill-drift-detector.sh
hooks/skill-failure-monitor.sh
hooks/skill-invocation-logger.sh
hooks/skill-post-execution-analysis.sh
hooks/skill-router-bash-gate.sh
hooks/skill-router-prompt-suggest.sh
hooks/skill-synthesis-scanner.sh
hooks/skill-usage-tracker.sh
hooks/state-heartbeat.sh
hooks/subagent-budget-enforcer.sh
hooks/subagent-context-injector.sh
hooks/task-completed.sh
hooks/task-created.sh
hooks/teammate-idle.sh
hooks/trust-score-validator.sh
hooks/usage-health-check.sh
hooks/user-prompt-capture.sh
hooks/validator-soak-weekly.sh
hooks/valkey-ensure.sh
```

## 4. RISKY / UNSAFE-to-auto-rewrite edge cases (human review required)

All **47** flagged cases are in `workflows/` and share ONE root cause: they
`from lib.<mod> import …` where `<mod>` (e.g. `telegram`, `shared_phases`, `utils`, `agent`,
`data_types`, `file_parser`) is a module of the **separate** `workflows/lib/` package, NOT the
COS `lib/` package. There is no top-level `lib/telegram.py`. The codemod's **module allowlist**
(373 real top-level `lib/` module names) correctly REFUSES to rewrite these — rewriting them to
`cos_lib.telegram` would break `workflows/`. This is the U1 collision manifesting *internally*.

**Disposition:** leave `workflows/` untouched by this rename; `workflows/lib/` is an
independent vendored ADW package and keeps its own name. Confirm no COS `lib.*` import hides
among them (none found — every flagged name resolves to `workflows/lib/`).

Flagged lines (sample):

```
workflows/backend_bug_pipeline.py:29  from lib.shared_phases import (
workflows/backend_bug_pipeline.py:50  from lib.telegram import (
workflows/backend_bug_pipeline.py:55  from lib.utils import get_service_config, make_workflow_id
workflows/backend_deploy_pipeline.py:23  from lib.shared_phases import (
workflows/backend_deploy_pipeline.py:35  from lib.telegram import (
workflows/backend_deploy_pipeline.py:40  from lib.utils import get_service_config, make_workflow_id
workflows/backend_feature_pipeline.py:32  from lib.shared_phases import (
workflows/backend_feature_pipeline.py:54  from lib.telegram import (
workflows/backend_feature_pipeline.py:59  from lib.utils import get_service_config, make_workflow_id
workflows/backend_feature_pipeline.py:83  from lib.utils import get_services_config
workflows/backend_migration_pipeline.py:25  from lib.agent import prompt_with_retry
workflows/backend_migration_pipeline.py:26  from lib.data_types import AgentPromptRequest
workflows/backend_migration_pipeline.py:27  from lib.shared_phases import (
workflows/backend_migration_pipeline.py:39  from lib.utils import get_project_root, get_service_config, make_workflow_id
workflows/backend_state.py:9  from lib.data_types import BackendWorkflowStateData
... (47 total)
```

## 5. String / path references (higher-risk bucket — enumerated, NOT auto-rewritten)

**125** references resolve a directory literally named `lib` (e.g.
`os.path.join(project_dir, "lib")`, `root / "lib" / name`, `sys.path.insert(0, .../lib)`,
`PYTHONPATH="$X/lib"`). These are **NOT** import statements; distinguishing *"path to THE
package"* (must become `cos_lib`) from *"a test fixture dir named lib"* (must stay) needs
human judgment, so the codemod enumerates rather than edits them.

| Directory | Refs |
|---|---|
| `tests` | 115 |
| `lib` | 4 |
| `scripts` | 4 |
| `packages` | 2 |

Real package-dir resolvers that WILL need updating (not fixtures):

```
lib/pattern_detector.py:228  lib_dir = os.path.join(project_dir, "lib")
lib/reinvention_guard.py:55  self.lib_path = self.project_root / "lib"
lib/wiring_validator.py:181  file_path = self.root / "lib" / name
packages/sdd-compound/lib/system_graph.py:233  lib_dir = os.path.join(project_root, "lib")
packages/verification-audit/lib/orchestrator_verify.py:40  _pkg_lib = os.path.join(os.path.dirname(__file__), "..", "..", "lib")
scripts/aspirational_audit.py:299  lib_modules = {path.stem for path in (project_root / "lib").glob("*.py") if not 
scripts/check_lib_wiring.py:85  path = root / "lib" / "_wiring-allowlist.txt"
tests/contracts/test_orchestrator_verify.py:40  _pkg_lib = os.path.join(_REPO_ROOT, "packages", "verification-audit", "lib")
tests/hooks/test_aspirational_audit_weekly.py:42  (tmp_path / "lib").mkdir()
tests/integration/test_aspirational_audit.py:38  (tmp_path / "lib").mkdir()
tests/unit/test_pattern_detector.py:29  (tmp_path / "lib").mkdir()
tests/unit/test_pattern_detector.py:30  (tmp_path / "lib" / "__init__.py").write_text("")
tests/unit/test_system_graph.py:92  lib_dir = tmp_path / "lib"
tests/unit/test_wiring_validator.py:24  lib = tmp_path / "lib"
```

Note: `PYTHONPATH="$PROJECT_DIR"` / `$PROJECT_DIR/.cognitive-os` (parent-of-package) stays
unchanged — only a path entry pointing *at the package dir itself* becomes `cos_lib`.

## 6. Symlinks (73) — no target rewrite needed

All **73** entries in `lib/` are symlinks whose files LIVE in `lib/` and point via
relative `../packages/*/lib/<mod>.py` into package-internal `lib/` dirs. Under `git mv lib
cos_lib` the symlink FILES move to `cos_lib/`; the relative targets stay valid because
`packages/` is a sibling of both `lib/` and `cos_lib/`. Verified with `readlink -f` on a sample:

```
lib/agent_bus.py -> ../packages/agent-coordination/lib/agent_bus.py
lib/agent_daemon.py -> ../packages/agent-lifecycle/lib/agent_daemon.py
lib/agent_dashboard.py -> ../packages/agent-coordination/lib/agent_dashboard.py
lib/agent_permissions.py -> ../packages/agent-lifecycle/lib/agent_permissions.py
```

**Flag:** every symlink target is itself a `packages/*/lib/` path. Those package-internal
`lib/` dirs are **NOT** renamed (only the top-level package is). The module BODIES behind the
symlinks (`packages/*/lib/*.py`, 57 of which do `from lib.<mod>`) ARE rewritten to `cos_lib`
since, once loaded as `cos_lib.<mod>`, their internal `from lib.` would otherwise fail.

## 7. Safety probe (false-positive tokens)

The boundary-anchored matcher (`(?<![A-Za-z0-9_.])lib(?=\.)` + `from lib import` +
`-m lib.`) was tested against 19 cases. All pass:

- **Untouched:** `pathlib` (2848 hits in repo), `zlib`, `glob`, `joblib`, `library`,
  `mylib.foo`, `a.lib`, `lib_path`, `self.lib`, `{'lib': 1}`, `foo_lib`.
- **Rewritten:** `from lib.foo import x`, `import lib.bar`, `from lib import baz`,
  `python3 -m lib.mod`, `"-m","lib.session_lifecycle"`.

`import pathlib` is safe because `\blib` has no word boundary inside `pathlib` (`h`+`l` are
both word chars); the negative lookbehind additionally blocks `.lib` / `_lib`.

## 8. Reversibility

- Idempotent: a second pass is a no-op (`from cos_lib.foo import x` is left as-is).
- Revert: `git mv cos_lib lib` + `python3 scripts/cos_lib_rename_codemod.py --revert --apply`
  (swaps OLD/NEW). Regex forward/reverse are symmetric (verified).
- The `git mv` of the package dir is emitted as an explicit operator step, never performed
  implicitly, so an aborted run cannot leave a half-moved package.

## 9. Atomic apply recipe (for the guarded env-session)

```bash
git checkout -b chore/cos-lib-rename
git mv lib cos_lib
printf 'lib -> cos_lib\n' >/dev/null  # package dir moved
COS_ALLOW_PROTECTED_CONFIG_WRITE=1 python3 scripts/cos_lib_rename_codemod.py --apply
# then manually resolve Section 5 string/path refs + re-run the test suite
```

