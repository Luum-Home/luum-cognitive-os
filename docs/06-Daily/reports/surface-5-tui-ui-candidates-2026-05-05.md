# Surface 5 (Custom TUI/UI) — Candidate Inventory & Initial Research

**Date**: 2026-05-05
**Author**: end-of-session research note
**Status**: research-only — no decision, no integration commitment
**Trigger**: ADR-172 (Multi-Surface UI Architecture) leaves the door open for a
fifth surface via separate ADR-173. User requested investigation of
open-source CLI/TUI tooling that could become the substrate for Surface 5

> **Discipline**: this is the *audit phase*, not the *integration phase*.
> upstream source. None of the candidates below are adopted yet. Each requires
> license verification, source-level review, and a documented match against a
> Surface 5 falsifiable claim before any code is written.

---

## Goal of Surface 5

User intent (paraphrased, 2026-05-05):

> Keep both: a flat CLI/TUI and a rich UI, without discarding either. The UI
> should model COS governance (lifecycle / doctrine / audit_class / hook reality)
> in ways Phoenix and Obsidian do not, while avoiding a heavy product detour.

Mapped to ADR-172 vocabulary:

- Surface 1 (CLI) stays as is — high-frequency, scriptable, pipe-friendly.
- Surface 5 (TUI/UI) is **additive**: a richer rendering layer over the same
  underlying state that the CLI already produces. The CLI is the
  source-of-truth; the TUI/UI is a renderer.
- Surfaces 2-4 (Phoenix, Engram Cloud, Obsidian) are not affected.

What Surface 5 must cover that no existing surface does:

1. Lifecycle states (sandbox / advisory / blocking / demoted / archived) —
   not modeled by Phoenix or Obsidian.
2. Doctrine proposals and demotions — same.
3. Audit_class and federation triggers — same.
4. Hook reality (which hooks actually fire vs which are wired) — same.
5. Live agent status / tool-call visualisation — partially in Phoenix as
   traces, but not in COS-governance shape.

What Surface 5 must NOT do:

- Replace the CLI surface (user explicit).
- Embed Phoenix or Engram Cloud rendering (those have their own surfaces).
- Be a generic "AI coding agent" — that is the substrate's job, not COS's.

---

## Top candidate (verified): sst/opencode → anomalyco/opencode

**Source**: [opencode.ai](https://opencode.ai) · GitHub `anomalyco/opencode`
(repo was renamed/transferred from `sst/opencode`).

**Verified facts (gh CLI metadata fetched 2026-05-05):**

| Field | Value |
|---|---|
| License | MIT |
| Stars | 155,216 |
| Primary language (per gh) | TypeScript |
| Last commit | 2026-05-05 (very active) |
| Homepage | opencode.ai |

**Caveat — source-language ambiguity:**

External 2026 write-ups describe opencode as *"Written in Go with the Bubble
Tea TUI framework"*, but `gh repo view` reports TypeScript as the primary
language today. Possible explanations (none verified yet):

- Recent rewrite Go → TypeScript.
- Mixed codebase where the TUI core is Go and the renderer/extensions are TS.
- Stale write-ups describing an older version.
- The `anomalyco/opencode` repo is a fork or rename and the original
  `sst/opencode` may have had a different primary language at the time the
  write-ups were authored.

**This must be resolved during the source-level audit before any adoption decision.**

**Positioning (per 2026 reviews):**

- Terminal-native: CLI + TUI.
- **Provider-agnostic** via Models.dev: 75+ LLM providers (Claude, GPT,
  Gemini, Groq, Bedrock, Azure, OpenRouter, Ollama local).
- Open-source MIT — adoption of code + patterns is allowed under our
  `license-policy.md`.
- Active community (155k stars, daily commits).

**Why opencode is the strongest single candidate:**

1. License is permissive (MIT) — we can lift code, not just patterns.
2. Tracking is verifiable (155k stars, daily activity, named maintainers).
3. Provider-agnostic dispatch overlaps with our `lib/dispatch.py` work
   (ADR-049). We could either align our dispatch with theirs or reuse theirs.
4. TUI rendering is the part we lack and they have, regardless of language.
5. MCP awareness (per write-ups) would let us plug Engram + other COS MCPs
   without writing custom adapters.

**Open questions for the audit:**

- What is the actual source language and TUI framework? (Go+Bubble Tea vs TS+Ink vs hybrid)
- How is "agent state" modeled? Could COS lifecycle / audit_class concepts
  be injected as first-class state, or only as opaque metadata?
- Is the architecture pluggable (extension points, hooks, themes) or
  monolithic (we would have to fork)?
- How does it handle long-running operator workflows (vs one-shot prompts)?
- What is the dependency footprint? Heavy framework or minimal?
- Does it expose its TUI primitives as a library, or only as a binary?

---

## Additional candidates provided by user

The user listed 13 additional repos to investigate. None are verified yet.
Each requires individual due-diligence per the framework above.

| Repo | URL | Notes (pre-audit) |
|---|---|---|
| openclaw/openclaw | github.com/openclaw/openclaw | Naming pattern suggests Claude-Code adjacent fork/clone. Audit needed. |
| qwibitai/nanoclaw | github.com/qwibitai/nanoclaw | Same pattern. |
| sipeed/picoclaw | github.com/sipeed/picoclaw | Sipeed is a known hardware vendor (RISC-V boards). Naming may indicate hardware/embedded angle. |
| openagen/zeroclaw | github.com/openagen/zeroclaw | Audit needed. |
| zeroclaw-labs/zeroclaw | github.com/zeroclaw-labs/zeroclaw | Possibly different project than openagen/zeroclaw despite shared name. |
| nanobot-ai/nanobot | github.com/nanobot-ai/nanobot | Different naming family. |
| HKUDS/nanobot | github.com/HKUDS/nanobot | HKUDS = HK university lab (Data Science). Likely different from nanobot-ai/nanobot. |
| TinyAGI/tinyclaw | github.com/TinyAGI/tinyclaw | Audit needed. |
| warengonzaga/tinyclaw | github.com/warengonzaga/tinyclaw | Possibly different project from TinyAGI/tinyclaw. |
| nullclaw/nullclaw | github.com/nullclaw/nullclaw | Audit needed. |
| nearai/ironclaw | github.com/nearai/ironclaw | NEAR Protocol's AI lab. Worth checking for blockchain-adjacent design. |
| heypinchy/pinchy | github.com/heypinchy/pinchy | Different naming family. |
| qhkm/zeptoclaw | github.com/qhkm/zeptoclaw | Audit needed. |

**Risk pattern**: many of these repo names (`*claw`, `nanobot`, `pinchy`,
`zeptoclaw`) follow naming conventions of small experimental projects.
Several may be:

- Tiny / abandoned forks of Claude Code.
- Experimental / research projects without production users.
- Aspirational marketing without working code (the same failure mode as

**Audit must classify each as REAL / DORMANT / ASPIRATIONAL** per the
`/component-reality-check` doctrine before any are considered for adoption.

---

## Audit framework for next session

For each candidate, produce a one-page entry with:

1. **License** — MIT/Apache-2.0/BSD allow code adoption; AGPL/SSPL/BSL block
   per `license-policy.md`.
2. **Activity signal** — last commit date, contributor count, star count
   trajectory (not absolute).
3. **Reality classification** — REAL (used in production by someone),
   DORMANT (works but not maintained), ASPIRATIONAL (claims > code).
4. **Source language and primary framework**.
5. **Architecture shape** — pluggable / monolithic / library / binary-only.
6. **Coverage of Surface 5 needs** — score 1-5 against each of the five
   needs listed above.
7. **Integration cost estimate** — order of magnitude (hours / days / weeks).
8. **Recommendation** — adopt-as-substrate / adopt-pattern-only /
   reference-only / reject.

After all candidates are scored, propose ADR-173 with:

- **One named substrate** (or a documented decision to build from scratch
  if no candidate scores high enough).
- **Real driver**: the first concrete artefact COS will render through
  Surface 5 (e.g., live `cos-boring-reliability` output as a TUI panel).
- **Falsifiable claim**: conditions under which Surface 5 would be revisited
  (e.g., "if Surface 5 is not used by any operator within 90 days, archive").
- **Boundary contract**: what Surface 5 does NOT do (no Phoenix overlap, no
  Engram Cloud overlap, no governance ADR creation — read-only renderer).

---

## Sources

- [OpenCode | The open source AI coding agent](https://opencode.ai/)
- [OpenCode vs Claude Code vs Cursor: AI Coding Agents Compared (2026)](https://computingforgeeks.com/opencode-vs-claude-code-vs-cursor/)
- [OpenCode vs Claude Code: Open-Source Freedom vs Agentic Power](https://www.openaitoolshub.org/en/blog/opencode-vs-claude-code)
- [Aider vs OpenCode vs Claude Code: 2026 CLI AI Coding Assistants Showdown](https://sanj.dev/post/comparing-ai-cli-coding-assistants)
- [Claude Code vs Codex CLI vs Aider vs OpenCode vs Pi vs Cursor (2026)](https://thoughts.jock.pl/p/ai-coding-harness-agents-2026)

---

## Status & next action

- **Status**: research-only. No code changes. No ADR-173 yet.
- **Next action (next session)**: run the audit framework above on opencode
  first (highest-confidence candidate), then triage the 13 user-provided
  repos in batches. Output: per-candidate one-pagers, then a synthesis
  proposing ADR-173 (or recommending no Surface 5 if the audit shows nothing
  meets the bar).
- **Cross-reference**: this report is the input to ADR-173. ADR-172 remains
  the authoritative UI architecture until ADR-173 lands.

---

## Cross-references

  pattern this audit must avoid.
- [ADR-172](../adrs/ADR-172-multi-surface-ui-architecture.md) — the
  architecture Surface 5 would extend.
- `rules/license-policy.md` — license allowlist/blocklist for adoption decisions.
- `scripts/aspirational_audit.py` — the REAL/DORMANT/ASPIRATIONAL
  classifier this audit invokes.

---

## Expanded candidate inventory (sonnet research, 2026-05-05)

> Audit scope: 60+ GitHub repos queried via `gh repo view` and `gh search repos`.
> License hard gate: AGPL/FSL/ELv2/SSPL/BSL → cannot adopt as substrate (pattern-only at best).
> Reality classification: REAL = active commits + production users; DORMANT = works but unmaintained; ASPIRATIONAL = claims without shipped code.
> Coverage score (0–5) against 5 Surface-5 needs: lifecycle states / doctrine proposals / audit_class / hook reality / live agent status.

### A. AI coding agent CLIs and TUIs

| Repo | License | Stars | Lang | Last push | Reality | SF5 score | Recommendation |
|---|---|---|---|---|---|---|---|
| [anomalyco/opencode](https://github.com/anomalyco/opencode) | MIT | 155k | TypeScript (100% TS, no Go) | 2026-05-05 | REAL | 1/5 | **substrate-candidate** |
| [charmbracelet/crush](https://github.com/charmbracelet/crush) | FSL-1.1-MIT¹ | 24k | Go | 2026-05-05 | REAL | 1/5 | pattern-only (license issue) |
| [Aider-AI/aider](https://github.com/Aider-AI/aider) | Apache-2.0 | 44k | Python | 2026-04-25 | REAL | 1/5 | reference |
| [aaif-goose/goose](https://github.com/aaif-goose/goose) | Apache-2.0 | 44k | Rust | 2026-05-05 | REAL | 1/5 | pattern-only |
| [continuedev/continue](https://github.com/continuedev/continue) | Apache-2.0 | 33k | TypeScript | 2026-05-05 | REAL | 0/5 | reference (IDE plugin, not TUI) |
| [cline/cline](https://github.com/cline/cline) | Apache-2.0 | 61k | TypeScript | 2026-05-05 | REAL | 0/5 | reference (VS Code extension) |
| [RooCodeInc/Roo-Code](https://github.com/RooCodeInc/Roo-Code) | Apache-2.0 | 24k | TypeScript | 2026-05-05 | REAL | 0/5 | reference (IDE plugin) |
| [openinterpreter/open-interpreter](https://github.com/openinterpreter/open-interpreter) | AGPL-3.0 | 63k | Python | 2026-05-04 | REAL | 1/5 | **BLOCKED** (AGPL) — reference only |
| [gptme/gptme](https://github.com/gptme/gptme) | MIT | 4k | Python | 2026-05-05 | REAL | 1/5 | reference |
| [sigoden/aichat](https://github.com/sigoden/aichat) | Apache-2.0 | 10k | Rust | 2026-02-23 | REAL | 0/5 | reference |
| [simonw/llm](https://github.com/simonw/llm) | Apache-2.0 | 12k | Python | 2026-05-05 | REAL | 0/5 | reference |
| [TheR1D/shell_gpt](https://github.com/TheR1D/shell_gpt) | MIT | 12k | Python | 2026-04-11 | REAL | 0/5 | reference |
| [gptscript-ai/gptscript](https://github.com/gptscript-ai/gptscript) | Apache-2.0 | 3k | Go | 2026-04-10 | REAL | 0/5 | reference |
| [code-yeongyu/oh-my-openagent](https://github.com/code-yeongyu/oh-my-openagent) | non-standard² | 56k | TypeScript | 2026-05-05 | REAL | 1/5 | **BLOCKED** (non-standard license) |
| [superset-sh/superset](https://github.com/superset-sh/superset) | ELv2³ | 10k | TypeScript | 2026-05-05 | REAL | 1/5 | **BLOCKED** (ELv2) |
| [anthropics/claude-code](https://github.com/anthropics/claude-code) | proprietary | 121k | Shell | 2026-05-04 | REAL | 2/5 | reference (our harness) |
| [Pythagora-io/gpt-pilot](https://github.com/Pythagora-io/gpt-pilot) | other | 34k | Python | 2026-04-17 | REAL | 0/5 | reference |

> ¹ FSL-1.1-MIT: Functional Source License with MIT future grant. Changes are source-available for 2 years, then flip to MIT. Not OSI-approved today. Cannot adopt as substrate until MIT flip. Can study patterns.
> ² oh-my-openagent uses a custom partial-license mentioning only third-party attribution. Code adoption requires legal review.
> ³ ELv2 (Elastic License 2.0) is a source-available license that restricts offering the software as a managed service. Cannot be adopted under COS license-policy.

### B. General top TUI apps (reference patterns, not AI-specific)

| Repo | License | Stars | Lang | Last push | Reality | Notes |
|---|---|---|---|---|---|---|
| [junegunn/fzf](https://github.com/junegunn/fzf) | MIT | 80k | Go | 2026-05-05 | REAL | Gold standard for TUI UX patterns |
| [jesseduffield/lazygit](https://github.com/jesseduffield/lazygit) | MIT | 77k | Go | 2026-05-04 | REAL | Best-in-class panel/keybinding model |
| [jesseduffield/lazydocker](https://github.com/jesseduffield/lazydocker) | MIT | 51k | Go | 2026-04-19 | REAL | Dashboard-style TUI over async state |
| [wagoodman/dive](https://github.com/wagoodman/dive) | MIT | 54k | Go | 2025-12-15 | DORMANT | Excellent layer-inspector pattern; no commits since Dec 2025 |
| [derailed/k9s](https://github.com/derailed/k9s) | Apache-2.0 | 34k | Go | 2026-04-21 | REAL | Best-in-class resource-list + live-watch TUI |
| [dlvhdr/gh-dash](https://github.com/dlvhdr/gh-dash) | MIT | 12k | Go | 2026-05-05 | REAL | Bubble Tea dashboard pattern, highly composable |
| [sxyazi/yazi](https://github.com/sxyazi/yazi) | MIT | 38k | Rust | 2026-05-05 | REAL | Async-first Ratatui app, great plugin model |
| [zellij-org/zellij](https://github.com/zellij-org/zellij) | MIT | 32k | Rust | 2026-05-05 | REAL | Plugin-capable terminal multiplexer |
| [helix-editor/helix](https://github.com/helix-editor/helix) | MPL-2.0 | 44k | Rust | 2026-05-03 | REAL | Modal editor; MPL-2.0 allows code reuse with file-level copyleft |
| [gitui-org/gitui](https://github.com/gitui-org/gitui) | MIT | 22k | Rust | 2026-04-23 | REAL | Ratatui-based; async git ops pattern |
| [ClementTsang/bottom](https://github.com/ClementTsang/bottom) | MIT | 13k | Rust | 2026-05-05 | REAL | Ratatui dashboard; multi-widget layout reference |
| [aristocratos/btop](https://github.com/aristocratos/btop) | Apache-2.0 | 32k | C++ | 2026-05-01 | REAL | C++ — unlikely substrate, good visual reference |
| [wtfutil/wtf](https://github.com/wtfutil/wtf) | MPL-2.0 | 17k | Go | 2026-05-01 | REAL | Module-based dashboard; MPL-2.0 OK with care |
| [darrenburns/posting](https://github.com/darrenburns/posting) | Apache-2.0 | 12k | Python | 2026-03-25 | REAL | Textual-based; excellent multi-pane layout |
| [charmbracelet/soft-serve](https://github.com/charmbracelet/soft-serve) | MIT | 7k | Go | 2026-05-04 | REAL | SSH-driven TUI; useful server-side TUI pattern |
| [yorukot/superfile](https://github.com/yorukot/superfile) | MIT | 17k | Go | 2026-05-05 | REAL | Bubble Tea file manager; good panel layout reference |
| [antonmedv/fx](https://github.com/antonmedv/fx) | MIT | 20k | Go | 2026-03-28 | REAL | Interactive JSON TUI; tree/scroll UX |
| [jarun/nnn](https://github.com/jarun/nnn) | BSD-2-Clause | 22k | C | 2026-04-19 | REAL | Extreme minimalism; not a substrate candidate |
| [jonas/tig](https://github.com/jonas/tig) | GPL-2.0 | 13k | C | 2026-05-01 | REAL | GPL-2.0 — **blocked** for adoption; reference only |
| [ranger/ranger](https://github.com/ranger/ranger) | GPL-3.0 | 17k | Python | 2026-04-26 | REAL | GPL-3.0 — **blocked** for adoption; reference only |
| [sachaos/viddy](https://github.com/sachaos/viddy) | MIT | 5k | Rust | 2026-02-05 | DORMANT | No commits since Feb 2026 |

### C. TUI frameworks

| Repo | License | Stars | Lang | Last push | Reality | Notes |
|---|---|---|---|---|---|---|
| [charmbracelet/bubbletea](https://github.com/charmbracelet/bubbletea) | MIT | 42k | Go | 2026-04-24 | REAL | **Tier-1 framework** — Elm architecture, used by lazygit, k9s, gh-dash, soft-serve, crush |
| [charmbracelet/lipgloss](https://github.com/charmbracelet/lipgloss) | MIT | 11k | Go | 2026-04-26 | REAL | Style engine for Bubble Tea |
| [charmbracelet/bubbles](https://github.com/charmbracelet/bubbles) | MIT | 8k | Go | 2026-04-26 | REAL | Reusable Bubble Tea components (table, list, progress, spinner) |
| [charmbracelet/glamour](https://github.com/charmbracelet/glamour) | MIT | 3k | Go | 2026-04-27 | REAL | Markdown rendering for terminal |
| [charmbracelet/gum](https://github.com/charmbracelet/gum) | MIT | 24k | Go | 2026-05-04 | REAL | Shell-scriptable Bubble Tea components |
| [charmbracelet/huh](https://github.com/charmbracelet/huh) | MIT | 7k | Go | 2026-04-22 | REAL | Form/prompt builder on Bubble Tea |
| [charmbracelet/vhs](https://github.com/charmbracelet/vhs) | MIT | 20k | Go | 2026-05-04 | REAL | TUI recording; useful for COS demo tooling |
| [ratatui/ratatui](https://github.com/ratatui/ratatui) | MIT | 20k | Rust | 2026-05-04 | REAL | **Tier-1 Rust framework** — immediate-mode, used by gitui, bottom, yazi, goose |
| [fdehau/tui-rs](https://github.com/fdehau/tui-rs) | MIT | 11k | Rust | 2023-08-06 | DORMANT | Predecessor to ratatui; archived in practice |
| [crossterm-rs/crossterm](https://github.com/crossterm-rs/crossterm) | MIT | 4k | Rust | 2026-04-08 | REAL | Low-level terminal driver under ratatui |
| [Textualize/textual](https://github.com/Textualize/textual) | MIT | 36k | Python | 2026-05-05 | REAL | **Tier-1 Python framework** — reactive, CSS-like, runs in terminal+browser |
| [Textualize/rich](https://github.com/Textualize/rich) | MIT | 56k | Python | 2026-04-12 | REAL | Rich text rendering; used standalone or under Textual |
| [vadimdemedes/ink](https://github.com/vadimdemedes/ink) | MIT | 38k | TypeScript | 2026-05-05 | REAL | **Tier-1 Node.js framework** — React-in-terminal; used by opencode |
| [anomalyco/opentui](https://github.com/anomalyco/opentui) | MIT | 11k | TypeScript | 2026-05-05 | REAL | Extracted TUI library from opencode; same org |
| [gdamore/tcell](https://github.com/gdamore/tcell) | Apache-2.0 | 5k | Go | 2026-05-05 | REAL | Low-level terminal cell API for Go |
| [gyscos/cursive](https://github.com/gyscos/cursive) | MIT | 4k | Rust | 2026-05-03 | REAL | Rust TUI framework; curses-style layout |
| [dankamongmen/notcurses](https://github.com/dankamongmen/notcurses) | other | 4k | C | 2026-04-28 | REAL | Not-curses; C library, license unclear |
| [gui-cs/Terminal.Gui](https://github.com/gui-cs/Terminal.Gui) | MIT | 11k | C# | 2026-05-05 | REAL | .NET TUI toolkit; irrelevant language for COS |
| [ArthurSonzogni/FTXUI](https://github.com/ArthurSonzogni/FTXUI) | MIT | 10k | C++ | 2026-05-04 | REAL | C++ TUI; not a substrate candidate |

### D. The 13 user-provided candidates (*claw / nanobot / pinchy family)

> Each repo was queried via `gh repo view --json`. Results as of 2026-05-05.

| Repo | License | Stars | Lang | Last push | Reality | Notes |
|---|---|---|---|---|---|---|
| [openclaw/openclaw](https://github.com/openclaw/openclaw) | MIT | 369k | TypeScript | 2026-05-05 | REAL | "Your personal AI assistant, any OS, any platform" — active, very large; likely Claude Code alternative |
| [qwibitai/nanoclaw](https://github.com/qwibitai/nanoclaw) | MIT | 29k | TypeScript | 2026-05-05 | REAL | Container-isolated, messaging-app integrations, memory, scheduled jobs |
| [sipeed/picoclaw](https://github.com/sipeed/picoclaw) | MIT | 29k | Go | 2026-05-05 | REAL | "Tiny, fast, deployable anywhere" — surprising: Sipeed known for hardware but this is Go AI agent |
| [openagen/zeroclaw](https://github.com/openagen/zeroclaw) | Apache-2.0 | 1.9k | Rust | 2026-03-15 | DORMANT | Last push Mar 2026; stars low; slower-moving branch of zeroclaw concept |
| [zeroclaw-labs/zeroclaw](https://github.com/zeroclaw-labs/zeroclaw) | Apache-2.0 | 31k | Rust | 2026-05-05 | REAL | Active Rust AI assistant infra; separate from openagen/zeroclaw |
| [nanobot-ai/nanobot](https://github.com/nanobot-ai/nanobot) | Apache-2.0 | 1.3k | Go | 2026-05-01 | REAL | MCP agent builder; small but active |
| [HKUDS/nanobot](https://github.com/HKUDS/nanobot) | MIT | 42k | Python | 2026-05-05 | REAL | HK Univ Data Science lab; "ultra-lightweight personal AI agent" — unrelated to nanobot-ai |
| [TinyAGI/tinyagi](https://github.com/TinyAGI/tinyagi) (fka tinyclaw) | MIT | 3.6k | TypeScript | 2026-03-30 | DORMANT | Renamed from tinyclaw; last push Mar 2026; slower pace |
| [warengonzaga/tinyclaw](https://github.com/warengonzaga/tinyclaw) | GPL-3.0 | 242 | TypeScript | 2026-05-04 | ASPIRATIONAL | 242 stars, GPL-3.0 **blocked**; "original Tiny Claw personal AI companion" — likely solo experiment |
| [nullclaw/nullclaw](https://github.com/nullclaw/nullclaw) | MIT | 7.4k | Zig | 2026-05-05 | REAL | Zig-based AI infra; unusual language choice; active |
| [nearai/ironclaw](https://github.com/nearai/ironclaw) | Apache-2.0 | 12k | Rust | 2026-05-05 | REAL | NEAR Protocol AI lab; "privacy, security, extensibility" — blockchain-adjacent design concerns |
| [heypinchy/pinchy](https://github.com/heypinchy/pinchy) | AGPL-3.0 | 155 | TypeScript | 2026-05-05 | ASPIRATIONAL | 155 stars, AGPL **blocked**; self-hosted wrapper on openclaw; very small |
| [qhkm/zeptoclaw](https://github.com/qhkm/zeptoclaw) | Apache-2.0 | 618 | Rust | 2026-05-05 | REAL | Active Rust binary for tools/memory/channels; small community |

### E. Additional discovery (from `gh search repos topic:tui`)

| Repo | License | Stars | Lang | Last push | Reality | Notes |
|---|---|---|---|---|---|---|
| [charmbracelet/crush](https://github.com/charmbracelet/crush) | FSL-1.1-MIT | 24k | Go | 2026-05-05 | REAL | Charm's own AI coding agent TUI built on Bubble Tea |
| [allinurl/goaccess](https://github.com/allinurl/goaccess) | MIT | 21k | C | 2026-04-23 | REAL | Real-time web log TUI; C-based |
| [saulpw/visidata](https://github.com/saulpw/visidata) | GPL-3.0 | 9k | Python | 2026-05-05 | REAL | GPL-3.0 blocked; data explorer TUI |
| [tstack/lnav](https://github.com/tstack/lnav) | BSD-2 | 10k | C++ | 2026-05-05 | REAL | Log file navigator with regex/SQL; reference only |
| [gcla/termshark](https://github.com/gcla/termshark) | MIT | 10k | Go | 2024-04-30 | DORMANT | No commits since Apr 2024 |
| [akavel/up](https://github.com/akavel/up) | Apache-2.0 | 9k | Go | 2024-09-05 | DORMANT | Pipe preview tool; no commits since Sep 2024 |
| [hatoo/oha](https://github.com/hatoo/oha) | MIT | 10k | Rust | 2026-05-05 | REAL | HTTP load tester with Ratatui TUI |

---

## Top picks for Surface 5 substrate consideration

### 1. anomalyco/opentui + anomalyco/opencode (TypeScript/Ink)

**Stars**: 10.8k (opentui) / 155k (opencode). **License**: MIT. **Reality**: REAL.

The discovery that `anomalyco/opentui` exists as a standalone library extracted from opencode's TUI layer resolves a key open question from the initial report. The opencode language question is now answered: it is 100% TypeScript (no Go). The TUI layer uses Ink (React-in-terminal). `opentui` is the primitives library; `opencode` is the full agent. COS already has TypeScript surface experience and the COS dispatch layer (ADR-049) could align with opencode's provider model. The substrate play here is to import opentui for layout/rendering primitives and build COS-specific panels (lifecycle states, hook reality, agent status) as React components. The dependency chain is clear: opentui → Ink → React → Node. Risk: Node runtime must be acceptable for a COS operator tool; this is a policy question, not a technical one.

**Recommendation**: first-priority substrate candidate. Audit opentui source next session before committing.

### 2. charmbracelet/bubbletea + bubbles + lipgloss (Go/Elm)

**Stars**: 42k (bubbletea). **License**: MIT. **Reality**: REAL.

The Charm stack is the most battle-tested Go TUI ecosystem: bubbletea provides the Elm-architecture message loop, lipgloss provides CSS-like styling, bubbles provides components (table, list, progress, viewport). Used in production by lazygit, k9s, gh-dash, and Charm's own crush (though crush uses FSL not MIT, the framework it runs on is MIT). COS is already partially Go (cmd/cos, cmd/cos-test per ADR-131). A Go-native TUI surface would compose naturally with the existing Go CLI layer. The model loop in bubbletea maps cleanly to COS lifecycle states as model fields and lifecycle transitions as messages. Dashboard panels (hook reality, agent status) map to bubbletea's viewport and list components. Risk: Elm architecture has a learning curve; team must internalize message-passing discipline.

**Recommendation**: strong substrate candidate if COS chooses Go runtime over Node. Go-first COS architecture makes this the lower-friction choice.

### 3. ratatui/ratatui (Rust/immediate-mode)

**Stars**: 20k. **License**: MIT. **Reality**: REAL.

Ratatui is the canonical Rust TUI framework (successor to the abandoned tui-rs). Used in production by gitui, bottom, yazi, and goose (Block's AI agent). The immediate-mode rendering model is explicit and predictable — no hidden state, every frame redrawn from scratch. For COS governance displays (which are read-mostly with occasional state updates), this is a good fit. zeroclaw-labs/zeroclaw and ironclaw both use Rust; if COS wanted to extract primitives from either, ratatui is the shared substrate. Risk: COS has minimal Rust surface today. Adding Rust means a new language in the toolchain.

**Recommendation**: substrate candidate if COS adopts Rust for Surface 5 and wants zero runtime dependencies. Lower priority than Bubble Tea or opentui given current COS language distribution.

### 4. Textualize/textual (Python)

**Stars**: 36k. **License**: MIT. **Reality**: REAL.

Textual is the most feature-rich Python TUI framework. It supports reactive programming, CSS-like styling, and can render in terminal or browser. COS is already Python-heavy (lib/, packages/, scripts/). A Textual-based Surface 5 would have zero new language runtime requirements. The browser rendering mode (via Textual Web) would let COS operators view governance state without a terminal if needed, blurring the line between TUI and web surface. Risk: Textual apps tend toward heavier weight than Bubble Tea; Python startup time is non-trivial for a tool that should feel snappy.

**Recommendation**: substrate candidate if COS wants Python-only toolchain and/or browser fallback. Strong second choice behind opentui if Node is acceptable.

### 5. zeroclaw-labs/zeroclaw (Rust)

**Stars**: 31k. **License**: Apache-2.0. **Reality**: REAL.

zeroclaw-labs is the canonical (more active) zeroclaw vs the dormant openagen fork. It describes itself as "fully autonomous AI personal assistant infrastructure, ANY OS, ANY PLATFORM". Apache-2.0 allows code adoption. The Rust + Ratatui combination makes it a potential source for agent lifecycle state management patterns. However, the project is not TUI-first — it is an infrastructure layer that happens to have a Rust TUI. The COS use case would be extracting its agent-state modeling, not its UI code.

**Recommendation**: pattern-only for agent state modeling. Not a TUI substrate candidate.

---

## Top picks for Surface 5 patterns to study (no adoption needed)

### 1. jesseduffield/lazygit (Go + Bubble Tea)

The gold standard for "complex async state visualized cleanly in a TUI". Lazygit renders a multi-panel view of git state (branches, commits, diff, stash) with keyboard-driven navigation and background git operations that update panels without blocking the user. The architecture — background workers emitting events, UI model subscribing and re-rendering — is the exact pattern COS needs for live agent status and hook reality displays. Study: its panel layout system, its background-refresh pattern, its keybinding model.

### 2. derailed/k9s (Go + tcell)

k9s manages Kubernetes clusters in a TUI with real-time resource watches, drill-down navigation, and log streaming. It is the closest existing analog to what COS Surface 5 needs: a governance dashboard over a live, updating system. k9s's "resource view → detail view → log/exec view" drill-down pattern maps directly to "component list → lifecycle detail → hook trace" in COS. Study: its resource-plugin system, its watch/update loop, its command palette.

### 3. dlvhdr/gh-dash (Go + Bubble Tea)

gh-dash renders GitHub PRs and issues in a configurable multi-column TUI. It uses Bubble Tea and bubbles components. The relevant pattern for COS: configurable column definitions that map to domain fields (author, status, review state) — analogous to mapping COS fields (lifecycle, audit_class, hook_reality). The configuration-driven column layout means operators could customize the Surface 5 view without code changes. Study: its column definition schema, its filter/sort model.

### 4. sxyazi/yazi (Rust + Ratatui)

Yazi is the best example of an async-first Ratatui app with a plugin system. Its architecture separates the async file I/O layer from the UI layer using message passing (like bubbletea's Elm model). The plugin system (Lua) would be worth studying as a pattern for COS operator customizations of Surface 5 panels. Study: its async task/message architecture, its plugin API surface.

### 5. Textualize/posting (Python + Textual)

Posting is a modern API client built on Textual. It is the best example of a complex multi-pane Textual app with form editing, response display, and keyboard navigation. It shows what Textual looks like at production scale before committing to that framework. Study: its layout composition, its modal dialog pattern, its keyboard handling.

---

## Aspirational/risky/abandoned (do not adopt)

| Candidate | Reason |
|---|---|
| [openinterpreter/open-interpreter](https://github.com/openinterpreter/open-interpreter) | AGPL-3.0 — hard blocked per license-policy.md |
| [heypinchy/pinchy](https://github.com/heypinchy/pinchy) | AGPL-3.0 — hard blocked; only 155 stars; wrapper over openclaw |
| [warengonzaga/tinyclaw](https://github.com/warengonzaga/tinyclaw) | GPL-3.0 — hard blocked; 242 stars; solo experiment, no community |
| [code-yeongyu/oh-my-openagent](https://github.com/code-yeongyu/oh-my-openagent) | Non-standard partial license; legal ambiguity; cannot adopt |
| [superset-sh/superset](https://github.com/superset-sh/superset) | ELv2 — source-available, not open-source; blocked |
| [charmbracelet/crush](https://github.com/charmbracelet/crush) | FSL-1.1-MIT — not OSI-approved today; 2-year delay before MIT flip; cannot adopt as substrate yet |
| [openagen/zeroclaw](https://github.com/openagen/zeroclaw) | Last push 2026-03-15; low stars (1.9k); superseded by zeroclaw-labs/zeroclaw |
| [TinyAGI/tinyagi](https://github.com/TinyAGI/tinyagi) | Dormant since Mar 2026; renamed from tinyclaw; no clear production use |
| [fdehau/tui-rs](https://github.com/fdehau/tui-rs) | Archived/abandoned; superseded by ratatui |
| [wagoodman/dive](https://github.com/wagoodman/dive) | No commits since Dec 2025; likely DORMANT |
| [sachaos/viddy](https://github.com/sachaos/viddy) | No commits since Feb 2026 |
| [gcla/termshark](https://github.com/gcla/termshark) | No commits since Apr 2024 — DORMANT |
| [akavel/up](https://github.com/akavel/up) | No commits since Sep 2024 — DORMANT |
| [coder/coder](https://github.com/coder/coder) | AGPL-3.0 — blocked; dev environment tool, not a TUI framework |
| [nearai/ironclaw](https://github.com/nearai/ironclaw) | NEAR Protocol blockchain-adjacent; adds crypto runtime concerns; adopt only if blockchain-native features are a requirement |
| [ranger/ranger](https://github.com/ranger/ranger) | GPL-3.0 — blocked for adoption |
| [jonas/tig](https://github.com/jonas/tig) | GPL-2.0 — blocked for adoption |
| [saulpw/visidata](https://github.com/saulpw/visidata) | GPL-3.0 — blocked for adoption |

---

## Sources

### AI coding agent CLIs and TUIs
- [anomalyco/opencode](https://github.com/anomalyco/opencode) — gh repo view
- [anomalyco/opentui](https://github.com/anomalyco/opentui) — gh repo view
- [charmbracelet/crush](https://github.com/charmbracelet/crush) — gh repo view + gh api license
- [Aider-AI/aider](https://github.com/Aider-AI/aider) — gh repo view
- [aaif-goose/goose](https://github.com/aaif-goose/goose) — gh repo view
- [continuedev/continue](https://github.com/continuedev/continue) — gh repo view
- [cline/cline](https://github.com/cline/cline) — gh repo view
- [RooCodeInc/Roo-Code](https://github.com/RooCodeInc/Roo-Code) — gh repo view
- [openinterpreter/open-interpreter](https://github.com/openinterpreter/open-interpreter) — gh repo view
- [gptme/gptme](https://github.com/gptme/gptme) — gh repo view
- [sigoden/aichat](https://github.com/sigoden/aichat) — gh repo view
- [simonw/llm](https://github.com/simonw/llm) — gh repo view
- [TheR1D/shell_gpt](https://github.com/TheR1D/shell_gpt) — gh repo view
- [gptscript-ai/gptscript](https://github.com/gptscript-ai/gptscript) — gh repo view
- [code-yeongyu/oh-my-openagent](https://github.com/code-yeongyu/oh-my-openagent) — gh repo view + gh api license
- [superset-sh/superset](https://github.com/superset-sh/superset) — gh repo view + gh api license
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — gh repo view
- [Pythagora-io/gpt-pilot](https://github.com/Pythagora-io/gpt-pilot) — gh repo view

### General top TUI apps
- [junegunn/fzf](https://github.com/junegunn/fzf) — gh repo view
- [jesseduffield/lazygit](https://github.com/jesseduffield/lazygit) — gh repo view
- [jesseduffield/lazydocker](https://github.com/jesseduffield/lazydocker) — gh repo view
- [wagoodman/dive](https://github.com/wagoodman/dive) — gh repo view
- [derailed/k9s](https://github.com/derailed/k9s) — gh repo view
- [dlvhdr/gh-dash](https://github.com/dlvhdr/gh-dash) — gh repo view
- [sxyazi/yazi](https://github.com/sxyazi/yazi) — gh repo view
- [zellij-org/zellij](https://github.com/zellij-org/zellij) — gh repo view
- [helix-editor/helix](https://github.com/helix-editor/helix) — gh repo view
- [gitui-org/gitui](https://github.com/gitui-org/gitui) — gh repo view
- [ClementTsang/bottom](https://github.com/ClementTsang/bottom) — gh repo view
- [aristocratos/btop](https://github.com/aristocratos/btop) — gh repo view
- [wtfutil/wtf](https://github.com/wtfutil/wtf) — gh repo view
- [darrenburns/posting](https://github.com/darrenburns/posting) — gh repo view
- [charmbracelet/soft-serve](https://github.com/charmbracelet/soft-serve) — gh repo view
- [yorukot/superfile](https://github.com/yorukot/superfile) — gh repo view
- [antonmedv/fx](https://github.com/antonmedv/fx) — gh repo view
- [jarun/nnn](https://github.com/jarun/nnn) — gh repo view
- [jonas/tig](https://github.com/jonas/tig) — gh repo view
- [ranger/ranger](https://github.com/ranger/ranger) — gh repo view
- [sachaos/viddy](https://github.com/sachaos/viddy) — gh repo view
- [allinurl/goaccess](https://github.com/allinurl/goaccess) — gh search repos topic:tui
- [saulpw/visidata](https://github.com/saulpw/visidata) — gh search repos topic:tui
- [tstack/lnav](https://github.com/tstack/lnav) — gh search repos topic:tui
- [gcla/termshark](https://github.com/gcla/termshark) — gh search repos topic:tui
- [akavel/up](https://github.com/akavel/up) — gh search repos topic:tui
- [hatoo/oha](https://github.com/hatoo/oha) — gh search repos topic:tui

### TUI frameworks
- [charmbracelet/bubbletea](https://github.com/charmbracelet/bubbletea) — gh repo view
- [charmbracelet/lipgloss](https://github.com/charmbracelet/lipgloss) — gh repo view
- [charmbracelet/bubbles](https://github.com/charmbracelet/bubbles) — gh repo view
- [charmbracelet/glamour](https://github.com/charmbracelet/glamour) — gh repo view
- [charmbracelet/gum](https://github.com/charmbracelet/gum) — gh repo view
- [charmbracelet/huh](https://github.com/charmbracelet/huh) — gh repo view
- [charmbracelet/vhs](https://github.com/charmbracelet/vhs) — gh repo view
- [ratatui/ratatui](https://github.com/ratatui/ratatui) — gh repo view
- [fdehau/tui-rs](https://github.com/fdehau/tui-rs) — gh repo view
- [crossterm-rs/crossterm](https://github.com/crossterm-rs/crossterm) — gh repo view
- [Textualize/textual](https://github.com/Textualize/textual) — gh repo view
- [Textualize/rich](https://github.com/Textualize/rich) — gh repo view
- [vadimdemedes/ink](https://github.com/vadimdemedes/ink) — gh repo view
- [gdamore/tcell](https://github.com/gdamore/tcell) — gh repo view
- [gyscos/cursive](https://github.com/gyscos/cursive) — gh repo view
- [dankamongmen/notcurses](https://github.com/dankamongmen/notcurses) — gh repo view
- [gui-cs/Terminal.Gui](https://github.com/gui-cs/Terminal.Gui) — gh repo view
- [ArthurSonzogni/FTXUI](https://github.com/ArthurSonzogni/FTXUI) — gh repo view

### *claw / nanobot / pinchy family
- [openclaw/openclaw](https://github.com/openclaw/openclaw) — gh repo view
- [qwibitai/nanoclaw](https://github.com/qwibitai/nanoclaw) — gh repo view
- [sipeed/picoclaw](https://github.com/sipeed/picoclaw) — gh repo view
- [openagen/zeroclaw](https://github.com/openagen/zeroclaw) — gh repo view
- [zeroclaw-labs/zeroclaw](https://github.com/zeroclaw-labs/zeroclaw) — gh repo view
- [nanobot-ai/nanobot](https://github.com/nanobot-ai/nanobot) — gh repo view
- [HKUDS/nanobot](https://github.com/HKUDS/nanobot) — gh repo view
- [TinyAGI/tinyagi](https://github.com/TinyAGI/tinyagi) — gh repo view (fka tinyclaw)
- [warengonzaga/tinyclaw](https://github.com/warengonzaga/tinyclaw) — gh repo view
- [nullclaw/nullclaw](https://github.com/nullclaw/nullclaw) — gh repo view
- [nearai/ironclaw](https://github.com/nearai/ironclaw) — gh repo view
- [heypinchy/pinchy](https://github.com/heypinchy/pinchy) — gh repo view
- [qhkm/zeptoclaw](https://github.com/qhkm/zeptoclaw) — gh repo view

### Prior sources (from initial report, 2026-05-05)
- [OpenCode | The open source AI coding agent](https://opencode.ai/)
- [OpenCode vs Claude Code vs Cursor: AI Coding Agents Compared (2026)](https://computingforgeeks.com/opencode-vs-claude-code-vs-cursor/)
- [OpenCode vs Claude Code: Open-Source Freedom vs Agentic Power](https://www.openaitoolshub.org/en/blog/opencode-vs-claude-code)
- [Aider vs OpenCode vs Claude Code: 2026 CLI AI Coding Assistants Showdown](https://sanj.dev/post/comparing-ai-cli-coding-assistants)
- [Claude Code vs Codex CLI vs Aider vs OpenCode vs Pi vs Cursor (2026)](https://thoughts.jock.pl/p/ai-coding-harness-agents-2026)

---

## Key findings summary (for ADR-173 input)

1. **opencode is 100% TypeScript/Ink** — the language ambiguity from the initial report is resolved. No Go, no Bubble Tea. The `anomalyco/opentui` library extracts the TUI primitives and is available as a standalone MIT package.
2. **Three credible substrate paths exist**: (a) TypeScript + Ink via opentui/opencode; (b) Go + Bubble Tea via Charm stack; (c) Python + Textual via Textualize.
3. **Charm's crush is not adoptable yet** — FSL-1.1-MIT blocks adoption for ~2 years. The framework underneath (bubbletea) is MIT.
4. **All 13 *claw repos exist** — none are aspirational-without-code. Three have license blocks (pinchy=AGPL, tinyclaw/warengonzaga=GPL-3.0) and two are dormant (openagen/zeroclaw, TinyAGI/tinyagi). None are strong Surface 5 substrate candidates — they are AI agent infrastructure, not TUI frameworks.
5. **openclaw/openclaw** (369k stars) dwarfs opencode (155k) and is the most-starred AI agent CLI in this audit. It is MIT-licensed and TypeScript. Its TUI approach is worth examining in the next session.
6. **AGPL blocklist hits**: open-interpreter, pinchy, coder/coder — all rejected.
7. **Pattern leaders to study before building**: lazygit (multi-panel async state), k9s (live resource governance TUI), gh-dash (configurable column layout), yazi (async plugin architecture).
