---
title: "HelixDB Annex D — License (AGPL-3.0 §13) & open-core trapdoor analysis"
date: 2026-05-11
parent: helixdb-comparison-2026-05-11.md
scope: research-only
license_constraint: "AGPL-3.0 — pattern-only adoption, clean-room rewrite required. This annex evaluates *why* the license blocks runtime adoption; it does not re-litigate the verdict."
---

> **License compliance disclaimer.** Structural descriptions and value references in this annex are paraphrased from upstream HelixDB (AGPL-3.0, https://github.com/HelixDB/helix-db). No verbatim source code is vendored into COS — code-block fences contain pseudo-syntax sketches, factual config values, or API surface enumerations that are non-creative or fair-use. Clean-room rewrites of any documented primitive MUST reference these annexes as **inputs**, not derive directly from upstream source. See [`helixdb-annex-d-license-opencore-risk-2026-05-11.md`](helixdb-annex-d-license-opencore-risk-2026-05-11.md) for the full license disposition (REJECT runtime / TRIAL-PATTERNS clean-room-only).

# Annex D — License and open-core risk

## D.1 The verbatim AGPL-3.0 §13 obligation

The repo `LICENSE` file is the unmodified AGPL-3.0 (header confirmed line 1: `GNU AFFERO GENERAL PUBLIC LICENSE Version 3, 19 November 2007`). Section 13 (the AGPL-defining clause) requires that:

> If you modify the Program, your modified version must prominently offer all users interacting with it remotely through a computer network […] an opportunity to receive the Corresponding Source of your version by providing access to the Corresponding Source from a network server at no charge […].

Applied to "a backing memory DB for an agent OS" this means:

1. **Network interaction triggers §13.** Any deployment of luum-agent-os in which a third party (an agent, a user, a remote MCP client, a CI service) interacts with a HelixDB-derived instance — even read-only — obliges us to publish the *complete* corresponding source of the modified version under AGPL-3.0.
2. **"Corresponding source" is interpreted broadly.** In practice, downstream license auditors (and litigation) extend it to any layer linking against AGPL Rust crates. If luum-agent-os links to `helix-db` as a Rust dependency, the whole linked binary inherits the §13 obligation. Dynamic linking is *not* a recognised AGPL escape hatch (unlike LGPL).
3. **"Modified" includes config-only forks** if a third party can argue functional change. The Cargo features `dev-instance`, `production`, `bench` already represent build-config divergence; running with a non-default feature set could itself be argued as "modified".
4. **MCP exposure is the worst case.** MCP-served data egress from a HelixDB instance is precisely the "remote network interaction" §13 targets. There is no defensible posture under which we ship `helix-db` as the Engram substrate without AGPL-ing the entire COS.

This is consistent with `rules/license-policy.md` which puts AGPL on the **BLOCK** list and with the prior addendum's `rejected` verdict for both the dependency-embed lane and the operator-installed-service lane.

## D.2 Open-core trapdoor evidence (string-by-string)

A repo-wide grep for `Enterprise|enterprise|premium|Lite|Cloud` (case-sensitive on the capital forms; full ripgrep `--include="*.rs" --include="*.toml" --include="*.md"`) yields the following load-bearing hits. This is not a marketing argument — these are mechanical, build-time and code-path-level splits.

### D.2.1 README — explicit "managed service / enterprise support" pitch

`README.md:131`:

> HelixDB is available as a managed service for selected users, if you're interested in using Helix's managed service or want enterprise support, [contact](mailto:founders@helix-db.com) us for more information and deployment options.

Status: marketing surface, not (yet) a code surface. Sets the commercial frame.

### D.2.2 CONTRIBUTORS.md — declared topology of the closed half

`CONTRIBUTORS.md:162-167, 215, 318`:

- `:162` "integrations/   # Cloud deployment integrations"
- `:167` "helix.rs    # Helix Cloud"
- `:215` "Helix Cloud (managed hosting)"
- `:318` "Cloud queries"

This is HelixDB's own self-description of the split.

### D.2.3 CLI source — enterprise code paths are real, not theoretical

`helix-cli/src/commands/workspace_flow.rs`:
- `:18 pub struct EnterpriseClusterResult { … }` — a real Rust type.
- `:30 Enterprise(EnterpriseClusterResult)` — variant of the `ClusterResult` enum.
- `:95 struct CreateEnterpriseClusterRequest<'a> { … }` — request-body type.
- `:106-114 fn build_enterprise_cluster_request(...)` — builder fn.
- `:159-162` `let cluster_type = if workspace.workspace_type == "enterprise" { … } else { "Selected workspace is not enterprise; creating a standard cluster." };` — runtime branch.
- `:169` `create_enterprise_cluster_flow(…)` — the dedicated flow.
- `:473 async fn create_enterprise_cluster_flow(…)` — definition.
- `:570 Ok(ClusterResult::Enterprise(EnterpriseClusterResult { … }))` — return path.

`helix-cli/src/config.rs`:
- `:77 pub enterprise: HashMap<String, EnterpriseInstanceConfig>` — config has a *first-class* enterprise instance map alongside `local` and `cloud`.
- `:553`, `:596`, `:633-634`, `:646`, `:668`, `:696` — repeated branches on the `enterprise:` map.
- `:634 InstanceInfo::Enterprise(enterprise_config)` — runtime discriminator.

`helix-cli/src/commands/compile.rs`:
- `:113 "Enterprise query project did not generate queries.json at {}"` — the open-source CLI **literally compiles a separate enterprise query project** and shells out for it. The enterprise build target is wired into the OSS CLI; the OSS CLI fails informatively if the closed enterprise crate is missing.
- `:118 resolve_enterprise_output_path(…)` — output-path resolver tailored to the enterprise target.

`helix-cli/src/prompts.rs`:
- `:453` "Prompt user to select cluster type (standard vs enterprise)"
- `:462 "enterprise",` literal
- `:487` "Prompt user to select availability mode for enterprise clusters"
- `:573-606` — interactive picker that handles a `enterprise: &[(String, String, String)]` slice alongside standard clusters.

`helix-cli/src/commands/dashboard.rs:435`: dashboard URL template `"{}/enterprise-clusters/{}"` — enterprise clusters have dedicated dashboard endpoints.

### D.2.4 Telemetry payload — DeployCloud is a first-class event

`metrics/src/events.rs:12, 35, 63, 87`:
- `EventType::DeployCloud` and the matching `EventData::DeployCloud(DeployCloudEvent)`. Cloud deploys are a metric vertical.

### D.2.5 Documented enterprise test plan

`helix-cli/ENTERPRISE_CLI_TEST_PLAN.md` exists as a 150+ line plan describing:
- "enterprise runtime/provisioner: `~/GitHub/helix-hyperscale`" (`:26`)
- "enterprise query DSL generator: `~/GitHub/helix-enterprise-ql`" (`:27`)
- "only `enterprise` workspaces can use enterprise clusters" (`:18`)
- "Direct API test: creating enterprise cluster from non-enterprise workspace returns `403`" (`:74`)
- Multiple phases (`Phase 2 - Enterprise Push Path`, `Phase 3 - Enterprise Sync Path`).

These reference **two private repositories** by path: `helix-hyperscale` (the closed runtime) and `helix-enterprise-ql` (a closed alternative DSL generator). The split is therefore not just deployment topology — there is a parallel **closed query-DSL generator** in a private repo that the OSS CLI knows about and can shell out to.

### D.2.6 Cargo features — the build-time switch

`helix-db/Cargo.toml:78-89`:
```
debug-output = ["helix-macros/debug-output"]
compiler     = ["pest", "pest_derive", "ariadne"]
cosine = []
api-key = []
build = ["compiler"]
vectors = ["cosine", "url"]
server = ["build", "compiler", "vectors", "reqwest"]
full = ["build", "compiler", "vectors"]
bench = ["polars"]
dev = ["debug-output", "server", "bench"]
dev-instance = []
default = ["server"]
production = ["api-key","server"]
```

Two surface features matter:
- `production` adds the API-key path. **The default profile does not enable it.** A naive operator following the README will ship auth-disabled.
- `dev-instance` toggles in built-in admin handlers (`gateway.rs:14-21` shows the `#[cfg(feature = "dev-instance")]` gating). These are not exposed in production builds — a clean enable/disable, but operators who flip the feature on for debugging keep the admin endpoints open.

### D.2.7 Summary — is the split mechanical or marketing?

**Mechanical, on multiple axes:**

- Rust types (`EnterpriseClusterResult`, `EnterpriseInstanceConfig`) exist in the OSS CLI.
- Config schema (`enterprise: HashMap<…>`) is committed.
- Build paths (`compile.rs` compiling a separate enterprise crate) exist.
- API endpoints (`/enterprise-clusters/{}`) are templated.
- Telemetry events (`DeployCloud`) are emitted.
- A documented test plan references two named **closed repos** the OSS half is expected to interact with.

The OSS half is wired up to be the thin client of a closed control plane. This is the canonical open-core trapdoor shape: take a dependency now, watch the OSS half hollow out over time. The license already prevents adoption; this trapdoor analysis is the reason the prior addendum kept `pattern-only` rather than escalating to a blanket REJECT-and-forget.

## D.3 Clean-room rewrite cost estimate

Per-primitive estimate of clean-room effort for the patterns the other annexes call out (rough person-weeks of Rust-strong engineer time; assume the engineer has never read the helix source):

| Primitive | Description | Effort (PW) | Notes |
|---|---|---|---|
| Compiled-DSL contract (Annex A) | Parser (pest) + analyzer (type checker) + Rust codegen for a typed graph-DSL | 6–10 | Dominated by error-recovery and migration validation. Significant grammar design work *before* coding. |
| Typed-ADT MCP surface (Annex C) | Recursive `ToolArgs`-equivalent enum + serde wire format + storage-layer adapter | 1–2 | Small once the grammar is set; serde does most of the work. |
| RRF + MMR reranker layer (Annex B) | Two strategies + score-normalizer + integration tests against a synthetic dataset | 1 | Textbook algorithms; cost is integration with whichever retrieval surface we have. |
| Filter-aware HNSW (Annex B) | Standard HNSW with filter-during-walk | 3–4 | Skip if we don't build a custom vector index. |
| Two-way inverted index (Annex B) | Forward + reverse postings | 2 | Skip while FTS5 is enough. |
| Single-writer worker pool (Annex C) | flume-bounded channels, oneshot reply, write-route HashSet | 1 | Skip until COS hosts a stateful shared backend. |
| IoContFn continuation (Annex C) | Suspend-and-resume around await inside a logical transaction | 1–2 | Only relevant if Engram grows a real transaction model. |
| LMDB-everything substrate (Annex A) | Heed3 wrapper, dup-sort tables, prefix-keyed adjacency | 4–6 | **Not recommended** — see Annex A §A.3. SQLite remains the right choice. |

**Total realistic adoption window** (only the three top-ranked primitives, see Annex E): **8–13 PW**, mostly in the compiled-DSL line. Without the DSL, **2–3 PW** for typed-MCP + reranker.

This is *clean-room cost only* — does not include the ADR + license audit + COS roadmap integration, which add ~1 PW of process overhead.

## D.4 Conclusion

License: blocking, end of discussion.

Trapdoor: real, mechanical, and the AGPL half is being positioned to depend on closed components. Even if the license flipped to MIT tomorrow, the open-core trajectory would still warrant caution per `docs/04-Concepts/architecture/external-tool-adoption-doctrine.md`.

Pattern lane: open for the three primitives in Annex E §1–§3, with the cost figures above.
