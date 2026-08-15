# Cognitive OS — Quickstart

**This page moved.** The install instructions live in one place now:
**[getting-started.md](getting-started.md)**.

- Under a minute → [Fast path](getting-started.md#fast-path-one-minute)
- Without Docker → [What Works Without Docker?](getting-started.md#what-works-without-docker)
- Update or remove → [Upgrade and uninstall](getting-started.md#upgrade-and-uninstall)

This file is kept as a redirect because other documents still link to it.

---

## Why this page no longer carries its own commands

It had drifted away from the repository it was describing (verified 2026-08-15):

- It cloned `github.com/luum-home/luum-agent-os`. The actual remote is
  `github.com/Luum-Home/luum-cognitive-os` (`git remote -v`), so the documented
  clone did not resolve.
- It offered `cos-init.sh --full` / `--minimal` / `--standard`. `scripts/cos-init.sh`
  parses no such flags (`grep -nE 'minimal|standard|full' scripts/cos-init.sh`
  returns nothing).

Its "what works without Docker" table was a subset of the one in
`getting-started.md`, which additionally covers the `cos` CLI row. Nothing
unique was lost in the merge.

If you install from a local clone of the source, that path still works and is
documented in [Upgrade and uninstall](getting-started.md#upgrade-and-uninstall).
