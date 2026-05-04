# Python Major Dependency Review — 2026-05-04

## Scope

Reviewed the 11 major-version candidates surfaced by `bash scripts/deps-update.sh --audit` after the minor/patch maintenance pass. This review does **not** apply `--major`; it records which upgrades are blocked by the current all-extras lock and which need upstream validation.

Evidence commands:

```bash
uv lock  # baseline resolver still succeeds
uv lock with temporary direct constraints: arize-phoenix>=15, pandas>=3,
  protobuf>=7, packaging>=26, importlib-metadata>=9, lxml>=6,
  marshmallow>=4, rich>=15, setuptools>=82, snowballstemmer>=3, wrapt>=2
```

External references checked:

- Arize Phoenix release notes: https://arize.com/docs/phoenix/release-notes
- pandas 3.0 release notes: https://pandas.pydata.org/docs/dev/whatsnew/v3.0.0.html
- Protocol Buffers version support / Python 7 note: https://protobuf.dev/support/version-support/ and https://protobuf.dev/news/2025-09-19
- importlib-metadata 9.0 history: https://importlib-metadata.readthedocs.io/en/stable/history.html
- lxml 6 changelog: https://lxml.de/6.0/changes-6.0.4.html
- marshmallow 4 upgrade/changelog: https://marshmallow.readthedocs.io/en/stable/upgrading.html and https://marshmallow.readthedocs.io/en/stable/changelog.html
- setuptools `pkg_resources` removal: https://setuptools.pypa.io/en/stable/deprecated/pkg_resources.html
- snowballstemmer release history: https://pypi.org/pypi/snowballstemmer/
- wrapt release notes: https://wrapt.readthedocs.io/en/master/changes.html

## Decisions

| Package | Current | Latest seen | Decision | Local blocker / reason |
|---|---:|---:|---|---|
| `arize-phoenix` | 14.6.0 | 15.2.0 | **Do not apply** | `arize-phoenix>=15` conflicts with `luum-cognitive-os[memory]` through `cognee`/`fastapi`/`aiosqlite` constraints in the all-extras lock. |
| `importlib-metadata` | 8.5.0 | 9.0.0 | **Do not apply** | `mlflow-skinny>=2.0` resolves to constraints excluding `importlib-metadata>=9`. v9 changes missing-metadata behavior, so this should wait for MLflow validation. |
| `lxml` | 5.4.0 | 6.1.0 | **Do not apply** | `crawl4ai>=0.8.0` requires `lxml>=5.3,<6.dev0`. |
| `marshmallow` | 3.26.2 | 4.3.0 | **Do not apply** | `nemoguardrails`/`langchain-community` path requires `marshmallow>=3.3.0,<4.0.0`; marshmallow 4 also has documented migration changes. |
| `packaging` | 24.2 | 26.2 | **Do not apply** | `cognee` → `limits>=4.4.1,<5` requires `packaging>=21,<25` in the all-extras lock. |
| `pandas` | 2.3.3 | 3.0.2 | **Do not apply** | `nemoguardrails>=0.11.1` requires `pandas>=1.4.0,<3`; pandas 3 changes default string dtype and removes deprecated APIs. |
| `protobuf` | 6.33.6 | 7.34.1 | **Do not apply** | `opentelemetry-proto` requires `protobuf>=3.13,<7.0`; Phoenix/OTel traces depend on that path. |
| `rich` | 14.3.4 | 15.0.0 | **Do not apply yet** | First-party usage is low risk, but `cognee`/`instructor` require `rich>=13.7.0,<15.0.0` under `luum-cognitive-os[memory]`. |
| `setuptools` | 81.0.0 | 82.0.1 | **Hold** | Targeted `pkg_resources` scan passed and the audit allowlist no longer masks future `pkg_resources` imports. Current blocker is `torch==2.11.0` requiring `setuptools<82`; applying `setuptools>=82` would downgrade the optional semantic stack to `torch 2.10.0` and CUDA 12 packages. |
| `snowballstemmer` | 2.2.0 | 3.0.1 | **Do not apply** | `crawl4ai>=0.8.0` requires `snowballstemmer>=2.2,<3.dev0`; PyPI also shows the initial 3.0.0 was yanked. |
| `wrapt` | 1.17.3 | 2.1.2 | **Hold** | Re-tested on 2026-05-04: `wrapt>=2` is unsatisfiable with current `arize-phoenix>=14.6.0` / `openinference-instrumentation>=0.1.48`; forcing it downgrades/removes observability packages. |

## Follow-up order

1. Re-check `cognee`, `crawl4ai`, `nemoguardrails`, `mlflow-skinny`, and OpenTelemetry constraints before any global `--major` run.
2. `pkg_resources` scan is complete; revisit `setuptools>=82` only after deciding whether the unrelated `torch`/CUDA universal-lock churn is acceptable or isolating the semantic extra.
3. Revisit `wrapt>=2` only after OpenInference/Phoenix publish a wrapt-2-compatible instrumentation set.
4. Do not use `bash scripts/deps-update.sh --apply --major` as a blanket operation until this table has fewer blockers.


## Follow-up attempt — 2026-05-04

- Removed `pkg_resources` from `tests/audit/test_no_undefined_imports.py` third-party allowlist and reran the audit; no first-party import uses it.
- Tried `uv lock --upgrade-package 'setuptools>=82'`; the resolver can select `setuptools 82.0.1`, but the generated lock also downgrades `torch` and rewrites CUDA 13 package entries to CUDA 12 package names. That is unrelated to `setuptools` and too broad for this maintenance slice.
- Decision: the `pkg_resources` blocker is cleared, but the package remains retained pending a dedicated lock-strategy decision for the optional `semantic` extra.


Cross-reference: `docs/reports/python-major-followup-2026-05-04.md` contains the second-pass resolver evidence for all retained majors.


## Resolution update — ADR-145

ADR-145 split heavy optional stacks into explicit dependency lanes. The core maintainer lock no longer carries the optional blockers listed above. See `docs/reports/python-major-lane-resolution-2026-05-04.md` for the resolved core-lane outcome.
