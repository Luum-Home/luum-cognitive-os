# ADR-011: Dual Gateway -- Bifrost Primary, LiteLLM Fallback

**Date:** 2026-03-28
**Status:** Superseded by ADR-018
**Commits:** 8968c9e, a7e0c3f
**Engram IDs:** 1721, 1722, 1724, 1740, 1744

## Context

Cognitive OS used LiteLLM as its sole AI gateway/LLM proxy. In March 2026, LiteLLM was compromised in the TeamPCP supply chain attack (PyPI versions 1.82.7-8 contained malicious code). The Cognitive OS installation was safe because it used Docker with SHA256-pinned images, but trust in LiteLLM as a single point of failure was damaged. Separately, a comprehensive evaluation of 11 open-source AI gateways revealed that Bifrost (Go, Apache 2.0, by MaximHQ) offered 50x lower proxy overhead (11 microseconds vs ~100ms for LiteLLM), a 3-tier budget hierarchy, and growing MCP support.

## Decision

Adopt a dual-gateway architecture with Bifrost as primary and LiteLLM as fallback:

**Routing priority**:
1. Claude models route directly via ClaudeExecutor (no proxy needed).
2. Bifrost-supported models (22+ providers) route through Bifrost when healthy.
3. Everything else (OpenRouter free tier, local models, custom providers) routes through LiteLLM.
4. If both gateways are down, fall back to the best available Claude model.

**Implementation**: `lib/gateway_selector.py` (new) handles health-aware routing. `lib/bifrost_client.py` (new) provides the Bifrost integration. Bifrost runs as an optional Docker service on port 8081, pinned to SHA256 digest.

## Alternatives Considered

- **Replace LiteLLM entirely with Bifrost**: Bifrost supports fewer providers (22+ vs 100+) and lacks some LiteLLM features (semantic caching, advanced spend tracking). Full replacement would lose coverage.
- **Stay with LiteLLM only**: The supply chain compromise demonstrated the risk of a single gateway. Even though the Docker deployment was safe, the PyPI attack surface remains for pip-based installations.
- **Use a cloud gateway (AWS Bedrock, Azure OpenAI)**: Adds external dependency, cost, and latency. Self-hosted gateways maintain the self-contained architecture.
- **Build a custom gateway**: Not justified when two mature open-source options exist. The dual approach gets the best of both.

## Consequences

- LLM routing gained redundancy -- a failure in either gateway does not take down model access.
- Performance-sensitive routes (high-throughput, low-latency) benefit from Bifrost's Go-based 11-microsecond overhead.
- Feature-rich routes (budget management, 100+ providers) continue using LiteLLM.
- The Docker Compose configuration grew by one service, but Bifrost's resource footprint is minimal compared to the Python-based LiteLLM.
- The gateway selector introduced a new abstraction layer that all model routing now flows through.

## Superseded

Bifrost was disabled during the Docker-to-pip migration (ADR-018, commit `767b772`). LiteLLM running as a pip library is now the sole gateway. The `lib/bifrost_client.py` and `lib/gateway_selector.py` files still exist but Bifrost is not running.
