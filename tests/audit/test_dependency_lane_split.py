from __future__ import annotations

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


ROOT = Path(__file__).resolve().parents[2]
HEAVY_LANES = {
    "llm": {"litellm", "redis"},
    "observability": {"arize-phoenix", "arize-phoenix-otel", "mlflow-skinny"},
    "memory": {"cognee"},
    "guardrails": {"nemoguardrails"},
    "crawling": {"crawl4ai"},
    "jupyter": {"jupyter", "notebook"},
    "semantic": {"sentence-transformers", "numpy"},
}


def _pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text())


def test_heavy_optional_lanes_are_not_pyproject_extras() -> None:
    extras = _pyproject()["project"].get("optional-dependencies", {})

    for lane in HEAVY_LANES:
        assert lane not in extras, f"{lane} must live in requirements/dependency-lanes, not pyproject extras"

    dev = "\n".join(extras["dev"])
    for lane in HEAVY_LANES:
        assert lane not in dev, f"dev extra must not pull heavy optional lane {lane}"


def test_heavy_lanes_have_requirement_files() -> None:
    lane_dir = ROOT / "requirements" / "dependency-lanes"

    for lane, expected_packages in HEAVY_LANES.items():
        path = lane_dir / f"{lane}.txt"
        assert path.exists(), f"missing dependency lane file: {path}"
        text = path.read_text()
        for package in expected_packages:
            assert package in text, f"{path} must document/install {package}"


def test_core_lock_excludes_known_blocking_heavy_packages() -> None:
    lock_text = (ROOT / "uv.lock").read_text()
    blocked_packages = {
        "arize-phoenix",
        "cognee",
        "crawl4ai",
        "nemoguardrails",
        "sentence-transformers",
        "torch",
        "mlflow-skinny",
        "pandas",
        "snowballstemmer",
    }

    for package in blocked_packages:
        assert f'name = "{package}"' not in lock_text, f"{package} belongs to an explicit heavy lane"
