# Sandbox Primitives Integration: Decision Research

**Date:** 2026-05-06
**Author:** Research agent (Claude Sonnet 4.6)
**Status:** RESEARCH-ONLY — no code changes
**Topic key:** `research/sandbox-primitives-integration`

---

## Executive Summary

Cognitive OS (COS) currently has no sandbox or microVM integration. All agent-generated code executes in the ambient host environment or inside user-managed Docker containers. The field has converged on three isolation tiers — OS-native primitives, embeddable runtime APIs, and managed cloud platforms — and the choice of first adapter determines COS's security posture, CI/CD portability, and operator trust curve for years. This document surveys ten sandbox systems (E2B, Daytona, Modal, ConTree, gVisor, Docker DockerWorkspace, Replit CoW, Bubblewrap/Firejail, macOS App Sandbox/Seatbelt, and OpenAI Codex sandbox internals), derives a comparative table, and recommends a sequenced adoption path.

---

## 1. Threat Model Context

Before comparing technologies, the threat model must be fixed. COS executes AI-generated Bash and Python commands via agent tool calls. The primary threats are:

1. **Accidental destruction** — `rm -rf ~/` or wide `git clean -fdx` from a confused agent.
2. **Secret exfiltration** — an agent reading `.env` or SSH keys outside the project root.
3. **Supply-chain execution** — a package install hooking into shell init files or calling home.
4. **Prompt-injection escalation** — malicious content in observed web pages or files driving the agent to execute harmful commands.

Docker containers share the host kernel, which means a container escape compromises the host. Kernel-level exploits are rare but the blast radius is catastrophic. Hardware-enforced microVMs raise the bar significantly; OS-native primitives (seccomp, Landlock, Seatbelt) add defence-in-depth without VM overhead.

The industry consensus as of 2026 is unambiguous: "shared-kernel container isolation (Docker/runc) isn't cutting it for executing untrusted AI agent code" (Northflank, 2026). AWS, Azure, and GCP have all migrated control planes toward hardware-enforced isolation.

---

## 2. Per-System Deep Dives

### 2.1 E2B (Firecracker)

**Company:** E2B Inc. (YC W23) | **License:** SaaS + BYOC/self-hosted options | **Source:** Apache 2.0 (SDK, template CLI)

E2B wraps Firecracker microVMs (the same VMM used by AWS Lambda and Fly.io) behind a developer SDK. Each sandbox boots a dedicated kernel in hardware-isolated memory, completely separated from host and sibling sandboxes. Cold start is approximately 150 ms for the managed SaaS offering; a "secure variant" is quoted at 80 ms. E2B's snapshot-restore path (following Firecracker's MAP_PRIVATE memory-mapping approach) can reach 28 ms when images are pre-warmed, by memory-mapping a snapshot file rather than re-booting the kernel.

**SDK ergonomics:** Official Python and TypeScript/JavaScript SDKs. Integration modules exist for LangChain, LlamaIndex, OpenAI, Anthropic, Mistral, and Llama. A `Sandbox.create()` call returns an object whose `.run_code(code, language)` method executes arbitrary Python, JavaScript, R, Java, or Bash with streaming stdout/stderr. Variables persist within a session context; sessions last up to 24 h on Pro tier.

**Pricing:** Pay-per-second compute. `$0.000014/s per vCPU` and `$0.0000045/GiB-s` for memory. Pro tier at `$150/month` unlocks 24 h sessions and higher concurrency. BYOC (your own AWS/GCP) substantially reduces egress costs; at 200 concurrent sandboxes the managed SaaS vs. BYOC differential is roughly 32% ($16,819 vs. $11,500/month in a Northflank benchmark).

**COS fit:** Excellent SDK ergonomics, strong isolation, Python-first — matches COS's primary execution language. Main drawback is external network dependency and cost at scale.

---

### 2.2 Daytona

**Company:** Daytona (raised $24 M Series A, February 2026) | **License:** Apache 2.0 (open-source core)

Daytona positions itself as "secure and elastic infrastructure for running AI-generated code." Its default isolation is Docker containers (shared kernel), but Kata Containers (microVM) is available on request. Cold starts are sub-90 ms due to container layer caching; Kata configuration extends this to approximately 200–300 ms. The platform distinguishes itself with stateful sandboxes — stopped sandboxes retain filesystem to object storage for later resumption — and a rich lifecycle model: `auto-stop` (default 15 min), `auto-archive` (7 days), `auto-delete`.

**SDK ergonomics:** Python, TypeScript, Ruby, Go, and Java SDKs. The `DaytonaSandbox` class exposes `create()`, `exec()`, `upload_file()`, `download_file()`, and `snapshot()`. Per the Mastra docs integration, Daytona is the default `WorkspaceProvider` in the Mastra agent framework as of 2026.

**Pricing:** Identical per-second compute rates to E2B ($0.000014/vCPU-s). No mandatory subscription tier — $200 free credits at signup, purely pay-as-you-go thereafter.

**COS fit:** Good for long-running stateful workflows (e.g., multi-step SDD apply phases). The Docker-default isolation is a concern for untrusted code; Kata must be explicitly opted into. Go SDK is relevant for COS's Go toolchain.

---

### 2.3 Modal Sandboxes

**Company:** Modal Labs | **License:** SaaS-only | **Isolation:** gVisor

Modal Sandboxes sit atop Modal's serverless container fabric and use gVisor as the isolation layer. gVisor inserts a user-space kernel (Sentry) between the containerized application and the host kernel, intercepting all system calls. This prevents direct kernel exploitation but introduces 10–30% I/O overhead on syscall-heavy workloads (2.2× for simple syscalls, 2.8× for file open/close in benchmarks).

Cold starts are advertised as sub-second; production observation ranges from 1–5 seconds depending on image size and platform capacity. Warm reuse stays under 200 ms, making Modal better suited for batch pipelines than interactive agent tools.

**SDK ergonomics:** Python SDK is complete; JavaScript/TypeScript and Go SDKs are in beta with incomplete parity. `modal.Sandbox.create(app, image=..., cpu=..., gpu=...)` returns a sandbox on which you call `.exec(cmd)`. GPU support is a genuine differentiator — A100 and H100 sandboxes are available for CUDA workloads.

**Pricing:** $0.0000394 per core/s plus $0.00000672 per GiB/s (with US 1.25× regional multiplier). Starter plan: $30/month credits, 100 containers, 10 GPU concurrency. Team plan: $250/month, 1,000 containers, 50 GPU concurrency.

**COS fit:** Best choice if COS agents need GPU-accelerated execution (ML model inference, CUDA code generation). Python-centrism limits polyglot COS workflows. No BYOC option is a vendor lock-in concern.

---

### 2.4 ConTree (Firecracker + Git-Like Branching)

**Company:** Nebius AI R&D | **License:** Apache 2.0 (SDK + MCP server) | **Isolation:** Firecracker microVMs

ConTree provides dedicated microVMs per execution with a branching execution model inspired by git: every execution produces an immutable filesystem snapshot, and agents can fork from any checkpoint, run N branches in parallel, and roll back instantly. This directly maps to agentic patterns like Monte Carlo Tree Search, best-of-N sampling, and speculative execution across multiple code-change hypotheses.

Cold start: 0.4–2 s when the rootfs image is cached (slower than E2B's warmed path, acceptable for batch). The ConTree team provides 7,000+ pre-built SWE-bench environments.

**SDK ergonomics:** Python SDK (`pip install contree-sdk`), MCP server (`uvx contree-mcp`), and REST API. Branching via `sandbox.fork(checkpoint_id)` is the key primitive not present in other platforms.

**Pricing:** Pay-per-execution rather than idle time, making it cost-efficient for intermittent branch-and-explore workflows.

**COS fit:** Uniquely suited for SDD apply-verify retry loops and parallel speculative agent execution. The branching model is architecturally aligned with COS's worktree divergence audit primitive. Main limitation is slower cold start vs. E2B.

---

### 2.5 gVisor

**Vendor:** Google (open source) | **License:** Apache 2.0 | **Isolation:** User-space kernel (syscall interception)

gVisor runs as `runsc`, an OCI-compatible container runtime. The Sentry component intercepts every syscall from the guest and either handles it in user space or makes a limited set of host syscalls. This eliminates most kernel-exploit vectors without requiring hardware virtualization, allowing it to run in environments where nested KVM is unavailable.

**Performance:** Startup adds only milliseconds (no VM boot). Syscall overhead is 2.2–2.8× for call-heavy operations; CPU-bound workloads see minimal impact. I/O-heavy workloads can degrade 10–30%. The systrap platform (seccomp SIGSYS interception) has lower syscall overhead than the KVM platform but suffers under nested virtualization.

**Deployment:** `containerd` + `runsc` on Kubernetes via `RuntimeClass: gvisor`. Used in production by Google Cloud Run, App Engine, and Modal.

**COS fit:** gVisor is a low-overhead, infrastructure-level hardening layer. Not a turnkey SDK. Best used as the backing runtime for a COS-managed container, not directly integrated. Relevant if COS deploys on Kubernetes.

---

### 2.6 Docker DockerWorkspace (OpenHands Pattern)

**Project:** OpenHands (All-Hands AI) | **License:** MIT | **Isolation:** Docker containers

OpenHands defines an abstract `BaseWorkspace` with three implementations: `LocalWorkspace` (in-process), `DockerWorkspace` (container), and `RemoteAPIWorkspace` (HTTP delegation). `DockerWorkspace` spawns a Docker container with `--cap-drop ALL --security-opt no-new-privileges`, then communicates over a REST+WebSocket API for command execution and file sync. Conversation automatically becomes a `RemoteConversation` when a `DockerWorkspace` is active.

**Isolation level:** Shared host kernel — the weakest of the surveyed options. A kernel exploit escapes the container. The model is appropriate for trusted agent code where the primary concern is accidental host modification, not adversarial code.

**Cold start:** Docker container startup: 1–10 s depending on image size and layer caching.

**COS fit:** The DockerWorkspace pattern is architecturally closest to COS's current non-sandboxed execution model. It would be the easiest migration path (lowest integration cost) but provides the weakest isolation guarantee. Daytona offers a drop-in replacement for `DockerWorkspace` with better lifecycle management, as demonstrated by the OpenHands-Daytona integration.

---

### 2.7 Replit CoW Block-Device Approach

**Company:** Replit | **License:** Proprietary (SaaS) | **Isolation:** Containers + CoW block device

Replit's architecture for safe AI agent development centers on a copy-on-write block device enabling constant-time filesystem snapshots regardless of Repl size. The approach separates production and development databases, restricts agent access to the development environment, and maintains an immutable append-only git remote as a recovery guarantee even if the entire filesystem is deleted.

The CoW semantics power Replit's "Snapshot Engine": when an AI agent makes file changes, Replit captures a versioned snapshot before and after. Rollback is instant (pointer swap, not data copy). Parallel sampling with 8 point improvement on SWE-bench benchmarks (72% to 80%) was demonstrated using this infrastructure.

**COS fit:** The CoW snapshot model is the inspiration for ConTree's branching approach and for COS's existing `state-snapshots.md` concept. The production system is Replit-proprietary but the pattern is open: use ext4 reflinks, btrfs snapshots, or ZFS clones at the filesystem layer before launching agent subprocesses. Applicable as a COS-internal primitive independent of any external SaaS.

---

### 2.8 Bubblewrap and Firejail (Lightweight Linux Sandboxes)

**Bubblewrap:** GNOME project, `~50 KB` binary, Apache 2.0. Uses `CLONE_NEWUSER` to create Linux namespaces without root. Flatpak uses it to sandbox every desktop application. On Linux, `bwrap --ro-bind / / --bind <repo-root> <repo-root> --unshare-all` creates a minimal filesystem view with write access only to the project directory. No root required.

**Firejail:** LGPL, setuid binary, richer out-of-box profiles. Ships with pre-built profiles for common apps. Requires elevated privileges, which creates a circularity problem for sandboxing agents that may already have compromised the process.

**Performance:** Near-zero cold start (microseconds — namespace creation only). No VM overhead.

**Isolation level:** OS-namespace-based (shared kernel). Defense against accidental host modification, not against kernel exploits. Equivalent to Docker's namespace model but without the daemon overhead.

**COS fit:** Bubblewrap is exactly what Claude Code itself uses on Linux (paired with Landlock for filesystem restrictions and seccomp for syscall filtering). It is already embedded in the COS host environment when Claude Code's sandboxing is enabled. The COS adapter path here is to expose the current bubblewrap policy to user configuration rather than adding a new dependency.

---

### 2.9 macOS App Sandbox / Seatbelt

**Vendor:** Apple | **Status:** App Sandbox (supported), `sandbox-exec`/Seatbelt (deprecated 2016, still functional) | **Isolation:** Syscall policy at XNU kernel level

macOS Seatbelt (`/usr/bin/sandbox-exec` with SBPL profiles) provides fine-grained syscall and file-path restrictions at the kernel level. Claude Code, Cursor, and Chrome all use it on macOS today. Key limitations for COS agents:

- Binary toggle on network: either fully permitted or fully denied (no per-domain rules).
- Package installation (Homebrew) requires explicit Seatbelt permission — agents that need `pip install` or `npm install` at runtime must be granted write access to the relevant paths.
- Custom policies are error-prone: common bugs include failing to block access to `~/Library` or dotfiles.
- App Sandbox (App Store entitlements model) requires code signing and a specific binary bundle structure — impractical for a CLI tool.

**Cold start:** Zero — Seatbelt applies to the existing process; no new process is spawned.

**COS fit:** Already in use by Claude Code's `--sandbox` flag on macOS. COS should expose Seatbelt policy generation as a configurable layer (project-specific writable root paths, network toggle) rather than building a new integration. The biggest gap is cross-platform consistency: the same agent prompt produces different sandbox behavior on macOS vs. Linux.

---

### 2.10 OpenAI Codex Sandbox Internals

**Project:** OpenAI Codex CLI | **License:** Apache 2.0 | **Isolation:** Landlock + seccomp (Linux); Seatbelt (macOS)

OpenAI Codex is the only major coding agent that ships with sandboxing enabled by default. The Linux implementation uses:

1. **Landlock** (kernel 5.13+): capability-based filesystem access control. Writable roots are explicitly listed; everything else is read-only.
2. **seccomp-BPF**: blocks network syscalls (`connect`, `bind`, `sendto`, etc.) unless `--full-auto` mode explicitly re-enables them.
3. Optional **Bubblewrap**: when `bwrap` is available, filesystem isolation is layered with `--ro-bind / /`, writable roots are overlaid with `--bind`, and `.git` and `.codex` paths are re-applied as read-only.

The key design insight is that `PR_SET_NO_NEW_PRIVS` is applied before seccomp, preventing privilege escalation within the sandbox. The `codex-linux-sandbox` helper binary serializes a policy from JSON config and applies both Landlock and seccomp atomically before exec-ing the agent process.

**COS fit:** Codex's sandbox architecture is the closest existing reference implementation to what COS needs. The policy abstraction (writable roots, network on/off, protected subpaths) maps cleanly to COS's workspace model. The `codex-linux-sandbox` binary is Apache 2.0 and could be adopted as a COS dependency for the "OS-native" sandbox tier.

---

## 3. Comparative Table

| System | Isolation Level | Cold Start (warm) | Pricing Model | SDK Languages | BYOC/Self-host | COS Adapter Difficulty |
|--------|----------------|-------------------|---------------|---------------|----------------|----------------------|
| E2B | Hardware (Firecracker microVM) | 80–150 ms | Per-second + sub tier | Python, TypeScript | Yes (AWS/GCP/Azure) | Low — clean Python SDK |
| Daytona | Container (default) / microVM (Kata) | 27–90 ms | Pay-as-you-go | Python, TS, Ruby, Go, Java | Yes (Apache 2.0 core) | Low — Go SDK available |
| Modal | User-space kernel (gVisor) | 1–5 s (production) | Per-second + plan tiers | Python primary; JS/Go beta | No | Medium — Python-only orchestration |
| ConTree | Hardware (Firecracker microVM) | 0.4–2 s | Pay-per-execution | Python, REST, MCP | Partial (SDK OSS) | Low — MCP server path |
| gVisor | User-space kernel (syscall intercept) | Milliseconds | Infrastructure (no SaaS) | Any OCI runtime | Yes | High — infra layer only |
| Docker (OpenHands) | Namespace (shared kernel) | 1–10 s | Infrastructure | Any Docker image | Yes (fully open) | Lowest — Docker daemon only |
| Replit CoW | Container + CoW snapshots | N/A (SaaS) | SaaS subscription | Proprietary | No | N/A — pattern inspiration only |
| Bubblewrap | Namespace (shared kernel) | ~0 ms | Free (OS primitive) | Any Linux process | N/A (host primitive) | Very Low — already in Claude Code |
| macOS Seatbelt | XNU syscall policy | ~0 ms | Free (OS primitive) | Any macOS process | N/A (host primitive) | Very Low — already in Claude Code |
| Codex Linux Sandbox | Landlock + seccomp + optional bwrap | ~0 ms | Free (Apache 2.0) | Any Linux binary | N/A (host primitive) | Low — binary can be vendored |

---

## 4. Integration Architecture for COS

### 4.1 The Adapter Interface

COS should define a `SandboxAdapter` protocol in `lib/sandbox/`:

```
SandboxAdapter
  .create(spec: SandboxSpec) -> SandboxHandle
  .exec(handle, cmd: str, env: dict) -> ExecResult
  .upload(handle, local_path, sandbox_path)
  .snapshot(handle) -> SnapshotRef
  .fork(handle, snapshot: SnapshotRef) -> SandboxHandle
  .destroy(handle)
```

This interface is purposely minimal — it maps to every reviewed system. The `fork` method is optional and signals ConTree-class branching capability. Implementations:

- `NullAdapter` (current behavior — passthrough to host shell)
- `BubblewrapAdapter` (Linux + macOS Seatbelt; zero new deps, zero cost)
- `E2BAdapter` (managed cloud; fastest path to hardware isolation)
- `DaytonaAdapter` (stateful workspaces; Go-friendly)
- `ConTreeAdapter` (branching SDD apply loops)

### 4.2 Isolation Tiers

COS should expose three configurable tiers in `cognitive-os.yaml`:

- **`none`** — current behavior; suitable for trusted local development.
- **`os-native`** — Bubblewrap (Linux) + Seatbelt (macOS) + Landlock/seccomp where available. Zero cost, zero external deps, near-zero latency. Suitable for all interactive agent sessions.
- **`microvm`** — E2B, Daytona (Kata mode), or ConTree. Required for untrusted code, production pipelines, and multi-tenant COS deployments.

### 4.3 Settings Schema Addition

```yaml
sandbox:
  tier: os-native          # none | os-native | microvm
  adapter: bubblewrap      # bubblewrap | e2b | daytona | contree
  writable_roots:
    - "."                  # project root
  network: deny            # allow | deny
  protected_paths:
    - ".env"
    - ".ssh"
    - "*.key"
  microvm:
    provider: e2b          # e2b | daytona | contree
    api_key_env: E2B_API_KEY
    session_timeout: 3600
```

---

## 5. Recommendation

### Primary Recommendation: BubblewrapAdapter as First Adapter

**Rationale:** Bubblewrap (Linux) and Seatbelt (macOS) are already used by Claude Code's own `--sandbox` flag. They require zero new runtime dependencies, zero cost, and add approximately 0 ms latency. The `os-native` tier closes the most common threat (accidental host modification, secret exfiltration) for 100% of COS users without requiring any API key or network call. The Codex Linux Sandbox binary (`codex-linux-sandbox`, Apache 2.0) provides a reference implementation whose policy model maps directly to COS's workspace abstraction.

**Implementation cost:** 1–2 days. Write a `BubblewrapAdapter` that wraps agent subprocess launches, reads `sandbox.writable_roots` from `cognitive-os.yaml`, and constructs the `bwrap` invocation with `--ro-bind / /`, workspace bind mounts, and a seccomp network filter.

### Secondary Recommendation: E2BAdapter for Cloud/Production Tier

When COS is used in a multi-tenant or CI/CD pipeline context, the `os-native` tier is insufficient — a compromised container can still escape shared-kernel isolation. E2B's Firecracker microVM adapter provides hardware-enforced isolation with the best developer ergonomics (polished Python SDK, 80–150 ms cold start, streaming stdout/stderr, BYOC for data-residency requirements).

**Implementation cost:** 1 day. E2B's Python SDK is straightforward. The primary design decision is session pooling — maintaining a warm pool of pre-booted microVMs reduces perceived latency from 150 ms to effectively zero for interactive sessions.

### Tertiary Recommendation: ConTreeAdapter for SDD Branching

ConTree's branching model — fork from checkpoint, run N branches in parallel, select winner — directly maps to COS's SDD apply-verify retry loop. When `sdd-apply` fails, instead of a sequential retry the orchestrator can fork N parallel branches with different fix strategies and pick the first passing branch. The Apache 2.0 MCP server makes integration trivial.

**Implementation cost:** 0.5 days for MCP server wiring. The branching semantic requires a small orchestrator change in the SDD apply-verify cycle.

### What NOT to Adopt

- **Modal**: Python-only orchestration and no BYOC disqualifies it for COS's polyglot multi-harness architecture.
- **gVisor directly**: Valuable as a backing runtime for Kubernetes deployments, but not a COS SDK integration target — it belongs in infra configuration.
- **Docker DockerWorkspace pattern only**: Weakest isolation, covered by Daytona's superset.
- **macOS App Sandbox entitlements**: Requires binary signing infrastructure that conflicts with COS's CLI distribution model.

---

## 6. Open Questions for Operator Decision

1. **Data residency requirement?** If yes, BYOC is mandatory → E2B BYOC or Daytona self-hosted over managed SaaS.
2. **GPU workloads in agent tools?** If yes, add Modal as a fourth adapter for GPU-accelerated sandboxes.
3. **Windows support priority?** Currently only Codex's WSL2 path handles Windows; all microVM options require KVM (Linux). COS on Windows would need a WSL2 shim or Docker-based fallback.
4. **Compliance/regulated industries?** Confidential Computing (AMD SEV-SNP, Intel TDX) would be the next tier above Firecracker — none of the reviewed platforms expose this as a COS-level API yet.

---

## Sources

1. [Daytona vs E2B in 2026: which sandbox for AI code execution? — Northflank](https://northflank.com/blog/daytona-vs-e2b-ai-code-execution-sandboxes)
2. [Top AI sandbox platforms in 2026, ranked — Northflank](https://northflank.com/blog/top-ai-sandbox-platforms-for-code-execution)
3. [How to sandbox AI agents in 2026: Firecracker, gVisor, runtimes & isolation strategies — Manveer C.](https://manveerc.substack.com/p/ai-agent-sandboxing-guide)
4. [E2B | The Enterprise AI Agent Cloud](https://e2b.dev/)
5. [E2B vs Daytona: Sandbox Comparison for Platform Engineers — ZenML](https://www.zenml.io/blog/e2b-vs-daytona)
6. [ConTree — Sandboxed Code Execution with Git-Like Branching for AI Agents](https://contree.dev/)
7. [Kata Containers vs Firecracker vs gVisor — Northflank](https://northflank.com/blog/kata-containers-vs-firecracker-vs-gvisor)
8. [gVisor Documentation — gvisor.dev](https://gvisor.dev/docs/)
9. [How I built sandboxes that boot in 28ms using Firecracker snapshots — DEV Community](https://dev.to/adwitiya/how-i-built-sandboxes-that-boot-in-28ms-using-firecracker-snapshots-i0k)
10. [OpenHands Docker Sandbox — docs.openhands.dev](https://docs.openhands.dev/sdk/guides/agent-server/docker-sandbox)
11. [Building a Secure OpenHands Runtime with Daytona Sandboxes — daytona.io](https://www.daytona.io/dotfiles/building-a-secure-openhands-runtime-with-daytona-sandboxes)
12. [Implementing a secure sandbox for local agents — Cursor Blog](https://cursor.com/blog/agent-sandboxing)
13. [Replit's Snapshot Engine Enables Safe AI Agent Development — ASCII News](https://ascii.co.uk/news/article/news-20251219-2c4c6a98/replits-snapshot-engine-enables-safe-ai-agent-development)
14. [A deep dive on agent sandboxes — Pierce Freeman](https://pierce.dev/notes/a-deep-dive-on-agent-sandboxes)
15. [Firecracker microVM architecture — firecracker-microvm.github.io](https://firecracker-microvm.github.io/)
16. [Coding Agent Sandbox: Secure Environments for AI-Generated Code — Bunnyshell](https://www.bunnyshell.com/guides/coding-agent-sandbox/)
17. [Modal Sandbox for AI Agents (2026) — Morph](https://www.morphllm.com/modal-sandbox)
18. [Daytona Sandbox Documentation](https://www.daytona.io/docs/en/sandboxes/)
19. [Sandboxing AI Agents in Linux — Senko Rašić](https://blog.senko.net/sandboxing-ai-agents-in-linux)
20. [Awesome Code Sandboxing for AI — GitHub/restyler](https://github.com/restyler/awesome-sandbox)

---

*Word count: ~3,200 words. Research methodology: 8 web searches, 12 web fetches, zero code changes.*
