"""Effect test: what the installer LEAVES on disk must equal the census.

`manifests/primitive-install-boundary.yaml` is the census of what the `default`
profile may project. `scripts/cos_init.py` copies rules from that census and
then applies the efficiency-profile filter, which DELETES every rule not in the
keep-set. When the keep-set was a hand-written constant, the two disagreed and
the installer silently deleted `model-routing.md` and `result-management.md`
after copying them — 15 rules installed where the census says 17, with no
warning.

This test runs the real installer into a temp directory and compares the files
on disk against the manifest. It deliberately does NOT read the installer's
internal constants: reading the intention cannot catch a filter that contradicts
it. Reverting the fix (`git show <pre-fix>:scripts/cos_init.py`) must make it
fail, naming the deleted rules.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = [pytest.mark.integration, pytest.mark.timeout(180)]

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
COS_INIT = REPO_ROOT / "scripts" / "cos_init.py"
BOUNDARY_MANIFEST = REPO_ROOT / "manifests" / "primitive-install-boundary.yaml"

RULE_DESTS = (
    Path(".claude") / "rules" / "cos",
    Path(".cognitive-os") / "rules" / "cos",
)


def _census_rule_files() -> set[str]:
    """Rule filenames the `default` profile is allowed to project, per the census."""
    manifest = yaml.safe_load(BOUNDARY_MANIFEST.read_text(encoding="utf-8"))
    entries = manifest["profiles"]["default"]["primitives"]["rules"]
    files = {Path(entry).name for entry in entries}
    assert files, "install-boundary manifest declares no rules for the default profile"
    return files


def _run_default_install(project: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["COS_REGISTRY_FILE"] = str(project.parent / "test-registry.json")
    return subprocess.run(
        [sys.executable, str(COS_INIT), "--default", "--harness", "claude"],
        cwd=project,
        capture_output=True,
        text=True,
        timeout=180,
        env=env,
    )


@pytest.fixture
def installed_project(tmp_path):
    project = tmp_path / "consumer"
    project.mkdir()
    subprocess.run(["git", "init"], cwd=project, capture_output=True, check=False)
    result = _run_default_install(project)
    assert result.returncode == 0, f"installer failed:\n{result.stdout}\n{result.stderr}"
    return project, result


@pytest.mark.parametrize("dest", RULE_DESTS, ids=lambda p: str(p))
def test_installed_rules_equal_the_census(installed_project, dest):
    """Rules surviving on disk == the census. Both directions, by name."""
    project, _ = installed_project
    rules_dir = project / dest
    assert rules_dir.is_dir(), f"{dest} was not created"

    on_disk = {path.name for path in rules_dir.glob("*.md")}
    census = _census_rule_files()

    deleted = sorted(census - on_disk)
    extra = sorted(on_disk - census)
    assert not deleted, (
        f"{dest}: the installer copied these rules from the census and then "
        f"deleted them — the consumer never sees them and gets no warning: {deleted}"
    )
    assert not extra, f"{dest}: rules installed outside the census: {extra}"


def test_reported_rule_count_matches_disk(installed_project):
    """The 'Rules: N installed' line must not overcount what survived the filter."""
    project, result = installed_project
    on_disk = len(list((project / RULE_DESTS[0]).glob("*.md")))
    expected = len(_census_rule_files())
    assert f"Rules:  {expected} installed" in result.stdout, (
        f"installer reported a different count than the census ({expected}); "
        f"stdout:\n{result.stdout}"
    )
    assert on_disk == expected


def test_help_rule_count_is_derived_not_hardcoded():
    """--help must state the census count, not a stale hand-written number."""
    result = subprocess.run(
        [sys.executable, str(COS_INIT), "--help"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr
    expected = len(_census_rule_files())
    assert f"{expected} core rules" in result.stdout, (
        f"--help does not report the census count ({expected}):\n{result.stdout}"
    )
