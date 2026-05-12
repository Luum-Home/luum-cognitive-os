# Proof Drill and Smoke Opt-In Agentic Primitives

## Purpose

Cognitive OS needs two validation modes that are related but not equivalent:

1. **Build/test the SO itself** — local, repeatable, normally cheap.
2. **Validate projects that implement the SO** — project-owned commands and
   harness projection checks.
3. **Qualify optional runtime paths** — Docker/headless, provider accounts,
   remote ingress, Engram Cloud, VM, Kubernetes, and similar proof surfaces.

The third category is not a default test lane. It is a proof drill or smoke
opt-in: explicit, evidence-producing, and bounded.

## Existing primitive review

| Surface | Current role | Scope | Notes |
|---|---|---|---|
| `skills/cognitive-os-test/SKILL.md` | SO test runner | os-self | Uses persisted pytest summaries and should remain SO-maintainer-only. |
| `skills/run-tests/SKILL.md` | Project test runner | consumer-project | The default way to test a downstream project. |
| `skills/smoke-test/SKILL.md` | Guided SO smoke | os-self | Existing smoke primitive; now linked to the registry. |
| `skills/test-contract-repair/SKILL.md` | Contract repair | os-self | Converts structural or stale tests into behavioral proof. |
| `scripts/smoke-qwen-fallback.sh` | Live provider smoke | os-self | Opt-in because it requires `ALIBABA_QWEN_API_KEY` and may cost money. |
| `scripts/smoke-multi-provider-fallback.sh` | Live provider smoke | os-self | Opt-in because it depends on provider-specific credentials. |
| `scripts/cos-headless-service-drill` | Docker/headless proof | os-self | Opt-in Docker proof with an integration contract. |
| `scripts/cos-engram-cloud-docker-smoke` | Engram Cloud Docker smoke | os-self | Opt-in Docker/local service proof. |
| `scripts/cos-cross-instance-drill` | Cross-instance proof | both | Can qualify transfer paths, but only with explicit temp artifacts. |
| `docs/09-Quality/manual-tests/service-control-plane-proof-drills.md` | Manual proof ladder | os-self | Keeps control-plane claims bounded until implementation matures. |

## Taxonomy

| Class | Default lane? | Typical trigger | Evidence expectation |
|---|---:|---|---|
| `standard-test-lane` | yes, when scoped | local code/test change | pass/fail output and summary |
| `smoke-opt-in` | no | live provider or narrow runtime check | command, env posture, exit, bounded claim |
| `proof-drill` | no | Docker/headless/service qualification | artifacts, cleanup mode, what proved/unproved |
| `manual-proof` | no | account/cloud/native lifecycle proof | human steps, commands, screenshots/log paths when useful |

## SO self-build versus consumer-project validation

Consumer projects must not inherit every SO maintainer drill. A downstream
project normally gets:

- projected harness instructions, hooks, rules, and skills according to profile;
- project-owned build/test commands through `/run-tests`;
- optional COS projection smokes only when the installer profile exposes them.

The SO maintainer repo additionally gets:

- `skills/cognitive-os-test/SKILL.md`;
- proof drills for headless runtime, provider fallback, Engram sync, and
  cross-instance learning;
- manual proof ladders for control-plane claims.

## Automated behavior tests already present

The repo already contains automated tests that support this doctrine:

- `tests/audit/test_skills_contracts.py` — skill frontmatter, references,
  catalog presence, and no procedural stubs.
- `tests/audit/test_marker_coverage.py` — test marker/lane coverage.
- `tests/audit/test_test_architecture_inventory.py` — inventory discipline for
  test architecture.
- `tests/integration/test_headless_service_drill.py` — Docker/headless drill
  contract without making it a default lane.
- `tests/contracts/test_cos_instance_implementation_phases.py` — phased COS
  instance installer assertions.
- `tests/contracts/test_host_cli_bridge_contract.py` — host CLI bridge deny-by
  default credential boundary.
- `tests/contracts/test_proof_drill_registry.py` — registry invariants for this
  primitive layer.

## Operating rules

1. If a task says “run tests”, choose the smallest standard lane that matches
   the changed surface.
2. If a task says “proof drill”, “smoke opt-in”, “live provider”, “Docker
   proof”, or “headless proof”, select from `manifests/proof-drill-registry.yaml`.
3. Do not treat missing provider credentials as failure of the SO. Record a
   skipped proof with the missing credential class.
4. Do not add proof drills to default CI or laptop lanes.
5. Every proof result must include what remains unproven.
6. If documentation claims more than the proof shows, repair the claim or create
   a stronger test before closing.

## Implemented selector and evidence adapter

- `scripts/proof-drill-select` reads `manifests/proof-drill-registry.yaml` and
  prints matching commands by `id`, `scope`, `class`, projection profile, and
  text selectors such as `provider`, `docker`, `headless`, and `codex`.
- `scripts/cos-instance-init --doctor --smoke --json` exposes registered proof
  drills for the selected instance profile without executing opt-in drills.
- `scripts/proof-drill-evidence-record` updates `docs/06-Daily/reports/proof-drill-evidence-latest.json`
  after a proof run.
- `scripts/acc_pipeline.py` consumes `docs/06-Daily/reports/proof-drill-evidence-latest.json`
  through the `proof_drill_evidence` adapter and maps successful proof rows to
  ACC `proof_drill:*` capabilities.
- `manifests/proof-drill-claim-map.yaml` maps durable runtime claims to stable
  proof drill ids so ACC also emits `proof_claim:*` capabilities. Passing
  evidence makes the claim `aligned`; failed evidence makes it `stale`; missing
  evidence leaves it `unverified`.
- `scripts/cos-headless-service-drill` records local Docker/headless evidence
  automatically after each run and records the Codex provider proof when the
  explicit `COS_RUN_PROVIDER_SMOKE=1` lane is used.
- `claude-provider-host-smoke` is registered as an opt-in proof drill after the
  host probe learned to discover Claude Code at governed known locations such as
  `$HOME/.local/bin/claude`.

## Remaining implementation slices

- Extend automatic evidence recording to any future proof scripts as they move
  from manual report-only procedures into stable scripts.
- Add more claim-map rows only after each claim has a stable proof drill id and
  bounded “does not prove” language.
- Keep consumer-project proof projection explicit; provider and Docker proof
  drills remain maintainer-only until a separate projection profile proves them
  safe downstream.
