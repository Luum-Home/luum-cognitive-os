---
type: concept-synthesis
source: docs/04-Concepts/architecture/service-control-plane-research-2026-05-04.md
provenance: "Separates what Cognitive OS already has from the headless service control plane it would need to run outside an IDE as an autonomous but governed service, using account-backed provider CLIs instead of forcing every path through API keys."
---

## What it is
Research note (2026-05-04) evaluating whether COS can grow from an IDE/harness-embedded worker surface into a headless `cosd` service (task queue -> cos-worker containers -> Engram Cloud -> artifact store -> PR/propose-only output).

## Key mechanics
- Current COS boundary: harness-embedded runtime (Claude Code/Codex own the process lifecycle); Docker worker surface (`docker/cos-worker/`) proven for container boot + smoke commands without an IDE-attached shell; Engram Cloud is a real service with local Docker proof. COS does **not** yet have a central `cosd` that admits tasks, leases work, retries crashes, stores artifacts, and proposes PRs.
- Reference systems reviewed: **Claude Code** (auth modes: Claude.ai login, Console credentials, Bedrock, Vertex, MS Foundry; macOS Keychain storage; `claude setup-token` generates a long-lived OAuth token for CI/scripts); **Codex** (`codex exec` intended for scripts/CI, emits JSONL events; API key recommended default for automation, ChatGPT-managed account auth in CI is an advanced/trusted-runner path); **OpenClaw** (headless gateway/control-plane architecture pattern — the lesson is the missing `cosd` layer, not the product surface to copy); **Hermes Agent** (always-on runtime with a Nous Tool Gateway — lesson: separate the service runtime from provider credentials/tools, keep gateways as adapters behind a contract).
- Economic premise: for the maintainer's solo-swarm, default posture should prefer official account-backed CLI execution before direct provider API-key execution (cost/plan-shape reasons) — this does not weaken the credential boundary.
- 6 non-negotiable credential rules: never read `~/.claude`, `~/.codex/auth.json`, macOS Keychain, browser cookies, or vendor token stores directly; may invoke already-authenticated official CLIs as subprocesses; may mount credentials into a worker only through explicit provider-documented mechanisms on trusted runners; every provider adapter must expose an `auth_probe` command returning `ready`/`auth_required`/`unsupported`/`unsafe`; evidence bundles must redact token-like strings from stdout/stderr before persistence; account-backed mode is not portable by default (a laptop login does not imply a safe cloud-worker credential).
- Credential modes table: `account-session`, `device-login`, `oauth-token` (sensitive, never logged), `api-key`, `provider-cloud`, `proxy-gateway` — all allowed with caveats; `unknown` is not allowed until a proof drill exists.
- Provider posture table: Claude Code / Codex supported as future account-backed executors invoking the official CLI on an authenticated host, or via documented OAuth/API/cloud-provider modes; Kimi/MiniMax/DeepSeek remain lab until a documented+proven headless auth contract exists; OpenRouter/gateway viable as `proxy-gateway`.
- Design implication: `cosd` should not know provider specifics directly — it schedules tasks and selects executor adapters that declare `executor_id`, `credential_mode`, `auth_probe`, `machine_readable_output`, `supports_jsonl_events`, `supports_patch_output`, `propose_only_required`.
- 6 open questions listed: transport shape (HTTP/socket/file-queue), queue backend (SQLite vs JSONL), worker spawn mechanism (Docker Compose vs subprocess), which service shape owns authenticated CLIs first, which provider adapter ships first (`codex-cli` vs `claude-cli`), and how strict `auth_probe` should be before a provider leaves `lab`.

## Relations & where used
Feeds directly into `service-control-plane-implementation-plan.md` (the staged build). References the ADR-161-era remote-ingress-adapter boundary concept.

## Status / caveats
Conclusion is explicitly bounded: COS should currently claim only "a worker surface and Engram Cloud service proof" and must **not** claim "a standalone autonomous service control plane" — that requires the `cosd` layer described here, which did not yet exist as of this research note.
