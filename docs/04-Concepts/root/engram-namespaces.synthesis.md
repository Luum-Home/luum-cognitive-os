---
type: concept-synthesis
source: docs/04-Concepts/root/engram-namespaces.md
provenance: "A single Engram instance serves all projects on a developer's machine — without namespaces, an agent on Project B could retrieve Project A's architecture decisions, causing incorrect code or security leaks."
---

## What it is

Namespace design isolating project-specific memory from universal cross-project patterns and anonymized metrics inside a single shared Engram instance.

## Key mechanics

**3 namespaces**:
- `cognitive-os` — universal knowledge shared across ALL projects (opt-in). Contains: skill feedback, language/tool-level error patterns, model-routing insights, convention patterns, hook improvements, tool-compatibility notes. Rule: NEVER project-specific data, NEVER credentials/URLs/infra details. Topic key prefix: `cognitive-os/{skill-feedback|error-pattern|model-routing|convention|hook-improvement}/...`.
- `{project}` — one project's private memory, NEVER shared. Contains: architecture decisions, service inventory, SDD artifacts, SRE fixes, bug discoveries, infra config, business logic, team conventions. Topic keys: `planning/{change}/{proposal|spec|design|tasks}`, `sre-fix/{container}/{error-type}`, `architecture/{component}`, `discovery/{slug}`, `session-summary/{date}`.
- `cognitive-os-meta` — aggregated, anonymized performance data (opt-in, anonymized). Contains: agent KPIs, squad performance, model cost analysis, skill execution metrics, error recurrence rates — counts/percentages/durations only, never content or project/service names. Topic keys: `cognitive-os-meta/{agent-kpis|squad-report|model-cost|skill-metrics}/...`.

**Current implementation**: Engram's existing `project` parameter provides isolation (`mem_save(project="{project}"|"cognitive-os"|"cognitive-os-meta", topic_key=..., content=...)`); topic key prefixes give logical sub-organization within each. Search is scoped: `mem_search(query=..., project="{project}")` cannot cross into another project's namespace.

**Promotion rule** (project→universal): when an agent discovers a NON-project-specific pattern, it saves to both project and `cognitive-os` namespaces (anonymized). Promote YES: language/framework bug workarounds, tool config patterns, skill improvements from failures, model routing optimizations. Promote NO: business logic decisions, infra config, service endpoint mappings. NEVER: credentials/auth details.

**Demotion rule**: if a "universal" pattern turns out project-specific — delete from `cognitive-os`, keep in `{project}`, add guard comment noting why demoted.

**Privacy hard rules**: project namespace never readable cross-project; no cross-project search; metrics namespace is anonymized (counts/percentages, never content); `/private` mode disables ALL Engram writes; deletion is per-namespace (removing a project deletes only its namespace). Every write carries audit fields: `project`, `topic_key`, `type`, `scope`, `timestamp`.

**Config** (`cognitive-os.yaml`): `engram.namespace` (project namespace name), `engram.universal_learning` (promote to cognitive-os), `engram.metrics_sharing` (share to cognitive-os-meta), `engram.privacy.{disable_universal_writes, disable_metrics, private_mode_on_start}`.

**Migration path**: Phase 1 (current) = single Engram instance, `project` param + topic-key-prefix logical separation. Phase 2 = explicit content-classification-based routing. Phase 3 = multi-tenant SaaS with separate physical Engram databases per namespace, API-gateway-enforced tenant isolation, universal knowledge replicated (not shared) to tenants.

## Relations & where used

`rules/engram-organization.md` (topic key prefix system this extends), `docs/04-Concepts/root/distributed-architecture.md` (Phase 1 multi-project namespace extension).

## Status / caveats

The "Future: Separate Databases" config block is explicitly marked "not yet available" — current implementation is single-instance with logical (parameter+prefix) separation only, not physical database isolation. Multi-tenant SaaS implications (GDPR deletion, data residency) are documented as forward-looking requirements, not implemented behavior.
