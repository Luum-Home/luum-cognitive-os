# Cross-check Part B: Sandbox & MCP (2026-05-08)

Phase: reconstruction. Direct verdicts by item; focus on real delta vs claim.

---

## 🔍4 Bubblewrap / sandbox-exec

**Verdict:** EQUIVALENT (minor plumbing delta, no technical advantage over upstream)

**Current local logic:**
- `packages/agent-lifecycle/lib/sandbox_adapter.py` (146 LOC) — selects backend by `platform.system()`, builds argv for `bwrap` (Linux) o `sandbox-exec` (macOS), exposes `SandboxPlan` dataclass + `run_sandboxed()` wrapper over `subprocess.run`.
- Wiring in `lib/dispatch.py` (~line 580) gated by `skill_requirements.require_sandbox=true`. Default = sandbox OFF.
- `scripts/cos-sandbox-run` CLI dry-run/JSON.
- microvm/contree → `adapter_contract` puro (without runtime), requiere env `COS_SANDBOX_MICROVM_RUNNER`.
- E2B: `packages/e2b-sandbox/` listed as thin_wrapper; no appeared in grep — confirmed there is no wiring real a E2B.

Applied bubblewrap policy:
```
bwrap --ro-bind / / --dev /dev --proc /proc --chdir <ws> [--unshare-net] --bind <writable> <writable>
```
sandbox-exec genera profile inline `(deny default)(allow process*)(allow file-read*)(allow file-write* (subpath ...))[(allow network*)]`.

**What research promised (ADR-232):** "Slices A–E implemented (2026-05-07)". Adapter dependency-free, opt-in native-only, no fallback implicit, microvm/contree contract-only.

**Code reality:** Slice A-B verified in code (adapter + dispatch preflight + manifest contract test). I did not audit Slice E, but the base exists. **NOT aspirational** — the module exists, is functional, and is wired to dispatch. The important point: this code does NOT "adopt" bubblewrap as a dependency; it is an argv builder of about 50 lines around `bwrap`/`sandbox-exec` invoked as subprocesses. It is exactly what the research recommends (host-native, no embed).

Compared with upstream (`containers/bubblewrap`): bwrap is a CLI binary of C under LGPL-2.1; nobody "adopts" it as a library. The idiomatic way to use it IS via subprocess argv. Our implementation is standard and matches the pattern used by flatpak/toolbox.

**Actual isolation provided vs promised:**
- Linux: equivalent to flatpak-spawn basic. `--ro-bind /` leaves the whole host FS visible read-only (is not a real chroot). Network unshared OK. Missing: `--die-with-parent`, `--new-session`, namespaces UID/PID, seccomp filter. For a write-capable agent, covers filesystem, does not provide defense-in-depth against exfil via unusual syscalls or sensitive reads.
- macOS: profile Seatbelt minimal. `(allow process*)` allows `fork/exec` of any binary. No mach IPC restriction, no keychain restriction. Profile fairly loose.

Research promised "permission boundaries below the prompt layer" — yes, it provides them. It did NOT promise gVisor-style hardening, so the gap between claim and code is small.

**Recommendation:** Code is OK as Slice A. Concrete improvements (no rewrites):
1. Add `--die-with-parent --new-session --cap-drop ALL` to the bwrap argv (1 line).
2. Tighten Seatbelt profile (`(deny process-fork)` except an allowlist).
3. Audit that `e2b-sandbox/` thin_wrapper is not listed as active in manifests if it has no wiring.

**Effort:** S (1-2h) for hardening of the argv. Anything additional (Landlock, seccomp BPF, microvm real) → M-L and out of scope reconstruction.

---

## 🔍5 fastmcp (jlowin/fastmcp)

**Verdict:** EXTERNAL_BETTER in what we delegate (decorator + transport stdio); EQUIVALENT in exposed surface. NO reimplementsmos fastmcp — we use it.

**Current local logic:**
- `mcp-server/cos_mcp.py` (870 LOC) and `packages/mcp-server/cos_mcp.py` (symlink, 870 LOC) — **importa `from fastmcp import FastMCP`** and registra 8 tools with `@mcp.tool`. Transport `mcp.run()` delegado a fastmcp.
- `packages/advisor-mcp/advisor_server.py` (577 LOC) — same pattern: `FastMCP("advisor")` + `@mcp.tool consult_advisor`.
- `packages/advisor-mcp/requirements.txt`: `fastmcp>=2.0.0`.
- `cos-package.yaml` declares dependency `fastmcp` with `install: pip install fastmcp`.
- `_FastMCPCompat`: local stub of ~15 LOC ONLY so unit tests run without installing fastmcp; `run()` raises `RuntimeError("fastmcp is required")`. It is NOT a reimplementation, it is a test seam.

**What research promised (ADR-231):** "MCP server surface adopted, Slices A–C". Reuse the server pre-existing, add package symlink, manifest, contract tests.

**Code reality:** Matches the claim. ADR-231 is transparent: it says "predates ADR-231" (that is, the server already existed and only the package was formalized). 8 exposed tools: engram_search, engram_save, task_state, rules_lookup, metrics_summary, quality_check, skill_suggest, cos_status (per ADR §A). There is a real symlink `mcp-server/cos_mcp.py` ↔ `packages/mcp-server/cos_mcp.py` (both 870 identical LOC).

**What we do NOT have vs upstream fastmcp** (according to the README of jlowin/fastmcp 2.x):
- We do not use `@mcp.resource` ni `@mcp.prompt` (only `@mcp.tool`). Fastmcp supports all three types.
- We do not use integrated auth of fastmcp 2.x (OAuth, bearer).
- We do not use transport SSE/HTTP — only stdio. Fastmcp supports ambos.
- We do not use `FastMCP.from_openapi()` or the Client. Only server stdio.

This is a reasonable subset; it is not critical debt.

**Recommendation:**
1. Raise version pin (`fastmcp>=2.0.0` is lax — pin a `>=2.x,<3` in advisor-mcp; the other server does not declare a version either).
2. Consider exposesr Engram as `@mcp.resource` instead of `@mcp.tool engram_search` (resources cache client-side, better UX in Claude Code).
3. NO reescribir nada custom; fastmcp upstream covers todo lo razonable.

**Effort:** S (30 min) for version pin. M (half day) for migrar a resources/prompts if there is concrete value.

---

## 🔍7 Deferred tool loading + ToolSearch (ADR-236)

**Verdict:** OURS_BETTER in governance/audit; EQUAL_OR_INFERIOR in runtime mechanism (Claude Code already does it natively). The real delta is manifest-driven planning + change detection, not the deferring itself.

**Current local logic:**
- `packages/agent-lifecycle/lib/deferred_tool_loading.py` (177 LOC) — manifest YAML driven (`manifests/deferred-tool-loading.yaml`), planner `plan_tool_loading()` that decides visible/deferred according to token threshold, `toolsearch_index()` that returns compact metadata, `list_changed()` with hash sha256 + state persisted in `.cognitive-os/metrics/deferred-tool-loading-state.json`.
- `provider_native_defer_payload()` — gate explicit in env `COS_NATIVE_DEFER_LOADING_PROVIDERS`. By default returns `native_defer_loading_supported=false` with reason "provider_api_not_available". **It is honest: does not claim to implement the protocol MCP `notifications/tools/list_changed` — only prepares it.**
- Wiring in `lib/dispatch.py:109` and `lib/dispatch.py:620` — uses `plan_tool_loading()` to decide whether to emit the payload with index to the provider.
- CLI `scripts/cos-deferred-tool-plan`.

**What research promised (ADR-236):** "Slices A–D implemented, 85% token reduction". The "85%" does not appear in the code; it is a research claim, not an ADR claim (the ADR does not assert that number).

**Code reality:** Slices A-D exist as planning + change detection helpers. Slice E (real `notifications/tools/list_changed` transport) is explicitly listed as NOT implemented in the ADR (line 54): *"Real MCP notifications/tools/list_changed transport emission; local detection is implemented and ready to feed it when host APIs expose the hook."* That is honest, not aspirational.

**Comparison with native Claude Code ToolSearch (visible in this same prompt):**
- Claude Code exposes deferred tools in `<system-reminder>` with their names and a native `ToolSearch` tool that loads schemas via `select:`/keyword query. Already works, without our manifest.
- Our code does NOT replace that — it complements it for cases where the provider is NOT Claude Code (Cursor, Windsurf, futures providers).

**Real delta over native ToolSearch:**
1. **Manifest-driven policy** — `always_available`, `load_mode: eager|deferred`, `category` declared in YAML, not hardcoded in the client. Claude Code decides alone.
2. **Change detection with hash** — `list_changed()` allows an external orchestrator to know when the set changed without relisting.
3. **Provider-agnostic** — the payload can be emitted to any MCP host via COS_NATIVE_DEFER_LOADING_PROVIDERS.
4. **Token threshold gate** — the bundle is deferred only if it exceeds `toolsearch_threshold_tokens` (default 10k). Claude Code applies its own heuristic.

**What is NOT a real delta:**
- The "deferring" itself already exists natively in Claude Code (this prompt is proof). In Claude Code sessions, our `provider_native_defer_payload()` returns `supported=false` por default, so the manifest remains an informational blueprint, not an operational one.
- "85% token reduction" — is not measured in this repo (I did not find calibrated metrics in `.cognitive-os/metrics/`). It is a research claim, not supported by local evidence. **Mark as ASPIRATIONAL CLAIM in research, NO in ADR-236**.

**Recommendation:**
1. Keep `deferred_tool_loading.py` as a layer of governance multi-provider (is worth it).
2. Document explicitly in ADR-236: "in Claude Code the module is a no-op (the host handles deferring); real value emerges when integrated with Cursor/Windsurf or an own MCP host".
3. Do NOT publish the "85% reduction" without measuring. Run a test with/without manifest in Cursor (which has MCP native limited) and publish the real delta.
4. Remove the "85%" from research if not measured or calibrate it.

**Effort:** S (15 min) for clarify status in ADR. M (1 day) for benchmark real of reduction.

---

## Resumen ejecutivo

| Item | Verdict | Aspirational? | Action |
|---|---|---|---|
| 🔍4 Bubblewrap/sandbox-exec | EQUIVALENT | No (Slice A–B verified) | Hardening argv (1-2h) |
| 🔍5 fastmcp | EXTERNAL_BETTER + EQUIVALENT in our surface | No (we use it genuinely) | Pin version, optional resources |
| 🔍7 Deferred tool loading | OURS_BETTER in governance | "85%" yes — unmeasured claim | Document status, measure or remove number |

**Cross-check findings:**
- The 3 ADRs (231/232/236) have honest status: they declare which slices exist and which do NOT. None is aspirational in the sense of "claim without code".
- The aspirational claim is in the **external research narrative** ("85% token reduction", "adopt-code via subprocess implies deeper integration than reality"). The code and ADRs are more conservative than how the research presents them.
- Pattern: COS is using bubblewrap/fastmcp/ToolSearch as **adapters/governance layers**, not as reimplementations. That is technically correct. The narrative of "adopt-code" overstates the depth.

**Main risk:** publishing the "85% reduction" number without measuring it erodes credibility. The rest of the code supports the claims.
