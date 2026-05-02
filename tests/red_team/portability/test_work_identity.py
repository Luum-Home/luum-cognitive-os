# SCOPE: both
"""Portability proofs for packages/agent-coordination/lib/work_identity.py.

These tests run work_identity functions against a temporary, standalone
git repository to prove the module has no dependency on luum-agent-os
runtime state (no SO-specific env vars, no .cognitive-os config, no
project-local files beyond what the module itself creates).

Three proofs:
  1. compute_fingerprint is deterministic in a clean environment with no
     PYTHONPATH tricks or SO runtime files present.
  2. find_existing_work returns None gracefully in a repo with no
     active-claims file and no matching commit (transparent no-op).
  3. embed + parse roundtrip works in an isolated subprocess that only
     imports work_identity — no other COS modules needed.
"""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_LIB = REPO_ROOT / "packages" / "agent-coordination" / "lib"

# Environment variables that tie a process to the SO runtime
_SO_VARS = (
    "CI",
    "PYTEST_CURRENT_TEST",
    "COGNITIVE_OS_SESSION_ID",
    "COGNITIVE_OS_PROJECT_DIR",
    "CODEX_PROJECT_DIR",
    "CLAUDE_PROJECT_DIR",
    "ORCHESTRATOR_MODE",
    "COS_ALLOW_DIRECT_MAIN",
)


def _clean_env(project_dir: Path) -> dict[str, str]:
    """Return an environment dict scrubbed of SO-specific variables."""
    env = os.environ.copy()
    for var in _SO_VARS:
        env.pop(var, None)
    # Point PYTHONPATH ONLY at the package lib — no full SO lib injection
    env["PYTHONPATH"] = str(PACKAGE_LIB)
    env["HOME"] = str(project_dir)  # Prevent ~/.gitconfig from leaking
    return env


def _init_minimal_git_repo(path: Path) -> Path:
    """Create a minimal git repo with one commit at *path*."""
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main", str(path)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.com"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "TestUser"], check=True, capture_output=True)
    seed = path / "seed.txt"
    seed.write_text("seed\n")
    subprocess.run(["git", "-C", str(path), "add", "seed.txt"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(path), "commit", "-m", "initial"],
        check=True,
        capture_output=True,
        env={
            "GIT_AUTHOR_NAME": "TestUser",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "TestUser",
            "GIT_COMMITTER_EMAIL": "test@example.com",
            "HOME": str(path.parent),
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        },
    )
    return path


# ---------------------------------------------------------------------------
# Proof 1 — compute_fingerprint is deterministic in isolation
# ---------------------------------------------------------------------------


def test_portability_compute_determinism_isolated(tmp_path: Path):
    """compute_fingerprint produces stable output in a clean subprocess.

    Runs two separate Python invocations in a temp dir with no SO env vars
    and confirms they produce the same fingerprint.
    """
    script = textwrap.dedent("""\
        from work_identity import compute_fingerprint
        import sys
        fp = compute_fingerprint("implement rate limiter", ["lib/rate_limiter.py"])
        print(fp)
    """)

    env = _clean_env(tmp_path)

    r1 = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, env=env, cwd=str(tmp_path),
    )
    r2 = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, env=env, cwd=str(tmp_path),
    )

    assert r1.returncode == 0, f"First run failed: {r1.stderr}"
    assert r2.returncode == 0, f"Second run failed: {r2.stderr}"

    fp1 = r1.stdout.strip()
    fp2 = r2.stdout.strip()
    assert fp1 == fp2, f"Fingerprints diverged: {fp1!r} vs {fp2!r}"
    assert len(fp1) == 16
    assert fp1.isalnum()


# ---------------------------------------------------------------------------
# Proof 2 — find_existing_work is transparent in a clean repo (no match)
# ---------------------------------------------------------------------------


def test_portability_find_transparent_in_clean_repo(tmp_path: Path):
    """find_existing_work exits cleanly and returns None in a plain git repo.

    The repo has no .cognitive-os dir, no active-claims.json, and no commit
    carrying a work-fingerprint trailer.  Result must be None (not an error).
    """
    repo = _init_minimal_git_repo(tmp_path / "repo")
    env = _clean_env(tmp_path)

    script = textwrap.dedent(f"""\
        import json, sys
        from pathlib import Path
        from work_identity import find_existing_work
        result = find_existing_work("deadbeefdeadbeef", Path({str(repo)!r}))
        print("null" if result is None else json.dumps(result))
    """)

    r = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, env=env, cwd=str(tmp_path),
    )

    assert r.returncode == 0, f"find_existing_work raised in clean repo: {r.stderr}"
    assert r.stdout.strip() == "null", f"Expected null, got: {r.stdout.strip()!r}"


# ---------------------------------------------------------------------------
# Proof 3 — embed + parse roundtrip works with only work_identity imported
# ---------------------------------------------------------------------------


def test_portability_embed_parse_roundtrip_isolated(tmp_path: Path):
    """embed_in_commit_msg + parse_fingerprint_from_msg roundtrip in isolation.

    A subprocess with only work_identity on sys.path computes a fingerprint,
    embeds it in a commit message, then parses it back.  No other COS modules
    are imported; this proves the primitive is self-contained.
    """
    env = _clean_env(tmp_path)

    script = textwrap.dedent("""\
        import sys
        from work_identity import (
            compute_fingerprint,
            embed_in_commit_msg,
            parse_fingerprint_from_msg,
        )
        fp = compute_fingerprint("self-contained test", ["lib/alpha.py", "lib/beta.py"])
        msg = "feat: self-contained test\\n\\nBody paragraph."
        with_trailer = embed_in_commit_msg(msg, fp)
        parsed = parse_fingerprint_from_msg(with_trailer)
        if parsed != fp:
            print(f"MISMATCH: embedded={fp!r} parsed={parsed!r}", file=sys.stderr)
            sys.exit(1)
        print(fp)
    """)

    r = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, env=env, cwd=str(tmp_path),
    )

    assert r.returncode == 0, f"Roundtrip failed in isolation: {r.stderr}"
    fp = r.stdout.strip()
    assert len(fp) == 16
    assert fp.isalnum()
