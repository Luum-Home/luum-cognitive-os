# COS Service Control Plane Research — 2026-05-04

This note separates what Cognitive OS already has from the headless service
control plane it would need to run outside an IDE as an autonomous but
governed service.

## Question

Can COS grow from an IDE/harness-embedded worker surface into a service like:

```text
cosd / scheduler
  -> task queue
  -> cos-worker containers
  -> Engram Cloud
  -> artifact/evidence store
  -> PR/propose-only output
```

And can that service use account-backed Claude Code, Codex, Kimi, MiniMax,
DeepSeek, or similar provider accounts without forcing every path through API
keys?

## Current COS boundary

COS currently has:

- **Harness-embedded runtime**: Claude Code, Codex, and projected harnesses own
  the process lifecycle, prompt loop, tool execution, and interactive approval.
  COS supplies rules, hooks, skills, manifests, memory wrappers, and evidence.
- **Docker worker surface**: `docker/cos-worker/` proves COS can boot in a
  container and run explicit smoke/proof commands without an IDE-attached
  shell.
- **Engram Cloud service**: the memory replication surface is now a real
  service backed by local Docker proof.

COS does **not** yet have a central `cosd` that admits tasks, leases work,
starts workers, retries crashes, stores artifacts, and proposes PRs.

## Reference systems

### Claude Code

Claude Code is still a CLI/harness, not a COS-style scheduler. Its official
authentication documentation matters because COS should not invent unsupported
credential flows:

- Claude Code supports multiple authentication modes, including Claude.ai
  login, Claude Console credentials, Bedrock, Vertex, and Microsoft Foundry.
- On macOS, Claude Code credentials are stored in the encrypted macOS Keychain;
  on Linux/Windows, they live under the Claude config directory.
- Authentication precedence is explicit: cloud provider credentials, bearer
  tokens, API keys, helper scripts, long-lived OAuth tokens, then subscription
  OAuth credentials.
- For non-browser automation, `claude setup-token` can generate a long-lived
  OAuth token for CI/scripts, but the token is sensitive and must be treated as
  credential material.

Source: <https://code.claude.com/docs/en/authentication>

### Codex

Codex has a richer first-party automation surface than a plain IDE extension:

- The Codex CLI runs locally and can authenticate with ChatGPT or an API key.
- Codex Cloud requires ChatGPT sign-in, while CLI/IDE support ChatGPT and API
  key auth.
- The CLI caches login state locally and can store credentials in a file or OS
  keyring.
- `codex exec` is explicitly intended for scripts/CI and can emit JSONL events.
- OpenAI recommends API keys by default for automation, while ChatGPT-managed
  account auth in CI/CD is an advanced/trusted-runner path.

Sources:

- <https://developers.openai.com/codex/cli>
- <https://developers.openai.com/codex/auth>
- <https://developers.openai.com/codex/noninteractive>

### OpenClaw

OpenClaw is relevant because it is headless/service-shaped. Its docs describe a
gateway/control-plane style architecture, a single embedded agent runtime, a
workspace, injected bootstrap files, session storage, command queues, and
channel delivery. The important lesson for COS is not to copy the product
surface; it is to recognize the missing `cosd` layer:

```text
channel/input -> gateway/control plane -> agent runtime -> tools/skills
```

Sources:

- <https://docs.openclaw.ai/concepts/agent>
- <https://openclaw-ai.net/en/architecture>

### Hermes Agent

Hermes is relevant as an always-on agent/runtime with broad toolsets and
provider/tool gateways. Its tool documentation describes terminal/file tools,
browser tools, memory/session search, delegation, cron jobs, messaging, MCP,
and a Nous Tool Gateway that can provide selected tools without separate API
keys for paid portal subscribers.

The lesson for COS: separate the service runtime from provider credentials and
tools. Provider/tool gateways are adapters behind a contract, not hardcoded
assumptions inside the scheduler.

Source: <https://hermes-agent.nousresearch.com/docs/user-guide/features/tools/>

## Credential model for a COS service

COS should not scrape, copy, or reinterpret provider credentials. It should
define account-backed executor adapters that invoke official provider CLIs or
gateways under explicit credential modes.

### Credential modes

| Mode | Meaning | Allowed for `cosd`? | Notes |
|---|---|---:|---|
| `account-session` | Official CLI is already logged in for the host user. | yes, local/trusted only | COS invokes the CLI; it does not read the token. |
| `device-login` | Official device/browser login flow provisions CLI auth. | yes | Good for headless trusted hosts when provider supports it. |
| `oauth-token` | Official long-lived OAuth token or equivalent. | yes, sensitive | Must be passed as a secret; never logged or stored in evidence. |
| `api-key` | Provider API key. | yes | Default for many automation surfaces; easiest to rotate. |
| `provider-cloud` | Bedrock/Vertex/Foundry/etc. environment credentials. | yes | Useful for organizations with cloud identity controls. |
| `proxy-gateway` | Enterprise/provider gateway handles billing/auth. | yes | COS authenticates to the gateway, not directly to model vendor. |
| `unknown` | Provider lacks a proven headless contract. | no | Must remain lab until a proof drill exists. |

### Non-negotiable credential rules

1. COS must never read `~/.claude`, `~/.codex/auth.json`, macOS Keychain,
   browser cookies, or vendor token stores directly.
2. COS may invoke official CLIs as subprocesses when the operator has already
   authenticated them.
3. COS may mount credentials into a worker only through explicit,
   provider-documented mechanisms and only on trusted runners.
4. Every provider adapter must expose an `auth_probe` command that returns
   `ready`, `auth_required`, `unsupported`, or `unsafe`.
5. Evidence bundles must redact token-like strings from stdout/stderr before
   persistence.
6. Account-backed mode is not portable by default. A local Claude Code login on
   a laptop does not automatically imply a safe cloud-worker credential.

## Provider posture

| Provider/runtime | Safe current COS posture |
|---|---|
| Claude Code | Supported as a future `claude-cli` account-backed executor only by invoking official `claude` in an authenticated host/session or by using documented OAuth/API/cloud-provider modes. |
| Codex | Supported as a future `codex-cli` executor through `codex exec`; account auth is possible on trusted hosts, while API key is the recommended default for automation per OpenAI docs. |
| Kimi | Lab until the specific CLI/API/headless auth contract is documented and proven. |
| MiniMax | Lab until the specific CLI/API/headless auth contract is documented and proven. |
| DeepSeek | Lab until the specific CLI/API/headless auth contract is documented and proven. |
| OpenRouter/LLM gateway | Viable as `proxy-gateway` if billing, policy, and token handling are explicit. |

## Design implication

The service control plane should not know how to talk to Claude, Codex, Kimi,
MiniMax, or DeepSeek directly. It should know how to schedule a task and choose
an executor adapter that declares:

```yaml
executor_id: codex-cli
credential_mode: account-session
auth_probe: scripts/cos-auth-probe --provider codex --mode account-session --json
machine_readable_output: true
supports_jsonl_events: true
supports_patch_output: true
propose_only_required: true
```

Provider-specific knowledge belongs in adapters and proof drills, not in
`cosd`.

## Open questions

- Should the first `cosd` be HTTP, Unix socket, or file-queue only?
- Should the local task queue use SQLite or append-only JSONL first?
- Should workers be spawned by Docker Compose initially, or should the first
  proof be a local subprocess to reduce moving parts?
- Which provider adapter should be first: `codex-cli` because `codex exec
  --json` is documented, or `claude-cli` because current COS operation is
  Claude-heavy?
- How strict should `auth_probe` be before a provider can move out of `lab`?

## Conclusion

The next durable architecture step is not “run all providers in Docker with
copied credentials”. The correct step is a small COS service control plane with
provider executors behind explicit account-backed and API-backed contracts.

Until that exists, COS should keep claiming:

> COS has a worker surface and Engram Cloud service proof.

And should not claim:

> COS has a standalone autonomous service control plane.

