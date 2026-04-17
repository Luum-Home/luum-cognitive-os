# Install Scripts — Functional Audit Scorecard

> Test framework: `tests/audit/test_install_scripts.py`
> Helpers: `tests/audit/shell_test_utils.py`
> Marker: `@pytest.mark.audit`
> Context: session 2026-04-16, post ADR-001, cluster A-D audit reports.

## Purpose

This scorecard documents WHICH tests cover WHICH scripts and WHY some scripts
cannot be fully exercised in a hermetic pytest run.  It is the single source
of truth for audit coverage of install/update/uninstall behaviour.

## Scope of scripts under audit

From the global sonnet audit (`docs/architecture/harness-adoption-gap/scripts-audit.md`)
and the four cluster reports (A–D):

| # | Script | Role | Delegates to |
|---|--------|------|--------------|
| 1 | `hooks/self-install.sh` | Self-hosting `SessionStart` sync | — |
| 2 | `scripts/cos-init.sh` | External-project installer | `generate-project-settings.sh` |
| 3 | `scripts/cos-update.sh` | Docker + framework update | `hooks/self-install.sh` (step 6) |
| 4 | `scripts/auto-update-projects.sh` | Batch updater across registered projects | `cos-init.sh` |
| 5 | `scripts/cos-init-global.sh` | Global `~/.claude/rules/cos/` install | — |
| 6 | `scripts/cos-bootstrap.sh` | First-run setup + Docker | `hooks/self-install.sh` (step 7) |
| 7 | `scripts/uninstall.sh` | Clean removal | — |
| 8 | `install.sh` | Root entry point | `cos-init.sh` |

Delegation chain (compact):
```
install.sh ─► cos-init.sh ─► generate-project-settings.sh
auto-update-projects.sh ─► cos-init.sh
cos-update.sh ─► hooks/self-install.sh
cos-bootstrap.sh ─► hooks/self-install.sh
```

## Test matrix

Layers defined in `rules/closed-loop-prompts.md` + ADR-010 inspiration.

| Script | L1 Syntax | L2 Dry-run / Help | L3 Behavior | L4 Regression |
|--------|:---------:|:-----------------:|:-----------:|:-------------:|
| `hooks/self-install.sh` | ✓ | (n/a — SessionStart hook, not user-invoked) | ✓ install → uninstall cycle | ✓ ADR-001 + cluster D |
| `scripts/cos-init.sh` | ✓ | ✓ --help rc=1 documented | ✓ indirect via ADR-001 dual-dest | ✓ cluster B flat driver layout |
| `scripts/cos-update.sh` | ✓ | ✓ --help rc=0, --dry-run documented | (skipped — needs Docker) | — |
| `scripts/auto-update-projects.sh` | ✓ | ✓ --help, --list (redirected $HOME) | (skipped — needs registered projects) | — |
| `scripts/cos-init-global.sh` | ✓ | ✓ --help | (skipped — needs $HOME write) | — |
| `scripts/cos-bootstrap.sh` | ✓ | ✓ --help | (skipped — needs Docker) | — |
| `scripts/uninstall.sh` | ✓ | ✓ --help | ✓ install → uninstall cycle | ✓ cluster D |
| `install.sh` | ✓ | ✓ --help | (skipped — needs network) | — |

Column meaning:
- **L1 Syntax** — parameterized `bash -n` check.  Every script must parse.
- **L2 Dry-run / Help** — `--help`, `--dry-run`, malformed-arg exit codes, no side effects in tmp_path.
- **L3 Behavior** — create throwaway project → install → assert expected paths → uninstall → assert clean.
- **L4 Regression** — the three specific bugs fixed this session.  Named in the test file.

## Regression coverage — the 3 named bugs

| Test | Bug it pins | File:line |
|------|-------------|-----------|
| `test_adr001_self_install_populates_claude_skills` | ADR-001 — harness read `.claude/skills/` but `self-install.sh` synced only to `.cognitive-os/skills/`. Skills were ghosts. | `tests/audit/test_install_scripts.py` |
| `test_adr001_cos_init_dual_dest_flat_driver` | Cluster B — `cos-init.sh` lacked driver-path install + used nested `cos/` layout that the harness cannot read. | `tests/audit/test_install_scripts.py` |
| `test_cluster_d_uninstall_removes_claude_skills` | Cluster D — `uninstall.sh` removed `.cognitive-os/skills/cos/` but left `.claude/skills/` as a stale symlink forest. | `tests/audit/test_install_scripts.py` |

Each regression test is **invariant-based**, not count-based:
- Presence/absence of `.claude/skills/<name>/SKILL.md`, not a fixed file count.
- Presence/absence of `.claude/skills/cos/` directory (must be FLAT, no `cos/` under driver).
- Presence/absence of `.claude/skills/` after uninstall (must be fully removed).

This keeps the tests robust when new skills are added to `skills/`.

## Known limitations

### 1. `install.sh` remote flow is skipped
The `install.sh` script without `--from` downloads from GitHub via `git clone`.
This is not hermetic.  Covered tests: syntax + `--help`.  Deep end-to-end is
out of scope for the audit.
Skip marker: `test_install_sh_remote_flow`.

### 2. `cos-bootstrap.sh` full flow needs Docker
The bootstrap script provisions Langfuse + LiteLLM containers and waits for
health endpoints.  Even with a local Docker daemon, the pull time makes this
a slow-suite test, not an audit-suite test.  Covered: syntax + `--help` + `--dry-run` args in CLI.
Skip marker: `test_cos_bootstrap_full_flow`.

### 3. `cos-init-global.sh` writes to `$HOME`
The global installer writes to `~/.claude/rules/cos/` by design.  pytest
cannot safely redirect `$HOME` for subprocesses without risk that a hooked
side-effect reaches the developer's real home.  We redirect `$HOME` in the
`run_shell` helper, but the global installer's contract is tied to the real
home dir, so the test only exercises syntax + `--help` + `--dry-run`.
Skip marker: `test_cos_init_global_writes_to_user_home`.

### 4. `auto-update-projects.sh` full flow needs a populated registry
The script reads `~/.cognitive-os/installations.json`.  We test the `--list`
code path against an empty registry (redirected `$HOME`), which exercises
argument parsing + registry-absent handling.  We do NOT exercise the
per-project update loop because that would require creating fake registered
projects and invoking `cos-init.sh` per-project — which is already covered
end-to-end by the cluster-B regression test.

### 5. `cos-update.sh` requires a COS-installed project
The script resolves `PROJECT_ROOT` from `SCRIPT_DIR/..`, so it always targets
the real repo regardless of the `cwd` passed by the test harness.  Running
it end-to-end would mutate the developer's checkout.  Covered: syntax +
`--help`.  The skills-sync side (step 6) is already covered by the
self-install regression tests.

### 6. `hooks/self-install.sh` is not directly user-invokable
It is wired into `SessionStart` and depends on `CLAUDE_PROJECT_DIR`.  Layer 2
(dry-run/help) does not apply; coverage goes straight from syntax (L1) to
behavior (L3) and regression (L4).

## Risk register

| Area | Risk | Mitigation |
|------|------|-----------|
| $HOME leakage | A script writes to the real `~/.claude/` | `run_shell` sets `HOME=cwd` by default; `auto-update-projects.sh` also has `HOME=tmp_path`. Global installer is SKIPPED. |
| Real repo mutation | `cos-init.sh` self-hosting guard triggers if invoked inside luum-agent-os | Test uses a throwaway `tmp_path/client-project` with no `hooks/self-install.sh` marker → guard does not trigger. |
| Subprocess hang | A shell loop waits for user input or network | All `run_shell` calls have `timeout<=60s`; root conftest adds SIGALRM 30s fallback. |
| Skill content drift | Regression test hardcodes skill names that could be renamed | Uses `compose-prompt`, `session-backlog`, `agent-dashboard` — all present as of 2026-04-16 per `skills/` inventory. If renamed, update `make_throwaway_project()`. |
| jq availability | Uninstaller + auto-update require jq; CI may lack it | jq-dependent tests skip cleanly with `shutil.which("jq") is None` check (layer 2). Behavior tests do NOT require jq for the minimal uninstall path we exercise. |
| Symlink vs copy semantics | `self-install.sh` symlinks; `cos-init.sh` copies | Regression tests use layout-agnostic `count_skills_at()` (works with either) and path-presence assertions. |

## How to run

```bash
# Just the audit layer
python3 -m pytest tests/audit/ -v

# With markers
python3 -m pytest tests/ -v -m audit

# Collect-only (smoke test that everything parses and imports)
python3 -m pytest tests/audit/test_install_scripts.py --collect-only

# Single regression test
python3 -m pytest tests/audit/test_install_scripts.py::test_adr001_self_install_populates_claude_skills -v
```

## Maintenance

When a new install/update/uninstall script is added:
1. Append it to `TARGET_SCRIPTS` in `tests/audit/shell_test_utils.py` → L1 coverage is automatic.
2. Add a `--help` expectation to the L2 parametrize if it is user-facing.
3. If it has side effects on `.claude/skills/`, extend `test_uninstall_removes_cos_components` or add a new regression test.

When a new ADR pins a behavioural invariant:
1. Add a test named `test_<adr-number>_<invariant>` to layer 4.
2. Reference the ADR + commit in the docstring.
3. Add a row to the "Regression coverage" table in this scorecard.

## Change log

| Date | Change | Author |
|------|--------|--------|
| 2026-04-16 | Initial scorecard + 3 regression tests (ADR-001, cluster B, cluster D) | session audit agent |
