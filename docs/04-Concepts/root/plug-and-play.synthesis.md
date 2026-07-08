---
type: concept-synthesis
source: docs/04-Concepts/root/plug-and-play.md
provenance: "Goal: add a full AI agent operating system to any project with 1 file and 1 command, with no code changes, no framework lock-in, and no vendor dependency."
---

## What it is
The plug-and-play architecture for dropping Cognitive OS into any project via a single `docker-compose.cognitive-os.yml` file plus a `cognitive-os.yaml` config, layered independently from the project's own infra/app-service compose files.

## Key mechanics
- 3-layer Docker Compose: Layer 1 `docker-compose.yml` (project infra: DB/cache/queues), Layer 2 `docker-compose.services.yml` (project's own services), Layer 3 `docker-compose.cognitive-os.yml` (universal — same file for any project: Langfuse observability on 3100, LiteLLM cost routing on 4000, NeMo Guardrails security on 8088, governance dashboard on 3200).
- Network sharing: a `shared-network` (external:true) connects project services to COS services so app calls can route through LiteLLM for cost tracking without code changes.
- `cognitive-os.yaml` controls: `project.phase` (reconstruction/stabilization/production/maintenance — how freely agents can rewrite vs need feature flags), `observability.langfuse`, `cost_control.litellm` (monthly_budget, per_agent_budget, model_routing defaults), `security.nemo_guardrails` (block_pii, block_prompt_injection), `governance`, `quality_gates` (test_coverage_minimum, architecture_compliance, license_check), `squads.enabled`.
- Skills portability: universal `SKILL.md` format (YAML frontmatter: name/version/description/tags/model + When to Use/Procedure/Inputs/Outputs sections); project skills in `.claude/skills/` (checked into repo), global skills in `~/.claude/skills/`, auto-generated skills in `.claude/skills/auto-generated/`.
- Hooks portability: plain POSIX shell scripts in `.claude/hooks/{PreToolUse,PostToolUse,PreCompact,Notification}/`; project-specific behavior via a `.claude/hooks/config.json` adapter (e.g., test commands per stack).
- Squad system (optional): YAML squad definitions (`apiVersion: cognitive-os/v1alpha1, kind: Squad`) map repos to skills/agents/governance (constitutional_gates, test_coverage_minimum).
- Engram namespace separation: `cognitive-os` (universal, shared across all projects), `{project-name}` (project-specific, never shared), `cognitive-os-meta` (KPIs/metrics, shared for global improvement).
- 5-step adoption: copy compose file -> create `cognitive-os.yaml` -> `docker compose up -d` -> optionally add `.claude/{rules,skills,hooks}` -> optionally connect app network to LiteLLM.

## Relations & where used
References `engram-namespaces.md` for the full namespace design. Comparison table contrasts "with vs without" COS across cost tracking, error learning, agent quality, security guardrails, skill reuse, multi-agent coordination, incident response, and context loss.

## Status / caveats
Presented as a working quick-start pattern; no explicit implementation status field. Requires nothing beyond Docker for core function — "no cloud account required (everything runs locally)."
