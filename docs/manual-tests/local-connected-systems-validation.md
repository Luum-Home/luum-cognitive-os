# Local Connected Systems Validation

This proof path validates Cognitive OS on a real local machine connected to the
systems it may need: declared CLIs, Python dependencies, MCP servers, memory,
Docker/reference services, and harness projections. It exists to prevent the
headless runtime plan from becoming aspirational.

## Purpose

Before claiming that Cognitive OS can run as a local runtime, CI worker, VM,
container, or future worker cluster, prove that a local installation can:

1. discover the active harness driver;
2. verify required and recommended dependencies;
3. install or report missing components through explicit profiles;
4. register or verify MCP wiring;
5. start only the services required by the selected profile;
6. run real quality checks and persist a test summary;
7. fail safely when optional systems are unavailable.

## Source of Truth

Dependency state must come from repository contracts, not from ad-hoc shell
checks spread through docs:

| Contract | Role |
| --- | --- |
| `manifests/dependencies.yaml` | Declares required, recommended, and optional CLIs, Python groups, and MCP servers. |
| `scripts/manifest-check.sh` | Reports dependency readiness for a selected profile. |
| `scripts/setup.sh` | Installs local development dependencies by profile. |
| `scripts/register-mcps.sh` | Registers MCP servers declared in the manifest where supported. |
| `scripts/cos-doctor-tools.sh` | Verifies active harness, driver settings, dependency wiring, and Engram host state. |
| `scripts/cos-doctor-memory-lifecycle.sh` | Verifies session memory lifecycle hooks and Engram paths. |
| `scripts/cos-bootstrap.sh` | Starts optional/reference infrastructure services when a full profile explicitly requests them. |
| `docs/architecture/infrastructure-service-catalog.md` | Explains why each service exists and whether it is core, optional, or reference-only. |

The validation flow must treat `manifests/dependencies.yaml` as the inventory
contract. If a tool or service is needed by the SO, it should be declared there
or cataloged as an infrastructure service. If it is not declared or cataloged,
it is not part of the supported runtime claim.

## Profiles

| Profile | Intended use | Expected behavior |
| --- | --- | --- |
| `minimal` | Fresh project or lightweight workstation | Required local CLIs and Python package only; no heavy services. |
| `default` / `standard` | Normal developer workstation | Adds test/development tooling and recommended memory/MCP checks. |
| `full` | Local connected systems validation | Adds optional tools and explicitly starts optional/reference services when Docker is available. |

Optional services must never become mandatory for default local use. Docker,
observability backends, Paperclip, Jupyter, Cognee HTTP, Opik local, and similar
systems are extension/reference surfaces unless a specific proof path enables
them.


## Isolated Product-System Mode

Local connected validation must not run against a developer's real production
workspace or shared service state by accident. When Cognitive OS is connected to
systems we develop as part of a product, the run must use an explicit isolation
contract:

| Surface | Isolation requirement |
| --- | --- |
| Repository | Use a disposable git worktree, temp clone, or mounted sandbox workspace. |
| Runtime state | Write only under `.cognitive-os/` inside the isolated workspace or an explicit artifact directory. |
| Service state | Use Docker Compose project names, local ports, or testcontainers namespaces that cannot collide with developer services. |
| Data | Seed synthetic fixtures; never connect to production data by default. |
| Secrets | Use fake/local secrets from env vars or a secret-manager test namespace; never generate secrets into repo files. |
| Registry | Temporary/canary installs must not enter the default COS registry. |
| Outputs | Patches, logs, summaries, and traces must be written as artifacts that can be deleted with the sandbox. |

This mode is the local precursor to the future headless worker runtime. It lets
Cognitive OS repair or build against real product-shaped systems while keeping
side effects bounded and auditable.

### Product-System Connection Contract

A product system may be connected to the local SO only through an explicit
adapter or profile that declares:

1. required tools and Python groups in `manifests/dependencies.yaml`;
2. required optional services in the infrastructure service catalog;
3. the command that starts those services locally;
4. readiness checks and teardown behavior;
5. which artifacts prove success;
6. degraded behavior when the product system is unavailable.

A connected-system proof is incomplete unless it proves both the happy path and
the isolation boundary. For example, a bug-repair proof should show that the SO
can reproduce a failing test against the product system, generate a patch in an
isolated workspace, run quality gates, persist artifacts, and tear everything
down without leaking host paths, credentials, or temporary installs.

## Automatic Install Boundary

Cognitive OS may help install or update components, but automatic remediation is
bounded:

- `scripts/setup.sh` may install local development dependencies for the selected
  profile.
- `scripts/manifest-check.sh` is a verifier, not an installer.
- `scripts/cos-doctor-tools.sh` is advisory by default; it should explain what is
  missing instead of silently mutating the host.
- MCP registration can be automated by `scripts/register-mcps.sh`, but the host
  application may still require a restart before newly registered MCP tools are
  visible.
- Heavy services must be explicit. `scripts/cos-bootstrap.sh` may start them only
  for a profile or command that intentionally opts into them.
- Secrets must come from environment variables or the host secret manager, never
  from generated repo files.

If a component cannot be installed automatically, the SO should still provide a
clear diagnosis, installation hint, degraded behavior, and proof that the core
runtime remains usable without that optional component.

## Manual Proof Path

Run these from the repository root.

### 1. Verify declared dependencies

```bash
bash scripts/manifest-check.sh --profile default
bash scripts/manifest-check.sh --profile full --json > .cognitive-os/reports/dependency-full.json
```

Acceptance criteria:

- required tools are present or the command exits non-zero with precise install
  hints;
- recommended/optional tools are reported without blocking the default profile;
- output can be saved as an artifact for later comparison.

### 2. Install profile dependencies intentionally

```bash
bash scripts/setup.sh --standard
```

For full connected validation only:

```bash
bash scripts/setup.sh --full
```

Acceptance criteria:

- install is idempotent;
- already-present dependencies are skipped;
- optional failures do not corrupt core state;
- full profile never runs implicitly during normal harness startup.

### 3. Verify harness and MCP wiring

For Codex:

```bash
COGNITIVE_OS_HARNESS=codex CODEX_PROJECT_DIR="$PWD" bash scripts/cos-doctor-tools.sh
```

For Claude Code:

```bash
COGNITIVE_OS_HARNESS=claude CLAUDE_PROJECT_DIR="$PWD" bash scripts/cos-doctor-tools.sh
```

Acceptance criteria:

- the active harness is detected from canonical metadata or explicit env;
- the native settings driver exists and is valid;
- Engram CLI and MCP registration are detected when available;
- missing recommended MCPs produce advisory output, not false product claims.

### 4. Verify memory lifecycle

```bash
COGNITIVE_OS_HARNESS=codex CODEX_PROJECT_DIR="$PWD" \
  bash scripts/cos-doctor-memory-lifecycle.sh --harness codex
```

Acceptance criteria:

- session-start, prompt, stop, and summary-reminder memory hooks are discoverable;
- Engram-dependent behavior degrades cleanly when Engram is unavailable;
- fallback JSONL/changelog artifacts are written for recovery.

### 5. Start optional connected services only when requested

```bash
bash scripts/cos-bootstrap.sh --profile full
```

Acceptance criteria:

- services started by Docker are limited to the selected profile;
- optional/reference services are not required for the core local runtime;
- service purpose and status match `docs/architecture/infrastructure-service-catalog.md`;
- logs and health results are written outside tracked source files.

### 6. Run a persistent test summary

```bash
bash scripts/pytest-with-summary.sh tests/ -m "not docker and not e2e"
```

Acceptance criteria:

- the run creates a timestamped directory under `.cognitive-os/reports/test-runs/`;
- failures, skips, xfails, and warnings are visible without rerunning the suite;
- generated artifacts are ignored by Git;
- the result is used to repair behavior, not to relax tests.

## Future Automation

The headless runtime should eventually expose one command that composes this
flow without hiding what it does, for example:

```bash
cos doctor --profile default --harness codex
cos doctor --profile full --connected-systems
```

That command should be a wrapper over the declared contracts above, not a second
source of dependency truth.
