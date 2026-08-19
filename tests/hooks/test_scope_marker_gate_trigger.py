# SCOPE: os-only
"""Behavioural mutation test for hooks/scope-marker-portability-gate.sh.

Every case runs the real hook with a real PreToolUse payload against a real git
repository and asserts on the exit code. Nothing here greps the hook source: a
gate whose regex mentions `os-only` is not a gate that *stops* an unproven
`os-only` primitive.

Four directions must hold at once:
  1. a primitive that declares any scope and lacks its paired proof is blocked
     (the class the `both`-only trigger could never see);
  2. a *new* primitive that declares no scope at all is blocked (the offender of
     2026-08-18 carried `declared_scope: null`);
  3. what already blocked keeps blocking, and a primitive with its proof keeps
     passing -- including a proof declared only in the behavior-evidence
     manifest, which the hook's own candidate list cannot see;
  4. paths outside the primitive registry, and pre-existing primitives that were
     merely modified, are untouched.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK_REL = "hooks/scope-marker-portability-gate.sh"
PAYLOAD = json.dumps({"tool_name": "Bash", "tool_input": {"command": "git commit -m wip"}})


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "hooks" / "_lib").mkdir(parents=True)
    (repo / "tests" / "red_team" / "portability").mkdir(parents=True)
    (repo / "cos_lib").mkdir()
    (repo / "manifests").mkdir()
    shutil.copy(REPO_ROOT / HOOK_REL, repo / HOOK_REL)
    for lib in ("common.sh", "git-command-parse.sh"):
        shutil.copy(REPO_ROOT / "hooks" / "_lib" / lib, repo / "hooks" / "_lib" / lib)
    for mod in ("__init__.py", "portability_proof_paths.py"):
        shutil.copy(REPO_ROOT / "cos_lib" / mod, repo / "cos_lib" / mod)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    return repo


def run_hook(repo: Path, **env_extra: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["COGNITIVE_OS_PROJECT_DIR"] = str(repo)
    env.pop("COS_ALLOW_UNPROVEN_SCOPE_BOTH", None)
    env.update(env_extra)
    # /bin/bash is 3.2 on macOS; the gate must parse and run there, not only
    # under whichever bash the PATH happens to expose.
    return subprocess.run(
        ["/bin/bash", str(repo / HOOK_REL)],
        input=PAYLOAD,
        text=True,
        capture_output=True,
        env=env,
        cwd=str(repo),
    )


def write(repo: Path, rel: str, text: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def commit_baseline(repo: Path, rel: str, text: str) -> None:
    """Land a file in history so a later edit is a modification, not an addition."""
    write(repo, rel, text)
    _git(repo, "add", rel)
    _git(repo, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "baseline")


HOOK_BODY = "#!/usr/bin/env bash\n# SCOPE: {scope}\necho hi\n"
NO_MARKER_BODY = "#!/usr/bin/env python3\n\"\"\"Docstring, no scope marker.\"\"\"\nprint(1)\n"
PROOF_BODY = "#!/usr/bin/env python3\n# SCOPE: os-only\ndef test_probe():\n    assert True\n"


# 1. The class the `both`-only trigger could never see.
@pytest.mark.parametrize("scope", ["os-only", "project", "both"])
def test_blocks_unproven_primitive_for_every_declared_scope(repo: Path, scope: str) -> None:
    write(repo, "scripts/measure_something.py", HOOK_BODY.format(scope=scope))
    _git(repo, "add", "scripts/measure_something.py")
    result = run_hook(repo)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "measure_something.py" in result.stderr


# 2. The offender of 2026-08-18: no scope marker at all.
def test_blocks_new_primitive_without_any_scope_marker(repo: Path) -> None:
    write(repo, "scripts/measure_skill_router_cost.py", NO_MARKER_BODY)
    _git(repo, "add", "scripts/measure_skill_router_cost.py")
    result = run_hook(repo)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "no SCOPE marker" in result.stderr


# 3a. A primitive with its paired proof still passes.
def test_allows_primitive_with_paired_proof(repo: Path) -> None:
    write(repo, "hooks/example-hook.sh", HOOK_BODY.format(scope="both"))
    write(repo, "tests/red_team/portability/test_example-hook.py", PROOF_BODY)
    _git(repo, "add", "hooks/example-hook.sh", "tests/red_team/portability/test_example-hook.py")
    result = run_hook(repo)
    assert result.returncode == 0, result.stdout + result.stderr


# 3b. A proof declared only in the behavior-evidence manifest also passes.
# Without this the expanded trigger would block 715 already-proven primitives.
def test_allows_primitive_proven_only_via_behavior_evidence_manifest(repo: Path) -> None:
    write(repo, "hooks/family-member.sh", HOOK_BODY.format(scope="both"))
    write(repo, "tests/red_team/portability/test_some_family.py", PROOF_BODY)
    write(
        repo,
        "manifests/primitive-behavior-evidence.yaml",
        "schema_version: primitive-behavior-evidence.v1\n"
        "evidence:\n"
        "- primitive: hooks/family-member.sh\n"
        "  tests:\n"
        "  - tests/red_team/portability/test_some_family.py\n",
    )
    _git(repo, "add", "hooks/family-member.sh")
    result = run_hook(repo)
    assert result.returncode == 0, result.stdout + result.stderr


# 3c. The bypass still waves an emergency commit through.
def test_bypass_allows_unproven_primitive(repo: Path) -> None:
    write(repo, "scripts/unproven.py", HOOK_BODY.format(scope="os-only"))
    _git(repo, "add", "scripts/unproven.py")
    result = run_hook(repo, COS_ALLOW_UNPROVEN_SCOPE_BOTH="1")
    assert result.returncode == 0, result.stdout + result.stderr


# 4a. A pre-existing markerless primitive that is merely edited is not blocked.
def test_allows_modified_pre_existing_primitive_without_marker(repo: Path) -> None:
    commit_baseline(repo, "scripts/legacy_tool.py", NO_MARKER_BODY)
    write(repo, "scripts/legacy_tool.py", NO_MARKER_BODY + "print(2)\n")
    _git(repo, "add", "scripts/legacy_tool.py")
    result = run_hook(repo)
    assert result.returncode == 0, result.stdout + result.stderr


# 4b. Paths outside the primitive registry keep their old freedom, marker or not.
@pytest.mark.parametrize(
    "rel",
    ["cos_lib/helper.py", "docs/06-Daily/reports/note.md", "packages/foo/lib/thing.py"],
)
def test_allows_non_registry_paths_with_scope_marker(repo: Path, rel: str) -> None:
    write(repo, rel, HOOK_BODY.format(scope="os-only"))
    _git(repo, "add", rel)
    result = run_hook(repo)
    assert result.returncode == 0, result.stdout + result.stderr


# 4c. A commit that stages nothing relevant is untouched.
def test_allows_commit_without_primitives(repo: Path) -> None:
    write(repo, "README.md", "# hi\n")
    _git(repo, "add", "README.md")
    result = run_hook(repo)
    assert result.returncode == 0, result.stdout + result.stderr
