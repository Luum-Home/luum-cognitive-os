# Cognitive OS Dependency Manifest

> Single source of truth for every tool, runtime, and library that Cognitive OS uses.
> For installation steps, see [Getting Started](../getting-started.md). For a one-command
> setup, run `scripts/setup.sh`.

---

## Quick Reference

| Category | Tool | Required? | Install via |
|----------|------|-----------|-------------|
| Runtime | Python >= 3.11 | Yes | System / brew |
| Runtime | Go (see `.go-version`) | For TUI/CLI | goenv |
| Package mgr | uv | Yes | brew / curl |
| Package mgr | goenv | For Go projects | brew |
| CLI | jq | Yes | brew |
| CLI | gh (GitHub CLI) | Yes | brew |
| CLI | Git >= 2.30 | Yes | System |
| AI | Claude Code (latest) | Yes | Anthropic installer |
| Memory | engram CLI | Recommended | See below |
| Migration | CLAMP | Optional | curl |
| Container | Docker >= 24 | Optional | Docker Desktop |
| Security | semgrep | Optional | brew |
| Security | aguara | Optional | go install |
| Security | parry-guard | Optional | brew tap |
| Security | mcp-scan | Optional | pip |
| Testing | cosmic-ray | Optional | pip |
| Testing | promptfoo | Optional | npm |

---

## 1. System Tools (brew)

Install with Homebrew on macOS. Linux equivalents noted where applicable.

| Tool | Purpose | Install |
|------|---------|---------|
| **jq** | JSON processing in hooks and scripts | `brew install jq` |
| **goenv** | Go version manager (reads `.go-version`) | `brew install goenv` |
| **gh** | GitHub CLI for PR/issue automation | `brew install gh` |
| **Docker** | Optional infrastructure services (Langfuse, LiteLLM) | [Docker Desktop](https://docs.docker.com/get-docker/) |
| **uv** | Fast Python package manager | `brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh \| sh` |

---

## 2. Go

The project uses Go for the `cos` CLI and `cos-test` TUI runner.

- **Required version**: read from `.go-version` (currently `1.25.6`)
- **Install via goenv**:
  ```bash
  goenv install "$(cat .go-version)"
  goenv global "$(cat .go-version)"
  ```
- **Verify**: `go version` should match `.go-version`

Go is only required if you plan to build or run `cmd/cos` or `cmd/cos-test`.
Core hooks, rules, and the SDD pipeline work without Go.

---

## 3. Python

### Runtime

- **Required version**: >= 3.11 (set in `pyproject.toml` `requires-python`)
- **Recommended**: use `uv` for virtual environment and dependency management

### Dependency Groups (from pyproject.toml)

The project defines these optional dependency groups. Install what you need:

| Group | Packages | Purpose |
|-------|----------|---------|
| *(core)* | pyyaml, jinja2 | Always installed. YAML config parsing, template rendering |
| **llm** | litellm, redis | LLM proxy routing and caching |
| **web** | fastapi, uvicorn | Web API server (MCP server, dashboard backend) |
| **observability** | opik, langfuse | LLM tracing and observability |
| **memory** | cognee | Cognitive memory engine |
| **guardrails** | nemoguardrails | Content safety and guardrails |
| **jupyter** | jupyter, notebook | GPU/compute sandbox |
| **crawling** | crawl4ai | Web crawling for research skills |
| **testing** | pytest, pytest-asyncio, pytest-timeout, pytest-xdist, mutmut, pytest-smell | Test suite with parallel execution and mutation testing |
| **security** | *(empty, see notes)* | Security tools installed separately (see section 6) |
| **enforcement** | pre-commit, ruff, vulture, import-linter, pytest-cov, diff-cover | Linting, dead code detection, import policy, coverage |
| **dev** | *(meta-group)* | Installs: llm + web + observability + memory + guardrails + jupyter + crawling + testing + enforcement |

### Install commands

```bash
# Minimal (core only)
uv venv && uv pip install -e .

# Standard (recommended for development)
uv venv && uv pip install -e ".[dev]"

# Specific groups
uv pip install -e ".[testing,enforcement]"
```

---

## 4. Tools Installed Outside pyproject.toml

These are installed globally (not in the project venv):

| Tool | Purpose | Install |
|------|---------|---------|
| **cosmic-ray** | Mutation testing (CI workflow in `.github/workflows/test-quality.yml`) | `pip install cosmic-ray` |
| **pyyaml** (global) | Required by pre-commit hook import checks that run outside the venv | `pip install pyyaml` |

---

## 5. Tools Installed via curl / Binary

### CLAMP (claude-move-project)

Project migration tool for moving Claude Code projects between directories.

```bash
curl -fsSL https://raw.githubusercontent.com/wsagency/claude-move-project/main/clamp -o /usr/local/bin/clamp
chmod +x /usr/local/bin/clamp
```

### engram CLI

Persistent memory layer used by hooks and skills. The project wraps it via
`lib/engram_client.py` (graceful degradation when unavailable).

```bash
# Install via npm (MCP server)
npx -y @anthropic/engram

# Or check the upstream repo for binary releases:
# https://github.com/Gentleman-Programming/engram
```

Configure in Claude Code MCP settings (`~/.claude/settings.json`):
```json
{
  "mcpServers": {
    "engram": {
      "command": "npx",
      "args": ["-y", "@anthropic/engram"]
    }
  }
}
```

---

## 6. Security Tools (Optional)

All security tools are optional. Hooks that depend on them skip gracefully
when the tool is not found.

| Tool | Purpose | Install |
|------|---------|---------|
| **semgrep** | Static analysis and SAST scanning | `brew install semgrep` |
| **aguara** | AI agent security scanner (deterministic patterns) | `go install github.com/garagon/aguara@latest` (or `bash scripts/install-aguara.sh`) |
| **mcp-aguara** | MCP server for aguara | `go install github.com/garagon/mcp-aguara@latest` |
| **parry-guard** | ML-based prompt injection detection | `brew install vaporif/tap/parry-guard` |
| **mcp-scan** | MCP server configuration scanner (Invariant Labs) | `pip install mcp-scan` (or `bash scripts/install-mcp-scan.sh`) |
| **promptfoo** | LLM red team testing | `npm install -g promptfoo` (or `bash scripts/install-promptfoo.sh`) |
| **garak** | LLM vulnerability scanner | `pip install garak` (heavy dependency, not in pyproject.toml) |

---

## 7. Claude Code Specifics

### Claude Code CLI

Install the latest version from Anthropic:
```bash
# See https://docs.anthropic.com/en/docs/claude-code
npm install -g @anthropic-ai/claude-code
```

### MCP Servers

MCP servers are configured per-user in `~/.claude/settings.json` (not in the
project). The project uses:

| Server | Purpose | Notes |
|--------|---------|-------|
| **engram** | Persistent memory (mem_save, mem_search, etc.) | See section 5 |
| **aguara** | Security scanning | Optional, see section 6 |
| **e2b** | Code sandbox execution | Optional |
| **context7** | Library documentation lookup | Optional |

---

## 8. Infrastructure Services (Docker)

These services are started via `scripts/cos-bootstrap.sh` and are entirely optional.
See [Getting Started](../getting-started.md#optional-start-infrastructure-services) for profiles.

| Service | Port | Profile | Purpose |
|---------|------|---------|---------|
| Langfuse | 3100 | minimal+ | Observability and tracing |
| LiteLLM | 4000 | standard+ | Cost control and model routing |
| NeMo Guardrails | 8088 | full | Content safety |
| Paperclip | 3200 | full | Governance dashboard |
| Jupyter | 8888 | full | GPU/compute sandbox |

---

## 9. Verification

Run the health check to verify your setup:

```bash
bash scripts/doctor.sh
```

This checks all dependencies and reports what is installed, missing, or misconfigured.
