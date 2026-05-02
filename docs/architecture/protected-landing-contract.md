# Protected Landing Contract

## Purpose

ADR-116 requires shared branches such as `main` and `master` to be updated through a protected landing path. This contract is **vendor-neutral**: GitHub is one possible adapter, not a dependency of Cognitive OS.

## Contract

A protected landing path must provide these guarantees:

1. **Serialized writes** — only one landing operation may advance a protected branch at a time.
2. **Fresh-base validation** — the candidate is validated against the current protected-branch head, not a stale base.
3. **Required gates** — configured tests/checks/claim validators pass before landing.
4. **Direct-agent push rejection** — autonomous agents cannot push directly to protected branches.
5. **Operator bypass visibility** — any emergency bypass is explicit, audited, and not a permanent shell default.
6. **Provenance** — landed commits or merge records identify session/work/queue context when available.

## Adapter matrix

| Remote/provider | Preferred adapter | Notes |
|---|---|---|
| GitHub | Branch protection/rulesets and merge queue when available | Optional adapter only; do not require `gh` or GitHub-specific APIs for core correctness. |
| GitLab | Protected branches and merge trains | Use provider-native checks and train serialization. |
| Gitea / Forgejo | Protected branches and required PR/checks where available | Capabilities vary by deployment/version. |
| Bitbucket | Branch permissions and merge checks | Use native branch restrictions when available. |
| Bare Git / SSH self-hosted | Server-side `pre-receive` / `update` hooks | Most vendor-neutral strong enforcement when server hooks can be installed. |
| Unknown / unsupported | COS local merge queue + pre-push gates | Allowed fallback, but status must report that remote enforcement is unknown. |

## Portable fallback layers

When provider-native protection is unavailable, Cognitive OS must still provide a local baseline:

1. `hooks/direct-main-guard.sh` — local actor-aware commit policy.
2. `.githooks/pre-push` — collision and claim checks before push.
3. COS merge queue — single-writer local landing path.
4. Optional server-side Git hook pack — generated `pre-receive`/`update` hooks for remotes where the operator controls the server.

## Non-goals

- Do not require `gh`.
- Do not require GitHub branch protection.
- Do not assume the repository is hosted on GitHub.
- Do not make local hooks the only safety boundary when a stronger remote mechanism is available.

## Future adapter interface

A provider adapter should expose:

```yaml
protected_landing:
  provider: auto|github|gitlab|gitea|forgejo|bitbucket|bare|unknown
  protected_branches: [main, master]
  local_queue_required: true
  remote_enforcement: required|optional|unavailable
  server_hooks_supported: true|false|unknown
```

The status command should report whether the current repo is using provider-native protection, server-side hooks, or local-only fallback.
