# ADR-145 — Split heavy optional dependencies into explicit dependency lanes

Date: 2026-05-04
Status: Accepted

## Status

Accepted — Implemented

## Context

The project lock previously included every optional extra declared in `pyproject.toml`.
That made unrelated optional stacks block core dependency hygiene:

- `wrapt>=2` could only resolve by downgrading/removing Phoenix/OpenInference observability packages.
- `setuptools>=82` conflicted with the semantic stack because `torch==2.11.0` requires `setuptools<82`.
- `rich>=15`, `packaging>=26`, `lxml>=6`, `snowballstemmer>=3`, `pandas>=3`, `marshmallow>=4`, `importlib-metadata>=9`, and `protobuf>=7` were blocked by optional memory, crawling, guardrails, MLflow, and OpenTelemetry paths.

Those packages are not all required for normal SO development. Treating them as one universal lock caused optional upstream constraints to hold back the core maintainer lane.

## Decision

Keep `pyproject.toml` focused on the core maintainer lane:

- first-party runtime dependencies,
- lightweight web/direct-provider adapters,
- testing and enforcement tooling.

Move heavy optional stacks to explicit lane requirement files under `requirements/dependency-lanes/`:

- `llm.txt`
- `observability.txt`
- `memory.txt`
- `guardrails.txt`
- `crawling.txt`
- `jupyter.txt`
- `semantic.txt`

The core lock may now advance dependency majors independently. Heavy lanes remain installable and testable on demand, but their upstream constraints no longer block `uv lock` for core development.

## Consequences

Positive:

- Core lock updates can apply safe majors without being blocked by optional stacks.
- Optional dependency risk is visible by lane instead of hidden inside an all-extras lock.
- `wrapt>=2`, `packaging>=26`, and `rich>=15` can be represented in the core lock when compatible with core dependencies.
- `setuptools` is removed from the core lock unless a core dependency requires it.

Trade-offs:

- `uv sync --extra semantic`, `uv sync --extra observability`, and similar package extras are no longer the installation contract for heavy lanes.
- Lane users must install the corresponding requirement file explicitly.
- Lane validation needs separate commands and cannot be inferred from `uv lock --check` alone.

## Alternatives rejected

- Keep all optional extras in the core lock: rejected because optional upstream
  constraints were blocking unrelated core maintainer dependency hygiene.
- Remove heavy optional stacks entirely: rejected because observability, memory,
  crawling, guardrails, Jupyter, semantic, and LLM stacks remain useful when a
  task explicitly enters that lane.

## Installation contract

Core maintainer lane:

```bash
uv sync --extra dev
```

Discover lanes:

```bash
bash scripts/dependency-lane.sh list
bash scripts/dependency-lane.sh show observability
```

Install a heavy optional lane:

```bash
bash scripts/dependency-lane.sh install observability
```

The helper resolves to `uv pip install -r requirements/dependency-lanes/<lane>.txt`. Lane-specific tests must declare their lane prerequisites and skip cleanly when the lane is absent.

## Verification

```bash
uv lock --check
python3 -m pytest tests/audit/test_dependency_lane_split.py tests/unit/test_dependency_lane_script.py tests/audit/test_no_undefined_imports.py -q
bash scripts/deps-update.sh --audit
```

`bash scripts/deps-update.sh --audit` is for human review after syncing the
target environment.

## Implementation Evidence

- Implemented in `pyproject.toml`: core dependencies and `dev` extra exclude heavy optional lanes.
- Implemented in `requirements/dependency-lanes/`: explicit heavy-lane requirement files for LLM, observability, memory, guardrails, crawling, Jupyter, and semantic stacks.
- Implemented in `scripts/dependency-lane.sh`: lane discovery, path lookup, display, and install helper.
- Validated by `tests/audit/test_dependency_lane_split.py`.
- Validated by `tests/unit/test_dependency_lane_script.py`.
- Validated by `tests/audit/test_no_undefined_imports.py`.
