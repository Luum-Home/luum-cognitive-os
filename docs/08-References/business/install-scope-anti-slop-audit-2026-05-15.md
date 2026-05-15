# Install Scope Anti-Slop Audit — 2026-05-15

## Verdict

Current evidence supports **two effective installation surfaces**, not three:

1. **`project` / `both`** — consumer filtered install. These are currently equivalent in installer logic and smoke evidence.
2. **`all`** — maintainer/full superset. It installs more agentic primitives, including `SCOPE: os-only`, but has not demonstrated better developer outcomes.

The product default for normal developers should be the minimal filtered surface until the larger surface proves better outcomes. More hooks, rules, and skills are not value by themselves.

## Evidence reviewed

| Claim area | Evidence | Assessment |
|---|---|---|
| Three install names | `install.sh` exposes `project`, `both`, and `all`; it also states `both` is the same as `project` and defaults to `both`. | The CLI has three accepted names, but only two effective semantics. |
| Scope filter implementation | `scripts/cos_init.py::scope_allows()` returns `True` for both `project` and `both` tags whenever the install scope is not `all`; it only treats `all` specially by disabling filtering. | `project` and `both` are intentionally equivalent today. |
| Smoke evidence | Latest install-scope smoke reports `project` and `both` with identical file counts and equivalent primitive signatures; `all` installs more files and `os-only` primitives. | Confirms two surfaces in runtime projection, not merely docs wording. |
| Value evidence for `all` | Latest smoke says `all` is larger by count, includes maintainer-only primitives, and extra `all` hooks do not all pass their probes. | `all` has higher surface area without demonstrated outcome gain. |
| Safety evidence | Secret detector and destructive git blocker pass representative probes in the install-scope smoke. | Basic safety has evidence. |
| Protected config evidence | The hook blocks agent control-plane paths such as `.claude/settings.json`; the policy does not include `.env`. | A `.env` Write probe is not a valid proof for this hook as currently specified. If product copy implies `.env` write blocking, that is a separate claim gap. |

## What the code actually says

### Installer naming

`install.sh` documents three accepted scope values, but the comments and help text already say `both` is not distinct:

- `project`: files tagged `SCOPE:project` or `SCOPE:both`
- `both`: same as `project`, and the current default for user projects
- `all`: every file, including `SCOPE:os-only`, for COS self-hosting

That is a compatibility surface, not three product tiers.

### Installer semantics

`scope_allows()` in `scripts/cos_init.py` implements the same collapse:

- `install_scope == "all"` returns `True` immediately.
- For non-`all`, `SCOPE: project` and `SCOPE: both` are both allowed.
- `SCOPE: os-only` is blocked.

There is no branch where `install_scope="project"` and `install_scope="both"` differ for file-level scope tags. `skill_scope_allows()` follows the same effective model for skill `SCOPE` markers.

### Profile/tier doctrine already prefers two tiers

ADR-093 explicitly collapsed installer profiles to two tiers: a sensible default and `--full` for mature projects / COS contributors. That ADR aligns with the anti-slop conclusion: default should be small; full should be opt-in.

The scope names should not be marketed as an independent third tier on top of that profile decision.

## Protected config guard clarification

The current protected-config guard is **not** a general `.env` write blocker. Its stated purpose and policy are narrower: control-plane config that can alter permissions, hooks, MCP tools, rules, skills, manifests, or runtime policy.

Evidence:

- Hook comment: “blocks writes to agent control-plane config unless explicitly approved.”
- Policy purpose: “agent control-plane files that can alter permissions, hooks, MCP tools, rules, skills, or runtime policy.”
- Protected globs include `.claude/**`, `.codex/**`, `.cursor/**`, `.continue/**`, `mcp.json`, `.mcp/**`, `hooks/**`, `rules/**`, selected `skills/**`, and selected `manifests/**`.
- Protected globs do **not** include `.env`.
- Existing security test proves `.claude/settings.json` is blocked and generated reports are allowed.

Therefore:

- Claim “protected-config-write-guard blocks control-plane writes” is supported.
- Claim “protected-config-write-guard blocks `.env` writes” is unsupported by policy and tests.
- Claim “COS prevents secret literals” is supported only through the secret detector / read-deny settings / related secret controls, not this hook.

## Product wording boundary

Allowed wording:

> COS currently has a filtered consumer install (`project`/`both`) and a full maintainer install (`all`). `both` is retained as a compatibility/default scope name and currently behaves like `project`.

Avoid wording:

> COS has three meaningful project installation tiers.

Avoid wording:

> `all` is better for developers because it installs more primitives.

Safer wording:

> `all` is for COS maintainers, self-hosting, debugging, and full-surface validation. It should become a developer recommendation only after a benchmark shows better outcomes that justify the added surface area.

## Required follow-up

1. **Documentation correction** — Replace any user-facing “three tiers” language with “two effective surfaces plus compatibility alias.”
2. **Install CLI clarification** — Keep accepting `project|both|all`, but label `both` as an alias/default, not a distinct product tier.
3. **Protected config scope decision** — Decide whether `.env` writes belong in protected-config policy. If yes, add policy glob and tests. If no, document that `.env` is covered by other secret/sensitive-file controls, not this hook.
4. **Outcome burden for `all`** — Require `all_default_justified=true` or equivalent benchmark evidence before recommending `all` as a default developer install.
5. **Cross-stack smoke closure** — Extend the dev-real smoke beyond Python before claiming cross-stack exhaustiveness.

## Bottom line

This is not a failure of COS if we act on it. The anti-slop gate is doing its job: it forces the product to prefer the smallest surface that achieves the same outcome, and it prevents a larger mesh from being called better without evidence.
