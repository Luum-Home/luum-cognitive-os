---
report_type: external-tools-reassessment-scope
date: 2026-05-08
schema_version: external-tools-reassessment-scope/v1
---

# External Tools Reassessment Scope — 2026-05-08

This is the deduplicated high/medium-confidence scope for the full reassessment requested by the operator. It is generated from the raw master inventory and groups repo-scout repositories, actual dependencies, package-level install commands, and radar named tools.

## Counts by domain

- **agents-orchestration-routing**: 45
- **foundation-dependencies**: 23
- **mcp-integration**: 9
- **memory-rag**: 31
- **observability-eval-optimization**: 8
- **sandbox-runtime-testing**: 4
- **security-supply-chain-guardrails**: 5
- **tui-cli-devtools**: 41
- **uncategorized**: 18

## Scope table

| Domain | Tool | Confidence | Kinds | Sources | Example paths |
|---|---|---|---|---|---|
| agents-orchestration-routing | `affaan-m/everything-claude-code` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/external-tools-radar-2026-05-06.md<br>docs/reports/primitives-and-tools-audit-2026-05-05.md |
| agents-orchestration-routing | `agentapi` | medium | tool-term | radar-term | docs/reports/cross-check-C-orchestration-2026-05-08.md<br>docs/reports/external-tools-comparative-matrix-2026-05-06.md |
| agents-orchestration-routing | `agentgateway/agentgateway` | high | repository, repository-ref | repo-scout-cluster-ref, repo-scout-file | docs/research/repo-scout/cluster-agent-orchestration-2026-05-06.md<br>docs/research/repo-scout/monitor-followup/agentgateway__agentgateway-2026-05-06.md |
| agents-orchestration-routing | `agentscope-ai/agentscope` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/primitives-and-tools-audit-2026-05-05.md<br>docs/research/repo-scout/cluster-agent-orchestration-2026-05-06.md |
| agents-orchestration-routing | `agentsmd/agents.md` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/external-tools-radar-2026-05-06.md<br>docs/research/repo-scout/cluster-skills-prompts-2026-05-06.md |
| agents-orchestration-routing | `Aider-AI/aider` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/architecture/agentic-mastery-license-weight-dx-matrix.md<br>docs/reports/cross-check-D-codegen-skills-tui-2026-05-08.md |
| agents-orchestration-routing | `anomalyco/opencode` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/multi-provider-agent-delegation-research-2026-05-05.md<br>docs/reports/remote-control-plane-alternatives-2026-05-05.md |
| agents-orchestration-routing | `AutoGen` | medium | tool-term | radar-term | docs/reports/cross-check-C-orchestration-2026-05-08.md |
| agents-orchestration-routing | `awslabs/agent-squad` | high | repository, repository-ref | repo-scout-cluster-ref, repo-scout-file | docs/research/repo-scout/cluster-agent-orchestration-2026-05-06.md<br>docs/research/repo-scout/monitor-followup/awslabs__agent-squad-2026-05-06.md |
| agents-orchestration-routing | `BeehiveInnovations/pal-mcp-server` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/external-tools-radar-2026-05-06.md<br>docs/reports/multi-provider-agent-delegation-research-2026-05-05.md |
| agents-orchestration-routing | `BerriAI/litellm` | high | repository, repository-ref | repo-scout-cluster-ref, repo-scout-file | docs/research/repo-scout/cluster-agent-orchestration-2026-05-06.md<br>docs/research/repo-scout/monitor-followup/BerriAI__litellm-2026-05-06.md |
| agents-orchestration-routing | `claude-agent-sdk` | high | python-package | pyproject | pyproject.toml |
| agents-orchestration-routing | `cline/cline` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/cross-check-C-orchestration-2026-05-08.md<br>docs/reports/surface-5-tui-ui-candidates-2026-05-05.md |
| agents-orchestration-routing | `coder/agentapi` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/external-tools-radar-2026-05-06.md<br>docs/reports/multi-provider-agent-delegation-research-2026-05-05.md |
| agents-orchestration-routing | `coleam00/Archon` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/external-tools-radar-2026-05-06.md<br>docs/research/repo-scout/cluster-agent-research-selfevolve-2026-05-06.md |
| agents-orchestration-routing | `ComposioHQ/agent-orchestrator` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/primitives-and-tools-audit-2026-05-05.md<br>docs/research/repo-scout/cluster-agent-orchestration-2026-05-06.md |
| agents-orchestration-routing | `continuedev/continue` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/surface-5-tui-ui-candidates-2026-05-05.md<br>docs/research/repo-scout/cluster-agent-codegen-2026-05-06.md |
| agents-orchestration-routing | `CrewAI` | medium | tool-term | radar-term | docs/reports/cross-check-C-orchestration-2026-05-08.md<br>docs/reports/external-tools-comparative-matrix-2026-05-06.md |
| agents-orchestration-routing | `crewAIInc/crewAI` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/research/orchestration-gaps/agent-to-agent-handoff.md<br>docs/research/repo-scout/cluster-agent-orchestration-2026-05-06.md |
| agents-orchestration-routing | `dmgrok/agent_skills_directory` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/architecture/agentic-mastery-license-weight-dx-matrix.md<br>docs/reports/external-tools-radar-2026-05-06.md |
| agents-orchestration-routing | `dollspace-gay/OpenClaudia` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/multi-provider-agent-delegation-research-2026-05-05.md<br>docs/research/repo-scout/cluster-cli-claw-derivatives-2026-05-06.md |
| agents-orchestration-routing | `FoundationAgents/MetaGPT` | high | repository, repository-ref | repo-scout-cluster-ref, repo-scout-file | docs/research/repo-scout/cluster-agent-orchestration-2026-05-06.md<br>docs/research/repo-scout/monitor-followup/FoundationAgents__MetaGPT-2026-05-06.md |
| agents-orchestration-routing | `gepa-ai/gepa` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/external-tools-radar-2026-05-06.md<br>docs/reports/primitives-and-tools-audit-2026-05-05.md |
| agents-orchestration-routing | `InternLM/WildClawBench` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/architecture/agentic-mastery-license-weight-dx-matrix.md<br>docs/research/repo-scout/cluster-cli-claw-derivatives-2026-05-06.md |
| agents-orchestration-routing | `JackChen-me/open-multi-agent` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/primitives-and-tools-audit-2026-05-05.md<br>docs/research/repo-scout/cluster-agent-orchestration-2026-05-06.md |
| agents-orchestration-routing | `litellm` | medium | install-command-tool, python-package, tool-term | cos-package-install, package-requirements, python-requirements, radar-term | docs/reports/external-tools-comparative-matrix-2026-05-06.md<br>docs/reports/external-tools-inventory-2026-05-06.md |
| agents-orchestration-routing | `luongnv89/claude-howto` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/primitives-and-tools-audit-2026-05-05.md<br>docs/research/repo-scout/cluster-skills-prompts-2026-05-06.md |
| agents-orchestration-routing | `maximhq/bifrost` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/adrs/ADR-049-llm-gateway-selection-and-overflow-providers.md<br>docs/research/repo-scout/cluster-agent-orchestration-2026-05-06.md |
| agents-orchestration-routing | `microsoft/agent-framework` | high | repository, repository-ref | repo-scout-cluster-ref, repo-scout-file | docs/research/repo-scout/cluster-agent-orchestration-2026-05-06.md<br>docs/research/repo-scout/deep/microsoft__agent-framework-2026-05-06.md |
| agents-orchestration-routing | `MiniMax-AI/MiniMax-M2` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/multi-provider-agent-delegation-research-2026-05-05.md<br>docs/research/repo-scout/cluster-agent-experimental-A-llm-tooling-2026-05-06.md |
| agents-orchestration-routing | `musistudio/claude-code-router` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/external-tools-radar-2026-05-06.md<br>docs/reports/multi-provider-agent-delegation-research-2026-05-05.md |
| agents-orchestration-routing | `NousResearch/hermes-agent` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/dependencies-license-audit-2026-05-06.md<br>docs/reports/docs-execution-latest.json |
| agents-orchestration-routing | `obra/superpowers` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/cross-check-D-codegen-skills-tui-2026-05-08.md<br>docs/reports/external-tools-radar-2026-05-06.md |
| agents-orchestration-routing | `openclaw/openclaw` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/multi-provider-agent-delegation-research-2026-05-05.md<br>docs/reports/remote-control-plane-alternatives-2026-05-05.md |
| agents-orchestration-routing | `OpenHands/OpenHands` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/architecture/agentic-mastery-license-weight-dx-matrix.md<br>docs/research/repo-scout/cluster-cli-claw-derivatives-2026-05-06.md |
| agents-orchestration-routing | `praetorian-inc/augustus` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/architecture/agentic-mastery-license-weight-dx-matrix.md<br>docs/reports/external-tools-radar-2026-05-06.md |
| agents-orchestration-routing | `QwenLM/qwen-code` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/multi-provider-agent-delegation-research-2026-05-05.md<br>docs/research/repo-scout/cluster-agent-codegen-2026-05-06.md |
| agents-orchestration-routing | `RooCodeInc/Roo-Code` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/surface-5-tui-ui-candidates-2026-05-05.md<br>docs/research/repo-scout/cluster-agent-codegen-2026-05-06.md |
| agents-orchestration-routing | `shanraisshan/claude-code-best-practice` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/primitives-and-tools-audit-2026-05-05.md<br>docs/research/repo-scout/cluster-agent-codegen-2026-05-06.md |
| agents-orchestration-routing | `sigoden/aichat` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/surface-5-tui-ui-candidates-2026-05-05.md<br>docs/research/repo-scout/cluster-agent-experimental-A-llm-tooling-2026-05-06.md |
| agents-orchestration-routing | `simonw/llm` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/external-tools-radar-2026-05-06.md<br>docs/reports/surface-5-tui-ui-candidates-2026-05-05.md |
| agents-orchestration-routing | `snyk/agent-scan` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/architecture/agentic-mastery-license-weight-dx-matrix.md<br>docs/reports/external-tools-radar-2026-05-06.md |
| agents-orchestration-routing | `stanfordnlp/dspy` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/architecture/agentic-mastery-license-weight-dx-matrix.md<br>docs/reports/external-tools-radar-2026-05-06.md |
| agents-orchestration-routing | `SWE-agent/SWE-agent` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/architecture/agentic-mastery-license-weight-dx-matrix.md<br>docs/reports/external-tools-radar-2026-05-06.md |
| agents-orchestration-routing | `TheR1D/shell_gpt` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/surface-5-tui-ui-candidates-2026-05-05.md<br>docs/research/repo-scout/cluster-agent-experimental-A-llm-tooling-2026-05-06.md |
| foundation-dependencies | `diff-cover` | high | python-package | pyproject | pyproject.toml |
| foundation-dependencies | `fastapi` | high | python-package | pyproject, python-requirements | pyproject.toml<br>requirements.txt |
| foundation-dependencies | `github.com/BurntSushi/toml` | high | go-module | go-mod | go.mod |
| foundation-dependencies | `import-linter` | high | python-package | pyproject | pyproject.toml |
| foundation-dependencies | `jinja2` | high | python-package | pyproject, python-requirements | pyproject.toml<br>requirements.txt |
| foundation-dependencies | `jupyter` | high | python-package | python-requirements | requirements.txt<br>requirements/dependency-lanes/jupyter.txt |
| foundation-dependencies | `luum-cognitive-os` | high | python-package | pyproject | pyproject.toml |
| foundation-dependencies | `modernc.org/sqlite` | high | go-module | go-mod | go.mod |
| foundation-dependencies | `mutmut` | high | python-package | pyproject | pyproject.toml |
| foundation-dependencies | `notebook` | high | python-package | python-requirements | requirements.txt<br>requirements/dependency-lanes/jupyter.txt |
| foundation-dependencies | `numpy` | high | python-package | python-requirements | requirements/dependency-lanes/semantic.txt |
| foundation-dependencies | `pre-commit` | high | python-package | pyproject | pyproject.toml |
| foundation-dependencies | `pytest` | high | python-package | pyproject, python-requirements | pyproject.toml<br>requirements.txt |
| foundation-dependencies | `pytest-asyncio` | high | python-package | pyproject, python-requirements | pyproject.toml<br>requirements.txt |
| foundation-dependencies | `pytest-cov` | high | python-package | pyproject | pyproject.toml |
| foundation-dependencies | `pytest-rerunfailures` | high | python-package | pyproject | pyproject.toml |
| foundation-dependencies | `pytest-smell` | high | python-package | pyproject | pyproject.toml |
| foundation-dependencies | `pytest-timeout` | high | python-package | pyproject, python-requirements | pyproject.toml<br>requirements.txt |
| foundation-dependencies | `pytest-xdist` | high | python-package | pyproject, python-requirements | pyproject.toml<br>requirements.txt |
| foundation-dependencies | `redis` | high | python-package | python-requirements | requirements.txt<br>requirements/dependency-lanes/llm.txt |
| foundation-dependencies | `ruff` | high | python-package | pyproject | pyproject.toml |
| foundation-dependencies | `uvicorn` | high | python-package | pyproject, python-requirements | pyproject.toml<br>requirements.txt |
| foundation-dependencies | `vulture` | high | python-package | pyproject | pyproject.toml |
| mcp-integration | `anthropic` | high | install-command-tool, python-package | cos-package-install, package-requirements | packages/advisor-mcp/cos-package.yaml<br>packages/advisor-mcp/requirements.txt |
| mcp-integration | `Bubblewrap` | medium | tool-term | radar-term | docs/reports/cross-check-B-sandbox-mcp-2026-05-08.md<br>docs/reports/external-tools-radar-2026-05-08-errata.md |
| mcp-integration | `E2B` | medium | tool-term | radar-term | docs/reports/cross-check-B-sandbox-mcp-2026-05-08.md<br>docs/reports/external-tools-comparative-matrix-2026-05-06.md |
| mcp-integration | `FastMCP` | medium | install-command-tool, python-package, tool-term | cos-package-install, package-requirements, radar-term | docs/reports/cross-check-B-sandbox-mcp-2026-05-08.md<br>docs/reports/external-tools-radar-2026-05-08-errata.md |
| mcp-integration | `google-generativeai` | high | install-command-tool, python-package | cos-package-install, package-requirements | packages/advisor-mcp/cos-package.yaml<br>packages/advisor-mcp/requirements.txt |
| mcp-integration | `httpx` | high | install-command-tool, python-package | cos-package-install, package-requirements | packages/advisor-mcp/cos-package.yaml<br>packages/advisor-mcp/requirements.txt |
| mcp-integration | `openai` | high | install-command-tool, python-package | cos-package-install, package-requirements, pyproject | packages/advisor-mcp/cos-package.yaml<br>packages/advisor-mcp/requirements.txt |
| mcp-integration | `opentelemetry-api` | high | install-command-tool | cos-package-install | packages/mcp-server/cos-package.yaml |
| mcp-integration | `pyyaml` | high | install-command-tool, python-package | cos-package-install, pyproject, python-requirements | packages/mcp-server/cos-package.yaml<br>pyproject.toml |
| memory-rag | `CodeGraphContext/CodeGraphContext` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/architecture/primitive-coverage-backend-benchmark-2026-05.md<br>docs/reports/primitive-coverage-backend-benchmark-2026-05-01.json |
| memory-rag | `Cognee` | medium | python-package, tool-term | python-requirements, radar-term | docs/reports/cross-check-A-memory-2026-05-08.md<br>docs/reports/external-tools-comparative-matrix-2026-05-06.md |
| memory-rag | `DavidAnson/markdownlint-cli2` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/architecture/primitive-coverage-tooling-research-2026-04.md<br>docs/research/repo-scout/cluster-dev-tools-cli-2026-05-06.md |
| memory-rag | `DEEP-PolyU/Awesome-GraphMemory` | high | repository, repository-ref | repo-scout-cluster-ref, repo-scout-file | docs/research/repo-scout/cluster-memory-graph-rag-2026-05-06.md<br>docs/research/repo-scout/deep/DEEP-PolyU__Awesome-GraphMemory-2026-05-06.md |
| memory-rag | `devwhodevs/engraph` | high | repository, repository-ref | repo-scout-cluster-ref, repo-scout-file | docs/research/repo-scout/cluster-memory-graph-rag-2026-05-06.md<br>docs/research/repo-scout/monitor-followup/devwhodevs__engraph-2026-05-06.md |
| memory-rag | `DSPy` | medium | tool-term | radar-term | docs/reports/cross-check-A-memory-2026-05-08.md<br>docs/reports/external-tools-comparative-matrix-2026-05-06.md |
| memory-rag | `egdev6/engram-monitor` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/primitives-and-tools-audit-2026-05-05.md<br>docs/research/repo-scout/cluster-memory-vector-2026-05-06.md |
| memory-rag | `getzep/graphiti` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/architecture/external-tool-adoption-doctrine.md<br>docs/reports/external-tools-radar-2026-05-06.md |
| memory-rag | `Graphiti` | medium | tool-term | radar-term | docs/reports/cross-check-A-memory-2026-05-08.md<br>docs/reports/external-tools-comparative-matrix-2026-05-06.md |
| memory-rag | `HippoRAG` | medium | tool-term | radar-term | docs/reports/cross-check-A-memory-2026-05-08.md<br>docs/reports/external-tools-comparative-matrix-2026-05-06.md |
| memory-rag | `HKUDS/LightRAG` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/external-tools-radar-2026-05-06.md<br>docs/research/repo-scout/cluster-memory-graph-rag-2026-05-06.md |
| memory-rag | `LangGraph` | medium | tool-term | radar-term | docs/reports/cross-check-C-orchestration-2026-05-08.md |
| memory-rag | `letta-ai/letta` | high | repository, repository-ref | repo-scout-cluster-ref, repo-scout-file | docs/research/repo-scout/cluster-memory-vector-2026-05-06.md<br>docs/research/repo-scout/monitor-followup/letta-ai__letta-2026-05-06.md |
| memory-rag | `LightRAG` | medium | tool-term | radar-term | docs/reports/cross-check-A-memory-2026-05-08.md<br>docs/reports/external-tools-comparative-matrix-2026-05-06.md |
| memory-rag | `lycheeverse/lychee` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/architecture/primitive-coverage-tooling-research-2026-04.md<br>docs/research/repo-scout/cluster-dev-tools-cli-2026-05-06.md |
| memory-rag | `lycheeverse/lychee-action` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/architecture/primitive-coverage-tooling-research-2026-04.md<br>docs/research/repo-scout/cluster-dev-tools-cli-2026-05-06.md |
| memory-rag | `MemPalace/mempalace` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/external-tools-radar-2026-05-06.md<br>docs/reports/primitives-and-tools-audit-2026-05-05.md |
| memory-rag | `memvid/memvid` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/primitives-and-tools-audit-2026-05-05.md<br>docs/research/repo-scout/cluster-memory-vector-2026-05-06.md |
| memory-rag | `Mibayy/token-savior` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/external-tools-radar-2026-05-06.md<br>docs/reports/primitives-and-tools-audit-2026-05-05.md |
| memory-rag | `microsoft/graphrag` | high | repository, repository-ref | repo-scout-cluster-ref, repo-scout-file | docs/research/repo-scout/cluster-memory-graph-rag-2026-05-06.md<br>docs/research/repo-scout/monitor-followup/microsoft__graphrag-2026-05-06.md |
| memory-rag | `MIRIX` | medium | tool-term | radar-term | docs/reports/cross-check-A-memory-2026-05-08.md<br>docs/reports/external-tools-comparative-matrix-2026-05-06.md |
| memory-rag | `Mirix-AI/MIRIX` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/primitives-and-tools-audit-2026-05-05.md<br>docs/research/repo-scout/cluster-memory-vector-2026-05-06.md |
| memory-rag | `modernc.org/memory` | high | go-module | go-mod | go.mod |
| memory-rag | `openai/codex` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/adrs/ADR-064-harness-agnostic-cognitive-os.md<br>docs/adrs/ADR-081-codex-harness-adapter.md |
| memory-rag | `OSU-NLP-Group/HippoRAG` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/external-tools-radar-2026-05-06.md<br>docs/research/repo-scout/cluster-memory-graph-rag-2026-05-06.md |
| memory-rag | `ragas` | high | python-package | python-requirements | requirements.txt |
| memory-rag | `rohitg00/agentmemory` | high | repository, repository-ref | repo-scout-cluster-ref, repo-scout-file | docs/research/repo-scout/cluster-memory-vector-2026-05-06.md<br>docs/research/repo-scout/monitor-followup/rohitg00__agentmemory-2026-05-06.md |
| memory-rag | `safishamsi/graphify` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/primitives-and-tools-audit-2026-05-05.md<br>docs/research/repo-scout/cluster-memory-graph-rag-2026-05-06.md |
| memory-rag | `Temporal` | medium | tool-term | radar-term | docs/reports/cross-check-A-memory-2026-05-08.md<br>docs/reports/external-tools-comparative-matrix-2026-05-06.md |
| memory-rag | `topoteretes/cognee` | high | repository, repository-ref | repo-scout-cluster-ref, repo-scout-file | docs/research/repo-scout/cluster-memory-graph-rag-2026-05-06.md<br>docs/research/repo-scout/monitor-followup/topoteretes__cognee-2026-05-06.md |
| memory-rag | `yifanfeng97/Hyper-Extract` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/primitives-and-tools-audit-2026-05-05.md<br>docs/research/repo-scout/cluster-memory-graph-rag-2026-05-06.md |
| observability-eval-optimization | `arize-phoenix` | high | python-package | python-requirements | requirements/dependency-lanes/observability.txt |
| observability-eval-optimization | `arize-phoenix-otel` | high | python-package | python-requirements | requirements/dependency-lanes/observability.txt |
| observability-eval-optimization | `deepeval` | high | python-package | python-requirements | requirements.txt |
| observability-eval-optimization | `Langfuse` | medium | python-package, tool-term | python-requirements, radar-term | docs/reports/cross-check-E-observability-debt-2026-05-08.md<br>docs/reports/external-tools-inventory-2026-05-06.md |
| observability-eval-optimization | `MLflow` | medium | python-package, tool-term | python-requirements, radar-term | docs/reports/cross-check-E-observability-debt-2026-05-08.md<br>docs/reports/external-tools-radar-2026-05-08-traceability.md |
| observability-eval-optimization | `mlflow-skinny` | high | python-package | python-requirements | requirements/dependency-lanes/observability.txt |
| observability-eval-optimization | `opik` | high | python-package | python-requirements | requirements.txt |
| observability-eval-optimization | `Phoenix` | medium | tool-term | radar-term | docs/reports/cross-check-E-observability-debt-2026-05-08.md<br>docs/reports/external-tools-inventory-2026-05-06.md |
| sandbox-runtime-testing | `e2b-dev/infra` | high | repository, repository-ref | repo-scout-cluster-ref, repo-scout-file | docs/research/repo-scout/cluster-security-supply-2026-05-06.md<br>docs/research/repo-scout/deep/e2b-dev__infra-2026-05-06.md |
| sandbox-runtime-testing | `Firecracker` | medium | tool-term | radar-term | docs/reports/external-tools-radar-2026-05-08.md |
| sandbox-runtime-testing | `testcontainers` | high | python-package | pyproject, python-requirements | pyproject.toml<br>requirements.txt |
| sandbox-runtime-testing | `testcontainers/testcontainers-python` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/dependencies-license-audit-2026-05-06.md<br>docs/research/repo-scout/cluster-security-supply-2026-05-06.md |
| security-supply-chain-guardrails | `Grype` | medium | tool-term | radar-term | docs/reports/external-tools-radar-INDEX.md |
| security-supply-chain-guardrails | `JuliusBrussee/caveman` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/dependencies-license-audit-2026-05-06.md<br>docs/reports/plugin-caveman-review-2026-04-20.md |
| security-supply-chain-guardrails | `nemoguardrails` | high | python-package | python-requirements | requirements.txt<br>requirements/dependency-lanes/guardrails.txt |
| security-supply-chain-guardrails | `semgrep/semgrep` | high | repository, repository-ref | repo-scout-cluster-ref, repo-scout-file | docs/research/repo-scout/cluster-security-supply-2026-05-06.md<br>docs/research/repo-scout/deep/semgrep__semgrep-2026-05-06.md |
| security-supply-chain-guardrails | `Syft` | medium | tool-term | radar-term | docs/reports/external-tools-radar-INDEX.md |
| tui-cli-devtools | `Aider` | medium | tool-term | radar-term | docs/reports/cross-check-C-orchestration-2026-05-08.md<br>docs/reports/cross-check-D-codegen-skills-tui-2026-05-08.md |
| tui-cli-devtools | `allinurl/goaccess` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/surface-5-tui-ui-candidates-2026-05-05.md<br>docs/research/repo-scout/cluster-dev-tools-tui-2026-05-06.md |
| tui-cli-devtools | `antonmedv/fx` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/surface-5-tui-ui-candidates-2026-05-05.md<br>docs/research/repo-scout/cluster-dev-tools-tui-2026-05-06.md |
| tui-cli-devtools | `aristocratos/btop` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/surface-5-tui-ui-candidates-2026-05-05.md<br>docs/research/repo-scout/cluster-dev-tools-tui-2026-05-06.md |
| tui-cli-devtools | `Bubble Tea` | medium | tool-term | radar-term | docs/reports/cross-check-D-codegen-skills-tui-2026-05-08.md<br>docs/reports/external-tools-radar-2026-05-06.md |
| tui-cli-devtools | `charmbracelet/bubbles` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/surface-5-tui-ui-candidates-2026-05-05.md<br>docs/research/repo-scout/cluster-tui-charm-go-2026-05-06.md |
| tui-cli-devtools | `charmbracelet/bubbletea` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/cross-check-D-codegen-skills-tui-2026-05-08.md<br>docs/reports/surface-5-tui-ui-candidates-2026-05-05.md |
| tui-cli-devtools | `charmbracelet/glamour` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/surface-5-tui-ui-candidates-2026-05-05.md<br>docs/research/repo-scout/cluster-tui-charm-go-2026-05-06.md |
| tui-cli-devtools | `charmbracelet/gum` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/surface-5-tui-ui-candidates-2026-05-05.md<br>docs/research/repo-scout/cluster-tui-charm-go-2026-05-06.md |
| tui-cli-devtools | `charmbracelet/huh` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/surface-5-tui-ui-candidates-2026-05-05.md<br>docs/research/repo-scout/cluster-tui-charm-go-2026-05-06.md |
| tui-cli-devtools | `charmbracelet/lipgloss` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/surface-5-tui-ui-candidates-2026-05-05.md<br>docs/research/repo-scout/cluster-tui-charm-go-2026-05-06.md |
| tui-cli-devtools | `charmbracelet/soft-serve` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/surface-5-tui-ui-candidates-2026-05-05.md<br>docs/research/repo-scout/cluster-tui-charm-go-2026-05-06.md |
| tui-cli-devtools | `charmbracelet/vhs` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/surface-5-tui-ui-candidates-2026-05-05.md<br>docs/research/repo-scout/cluster-tui-charm-go-2026-05-06.md |
| tui-cli-devtools | `ClementTsang/bottom` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/surface-5-tui-ui-candidates-2026-05-05.md<br>docs/research/repo-scout/cluster-dev-tools-tui-2026-05-06.md |
| tui-cli-devtools | `crossterm-rs/crossterm` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/surface-5-tui-ui-candidates-2026-05-05.md<br>docs/research/repo-scout/cluster-tui-rust-2026-05-06.md |
| tui-cli-devtools | `derailed/k9s` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/surface-5-tui-ui-candidates-2026-05-05.md<br>docs/research/repo-scout/cluster-dev-tools-tui-2026-05-06.md |
| tui-cli-devtools | `dlvhdr/gh-dash` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/surface-5-tui-ui-candidates-2026-05-05.md<br>docs/research/repo-scout/cluster-dev-tools-tui-2026-05-06.md |
| tui-cli-devtools | `gitui-org/gitui` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/surface-5-tui-ui-candidates-2026-05-05.md<br>docs/research/repo-scout/cluster-dev-tools-tui-2026-05-06.md |
| tui-cli-devtools | `hatoo/oha` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/surface-5-tui-ui-candidates-2026-05-05.md<br>docs/research/repo-scout/cluster-dev-tools-tui-2026-05-06.md |
| tui-cli-devtools | `jarun/nnn` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/surface-5-tui-ui-candidates-2026-05-05.md<br>docs/research/repo-scout/cluster-dev-tools-tui-2026-05-06.md |
| tui-cli-devtools | `jesseduffield/lazydocker` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/surface-5-tui-ui-candidates-2026-05-05.md<br>docs/research/repo-scout/cluster-dev-tools-tui-2026-05-06.md |
| tui-cli-devtools | `jesseduffield/lazygit` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/surface-5-tui-ui-candidates-2026-05-05.md<br>docs/research/repo-scout/cluster-dev-tools-tui-2026-05-06.md |
| tui-cli-devtools | `junegunn/fzf` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/surface-5-tui-ui-candidates-2026-05-05.md<br>docs/research/repo-scout/cluster-dev-tools-cli-2026-05-06.md |
| tui-cli-devtools | `nearai/ironclaw` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/remote-control-plane-alternatives-2026-05-05.md<br>docs/reports/surface-5-tui-ui-candidates-2026-05-05.md |
| tui-cli-devtools | `nullclaw/nullclaw` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/remote-control-plane-alternatives-2026-05-05.md<br>docs/reports/surface-5-tui-ui-candidates-2026-05-05.md |
| tui-cli-devtools | `qhkm/zeptoclaw` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/remote-control-plane-alternatives-2026-05-05.md<br>docs/reports/surface-5-tui-ui-candidates-2026-05-05.md |
| tui-cli-devtools | `qwibitai/nanoclaw` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/remote-control-plane-alternatives-2026-05-05.md<br>docs/reports/surface-5-tui-ui-candidates-2026-05-05.md |
| tui-cli-devtools | `ratatui/ratatui` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/surface-5-tui-ui-candidates-2026-05-05.md<br>docs/research/repo-scout/cluster-tui-rust-2026-05-06.md |
| tui-cli-devtools | `rich` | high | python-package | pyproject | pyproject.toml |
| tui-cli-devtools | `sachaos/viddy` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/surface-5-tui-ui-candidates-2026-05-05.md<br>docs/research/repo-scout/cluster-dev-tools-tui-2026-05-06.md |
| tui-cli-devtools | `sipeed/picoclaw` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/remote-control-plane-alternatives-2026-05-05.md<br>docs/reports/surface-5-tui-ui-candidates-2026-05-05.md |
| tui-cli-devtools | `Superpowers` | medium | tool-term | radar-term | docs/reports/cross-check-D-codegen-skills-tui-2026-05-08.md<br>docs/reports/external-tools-comparative-matrix-2026-05-06.md |
| tui-cli-devtools | `sxyazi/yazi` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/surface-5-tui-ui-candidates-2026-05-05.md<br>docs/research/repo-scout/cluster-dev-tools-tui-2026-05-06.md |
| tui-cli-devtools | `Textualize/rich` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/surface-5-tui-ui-candidates-2026-05-05.md<br>docs/research/repo-scout/cluster-tui-py-other-2026-05-06.md |
| tui-cli-devtools | `Textualize/textual` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/surface-5-tui-ui-candidates-2026-05-05.md<br>docs/research/repo-scout/cluster-tui-py-other-2026-05-06.md |
| tui-cli-devtools | `tstack/lnav` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/surface-5-tui-ui-candidates-2026-05-05.md<br>docs/research/repo-scout/cluster-dev-tools-tui-2026-05-06.md |
| tui-cli-devtools | `wagoodman/dive` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/surface-5-tui-ui-candidates-2026-05-05.md<br>docs/research/repo-scout/cluster-dev-tools-tui-2026-05-06.md |
| tui-cli-devtools | `wtfutil/wtf` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/surface-5-tui-ui-candidates-2026-05-05.md<br>docs/research/repo-scout/cluster-dev-tools-tui-2026-05-06.md |
| tui-cli-devtools | `yorukot/superfile` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/surface-5-tui-ui-candidates-2026-05-05.md<br>docs/research/repo-scout/cluster-dev-tools-tui-2026-05-06.md |
| tui-cli-devtools | `zellij-org/zellij` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/surface-5-tui-ui-candidates-2026-05-05.md<br>docs/research/repo-scout/cluster-dev-tools-tui-2026-05-06.md |
| tui-cli-devtools | `zeroclaw-labs/zeroclaw` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/remote-control-plane-alternatives-2026-05-05.md<br>docs/reports/surface-5-tui-ui-candidates-2026-05-05.md |
| uncategorized | `crawl4ai` | high | python-package | python-requirements | requirements.txt<br>requirements/dependency-lanes/crawling.txt |
| uncategorized | `github.com/dustin/go-humanize` | high | go-module | go-mod | go.mod |
| uncategorized | `github.com/google/uuid` | high | go-module | go-mod | go.mod |
| uncategorized | `github.com/mattn/go-isatty` | high | go-module | go-mod | go.mod |
| uncategorized | `github.com/ncruces/go-strftime` | high | go-module | go-mod | go.mod |
| uncategorized | `github.com/remyoudompheng/bigfft` | high | go-module | go-mod | go.mod |
| uncategorized | `golang.org/x/sys` | high | go-module | go-mod | go.mod |
| uncategorized | `LangChain` | medium | tool-term | radar-term | docs/reports/external-tools-inventory-2026-05-06.md |
| uncategorized | `mattpocock/skills` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/primitives-and-tools-audit-2026-05-05.md<br>docs/research/repo-scout/cluster-skills-prompts-2026-05-06.md |
| uncategorized | `memu` | high | python-package | python-requirements | requirements.txt |
| uncategorized | `modernc.org/libc` | high | go-module | go-mod | go.mod |
| uncategorized | `modernc.org/mathutil` | high | go-module | go-mod | go.mod |
| uncategorized | `nashsu/AutoCLI` | high | repository, repository-ref | repo-scout-cluster-ref, repo-scout-file | docs/research/repo-scout/cluster-cli-claw-derivatives-2026-05-06.md<br>docs/research/repo-scout/monitor-followup/nashsu__AutoCLI-2026-05-06.md |
| uncategorized | `NATS` | medium | tool-term | radar-term | docs/reports/external-tools-radar-2026-05-08.md |
| uncategorized | `OPA` | medium | tool-term | radar-term | docs/reports/external-tools-radar-2026-05-08.md |
| uncategorized | `sentence-transformers` | high | python-package | python-requirements | requirements/dependency-lanes/semantic.txt |
| uncategorized | `smykla-skalski/klaudiush` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/architecture/cos-dispatch/README.md<br>docs/research/repo-scout/cluster-cli-claw-derivatives-2026-05-06.md |
| uncategorized | `unclecode/crawl4ai` | high | repository, repository-ref | doc-github-ref, repo-scout-cluster-ref, repo-scout-file | docs/reports/external-tools-radar-2026-05-06.md<br>docs/research/repo-scout/cluster-browser-automation-2026-05-06.md |
