---
adr: 343
title: codebase-memory-mcp — Recommend-Only, and a Conditional Structural-Discovery Directive
status: accepted
implementation_status: partial-blocked
date: 2026-08-15
---
# ADR-343: codebase-memory-mcp — Recommend-Only, and a Conditional Structural-Discovery Directive

- Implementation status: partial-blocked (detection script landed and demonstrated; the rule file is blocked by the protected-config write guard and ships as a runbook patch)
- Date: 2026-08-15
- Owner: Cognitive OS maintainers

## Status

accepted

## Context

The operator asked to "install codebase-memory-mcp from the agent OS itself, or
have it recommend it". Both options were left open. What the repo actually looked
like, measured:

| Claim | Verdict | Command |
|---|---|---|
| The repo has zero references to the MCP | **True** (the only hits are today's own reports) | `grep -rn "codebase-memory" . \| grep -v '^./.git/'` |
| A repo hook injects a "use the graph FIRST" directive | **False** — the directive is not in this repo at all | `grep -rn "Code Discovery Protocol\|tools FIRST" . \| grep -v '^./.git/'` → only quotations inside a report |
| The MCP has never indexed this repo | **True** — 8 projects in the graph, none of them this one | `python3 scripts/check_codebase_memory_readiness.py` |
| The SO has no MCP machinery | **False** — `manifests/mcp-server-registration.yaml` (ADR-231), `manifests/dependencies.yaml` `mcp_servers:`, `scripts/register-mcps.sh`, `scripts/check_mcp_servers.py` all predate this | `git ls-files \| grep -i mcp` |

So there is a real defect, and it is not the one the framing suggested. An
unconditional directive of the form *"ALWAYS use codebase-memory-mcp tools
FIRST"* exists in the operator's environment, outside this repo. Applied here it
orders an agent to consult a graph that does not contain this project, burn the
call, and fall back to `grep`. The defect is the missing precondition, not a
missing installation.

Three further facts shaped the decision:

- **The server is real and installable.** `npm view codebase-memory-mcp` →
  `0.10.5`, `license = MIT`, `repository.url = git+https://github.com/DeusData/codebase-memory-mcp.git`.
  It passes `rules/license-policy` (ALLOW MIT).
- **It ships its own multi-harness installer.** `codebase-memory-mcp --help`
  advertises `install`/`uninstall`/`update` and auto-detection of Claude Code,
  Codex CLI, Gemini CLI, Zed, OpenCode, Antigravity, Aider, KiloCode and Kiro.
- **It has a headless CLI.** `codebase-memory-mcp cli <tool> [json]` runs a
  single tool without an MCP session, which makes the precondition mechanically
  checkable from a plain script.

## Decision

**Recommend-only, plus a conditional directive. The Cognitive OS does not install
`codebase-memory-mcp` and does not write MCP configuration for any harness.**

Concretely:

1. **Land a detection script** — `scripts/check_codebase_memory_readiness.py`.
   Read-only, deterministic, no network. Exit `0` READY (server reachable **and**
   this project indexed), `1` NOT_READY, `2` ERROR.
2. **Make the directive conditional and bring it in-repo** —
   `rules/codebase-memory-directive.md` fires only on `READY`; on `NOT_READY` the
   agent must use `Grep`/`Glob` and must not index on its own initiative.
3. **Do not install, and do not emit MCP config.**

### Why not install

- **Blast radius.** Installing means the SO writes MCP config into every
  consumer install, adding an external runtime dependency to all of them.
- **The value is zero until each project is indexed**, and indexing is a
  per-project, stateful, expensive operation the SO cannot perform at install
  time. An installed-but-unindexed server is exactly the defect above, shipped
  wider.
- **The vendor owns the installer, and it covers nine harnesses.** Emitting our
  own `.mcp.json` / `.codex/config.toml` / opencode config would mean asserting
  three harness contracts against a tool that already implements all nine. This
  repo has a fresh, concrete example of the failure mode: a 228-line harness
  driver written against an imagined contract. The correct install command is the
  vendor's — `codebase-memory-mcp install` — not ours.
- **No measured benefit here.** Nobody has benchmarked graph-vs-grep on *this*
  repository, and this repository is not in the graph. Recommending a tool on
  unmeasured efficiency grounds would be an assertion without a command.

### Relationship to the external-tool adoption freeze

`manifests/external-tool-adoption-freeze.yaml` is `frozen: true` since
2026-05-11, because accumulating externally-derived code without IP counsel
review compounds risk (ADR-267 Gap 1).

**This decision does not adopt anything.** Nothing upstream is vendored, ported
or reimplemented — no code, no algorithm, no schema. What lands is a detection
script written here and an advisory rule that *restricts* when an existing
directive may fire. The IP surface the freeze protects is untouched, and
`unfreeze_requires` is neither satisfied nor invoked.

It is nonetheless **recorded as a written exception** under `operator_exceptions`
in that manifest, because the operator's decision sits adjacent to the policy and
a manifest that says `frozen: true` while practice adopts is worse than either
posture alone.

Two holes are disclosed there rather than papered over:

- `gated_path_globs` does not cover `manifests/dependencies.yaml`, so an MCP
  recommendation declared there would never reach the gate.
- **A profile-configured MCP bypasses the policy entirely.** The freeze governs
  *documented* adoption, not *de-facto* use; this server is already reachable on
  this machine by that path. This decision does not close that hole — closing it
  is an operator decision about scope, not a documentation fix.

And the enforcer is inert regardless: `hooks/adoption-freeze-gate.sh` is
registered in neither `.claude/settings.json` (`grep -c` → 0) nor
`.githooks/pre-commit` (no such file). That makes the *written* exception more
important, not less, since no mechanism would have recorded it.

### Not an entry in the licenses inventory

`manifests/external-tool-licenses.yaml` tracks tools "vendored or ported into
Cognitive OS", and `NOTICE` carries their attribution. This case ports nothing,
so it correctly appears in neither. Stated explicitly so a later audit does not
read the absence as the `aider`/`dspy` gap, where genuinely adopted code is
missing from both inventories.

### Not a replacement for Graphify

`manifests/primitive-lifecycle.yaml` sets Graphify's `sunset_criteria` as
"replaced by an **owned** COS context graph primitive with **equivalent
receipts**". A third-party MCP is not owned and has produced no equivalent
receipts, so **this decision does not authorise retiring Graphify**. Measured
overlap is 3 of 11 capabilities; the remaining 8 do not compete. The two coexist:
Graphify stays explicit team/advisory tooling with `runtime_projection: false`.

## Consequences

**When the MCP is absent** — the script exits `1`, the rule tells the agent to use
`Grep`/`Glob`, and nothing breaks. No consumer install gains a dependency.

**When the MCP is present but the project is unindexed** — the same `1`, the same
fallback. This is this repository's state today, and the case the unconditional
directive got wrong.

**When both hold** — the graph is a legitimate first move for structural
questions.

**Multi-harness coverage is deliberately asymmetric, and this is the honest
scope:** the script *reads* candidate config locations for Claude Code and Codex
to discover a command, and treats `PATH` as the primary signal. It **writes**
nothing for any harness, so no harness contract is asserted. opencode, Cursor,
Zed, Gemini CLI and the rest are **not verified** by this ADR and do not need to
be — the vendor's installer owns them. Should the SO ever emit MCP config, that
work must first produce `sources:`/`verified:` schema manifests and conformance
tests, in the shape of `manifests/codex-hooks-schema.yaml`.

**Known limitation:** the rule is advisory, not enforced. Nothing makes an agent
run the check. Wiring it to a hook is a separate decision with its own blast
radius, and `hooks/**` is a protected path an agent cannot write.

## Implementation

- `scripts/check_codebase_memory_readiness.py` — landed, demonstrated in all
  three states (READY on an indexed project, NOT_READY here, NOT_READY with the
  server unreachable).
- `manifests/external-tool-adoption-freeze.yaml` — `operator_exceptions` entry;
  `frozen`, `unfreeze_requires` and `gated_path_globs` unchanged.
- `docs/05-Methodology/runbooks/codebase-memory-directive-2026-08-15/` — the rule
  file as a verified patch (`git apply --check` passes), blocked from direct
  write by `hooks/protected-config-write-guard.sh`.
- `docs/06-Daily/reports/codebase-memory-mcp-adopcion-2026-08-15.md` — report.

## Verification

```bash
python3 scripts/check_codebase_memory_readiness.py --explain            # exit 0
python3 scripts/check_codebase_memory_readiness.py                      # exit 1 here
python3 scripts/check_codebase_memory_readiness.py --json
git apply --check docs/05-Methodology/runbooks/codebase-memory-directive-2026-08-15/conditional-directive.patch
python3 -c "import yaml;m=yaml.safe_load(open('manifests/external-tool-adoption-freeze.yaml'));assert m['frozen'] is True;print(m['operator_exceptions'][0]['id'])"
```
