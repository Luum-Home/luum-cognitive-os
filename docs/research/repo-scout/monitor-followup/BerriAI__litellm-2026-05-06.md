---
date: 2026-05-06
repo: BerriAI/litellm
mode: monitor-followup-light-deep
phase: 2
---

# Monitor Follow-up: BerriAI/litellm

## Phase 1 (Shallow) Verdict
- **Verdict:** monitor
- **Rationale:** MIT (root); enterprise/ proprietary. ADR-049 already covers Qwen-primary routing.

## Phase 2 (Light-Deep) Verification

### Repository Facts (gh api)
- **License (SPDX):** `NOASSERTION`
- **Stars:** 45824
- **Archived:** False
- **Last push:** 2026-05-06T06:30:07Z (active (<30d))
- **Primary language:** Python
- **Open issues:** 2852
- **Description:** Python SDK, Proxy Server (AI Gateway) to call 100+ LLM APIs in OpenAI (or native) format, with cost tracking, guardrails, loadbalancing and logging. [Bedrock, Azure, OpenAI, VertexAI, Cohere, Anthropic, Sagemaker, HuggingFace, VLLM, NVIDIA NIM]
- **Top-level entries (first 3):** .circleci, .devcontainer, .dockerignore

### Deep Finding
Very active (commits within days), 50k+ stars, MIT root + proprietary enterprise/. Provider abstraction battle-tested across 100+ LLMs. Adoption would invert COS topology since lib/dispatch.py already covers our needs.

### Peer Overlap with COS
Broader provider matrix and observability hooks than lib/dispatch.py, but ADR-049's Qwen-primary topology is intentional.

## Revised Verdict

**REVISED_VERDICT:** `MONITOR_CONFIRMED`

- **Integration effort if any:** medium-large (would replace dispatch.py and re-wire ADR-049)
- **License gate:** pass
- **Archived gate:** pass
