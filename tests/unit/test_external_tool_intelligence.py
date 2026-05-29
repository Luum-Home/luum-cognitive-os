from __future__ import annotations

from pathlib import Path

from lib.external_tool_intelligence import (
    audit_adoption,
    direct_dependencies,
    inventory,
    render_radar,
    research_check,
)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_inventory_reads_dependency_manifests(tmp_path: Path) -> None:
    write(tmp_path / "requirements.txt", "fastmcp>=1\n# comment\n")
    write(tmp_path / "pyproject.toml", '[project]\ndependencies = ["pyyaml>=6"]\n')
    write(tmp_path / "go.mod", "module example\n\nrequire (\n\tgithub.com/BurntSushi/toml v1.4.0\n\tgolang.org/x/sys v0.1.0 // indirect\n)\n")

    deps = direct_dependencies(tmp_path)

    assert deps["requirements.txt"] == ["fastmcp"]
    assert deps["pyproject.toml"] == ["pyyaml"]
    assert deps["go.mod"] == ["github.com/burntsushi/toml"]

    payload = inventory(tmp_path, include_docs=False)
    ids = {item["id"] for item in payload["items"]}
    assert {"fastmcp", "pyyaml", "github.com/burntsushi/toml"}.issubset(ids)




def test_pyproject_self_extras_are_not_external_tools(tmp_path: Path) -> None:
    write(
        tmp_path / "pyproject.toml",
        '[project]\nname = "demo-os"\ndependencies = ["pyyaml>=6"]\n[project.optional-dependencies]\ndev = ["demo-os[testing]", "pytest>=8"]\n',
    )

    deps = direct_dependencies(tmp_path)

    assert "demo-os" not in deps["pyproject.toml"]
    assert deps["pyproject.toml"] == ["pytest", "pyyaml"]



def test_pyproject_parser_fallback_reads_multiline_arrays(monkeypatch, tmp_path: Path) -> None:
    import lib.compat_tomllib as compat_tomllib

    monkeypatch.setattr(compat_tomllib, "_tomllib", None)
    write(
        tmp_path / "pyproject.toml",
        """[project]
name = "demo"
dependencies = [
  "pyyaml>=6",
  # comment inside array
  "jinja2>=3",
]
[project.optional-dependencies]
testing = [
  "pytest>=8",
  "demo[dev]",
]
""",
    )

    deps = direct_dependencies(tmp_path)

    assert deps["pyproject.toml"] == ["jinja2", "pytest", "pyyaml"]

def test_audit_detects_remove_dependency_and_overlay_contradiction(tmp_path: Path) -> None:
    write(tmp_path / "requirements.txt", "litellm>=1\nsemgrep>=1\n")
    manifest = tmp_path / "manifests" / "external-tools-adoption.yaml"
    write(
        manifest,
        """
schema_version: external-tools-adoption/v1
tools:
  - id: litellm
    verdict: REMOVE
    package_names: [litellm]
    evidence: {consumers: [], tests: []}
  - id: semgrep
    verdict: DEFER
    package_names: [semgrep]
    evidence: {consumers: [], tests: []}
""",
    )
    overlay = tmp_path / ".cognitive-os" / "external-tools-overlay.yaml"
    write(
        overlay,
        """
schema_version: cos-project-tool-overlay/v1
local_tools:
  - id: semgrep
    source: os-radar
    local_status: enabled
    reason: local CI
waivers: []
""",
    )

    report = audit_adoption(tmp_path, manifest, overlay)
    codes = {finding["code"] for finding in report["findings"]}

    assert report["status"] == "block"
    assert "removed-tool-still-used" in codes
    assert "overlay-contradiction-without-waiver" in codes


def test_adopt_requires_consumer_proof(tmp_path: Path) -> None:
    write(tmp_path / "requirements.txt", "ragas>=1\n")
    manifest = tmp_path / "manifest.yaml"
    write(
        manifest,
        """
schema_version: external-tools-adoption/v1
tools:
  - id: ragas
    verdict: ADOPT
    package_names: [ragas]
    evidence: {consumers: [], tests: []}
""",
    )

    report = audit_adoption(tmp_path, manifest)

    assert any(f["code"] == "adopt-without-consumer-proof" for f in report["findings"])


def test_render_combines_os_manifest_and_project_overlay(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.yaml"
    overlay = tmp_path / "overlay.yaml"
    write(
        manifest,
        """
schema_version: external-tools-adoption/v1
tools:
  - id: fastmcp
    domain: mcp
    verdict: INTEGRATE
    package_names: [fastmcp]
""",
    )
    write(
        overlay,
        """
schema_version: cos-project-tool-overlay/v1
local_tools:
  - id: fastmcp
    source: os-radar
    local_status: enabled
    reason: local MCP smoke
""",
    )

    payload = render_radar(manifest, overlay, mode="combined")

    assert payload["effective_project_view"][0]["cos_verdict"] == "INTEGRATE"


def test_research_check_requires_license_footprint_sources_tests_and_rollback(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate.yaml"
    write(candidate, "id: candidate-tool\nlicense: MIT\n")

    report = research_check(candidate)
    fields = {finding["details"].get("field") for finding in report["findings"] if finding["code"] == "research-packet-missing-field"}

    assert report["status"] == "block"
    assert {"footprint", "adoption_kind", "source_links", "test_plan", "rollback_path"}.issubset(fields)
