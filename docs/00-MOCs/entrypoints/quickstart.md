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
- It presented `cos-init.sh --full` / `--minimal` / `--standard` as three
  profiles. There are only two: `--minimal`, `--standard` and `--lean` all remap
  to `--default` under ADR-093, so the only real choice is `--default` (the
  no-flag default) or `--full`.

> **Correction, 2026-08-15.** An earlier version of this page claimed
> `scripts/cos-init.sh` parsed none of those flags. That was wrong. All three
> parse and run; the check behind the claim grepped `scripts/cos-init.sh`, a
> 15-line shim that `exec`s `scripts/cos_init.py` — the parser lives in the
> Python file. Verify with `bash scripts/cos-init.sh --minimal --help`, or see
> [install-doors-forensics-2026-08-15.md](../../06-Daily/reports/install-doors-forensics-2026-08-15.md).

Its "what works without Docker" table was a subset of the one in
`getting-started.md`, which additionally covers the `cos` CLI row.

The local-clone install path this page used to document is back in
[Installation → From a local clone](getting-started.md#from-a-local-clone-of-the-source),
with the clone URL corrected.
