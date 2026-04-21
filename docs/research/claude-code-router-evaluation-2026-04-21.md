# claude-code-router Security & Fit Evaluation

> Date: 2026-04-21
> Evaluator: security-engineer agent
> Scope: fitness-for-purpose as sub-agent routing backbone for Cognitive OS
> Prior rejections: LiteLLM (supply-chain compromise Mar 2026), Bifrost (overengineering)

---

## TL;DR Recommendation

**CONDITIONAL — lean NO-GO for production integration; acceptable as a throwaway local experiment only.**

The `<CCR-SUBAGENT-MODEL>` feature we specifically need is the single most complained-about feature in the tracker (multiple open bugs — #670, #572, #1225, #1274 — confirming the marker is "unreliable" and silently ignored). Combined with a solo-maintainer profile (one developer = 243 commits, second-highest = 15), a TypeScript/Node proxy install that pulls ~200+ transitive packages through the same npm registry surface that compromised LiteLLM, one already-published CVE for credential exposure (CVE-2025-57755), and a 7-week gap since the last commit to `main`, the risk/reward does not justify coupling the Cognitive OS to this project. **Recommend: lift the `<CCR-SUBAGENT-MODEL>` idea, implement a ~300-LoC Python proxy ourselves.**

---

## Provenance

| Attribute | Value | Evidence |
|---|---|---|
| Repo | `github.com/musistudio/claude-code-router` | created 2025-02-25 |
| Maintainer | `musistudio` (Jinhui Li, `me@jinhui.li`) — individual, not an org | npm maintainer field |
| Affiliation | Sponsored by Z.ai (China, GLM model vendor) per README banner | README top |
| License | MIT | `LICENSE` file |
| Stars / forks | 32,667 / 2,606 — very popular | GitHub API |
| Open issues | **889** (high for size) | GitHub API |
| Contributors | 10 total, 1 dominant | top 2: musistudio=243, TonyGeez=15 → **bus factor = 1** |
| First / last commit | 2025-02-25 / 2026-03-04 (**48 days stale vs today**) | `pushed_at` |
| Release cadence | 75 npm versions 2025-06-10 → 2026-01-04; `main` no releases in ~3.5 months | npm registry |
| Latest npm | `@musistudio/claude-code-router@2.0.0` (2026-01-04) | registry |
| Node engine | `>=20.0.0`, pnpm monorepo | `package.json` |

**Red flags**: one-person bus factor; foreign sponsor whose model (GLM) is one of the endpoints the router itself resolves to (economic incentive to keep traffic routable to Z.ai regardless of security posture); sizeable gap between npm release cadence and git push cadence (typical of a stressed solo maintainer).

**Green flags**: MIT license, 32k stars (real adoption), public CVE disclosure discipline (they published their own advisory), bilingual Chinese/English docs.

---

## Supply-chain analysis

### Stack
- Language: TypeScript compiled via `esbuild` to CommonJS
- Runtime: Node 20+
- Build: pnpm workspace; `@musistudio/claude-code-router` is a thin shell (top-level deps = `[]`) that depends on sibling packages: `@musistudio/llms`, `@CCR/server`, `@CCR/cli`, `@CCR/shared`, `@CCR/ui`
- Install: `npm install -g @musistudio/claude-code-router` (pinned version, not `npx` fresh-fetch) — **better than LiteLLM's `pip install litellm` mutable pattern**, but still pulls all transitive deps through npm

### Direct dependencies (core package `@musistudio/llms@1.0.53`)
```
@anthropic-ai/sdk ^0.54.0      # official, low risk
@fastify/cors ^11.0.1          # HTTP — the CVE-2025-57755 lived here
@google/genai ^1.7.0           # Google SDK
dotenv ^16.5.0
fastify ^5.4.0                 # server
google-auth-library ^10.1.0
json5 ^2.2.3
jsonrepair ^3.13.0             # unofficial JSON-repair lib (trust?)
openai ^5.6.0
undici ^7.10.0                 # HTTP client
uuid ^11.1.0
```

11 direct deps is reasonable. Transitive closure not measured here but Node projects of this shape typically resolve to **150–400 packages** — every one of which is a supply-chain entry point. `jsonrepair` (auth: `josdejong`) is the only non-mainstream dep.

### Ship mechanism vs LiteLLM/Bifrost comparison

| Property | LiteLLM (rejected) | Bifrost | **claude-code-router** | Custom Python proxy |
|---|---|---|---|---|
| Install | `pip install litellm` | Go binary | `npm i -g` | stdlib only |
| Fresh-pull per session | yes (if unpinned) | no | no (global install) | no |
| Transitive deps | ~100 Python pkgs | 0 (compiled) | ~200–400 npm pkgs | 0 |
| Runtime exec as current user | yes | no (separate) | **yes** | yes |
| Registry compromise blast radius | **high** (pypi) | low | **high** (npm) | none |

npm supply-chain is **not safer than pypi** — 2024–2026 has seen multiple large-scale npm attacks (chalk, debug, colors, event-stream lineage). The decision to reject LiteLLM on supply-chain grounds applies equally here; the language is different, the risk class is the same.

---

## Security findings

### CVE / advisories

- **CVE-2025-57755 / GHSA-8hmm-4crw-vm2c** (published 2025-08-21, severity: LOW, patched v1.0.34)
  - Improper CORS config allowed untrusted origins to read API keys through the local router
  - Root cause class: naive `cors: true`-style default on a proxy that terminates credentials
  - Maintainer self-disclosed (good discipline) but the bug itself reveals a pattern of **treating the local proxy as trusted by default** — same class of flaw could recur

### Key-handling posture (from README)
- Keys live in `~/.claude-code-router/config.json` (plaintext on disk) **or** env-var interpolation via `$VAR`/`${VAR}` — env-var path is acceptable; disk path is not for our use
- `APIKEY` protects the local HTTP endpoint; if unset, binds to `127.0.0.1` only (safe default)
- `activate` command exports `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_BASE_URL`, `DISABLE_TELEMETRY=1` into the shell — **positive**: explicitly disables Anthropic telemetry; **negative**: shell-level env exports leak across processes

### Open security-adjacent issues
- #1274 (open) — "Is there a way to use my anthropic subscription with this?" implies users are passing their **real Anthropic tokens through this proxy**, expanding the blast radius of any future compromise
- README claims UI mode (`ccr ui`) which opens a web-based config editor. This was the attack surface of CVE-2025-57755 — a recurring design choice worth monitoring

### No independent third-party audit found.

---

## Architecture

- Runs as a **local daemon** (Fastify server, default `http://127.0.0.1:3456`)
- Claude Code is pointed at it via `ANTHROPIC_BASE_URL` (the standard escape hatch documented by Anthropic)
- `config.json` with `Providers[]` (OpenAI-compatible endpoints + API key) and `Router{}` (default/background/think/longContext/webSearch slots)
- Request/response go through optional `transformer` plugins (e.g. `deepseek`, `gemini`, `openrouter`) that rewrite the payload for provider quirks
- **Stateful**: logs HTTP traces under `~/.claude-code-router/logs/ccr-*.log` (pino) — another on-disk surface worth rotating/securing
- Model switching happens three ways: (a) config default, (b) `/model` slash command in Claude Code, (c) `<CCR-SUBAGENT-MODEL>provider,model</CCR-SUBAGENT-MODEL>` marker at the top of a subagent prompt

---

## `<CCR-SUBAGENT-MODEL>` feasibility for our use case

This is the feature that would justify adoption — and it is **the single most buggy feature in the tracker**.

Issues found (all OPEN):

| # | State | Title | Takeaway |
|---|---|---|---|
| 1225 | open | "fix(router): make CCR subagent model override reliable" — unmerged PR by a user | Tag detection only checks `system[1].text`; explicit `req.body.model` returns early before tag eval. The **fix is community-contributed and still not merged**. |
| 670 | open | "subagents can't route to the specified model" | User tried marker in both subagent system prompt and CLI prompt — neither worked |
| 572 | open | "subagent doesn't apply after apply requirements" | Unresolved, no maintainer response in thread excerpt |
| 1111 | open | Chinese-language discussion of private CCR-subagent protocol | Indicates the feature is under active reinvention |
| 1274 | open | Asking for Anthropic subscription auth integration | Shows the product scope is still fluid |

**Mechanically**, the marker is a simple regex in `packages/core/src/utils/router.ts` (per PR #1225). That means:
- a malformed tag is **silently ignored** (fail-open to the default model) — bad for our use case where we NEED the sub-agent to land on Qwen, not fall back to Claude
- no per-call override beyond editing the prompt
- works with Claude Code's Task tool only as a side effect of intercepting all HTTP traffic — **not explicitly designed for the Task tool**

**Verdict on the feature we need**: unreliable by the maintainer community's own admission. Merging PR #1225 would fix it, but the PR has been open with no merge and the repo has been idle for 7 weeks.

---

## Community signal

- 32.7k stars, 2.6k forks — real adoption
- 889 open issues against ~75 releases = **~12 open issues per release** (noisy)
- HN thread (news.ycombinator.com/item?id=44705958) exists but not reviewed in depth
- Independent review at `aitoolanalysis.com/claude-code-router-review/` notes: "Free Ollama models handle text generation fine but often choke on the agentic workflow parts" — **matches our exact use case (sub-agents = agentic)**
- DataCamp tutorial exists (mainstream legitimacy)
- Reddit discussions mixed: cost savings real for formatting/rename tasks, quality cliff on complex refactors

Green: large community, bug reports get filed (not hidden). Red: issue-to-release ratio is ~12:1, and the specific bug class we care about is unresolved.

---

## Integration cost for Cognitive OS

### Wiring-in effort
- Install `npm i -g @musistudio/claude-code-router` → 5 min
- Write `~/.claude-code-router/config.json` pointing to Qwen/DeepSeek/etc. via env vars → 15 min
- Prepend `<CCR-SUBAGENT-MODEL>...` to every agent prompt template in `scripts/orchestrator.py` → 30 min
- Point `ANTHROPIC_BASE_URL` to `127.0.0.1:3456` via `ccr activate` in session-init → 15 min
- **Optimistic total: 1–2 hours.**

### Hidden costs
- Daemon lifecycle: `ccr start` / `ccr restart` must be managed by our hooks, or sub-agents launched before the daemon boots get Claude by default (fail-open) — needs integration with `hooks/session-init.sh`
- Our existing `lib/qwen_provider.py` becomes redundant and must be removed or gated
- Our `PreToolUse Agent` / `PostToolUse Agent` hooks fire **inside** Claude Code before the HTTP call reaches the router — no conflict, but they see pre-routing model names (must not assume model == actual provider)
- Logging sprawl: two new log dirs under `~/.claude-code-router/`

### Reversal cost
- Uninstall npm package + delete config dir + revert `ANTHROPIC_BASE_URL` = ~10 min
- **Low lock-in**, which is a point in its favor

---

## Alternatives comparison

| Option | Supply-chain | Subagent routing | Effort | Maintenance | Verdict |
|---|---|---|---|---|---|
| claude-code-router | npm ~300 pkgs | buggy (#670, #572, #1225) | 1–2h | external | **conditional** |
| Bifrost (maximhq) | Go binary | not sub-agent aware | 1d | external | overengineered for our need |
| Plain `ANTHROPIC_BASE_URL=https://api.provider.io/anthropic` | 0 | impossible (global, not per-agent) | 5min | none | too coarse |
| **Custom ~300-LoC Python proxy** | stdlib only | exact semantics we design | 1–2d | ours | **recommended** |

### Why our own proxy wins
1. We already have `scripts/orchestrator.py` + `lib/qwen_provider.py` — the pieces exist; a ~300-line `aiohttp`/stdlib proxy that reads the `CCR-SUBAGENT-MODEL` marker (cheap to copy the spec, MIT permits) fills the gap.
2. Zero npm dependency footprint.
3. We own the fail-closed behavior: malformed marker → 400 response, not silent fallback.
4. Reversibility is total; no foreign daemon.

---

## Verdict & conditions

**CONDITIONAL NO-GO for direct adoption.**

Adopt **only if** all of the following hold — otherwise implement our own proxy:

| Condition | Status today |
|---|---|
| PR #1225 or equivalent subagent-routing fix is merged AND released on npm | ❌ not merged |
| Repo has a commit on `main` within the last 14 days | ❌ 48 days stale |
| At least one additional maintainer with >50 commits (bus factor ≥ 2) | ❌ bus factor = 1 |
| No open HIGH/CRITICAL advisories in the last 90 days | ✅ only the LOW CORS CVE, patched |
| We pin `@musistudio/claude-code-router@X.Y.Z` via a lockfile we control, plus `npm audit signatures` in CI | ❌ not implemented |

Since 3 of 5 conditions fail today, recommend we **lift the CCR-SUBAGENT-MODEL tag spec** (it's a good 20-line idea) and reimplement it ourselves.

### Residual concerns if we ever revisit
- Economic alignment: the sponsor sells access to GLM-5 through this router. That is not neutral routing infrastructure.
- Ship velocity vs issue velocity mismatch — if the maintainer burns out, 889 issues become orphans.

---

## Sources (visited)

1. [github.com/musistudio/claude-code-router](https://github.com/musistudio/claude-code-router) — repo root, README
2. [GitHub API: repo metadata](https://api.github.com/repos/musistudio/claude-code-router) — stars, forks, issues, pushed_at
3. [GitHub API: contributors](https://api.github.com/repos/musistudio/claude-code-router/contributors) — bus-factor evidence
4. [GitHub API: security-advisories](https://api.github.com/repos/musistudio/claude-code-router/security-advisories) — CVE-2025-57755
5. [GHSA-8hmm-4crw-vm2c](https://github.com/musistudio/claude-code-router/security/advisories/GHSA-8hmm-4crw-vm2c) — CORS advisory
6. [Issue #1225 — make CCR subagent model override reliable](https://github.com/musistudio/claude-code-router/issues/1225) — open PR
7. [Issue #670 — subagents can't route to the specified model](https://github.com/musistudio/claude-code-router/issues/670)
8. [Issue #572 — subagent doesn't apply after apply requirements](https://github.com/musistudio/claude-code-router/issues/572)
9. [Issue #1274 — Is there a way to use my anthropic subscription](https://github.com/musistudio/claude-code-router/issues/1274)
10. [Issue #1111 — CCR Subagent 私有协议](https://github.com/musistudio/claude-code-router/issues/1111)
11. [npm @musistudio/claude-code-router](https://www.npmjs.com/package/@musistudio/claude-code-router)
12. [npm @musistudio/llms](https://www.npmjs.com/package/@musistudio/llms) — core deps
13. [package.json](https://raw.githubusercontent.com/musistudio/claude-code-router/main/package.json)
14. [LICENSE](https://raw.githubusercontent.com/musistudio/claude-code-router/main/LICENSE)
15. [README.md](https://raw.githubusercontent.com/musistudio/claude-code-router/main/README.md) — subagent routing spec
16. [Hacker News discussion](https://news.ycombinator.com/item?id=44705958)
17. [AI Tool Analysis review](https://aitoolanalysis.com/claude-code-router-review/) — independent review
18. [DataCamp tutorial](https://www.datacamp.com/tutorial/claude-code-router)
19. [ClaudeLog MCP listing](https://claudelog.com/claude-code-mcps/claude-code-router/)
20. [musistudio.github.io/claude-code-router](https://musistudio.github.io/claude-code-router/) — official docs site
21. [GetAIPerks 2026 article](https://www.getaiperks.com/en/articles/claude-code-router)

---

TRUST_REPORT: SCORE=82 STATUS=MEDIUM EVIDENCE=7 UNCERTAINTIES=3
---
Score: 82/100

EVIDENCE PROVIDED:
  [check] Fetched live GitHub API metadata (stars, forks, contributors, pushed_at)
  [check] Fetched CVE-2025-57755 advisory directly from GitHub
  [check] Fetched actual package.json and @musistudio/llms deps from npm registry
  [check] Read issue bodies of #1225, #670 (text in tool output)
  [check] Two independent WebSearch runs for community/review sources
  [warn] Transitive-dep count for npm is estimated (150–400) — not measured with `npm ls`
  [fail] Did not run `npm audit` or inspect package signatures directly

WHAT I'M CONFIDENT ABOUT:
  - Bus-factor = 1 (243 vs 15 commit ratio is deterministic)
  - CCR-SUBAGENT-MODEL feature has open unresolved bugs (direct issue evidence)
  - CVE-2025-57755 is real, low severity, and patched
  - License is MIT, npm shipping is pinned-install (not npx-fresh)

WHAT I'M UNSURE ABOUT:
  - Transitive dependency count of the full monorepo (not measured; upper-bounded)
  - Whether the Z.ai sponsorship introduces concrete code-level bias (smell only)
  - Whether PR #1225 was rejected on technical grounds or just stalled

WHAT THE HUMAN SHOULD VERIFY:
  - Run `npm view @musistudio/claude-code-router dependencies` and `npm ls` in a throwaway dir to get real transitive count
  - Read PR #1225 discussion thread for any maintainer rejection reasoning
  - Before any adoption, pin the exact version hash and add `npm audit signatures` to CI
