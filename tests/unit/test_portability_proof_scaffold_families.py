"""The scaffold must never emit a proof that cannot pass, or one that cannot fail.

Regression under test (2026-08-18): the single default template emitted
``[str(ARTIFACT), "--help"]`` for every non-``.py`` artifact, so scaffolding a
Markdown rule produced a test that tried to *execute* the Markdown and died with
``PermissionError`` -- paired with a ``test_..._artifact_exists`` that could
never fail. These tests run the real generator and then run what it generated.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "cos-portability-proof-scaffold"
PORTABILITY = "tests/red_team/portability"


def _load_module():
    loader = importlib.machinery.SourceFileLoader("cos_portability_proof_scaffold", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    spec.loader.exec_module(module)
    return module


def _fixture_repo(tmp_path: Path) -> Path:
    """A throwaway repo root laid out like this one, minus everything else."""
    root = tmp_path / "fixture-repo"
    (root / "scripts").mkdir(parents=True)
    (root / PORTABILITY).mkdir(parents=True)
    # The doc/data branches reuse the OS's own absolute-path detector, which
    # side-loads the classifier next to it.
    for name in ("primitive_scope_health.py", "primitive_scope_classifier.py"):
        (root / "scripts" / name).write_text(
            (REPO / "scripts" / name).read_text(encoding="utf-8"), encoding="utf-8"
        )
    return root


def _write(root: Path, rel: str, body: str, mode: int = 0o755) -> None:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    target.chmod(mode)


def _run_generated(proof: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-m", "pytest", str(proof), "-q", "-p", "no:cacheprovider", "--no-header"],
        cwd=str(proof.parent),
        text=True,
        capture_output=True,
        timeout=180,
        check=False,
        env=env,
    )


ARGPARSE_SCRIPT = """#!/usr/bin/env python3
import argparse
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="fixture audit")
    parser.add_argument("--strict", action="store_true")
    parser.parse_args()
    print("fixture audit over", REPO.name)
    return 0


raise SystemExit(main())
"""

# No argparse: `--help` runs the whole audit and exits 1, exactly like the
# shipped scripts the hand-written proofs had to work around.
NO_ARGPARSE_SCRIPT = """#!/usr/bin/env python3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
print("audit of", REPO.name, "argv=", sys.argv[1:])
raise SystemExit(1)
"""

SHELL_SCRIPT = """#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "shell audit over $(basename "$REPO")"
"""

RULE_WITH_FRONTMATTER = """<!-- SCOPE: both -->
---
rule: fixture-rule
scope: both
status: active
---

# Fixture rule

Run `scripts/fixture-audit.sh` to check the contract.
"""

PROSE_ONLY_DOC = """# Fixture notes

Some prose. No frontmatter, no gate script, nothing a machine can check.
"""


def test_argparse_python_gets_a_help_proof_that_runs_and_passes(tmp_path: Path) -> None:
    mod = _load_module()
    root = _fixture_repo(tmp_path)
    _write(root, "scripts/fixture-cli.py", ARGPARSE_SCRIPT)

    proof = mod.scaffold(root, "scripts/fixture-cli.py")

    text = proof.read_text(encoding="utf-8")
    assert "test_help_succeeds_from_arbitrary_project_root" in text
    result = _run_generated(proof)
    assert result.returncode == 0, result.stdout + result.stderr


def test_script_without_argparse_is_not_given_a_help_zero_assertion(tmp_path: Path) -> None:
    """`--help -> 0` on an argparse-less audit asserts a non-event."""
    mod = _load_module()
    root = _fixture_repo(tmp_path)
    _write(root, "scripts/fixture-audit.py", NO_ARGPARSE_SCRIPT)

    proof = mod.scaffold(root, "scripts/fixture-audit.py")

    text = proof.read_text(encoding="utf-8")
    assert "test_help_succeeds_from_arbitrary_project_root" not in text
    assert '"--help"' not in text
    result = _run_generated(proof)
    assert result.returncode == 0, result.stdout + result.stderr


def test_executable_shell_gets_a_proof_that_runs_and_passes(tmp_path: Path) -> None:
    mod = _load_module()
    root = _fixture_repo(tmp_path)
    _write(root, "scripts/fixture-audit.sh", SHELL_SCRIPT)

    proof = mod.scaffold(root, "scripts/fixture-audit.sh")

    result = _run_generated(proof)
    assert result.returncode == 0, result.stdout + result.stderr


def test_mode_644_shell_is_covered_because_the_proof_names_the_interpreter(tmp_path: Path) -> None:
    """A 644 script exec'd directly returns 126; the proof must invoke ``bash``."""
    mod = _load_module()
    root = _fixture_repo(tmp_path)
    _write(root, "scripts/fixture-bench.sh", SHELL_SCRIPT, mode=0o644)

    # A shell reports the exec refusal as 126; Python's own exec raises instead.
    direct = subprocess.run(
        ["/bin/sh", "-c", shlex.quote(str(root / "scripts/fixture-bench.sh"))],
        capture_output=True,
        text=True,
        check=False,
    )
    assert direct.returncode == 126, "fixture is not actually mode-644-blocked"
    with pytest.raises(PermissionError):
        subprocess.run([str(root / "scripts/fixture-bench.sh")], capture_output=True, check=False)

    proof = mod.scaffold(root, "scripts/fixture-bench.sh")

    assert '["bash", str(ARTIFACT)]' in proof.read_text(encoding="utf-8")
    result = _run_generated(proof)
    assert result.returncode == 0, result.stdout + result.stderr


def test_markdown_gets_a_real_proof_not_an_attempt_to_execute_it(tmp_path: Path) -> None:
    mod = _load_module()
    root = _fixture_repo(tmp_path)
    _write(root, "rules/fixture-rule.md", RULE_WITH_FRONTMATTER, mode=0o644)
    _write(root, "scripts/fixture-audit.sh", SHELL_SCRIPT)

    proof = mod.scaffold(root, "rules/fixture-rule.md")

    text = proof.read_text(encoding="utf-8")
    assert "str(ARTIFACT)] + [\"--help\"]" not in text
    assert "fixture-rule.md" in text
    assert "test_frontmatter_parses_from_arbitrary_project_root" in text
    result = _run_generated(proof)
    assert result.returncode == 0, result.stdout + result.stderr


def test_markdown_without_any_machine_checkable_claim_is_refused(tmp_path: Path) -> None:
    """The cheap green here is a file-exists test. Refusal is the right output."""
    mod = _load_module()
    root = _fixture_repo(tmp_path)
    _write(root, "docs/fixture-notes.md", PROSE_ONLY_DOC, mode=0o644)

    with pytest.raises(mod.Unprovable) as excinfo:
        mod.scaffold(root, "docs/fixture-notes.md")

    assert "frontmatter" in excinfo.value.reason
    assert excinfo.value.hint
    assert not (root / PORTABILITY / "test_fixture-notes.py").exists()


def test_refusal_reaches_the_cli_as_a_distinct_exit_code(tmp_path: Path) -> None:
    mod = _load_module()
    root = _fixture_repo(tmp_path)
    _write(root, "docs/fixture-notes.md", PROSE_ONLY_DOC, mode=0o644)

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(root), "--artifact", "docs/fixture-notes.md"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == mod.REFUSAL_EXIT
    assert "REFUSING" in result.stderr
    assert "false green" in result.stderr


def test_generated_proofs_carry_no_existence_only_test(tmp_path: Path) -> None:
    """`assert ARTIFACT.exists()` as a standalone test can never fail. Banned."""
    mod = _load_module()
    root = _fixture_repo(tmp_path)
    _write(root, "scripts/fixture-cli.py", ARGPARSE_SCRIPT)
    _write(root, "scripts/fixture-audit.sh", SHELL_SCRIPT)
    _write(root, "rules/fixture-rule.md", RULE_WITH_FRONTMATTER, mode=0o644)

    for rel in ("scripts/fixture-cli.py", "scripts/fixture-audit.sh", "rules/fixture-rule.md"):
        text = mod.build_template(root, rel)
        assert "_artifact_exists" not in text, rel
        assert "assert ARTIFACT.exists()" not in text, rel


def test_no_probe_refuses_instead_of_guessing_an_executable_template(tmp_path: Path) -> None:
    mod = _load_module()
    root = _fixture_repo(tmp_path)
    _write(root, "scripts/fixture-cli.py", ARGPARSE_SCRIPT)

    with pytest.raises(mod.Unprovable) as excinfo:
        mod.build_template(root, "scripts/fixture-cli.py", probe=False)
    assert "measurements, not greps" in excinfo.value.hint


def test_unterminating_artifact_is_refused_with_a_streaming_hint(tmp_path: Path) -> None:
    """scripts/hook-io-overhead-bench.sh is the real instance of this family."""
    mod = _load_module()
    root = _fixture_repo(tmp_path)
    _write(root, "scripts/fixture-bench.sh", "#!/usr/bin/env bash\necho PART A\nsleep 30\n")

    with pytest.raises(mod.Unprovable) as excinfo:
        mod.build_template(root, "scripts/fixture-bench.sh", timeout=2)
    assert "did not terminate" in excinfo.value.reason
    assert "streaming proof" in excinfo.value.hint
