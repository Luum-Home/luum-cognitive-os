---
type: methodology-synthesis
source: docs/05-Methodology/setup/dependencies.md
provenance: "Single source of truth for every tool, runtime, and library Cognitive OS uses, organized by category with install commands, so a developer or CI worker can provision the exact dependency surface without guessing."
---

## What it is

The consolidated dependency manifest/reference for Cognitive OS: a quick-reference table plus nine detailed sections covering system tools, Go, Python, curl/binary installs, security tools, Claude Code specifics, Docker infrastructure services, and verification.

## Key mechanics

- Quick reference: required tools are Python ≥ 3.11, `uv`, `jq`, `gh`, Git ≥ 2.30, Claude Code; Go (via goenv) is required only for TUI/CLI work; engram CLI is recommended; Docker, CLAMP, semgrep, aguara, parry-guard, mcp-scan, cosmic-ray, promptfoo, and GoReleaser are optional.
- System tools install via Homebrew (`jq`, `goenv`, `gh`, `uv`, GoReleaser); GoReleaser install/validation is scripted (`scripts/install-goreleaser.sh --install` / `--check --snapshot-smoke`) and follows official guidance (Homebrew first, `go install` fallback) without touching release credentials — publishing stays GitHub Actions/tag-driven.
- Go: version pinned in `.go-version` (currently `1.25.6`), installed via `goenv install/global`; only required for `cmd/cos`/`cmd/cos-test` — core hooks/rules/SDD pipeline work without Go.
- Python: requires ≥ 3.11 per `pyproject.toml`; optional dependency groups are `llm` (litellm, redis), `web` (fastapi, uvicorn), `observability` (opik, langfuse), `memory` (cognee), `guardrails` (nemoguardrails), `jupyter`, `crawling` (crawl4ai), `testing` (pytest + plugins + mutmut), `security` (empty — tools installed separately), `enforcement` (pre-commit, ruff, vulture, import-linter, pytest-cov, diff-cover), and a `dev` meta-group installing all of the above. Install via `uv venv && uv pip install -e ".[dev]"` (or targeted groups).
- Outside-venv tools: `cosmic-ray` (mutation testing, used in a CI workflow) and a global `pyyaml` install (needed by pre-commit import checks that run outside the venv).
- curl/binary installs: CLAMP (project migration tool, via a raw GitHub curl+chmod) and the engram CLI (via `npx -y @anthropic/engram`, configured in `~/.claude/settings.json` `mcpServers`, with graceful degradation via `lib/engram_client.py` when unavailable).
- Security tools (all optional, hooks degrade gracefully without them): semgrep, aguara (+ mcp-aguara), parry-guard, mcp-scan, promptfoo, garak.
- Claude Code specifics: CLI install via `npm install -g @anthropic-ai/claude-code`; four MCP servers are named as used by the project — engram, aguara, e2b, context7 — configured per-user, not per-project.
- Docker infrastructure services (all optional, started via `scripts/cos-bootstrap.sh`): Langfuse (3100, minimal+ profile), LiteLLM (4000, standard+), NeMo Guardrails (8088, full), Jupyter (8888, full).
- Verification: `bash scripts/doctor.sh` checks all dependencies and reports installed/missing/misconfigured state.

## Relations & where used

Cross-references `getting-started.md` for installation steps, `scripts/setup.sh` for one-command setup, and is explicitly audited as a "current repo surface" in the sibling `cross-device-dependencies.md` (ADR-168), which notes this doc "claims single source of truth but still mixes install commands in prose."

## Status / caveats

The sibling `cross-device-dependencies.md` doc explicitly flags this file as mixing install commands into prose rather than being fully manifest-driven — noted here per the faithfulness rule rather than resolved. The engram CLI section shows a genuine internal tension worth flagging: it documents install via `npx -y @anthropic/engram` (an MCP-server-style npm package) while also noting "the upstream repo for binary releases" and separately stating the local machine actually uses a Homebrew binary (per the cross-device audit doc) — the two install paths (npm package vs. Homebrew binary) are not reconciled in this document.
