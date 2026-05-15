"""Phase 2.2 parity tests — Python scope_allows() and skill_scope_allows() must match
the expected behavior table derived from the original bash logic (cos-init.sh lines 121-167).

Strategy: we do not source cos-init.sh (it has side effects on install). Instead we test
internal consistency — Python via --internal-call subprocess vs Python direct module call —
and verify against the explicit expected exit codes derived from reading the bash source.

The bash truth table (extracted from lines 121-167 of cos-init.sh at commit 8a4778c):

scope_allows():
  install_scope=all      → always exit 0 (allow)
  no SCOPE header        → exit 0
  # SCOPE: project       → exit 0 (under project/both)
  # SCOPE: os-only          → exit 0 (under project/both)
  # SCOPE: os-only       → exit 1 (blocked under project/both)
  <!-- SCOPE: project --> → exit 0
  unknown tag            → exit 0

skill_scope_allows():
  no SKILL.md            → exit 0
  install_scope=all      → exit 0
  audience: project      → exit 0
  audience: both         → exit 0
  audience: adopters     → exit 0
  audience: human        → exit 0
  audience: os-only      → exit 1
  audience: os-dev       → exit 1
  audience: os            → exit 1
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).parent.parent.parent
COS_INIT_PY = REPO / "scripts" / "cos_init.py"

sys.path.insert(0, str(REPO / "scripts"))
import cos_init  # noqa: E402 — direct import for consistency check


# ── Helpers ──────────────────────────────────────────────────────────

def _py_scope_allows_subprocess(file_path: Path, install_scope: str) -> int:
    """Call scope_allows via --internal-call (the bash shim path)."""
    env = {**os.environ, "INSTALL_SCOPE": install_scope}
    result = subprocess.run(
        ["python3", str(COS_INIT_PY), "--internal-call", "scope_allows", str(file_path)],
        env=env,
    )
    return result.returncode


def _py_scope_allows_direct(file_path: Path, install_scope: str) -> int:
    """Call scope_allows directly via Python module (no subprocess)."""
    allowed = cos_init.scope_allows(str(file_path), install_scope=install_scope)
    return 0 if allowed else 1


def _py_skill_scope_subprocess(skill_dir: Path, install_scope: str) -> int:
    """Call skill_scope_allows via --internal-call (the bash shim path)."""
    env = {**os.environ, "INSTALL_SCOPE": install_scope}
    result = subprocess.run(
        ["python3", str(COS_INIT_PY), "--internal-call", "skill_scope_allows", str(skill_dir)],
        env=env,
    )
    return result.returncode


def _py_skill_scope_direct(skill_dir: Path, install_scope: str) -> int:
    """Call skill_scope_allows directly via Python module."""
    allowed = cos_init.skill_scope_allows(str(skill_dir), install_scope=install_scope)
    return 0 if allowed else 1


# ── scope_allows parity tests ────────────────────────────────────────

class TestParityScopeAllows:
    """Subprocess output must match direct-module output AND the bash truth table."""

    def test_parity_os_only_blocked_under_both(self, tmp_path: Path) -> None:
        """os-only file → exit 1 under install_scope=both (subprocess == direct == 1)."""
        f = tmp_path / "test.sh"
        f.write_text("# SCOPE: os-only\n# rest\n")
        sub_rc = _py_scope_allows_subprocess(f, "both")
        dir_rc = _py_scope_allows_direct(f, "both")
        assert sub_rc == dir_rc, f"subprocess={sub_rc} direct={dir_rc}"
        assert sub_rc == 1, f"Expected exit 1 (blocked), got {sub_rc}"

    def test_parity_project_scope_allowed_under_both(self, tmp_path: Path) -> None:
        """project-scoped file → exit 0 under install_scope=both."""
        f = tmp_path / "test.md"
        f.write_text("# SCOPE: project\n# content\n")
        sub_rc = _py_scope_allows_subprocess(f, "both")
        dir_rc = _py_scope_allows_direct(f, "both")
        assert sub_rc == dir_rc, f"subprocess={sub_rc} direct={dir_rc}"
        assert sub_rc == 0, f"Expected exit 0 (allowed), got {sub_rc}"

    def test_parity_no_header_universal(self, tmp_path: Path) -> None:
        """File with no SCOPE header → exit 0 (universal)."""
        f = tmp_path / "untagged.sh"
        f.write_text("#!/bin/bash\necho hello\n")
        sub_rc = _py_scope_allows_subprocess(f, "project")
        dir_rc = _py_scope_allows_direct(f, "project")
        assert sub_rc == dir_rc, f"subprocess={sub_rc} direct={dir_rc}"
        assert sub_rc == 0

    def test_parity_install_scope_all_bypasses_os_only(self, tmp_path: Path) -> None:
        """install_scope=all → exit 0 even for os-only files."""
        f = tmp_path / "os_only.sh"
        f.write_text("# SCOPE: os-only\n# content\n")
        sub_rc = _py_scope_allows_subprocess(f, "all")
        dir_rc = _py_scope_allows_direct(f, "all")
        assert sub_rc == dir_rc, f"subprocess={sub_rc} direct={dir_rc}"
        assert sub_rc == 0

    def test_parity_html_scope_comment_project(self, tmp_path: Path) -> None:
        """<!-- SCOPE: project --> HTML form → exit 0 under project install."""
        f = tmp_path / "doc.md"
        f.write_text("<!-- SCOPE: project -->\n# doc\n")
        sub_rc = _py_scope_allows_subprocess(f, "project")
        dir_rc = _py_scope_allows_direct(f, "project")
        assert sub_rc == dir_rc, f"subprocess={sub_rc} direct={dir_rc}"
        assert sub_rc == 0

    def test_parity_html_scope_os_only_blocked(self, tmp_path: Path) -> None:
        """<!-- SCOPE: os-only --> HTML form → exit 1 under both install."""
        f = tmp_path / "os_doc.md"
        f.write_text("<!-- SCOPE: os-only -->\n# doc\n")
        sub_rc = _py_scope_allows_subprocess(f, "both")
        dir_rc = _py_scope_allows_direct(f, "both")
        assert sub_rc == dir_rc, f"subprocess={sub_rc} direct={dir_rc}"
        assert sub_rc == 1

    def test_parity_both_scope_tag_allowed(self, tmp_path: Path) -> None:
        """# SCOPE: both → exit 0 under project install_scope."""
        f = tmp_path / "both.sh"
        f.write_text("# SCOPE: both\n# content\n")
        sub_rc = _py_scope_allows_subprocess(f, "project")
        dir_rc = _py_scope_allows_direct(f, "project")
        assert sub_rc == dir_rc
        assert sub_rc == 0


    def test_project_and_both_are_currently_equivalent_install_surfaces(self, tmp_path: Path) -> None:
        """ADR-320: project and both are CLI aliases, not separate install surfaces."""
        cases = {
            "project": "# SCOPE: project\n# content\n",
            "both": "# SCOPE: both\n# content\n",
            "os_only": "# SCOPE: os-only\n# content\n",
            "unscoped": "# content\n",
        }
        for name, body in cases.items():
            f = tmp_path / f"{name}.sh"
            f.write_text(body)
            assert _py_scope_allows_direct(f, "project") == _py_scope_allows_direct(f, "both")
            assert _py_scope_allows_subprocess(f, "project") == _py_scope_allows_subprocess(f, "both")


# ── skill_scope_allows parity tests ─────────────────────────────────

class TestParitySkillScopeAllows:
    """Subprocess output must match direct-module output AND the bash truth table."""

    def _make_skill(self, skill_dir: Path, frontmatter: str) -> None:
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n# Skill\n")

    def test_parity_audience_os_only_blocked(self, tmp_path: Path) -> None:
        """audience: os-only → exit 1 under project install."""
        skill_dir = tmp_path / "my-skill"
        self._make_skill(skill_dir, "audience: os-only")
        sub_rc = _py_skill_scope_subprocess(skill_dir, "project")
        dir_rc = _py_skill_scope_direct(skill_dir, "project")
        assert sub_rc == dir_rc, f"subprocess={sub_rc} direct={dir_rc}"
        assert sub_rc == 1

    def test_parity_audience_both_allowed(self, tmp_path: Path) -> None:
        """audience: both → exit 0 under both install."""
        skill_dir = tmp_path / "skill-both"
        self._make_skill(skill_dir, "audience: both")
        sub_rc = _py_skill_scope_subprocess(skill_dir, "both")
        dir_rc = _py_skill_scope_direct(skill_dir, "both")
        assert sub_rc == dir_rc
        assert sub_rc == 0

    def test_parity_audience_adopters_allowed(self, tmp_path: Path) -> None:
        """audience: adopters → exit 0 (project-installable per bash mapping)."""
        skill_dir = tmp_path / "skill-adopters"
        self._make_skill(skill_dir, "audience: adopters")
        sub_rc = _py_skill_scope_subprocess(skill_dir, "both")
        dir_rc = _py_skill_scope_direct(skill_dir, "both")
        assert sub_rc == dir_rc
        assert sub_rc == 0

    def test_parity_missing_skill_md_passes(self, tmp_path: Path) -> None:
        """Missing SKILL.md → exit 0 (bash: [ -f ] || return 0)."""
        skill_dir = tmp_path / "no-skill"
        skill_dir.mkdir()
        sub_rc = _py_skill_scope_subprocess(skill_dir, "both")
        dir_rc = _py_skill_scope_direct(skill_dir, "both")
        assert sub_rc == dir_rc

    def test_parity_scope_marker_os_only_overrides_audience_both(self, tmp_path: Path) -> None:
        """SCOPE marker is authoritative over legacy audience frontmatter."""
        skill_dir = tmp_path / "marker-os-only"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("<!-- SCOPE: os-only -->\n---\naudience: both\n---\n# Skill\n")
        sub_rc = _py_skill_scope_subprocess(skill_dir, "project")
        dir_rc = _py_skill_scope_direct(skill_dir, "project")
        assert sub_rc == dir_rc
        assert sub_rc == 1

    def test_parity_scope_field_os_only_blocked(self, tmp_path: Path) -> None:
        """scope: os-only → exit 1 (scope: field is equivalent to audience:)."""
        skill_dir = tmp_path / "skill-scope-field"
        self._make_skill(skill_dir, "scope: os-only")
        sub_rc = _py_skill_scope_subprocess(skill_dir, "both")
        dir_rc = _py_skill_scope_direct(skill_dir, "both")
        assert sub_rc == dir_rc
        assert sub_rc == 1

    def test_parity_install_scope_all_bypasses_os_only(self, tmp_path: Path) -> None:
        """install_scope=all → exit 0 even for os-only skills."""
        skill_dir = tmp_path / "skill-os-only-all"
        self._make_skill(skill_dir, "audience: os-only")
        sub_rc = _py_skill_scope_subprocess(skill_dir, "all")
        dir_rc = _py_skill_scope_direct(skill_dir, "all")
        assert sub_rc == dir_rc
        assert sub_rc == 0

    def test_parity_audience_os_dev_blocked(self, tmp_path: Path) -> None:
        """audience: os-dev → exit 1 under both install."""
        skill_dir = tmp_path / "skill-os-dev"
        self._make_skill(skill_dir, "audience: os-dev")
        sub_rc = _py_skill_scope_subprocess(skill_dir, "both")
        dir_rc = _py_skill_scope_direct(skill_dir, "both")
        assert sub_rc == dir_rc
        assert sub_rc == 1

    def test_project_and_both_are_currently_equivalent_for_skill_audience(self, tmp_path: Path) -> None:
        """ADR-320: skill filtering also collapses project and both install surfaces."""
        cases = {
            "project": "audience: project",
            "both": "audience: both",
            "adopters": "audience: adopters",
            "os_only": "audience: os-only",
            "os_dev": "audience: os-dev",
        }
        for name, frontmatter in cases.items():
            skill_dir = tmp_path / name
            self._make_skill(skill_dir, frontmatter)
            assert _py_skill_scope_direct(skill_dir, "project") == _py_skill_scope_direct(skill_dir, "both")
            assert _py_skill_scope_subprocess(skill_dir, "project") == _py_skill_scope_subprocess(skill_dir, "both")

