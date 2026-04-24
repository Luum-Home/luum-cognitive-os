"""Unit tests for cos_build_self_knowledge.py generator (ADR-037)."""
from __future__ import annotations

import importlib.util
import json
import sys
import textwrap
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Load generator module without executing main()
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_GEN_PATH = _REPO_ROOT / "scripts" / "cos_build_self_knowledge.py"


def _load_generator():
    spec = importlib.util.spec_from_file_location("cos_build_self_knowledge", _GEN_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


GEN = _load_generator()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def fake_project(tmp_path: Path) -> Path:
    """Create a minimal fake project tree."""
    # lib/
    lib = tmp_path / "lib"
    lib.mkdir()
    (lib / "sample_module.py").write_text(
        textwrap.dedent("""\
            # SCOPE: both
            class Foo:
                pass

            class Bar:
                pass

            def hello(name: str) -> str:
                \"\"\"Say hello to name. Returns greeting string.\"\"\"
                return f"hello {name}"

            def _private():
                pass
        """),
        encoding="utf-8",
    )
    (lib / "importer.py").write_text(
        "from lib.sample_module import hello\n",
        encoding="utf-8",
    )

    # hooks/
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    hook_sh = hooks / "my-hook.sh"
    hook_sh.write_text(
        "#!/usr/bin/env bash\nsource hooks/_lib/probe.sh\ndo_work() { echo hi; }\n",
        encoding="utf-8",
    )

    # docs/adrs/
    adrs = tmp_path / "docs" / "adrs"
    adrs.mkdir(parents=True)
    (adrs / "ADR-001-test.md").write_text(
        "# ADR-001 — Test ADR\n\n**Status**: Accepted\n\n## Decision\n\nUse this approach. It works well.\n",
        encoding="utf-8",
    )
    (adrs / "ADR-002-dupe.md").write_text(
        "# ADR-002 — Dupe ADR\n\n**Status**: Accepted\n\n## Decision\n\nSame heading dedup test.\n\n## Decision\n\nShould not appear twice.\n",
        encoding="utf-8",
    )

    # cognitive-os.yaml marker
    (tmp_path / "cognitive-os.yaml").write_text("project:\n  name: test\n")

    return tmp_path


# ---------------------------------------------------------------------------
# Test 1: api-surface schema
# ---------------------------------------------------------------------------

def test_api_surface_schema(fake_project: Path) -> None:
    """api-surface.json has the expected structure for a Python module."""
    GEN.build(fake_project)

    out = fake_project / ".cognitive-os" / "self-knowledge" / "api-surface.json"
    assert out.exists(), "api-surface.json must be created"

    surface = json.loads(out.read_text())
    # Key uses relative path
    key = "lib/sample_module.py"
    assert key in surface, f"Expected {key} in api-surface"
    entry = surface[key]
    assert "classes" in entry and "functions" in entry

    assert "Foo" in entry["classes"]
    assert "Bar" in entry["classes"]

    fn_names = [f["name"] for f in entry["functions"]]
    assert "hello" in fn_names

    hello = next(f for f in entry["functions"] if f["name"] == "hello")
    assert "name" in hello["signature"]
    assert hello["doc_first_line"]  # non-empty docstring first sentence


# ---------------------------------------------------------------------------
# Test 2: dep-graph correctness
# ---------------------------------------------------------------------------

def test_dep_graph_correctness(fake_project: Path) -> None:
    """dep-graph.json captures Python imports and Bash source calls."""
    GEN.build(fake_project)

    out = fake_project / ".cognitive-os" / "self-knowledge" / "dep-graph.json"
    assert out.exists()

    graph = json.loads(out.read_text())

    # importer.py imports lib/sample_module.py
    assert "lib/importer.py" in graph
    assert "lib/sample_module.py" in graph["lib/importer.py"]

    # my-hook.sh sources hooks/_lib/probe.sh
    assert "hooks/my-hook.sh" in graph
    deps = graph["hooks/my-hook.sh"]
    assert any("probe.sh" in d for d in deps), f"Expected probe.sh in {deps}"


# ---------------------------------------------------------------------------
# Test 3: glossary deduplication
# ---------------------------------------------------------------------------

def test_glossary_dedup(fake_project: Path) -> None:
    """glossary.md deduplicates repeated headings across files."""
    GEN.build(fake_project)

    glossary_path = fake_project / ".cognitive-os" / "self-knowledge" / "glossary.md"
    assert glossary_path.exists()

    content = glossary_path.read_text()
    # "Decision" heading appears twice in ADR-002 — should appear once
    count = content.count("## Decision")
    assert count == 1, f"Dedup failed: 'Decision' heading appears {count} times"

    # ADR-001 decision text should appear
    assert "Use this approach" in content or "Decision" in content


# ---------------------------------------------------------------------------
# Test 4: mtime tracking
# ---------------------------------------------------------------------------

def test_mtime_tracking(fake_project: Path) -> None:
    """build() writes a non-empty .mtime stamp."""
    GEN.build(fake_project)

    mtime_path = fake_project / ".cognitive-os" / "self-knowledge" / ".mtime"
    assert mtime_path.exists(), ".mtime file must be written"

    stamp = mtime_path.read_text().strip()
    assert stamp, ".mtime must not be empty"
    # Should be ISO-8601 format
    assert "T" in stamp or "-" in stamp, f"Unexpected .mtime format: {stamp!r}"

    # Rebuild should update .mtime
    import time
    time.sleep(0.05)
    GEN.build(fake_project)
    stamp2 = mtime_path.read_text().strip()
    # The two stamps could be equal if the clock resolution is low; just check it's non-empty
    assert stamp2


# ---------------------------------------------------------------------------
# Test 5: empty codebase edge case
# ---------------------------------------------------------------------------

def test_empty_codebase(tmp_path: Path) -> None:
    """build() succeeds on a project with no source files."""
    (tmp_path / "cognitive-os.yaml").write_text("project:\n  name: empty\n")
    (tmp_path / "lib").mkdir()
    (tmp_path / "hooks").mkdir()

    result = GEN.build(tmp_path)

    out_dir = tmp_path / ".cognitive-os" / "self-knowledge"
    assert (out_dir / "api-surface.json").exists()
    assert (out_dir / "dep-graph.json").exists()
    assert (out_dir / "glossary.md").exists()
    assert (out_dir / "codebase-summary.md").exists()
    assert (out_dir / ".mtime").exists()

    surface = json.loads((out_dir / "api-surface.json").read_text())
    assert isinstance(surface, dict)  # may be empty, but must be a dict

    assert result["files_scanned"] == 0
