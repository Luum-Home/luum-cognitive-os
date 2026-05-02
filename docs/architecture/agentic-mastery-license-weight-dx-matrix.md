# Agentic Mastery — License, Weight, and DX Matrix

> Date: 2026-05-02
> Purpose: decide which external agentic-AI tools can influence Cognitive OS, which can be optional adapters, and which must stay out of the core.

## Policy

Cognitive OS implements the mandatory path with a **small deterministic internal core**. External tools are allowed only as:

1. **Reference** — learn from the design; no dependency.
2. **Optional CLI / dev lane** — operator installs explicitly; never required by default.
3. **Optional benchmark adapter** — only for benchmark lanes; not part of project install.
4. **Blocked** — incompatible license, excessive weight, unclear provenance, or unacceptable data-sharing behavior.

No tool may become a default dependency until it passes a pinned-version license gate.

## License gate requirements

Before any integration moves beyond reference status, record:

| Field | Requirement |
|---|---|
| Repository | Canonical upstream URL. |
| Version | Immutable tag, release, or commit. |
| License | SPDX ID from upstream license file and package metadata. |
| Transitive dependencies | Scan with the repo license policy; AGPL/SSPL/BSL/ELv2 stay blocked. |
| Install mode | `none`, `optional-cli`, `optional-container`, `dev-only`, or `vendored`. |
| Data sharing | Whether prompts, code, tool descriptions, or skill contents leave the machine. |
| Default impact | Must be zero for fresh COS installs unless explicitly accepted. |

## Weight scale

| Weight | Meaning |
|---|---|
| None | Used only as reference or docs. |
| Low | Small Python/Bash module, no new service, no Docker, no large dataset. |
| Medium | Adds a CLI/package or extra test/report path, but not on hot path. |
| High | Requires npm/Python dependency trees, external APIs, or long-running scans. |
| Very high | Requires Docker images, benchmark datasets, browser/OS environments, or multi-repo harnesses. |

## DX scale

| DX value | Meaning |
|---|---|
| High | Improves daily operator confidence or prevents severe agent mistakes. |
| Medium | Useful for maintainers or periodic quality work. |
| Low | Mostly research/comparison value. |

## Matrix

### Security and Lethal Trifecta

| Tool / source | Apparent license | Confidence | Weight if used | Default? | DX value | Recommended integration | Notes |
|---|---|---:|---|---|---|---|---|
| [Simon Willison — lethal trifecta](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/) | Article / doctrine | High | None | Yes, as policy | High | Implement internally | Use the three-dimension model; no code dependency. |
| [snyk/agent-scan](https://github.com/snyk/agent-scan) / [PyPI](https://pypi.org/project/snyk-agent-scan/) | Apache-2.0 in public metadata | Medium-high | Medium/High | No | High for security teams | Optional scanner | PyPI notes local checks plus Agent Scan API use; data-sharing policy must be surfaced before use. |
| [promptfoo](https://github.com/promptfoo/promptfoo) | MIT in repo metadata | High | Medium/High | No | Medium-high | Optional red-team/eval lane | Good CI/reporting fit; avoid default npm dependency. |
| [garak](https://github.com/NVIDIA/garak) | Apache-2.0 in repo/site metadata | High | High | No | Medium | Optional deep red-team lane | Powerful but too heavy for default installs. |
| [Augustus](https://github.com/praetorian-inc/augustus) | Apache-2.0 in repo metadata | High | Medium | No | Medium | Optional local red-team binary | Single Go binary is attractive for opt-in security smoke tests. |
| [oktsec](https://github.com/oktsec/oktsec) | Needs pinned verification | Low/medium | Medium | No | Medium | Reference first | Agent firewall concepts are useful; do not integrate until license and maturity are verified. |
| [agent-security-scanner-mcp](https://github.com/sinewaveai/agent-security-scanner-mcp) | Needs pinned verification | Low/medium | Medium | No | Medium | Reference/optional MCP only | Useful shape for MCP scanning; MCP hot path must remain internal. |

### Agent-Computer Interface

| Tool / source | Apparent license | Confidence | Weight if used | Default? | DX value | Recommended integration | Notes |
|---|---|---:|---|---|---|---|---|
| [SWE-agent ACI](https://github.com/SWE-agent/SWE-agent/blob/main/docs/background/aci.md) | Research/docs; repo license must be pinned | Medium | None | Yes, as design influence | High | Reference | Strong evidence that interface design affects success. |
| [SWE-agent](https://github.com/SWE-agent/SWE-agent) | Needs pinned verification | Medium | High | No | Medium | Reference/benchmark adapter | Do not vendor. Borrow ACI lessons and trajectory ideas. |
| [opencode](https://github.com/opencode-ai/opencode) | MIT in repo metadata | High | Medium/High | No | Medium | Reference/optional adapter | Tool vocabulary is useful; no default dependency. |
| [aider](https://github.com/aider-ai/aider) | Apache-2.0 in repo metadata | High | Medium | No | High as UX reference | Reference/optional baseline | Git-native flow informs diff-first/propose-first COS behavior. |
| [augment-swebench-agent](https://github.com/augmentcode/augment-swebench-agent) | Needs pinned verification | Low/medium | High | No | Low/medium | Reference only | Useful benchmark architecture reference; too specialized for default. |

### Skill efficacy

| Tool / source | Apparent license | Confidence | Weight if used | Default? | DX value | Recommended integration | Notes |
|---|---|---:|---|---|---|---|---|
| [SkillsBench](https://github.com/benchflow-ai/skillsbench) | Needs pinned verification | Low/medium | Medium/High | No | Medium | Reference/optional benchmark | Use paired task methodology; don't import by default. |
| [SWE-Skills-Bench](https://arxiv.org/abs/2603.15401) | Paper + repo claimed by paper | Medium | None/Medium | No | High for SO maintainers | Reference | Use marginal-utility framing for COS skills. |
| [SkillLearnBench](https://arxiv.org/abs/2604.20087) | Paper | Medium | None | No | Medium | Reference | Later self-improvement validation. |
| [DSPy](https://github.com/stanfordnlp/dspy) | Needs pinned verification | Medium | Medium/High | No | Medium | Reference first | Useful for compiled/evaluated prompts; optional later. |
| [agentevals](https://github.com/langchain-ai/agentevals) | Needs pinned verification | Medium | Medium | No | Medium | Optional trajectory eval | Useful once COS has stable trajectory schema. |
| [agent_skills_directory](https://github.com/dmgrok/agent_skills_directory) | MIT for directory; individual skills vary | Medium-high | Low/Medium | No | Medium | Reference | Good provenance/trust metadata shape; do not ingest skills blindly. |

### Runtime benchmarks

| Tool / source | Apparent license | Confidence | Weight if used | Default? | DX value | Recommended integration | Notes |
|---|---|---:|---|---|---|---|---|
| [SWE-bench](https://github.com/swe-bench) | Needs pinned verification for code and datasets | Medium | Very high | No | Medium | Optional benchmark adapter | Canonical external validation, too heavy for default. |
| [vexp-swe-bench](https://github.com/Vexp-ai/vexp-swe-bench) | Needs pinned verification | Medium | Medium | No | Medium | Reference metric taxonomy | Good cost/duration/unique-win framing. |
| [Agentless](https://github.com/OpenAutoCoder/Agentless) | MIT claimed in public paper/search metadata | Medium | High | No | Medium | Optional baseline/reference | Important non-agent baseline to avoid overengineering. |
| [OpenHands](https://github.com/OpenHands/OpenHands) | MIT except enterprise directory | High | Very high | No | Medium | Optional external baseline | Core may be permissive; enterprise directory must remain excluded. |
| [SWE-bench sb-cli](https://github.com/SWE-bench/sb-cli) | Needs pinned verification | Medium | Medium | No | Low/medium | Optional submission adapter | Later external validation only. |
| [mco](https://github.com/mco-org/mco) | Needs pinned verification | Low/medium | Medium | No | Medium | Optional cross-provider benchmark helper | Useful only after COS result schema is stable. |

### Adversarial generalization

| Tool / source | Apparent license | Confidence | Weight if used | Default? | DX value | Recommended integration | Notes |
|---|---|---:|---|---|---|---|---|
| [AgentBench](https://github.com/THUDM/AgentBench) | Needs pinned verification | Medium | Very high | No | Low/medium | Reference taxonomy | Too broad/heavy for default. |
| [General-AgentBench](https://github.com/cxcscmu/General-AgentBench) | MIT in repo metadata | High | Very high | No | Medium | Reference/adversarial methodology | Strong evidence for context ceiling and verification gap. |
| [OSWorld](https://github.com/xlang-ai/OSWorld) | Apache-2.0 in paper/docs | Medium-high | Very high | No | Low/medium | Future optional computer-use lane | Requires real OS environments; not core. |
| [AndroidWorld](https://github.com/google-research/android_world) | Needs pinned verification | Medium | Very high | No | Low | Future portability reference | Mobile/control benchmark; not near-term SO work. |
| [WildClawBench](https://github.com/InternLM/WildClawBench) | MIT in repo metadata | High | Very high | No | Medium | Reference/adversarial scenarios | Useful task families: privacy leaks, prompt injection, malicious skills. |
| [AgencyBench](https://github.com/GAIR-NLP/AgencyBench) | Needs pinned verification | Medium | Very high | No | Low/medium | Reference only | Long-horizon methodology; too expensive initially. |
| [ARC Prize](https://arcprize.org/) / [Procgen](https://github.com/openai/procgen) | Mixed; Procgen license must be pinned | Medium | Medium/High | No | Medium | Principle/reference | Use procedural-generalization doctrine, not dependency. |

## Default install impact

Default Cognitive OS install should add only:

| Capability | Default impact |
|---|---|
| Lethal Trifecta Gate | One small Python module + one Bash hook + JSONL metrics. |
| ACI MVP | One normalizer module + docs/contracts, once implemented. |
| Skill efficacy | Reads existing metrics; reports generated only on demand. |
| Runtime benchmark | No default runtime cost; tasks run only by explicit command. |
| Adversarial generalization | No default runtime cost; scenarios generated only by explicit command. |

No Docker images, external benchmark datasets, npm trees, model eval frameworks, or SaaS scanners should be installed by default.

## DX impact

| Capability | Developer-facing value | Risk if overbuilt |
|---|---|---|
| Lethal Trifecta Gate | Higher confidence using agents around private repos and untrusted issue/docs content. | False positives blocking legitimate workflows. |
| ACI | Less context waste, clearer failures, better tool observations. | Wrapping tools too much and hiding useful raw evidence. |
| Skill efficacy | Shows which skills help, cost, or regress. | Metric noise if tasks are not paired fairly. |
| Vanilla-vs-COS benchmark | Proves whether COS helps versus vanilla. | Expensive, flaky benchmarks if too large too early. |
| Adversarial generalization | Catches failures contract tests miss. | Scenario explosion and slow local validation. |

## Implementation decision

The approved direction is:

1. Build internal deterministic cores first.
2. Keep all external tools opt-in.
3. Require pinned-version license evidence before each adapter.
4. Benchmark before making DX claims.
5. Present simple reports: `safety`, `aci`, `skills`, `benchmark`, `adversarial`.


## Automated license gate

The pinned optional-tool manifest lives at `.cognitive-os/tests/agentic-tools/license-matrix.json` and is checked by `scripts/agentic_tool_license_matrix.py`. The script is stdlib-only, requires no network access, blocks AGPL/SSPL/BSL/ELv2/Commons-Clause license families, and blocks `default_enabled=true` for external tools with `High` or `Very high` weight. It can emit Markdown and JSON reports for CI or local review. `scripts/agentic-tool-license-matrix.py` is the hyphenated CLI entrypoint for maintainers.

## Near-term actions

1. Implement Lethal Trifecta Gate MVP.
2. Add `scripts/agentic_tool_license_matrix.py` later to refresh this matrix from pinned metadata.
3. Add optional-tool status reporting to `make test-agentic-mastery` once that target exists.
