# Python Major Lane Resolution — 2026-05-04

## Summary

The retained Python majors were resolved architecturally by ADR-145: heavy optional dependency stacks moved out of `pyproject.toml` extras into explicit requirement lanes under `requirements/dependency-lanes/`.

This changes the question from "can every optional stack upgrade together in one universal lock?" to "can the core maintainer lane stay current while optional lanes are validated independently?"

## Core lock outcome

After the split, the core lock no longer contains the optional blockers:

- `arize-phoenix`
- `cognee`
- `crawl4ai`
- `nemoguardrails`
- `mlflow-skinny`
- `opentelemetry-proto`
- `torch`
- `lxml`
- `pandas`
- `protobuf`
- `snowballstemmer`

Core lock majors advanced or disappeared:

| Former blocker | Core-lane outcome |
|---|---|
| `wrapt>=2` | Applied in core lock: `wrapt 2.1.2`. Phoenix/OpenInference remains in `observability.txt`. |
| `setuptools>=82` | No longer present in the core lock. Torch semantic blocker moved to `semantic.txt`. |
| `rich>=15` | Applied in core lock: `rich 15.0.0`. Cognee/instructor blocker moved to `memory.txt`. |
| `packaging>=26` | Applied in core lock: `packaging 26.2`. Cognee/limits blocker moved to `memory.txt`. |
| `importlib-metadata>=9` | No longer present in the core lock after moving LiteLLM/MLflow-heavy lanes out. |
| `arize-phoenix>=15` | Not part of core lock; tracked by `observability.txt`. |
| `lxml>=6`, `snowballstemmer>=3` | Not part of core lock; tracked by `crawling.txt`. |
| `pandas>=3`, `marshmallow>=4` | Not part of core lock; tracked by `guardrails.txt` / semantic transitive lanes. |
| `protobuf>=7` | Not part of core lock; tracked by `observability.txt`. |

## Remaining work

Optional lane owners can still audit their lane files separately. Their upstream constraints are no longer allowed to block the core maintainer lock. Use `bash scripts/dependency-lane.sh list|show|install <lane>` for lane discovery and installation.

Validation:

```bash
uv lock --check
python3 -m pytest tests/audit/test_dependency_lane_split.py tests/audit/test_no_undefined_imports.py -q
```
