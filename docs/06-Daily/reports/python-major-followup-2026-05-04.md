# Python Major Follow-up — 2026-05-04

## Scope

Followed the dependency-maintenance order after Docker audit cleanup:

1. `wrapt>=2` with Phoenix/OpenTelemetry/OpenInference protection.
2. `setuptools>=82` after the `pkg_resources` first-party scan cleared.
3. Remaining blocker clusters: `cognee`, `crawl4ai`, `nemoguardrails`, `mlflow-skinny`, and OpenTelemetry/protobuf.

This follow-up intentionally avoids `bash scripts/deps-update.sh --apply --major` because the all-extras lock combines optional surfaces (`observability`, `memory`, `guardrails`, `crawling`, `semantic`) whose upstream constraints conflict.

## Resolver attempts

| Candidate | Command shape | Result | Decision |
|---|---|---|---|
| `wrapt>=2` | `uv lock --upgrade-package 'wrapt>=2'` | Resolver can force `wrapt 2.1.2` only by downgrading/removing observability packages: `arize-phoenix 14.6.0 -> 12.6.1`, `openinference-instrumentation 0.1.48 -> 0.1.40`, removal of `openinference-instrumentation-openai` and `opentelemetry-instrumentation`. | Do not apply. This would silently weaken the Phoenix/OpenTelemetry surface the test was supposed to protect. |
| `wrapt>=2` with current observability floor | `uv lock --upgrade-package 'wrapt>=2' --upgrade-package 'arize-phoenix>=14.6.0' --upgrade-package 'openinference-instrumentation>=0.1.48' --upgrade-package 'openinference-instrumentation-openai>=0.1.45' --upgrade-package 'opentelemetry-instrumentation>=0.62b1'` | Unsatisfiable: `openinference-instrumentation==0.1.48` depends on `wrapt>=1.14.0,<2`; `arize-phoenix>=14.6.0` requires that instrumentation path. | Hard upstream blocker until OpenInference/Phoenix release a wrapt-2-compatible set. |
| `setuptools>=82` | `uv lock --upgrade-package 'setuptools>=82'` | Resolver selects `setuptools 82.0.1`, but also downgrades `torch 2.11.0 -> 2.10.0` and rewrites CUDA 13 packages to CUDA 12 packages. | Do not apply in this slice. The blocker is `torch==2.11.0` declaring `setuptools<82`, not first-party `pkg_resources`. |
| `setuptools>=82` with current Torch floor | `uv lock --upgrade-package 'setuptools>=82' --upgrade-package 'torch==2.11.0'` | Unsatisfiable: `torch==2.11.0` depends on `setuptools<82`; `sentence-transformers>=3.0` brings the Torch path through the `semantic` extra. | Hard blocker unless accepting a semantic-stack Torch downgrade or waiting for a Torch release compatible with `setuptools>=82`. |
| `arize-phoenix>=15`, `packaging>=26`, `rich>=15` | `uv lock --upgrade-package ...` | Unsatisfiable through `cognee`/`instructor`/`limits`: `instructor` requires `rich<15`; `limits` requires `packaging<25`; `arize-phoenix>=15` conflicts with the same memory stack. | Retain. Requires upstream memory-stack compatibility. |
| `lxml>=6`, `snowballstemmer>=3` | `uv lock --upgrade-package ...` | Unsatisfiable: available `crawl4ai>=0.8.0` requires `lxml>=5.3,<6.dev0` and `snowballstemmer>=2.2,<3.dev0`. | Retain. Requires crawl4ai compatibility. |
| `pandas>=3` | `uv lock --upgrade-package 'pandas>=3'` | Unsatisfiable through the guardrails stack; `nemoguardrails>=0.11.1` requires `pandas<3`, and lower versions conflict with current `crawl4ai`/`lark` and other dev constraints. | Retain. Requires guardrails-stack compatibility or removal from all-extras dev. |
| `marshmallow>=4` | `uv lock --upgrade-package 'marshmallow>=4'` | Unsatisfiable through `dataclasses-json`/`langchain-community` paths used by semantic/guardrails dependencies; available `dataclasses-json` still requires `marshmallow<4`. | Retain. Requires LangChain/dataclasses-json ecosystem compatibility. |
| `importlib-metadata>=9` | `uv lock --upgrade-package 'importlib-metadata>=9'` | Unsatisfiable: available `mlflow-skinny` ranges require `importlib-metadata<9`. | Retain. Requires MLflow compatibility. |
| `protobuf>=7` | `uv lock --upgrade-package 'protobuf>=7'` | Unsatisfiable: `opentelemetry-proto` available ranges require `protobuf<7`; Phoenix/OTel traces depend on that path. | Retain. Requires OpenTelemetry proto compatibility. |

## Outcome

No Python major was safely applied in this pass.

The useful progress is stricter evidence:

- `wrapt>=2` is now a hard OpenInference/Phoenix compatibility blocker, not merely an untested risk.
- `setuptools>=82` is now a Torch/semantic-stack compatibility blocker, not a `pkg_resources` blocker.
- The remaining clusters were re-proven against the current `origin/main` lock on 2026-05-04.

## Next unblock triggers

1. OpenInference/Phoenix releases instrumentation with `wrapt>=2` support.
2. Torch/sentence-transformers semantic stack releases a `setuptools>=82`-compatible path without downgrading Torch/CUDA in the universal lock.
3. `cognee`/`instructor`/`limits` relax `rich<15` and `packaging<25` constraints.
4. `crawl4ai` relaxes `lxml<6` and `snowballstemmer<3`.
5. `nemoguardrails`/LangChain/dataclasses-json relax pandas/marshmallow major bounds.
6. `mlflow-skinny` relaxes `importlib-metadata<9`.
7. `opentelemetry-proto` supports `protobuf>=7`.


## Resolution update — ADR-145

The second-pass blockers are still true inside their optional lanes, but they no longer block the core maintainer lock. ADR-145 moved heavy lanes to `requirements/dependency-lanes/`; see `docs/06-Daily/reports/python-major-lane-resolution-2026-05-04.md`.
