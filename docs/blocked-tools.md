# Cognitive OS — Blocked Tools

> Tools that are technically excellent but blocked by [Cognitive OS license policy](../research/license-analysis.md).
> Documented here so we remember WHY they were excluded and can revisit if licensing changes.

---

## Blocked by AGPL

### Daytona (65k stars) — Runtime Sandbox
- **License**: AGPL v3
- **What it does**: Development environment management with instant workspace creation. Best-in-class developer experience for sandboxed environments.
- **Why it's excellent**: 65k stars (largest in the sandbox category by far), polished UX, multi-IDE support, Git-native workflows.
- **Why it's blocked**: AGPL requires open-sourcing all code that interacts with it over a network. As a SaaS platform, using Daytona would require us to open-source our entire codebase.
- **Alternative**: E2B (Apache 2.0, 11.4k stars) — less polished UX but fully permissive license and Firecracker-based security.
- **Revisit if**: Daytona offers a commercial license or relicenses to Apache 2.0/MIT.

### Windmill — Scheduler / Workflow Engine
- **License**: AGPL v3
- **What it does**: Workflow automation platform with visual DAG builder, multi-language support, and built-in scheduling.
- **Why it's excellent**: Powerful visual workflow editor, supports Python/TypeScript/Go/Bash scripts, built-in secret management.
- **Why it's blocked**: Same AGPL issue as Daytona — network interaction triggers copyleft obligation.
- **Alternative**: Temporal (MIT, 19k stars) — more mature, larger ecosystem, production-proven at scale.
- **Revisit if**: Windmill relicenses or offers a permissive commercial license.

### QueryWeaver (FalkorDB/QueryWeaver) — Text2SQL
- **License**: AGPL-3.0
- **What it does**: Text2SQL using graph-powered schema understanding for natural language to SQL conversion.
- **Why it's excellent**: New project leveraging FalkorDB's graph capabilities for schema-aware query generation.
- **Why it's blocked**: AGPL requires distributing source of any modified/linked software.
- **Alternative**: SQLAgent patterns with MIT-licensed components.
- **Revisit if**: QueryWeaver relicenses. Evaluated: 2026-03-26.

---

## Blocked by SSPL

### Inngest — Scheduler / Event-Driven Workflows
- **License**: SSPL (Server Side Public License)
- **What it does**: Event-driven durable functions. Step functions with automatic retries, fan-out, and scheduling.
- **Why it's excellent**: Elegant developer experience, no infrastructure to manage, built-in observability.
- **Why it's blocked**: SSPL explicitly prohibits offering the software as a service. Designed specifically to block SaaS competitors.
- **Alternative**: Hatchet (MIT, 6.6k stars) — PostgreSQL-based, similar DAG orchestration capabilities.
- **Revisit if**: Inngest relicenses. SSPL projects rarely change license, so this is unlikely.

### FalkorDB (FalkorDB/FalkorDB) — Graph Database
- **License**: SSPL (Server Side Public License v1)
- **What it does**: Graph database using GraphBLAS for high-performance graph operations.
- **Why it's excellent**: 3.7k stars, actively maintained, fast graph queries leveraging sparse linear algebra.
- **Why it's blocked**: SSPL requires open-sourcing entire service stack if offered as a service.
- **Alternative**: Apache AGE (Apache 2.0) — PostgreSQL graph extension with Cypher query support.
- **Revisit if**: FalkorDB relicenses. Evaluated: 2026-03-26.

---

## Blocked by ELv2

### Arize Phoenix — Observability
- **License**: Elastic License v2 (ELv2)
- **What it does**: LLM observability and evaluation platform. Traces, evals, datasets, experiments.
- **Why it's excellent**: Deep evaluation capabilities, experiment tracking, dataset management. Strong integration with LangChain ecosystem.
- **Why it's blocked**: ELv2 prohibits offering the software as a managed service. While we could self-host for internal use, the license creates ambiguity around SaaS boundaries.
- **Alternative**: Langfuse (MIT, 23k stars) — covers tracing, prompts, evals, and cost tracking with a fully permissive license.
- **Revisit if**: Arize relicenses Phoenix or offers a separate permissive edition.

---

## Summary Table

| Tool | Category | Stars | License | Blocker | Best Alternative |
|------|----------|-------|---------|---------|-----------------|
| Daytona | Sandbox | 65k | AGPL | Copyleft (network) | E2B (Apache 2.0) |
| Windmill | Scheduler | — | AGPL | Copyleft (network) | Temporal (MIT) |
| QueryWeaver | Text2SQL | new | AGPL | Copyleft (linked) | SQLAgent (MIT) |
| Inngest | Scheduler | — | SSPL | Blocks SaaS | Hatchet (MIT) |
| FalkorDB | Graph DB | 3.7k | SSPL | Blocks SaaS | Apache AGE (Apache 2.0) |
| Arize Phoenix | Observability | — | ELv2 | Blocks managed service | Langfuse (MIT) |

---

## License Watch

These tools should be monitored for license changes. The trend in 2024-2025 has been:
- Some AGPL projects offering commercial dual licenses
- Some BSL projects converting to Apache 2.0 after the time-delay period
- ELv2 projects occasionally releasing community editions under permissive licenses

Check quarterly for updates.
