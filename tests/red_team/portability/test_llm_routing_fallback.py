# SCOPE: os-only
"""Portability proof for cos_lib/llm_routing_fallback.py.

Pins that the ADR-297 LLM routing tail-cleanup layer imports and its primary
entry point (``llm_route``) work from an arbitrary working directory, using
only ``COS_PROJECT_ROOT``-relative ``.cognitive-os/`` paths for its cache,
rate-limit state, and audit trail — never anything that assumes it is
running inside the Cognitive OS source repo itself.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "cos_lib/llm_routing_fallback.py"


def test_llm_routing_fallback_imports_from_arbitrary_project_root(tmp_path: Path, monkeypatch) -> None:
    """Falsification probe: library import must not depend on process cwd."""
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location("portability_llm_routing_fallback", ARTIFACT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)


def test_llm_route_works_in_arbitrary_consumer_project(tmp_path: Path) -> None:
    """Falsification probe: exercise the real ``llm_route`` entry point with a
    fake dispatch function, in a subprocess run from an arbitrary cwd with
    ``COS_PROJECT_ROOT`` pointed at a throwaway project dir (standing in for a
    consumer project that merely installed the OS — not the Cognitive OS
    source repo). Confirms the cache/audit/state files land only under the
    consumer project's own ``.cognitive-os/`` tree.
    """
    project_dir = tmp_path / "consumer-project"
    project_dir.mkdir()
    consumer_cwd = tmp_path / "somewhere-else"
    consumer_cwd.mkdir()

    script = (
        "import sys; sys.path.insert(0, %r)\n"
        "from cos_lib.llm_routing_fallback import LLMCandidate, llm_route\n"
        "\n"
        "class FakeResult:\n"
        "    success = True\n"
        "    text = 'skill-b'\n"
        "    provider_used = 'fake-provider'\n"
        "    latency_ms = 5\n"
        "\n"
        "def fake_dispatch(**kwargs):\n"
        "    return FakeResult()\n"
        "\n"
        "candidates = [\n"
        "    LLMCandidate('skill-a', 'skill-a', 0.40, 'does a'),\n"
        "    LLMCandidate('skill-b', 'skill-b', 0.38, 'does b'),\n"
        "    LLMCandidate('skill-c', 'skill-c', 0.35, 'does c'),\n"
        "]\n"
        "result = llm_route('do the thing', candidates, dispatch_fn=fake_dispatch)\n"
        "print(result.invoke_command)\n"
        "print(result.provider)\n"
        "print(result.cache_hit)\n"
    ) % (str(REPO_ROOT),)

    env = {"PATH": "/usr/bin:/bin", "COS_PROJECT_ROOT": str(project_dir)}
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=consumer_cwd,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    lines = result.stdout.strip().splitlines()
    assert lines[0] == "skill-b"
    assert lines[1] == "fake-provider"
    assert lines[2] == "False"

    # Cache + metrics + rate-limit state land only under the consumer
    # project's own .cognitive-os/ tree, relative to COS_PROJECT_ROOT.
    assert (project_dir / ".cognitive-os" / "cache" / "llm-routing").is_dir()
    assert (project_dir / ".cognitive-os" / "metrics" / "llm-routing.jsonl").is_file()
    assert not (tmp_path / ".cognitive-os").exists()
    assert not (consumer_cwd / ".cognitive-os").exists()
