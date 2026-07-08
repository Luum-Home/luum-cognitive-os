---
type: concept-synthesis
source: docs/04-Concepts/architecture/functional-audit/scorecard-install-scripts.md
provenance: "Session 2026-04-16, post ADR-001 and cluster A-D audit reports: which tests cover which install/update/uninstall scripts, and why some can't be hermetically exercised."
---

## What it is

Scorecard mapping the 8 install/update/uninstall scripts to their pytest coverage layers (L1 syntax, L2 dry-run/help, L3 behavior, L4 regression), and the authoritative source of truth for audit coverage of install/update/uninstall behavior.

## Key mechanics

- Delegation chain: `install.sh` -> `cos-init.sh` -> `generate-project-settings.sh`; `auto-update-projects.sh` -> `cos-init.sh`; `cos-update.sh` -> `hooks/self-install.sh` (step 6); `cos-bootstrap.sh` -> `hooks/self-install.sh` (step 7).
- Three named regression tests pin real bugs, all invariant-based (presence/absence, not fixed counts): `test_adr001_self_install_populates_claude_skills` (ADR-001: harness read `.claude/skills/` but `self-install.sh` synced only `.cognitive-os/skills/`, so skills were "ghosts"); `test_adr001_cos_init_dual_dest_flat_driver` (cluster B: `cos-init.sh` lacked driver-path install and used a nested `cos/` layout the harness can't read); `test_cluster_d_uninstall_removes_claude_skills` (cluster D: `uninstall.sh` left `.claude/skills/` as a stale symlink forest after removing `.cognitive-os/skills/cos/`).
- Known coverage gaps (all deliberate, documented): `install.sh` remote git-clone flow (not hermetic, syntax+`--help` only); `cos-bootstrap.sh` full flow (needs Docker/Langfuse/LiteLLM containers); `cos-init-global.sh` (writes real `$HOME` by design); `auto-update-projects.sh` per-project update loop (covered indirectly via the cluster-B regression test instead); `cos-update.sh` (resolves `PROJECT_ROOT` to the real repo, so a full run would mutate the developer's checkout).
- Risk register: `$HOME` leakage mitigated by `run_shell` redirecting `HOME=cwd`/`tmp_path`; real-repo mutation mitigated by a throwaway `tmp_path/client-project` with no self-install marker (self-hosting guard doesn't trigger); subprocess hangs mitigated by `timeout<=60s` + root conftest SIGALRM 30s fallback; jq-dependent tests skip cleanly via `shutil.which("jq") is None`.

## Relations & where used

`tests/audit/test_install_scripts.py`, `tests/audit/shell_test_utils.py`, `docs/04-Concepts/architecture/harness-adoption-gap/scripts-audit.md` (cluster A-D parent report), ADR-001.

## Status / caveats

Test framework doc, not a decision doc. Run via `python3 -m pytest tests/audit/ -v -m audit`. Maintenance rule: new install scripts get appended to `TARGET_SCRIPTS` for automatic L1 coverage. Change log: 2026-04-16 initial scorecard + 3 regression tests.
