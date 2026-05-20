"""Characterization tests for the 3 sites that read cognitive-os.yaml.

Locks in the CURRENT (pre-unification) behavior of three independent parsers
so a future refactor that consolidates them into a single config_loader can
detect any behavioral drift.

Sites covered:
    1. lib/dispatch_helper.py
       - _find_config_path()           - candidate-path search order
       - _read_max_parallel_agents()   - regex line-by-line, no PyYAML
    2. lib/agent_health_monitor.py
       - _read_timeout_seconds()       - regex line-by-line, no PyYAML
    3. hooks/_lib/dispatch_gate_check.py
       - top-level script using yaml.safe_load + nested dict access

Key divergences locked in by these tests:
    * Search-path ORDER differs between the three sites.
    * Regex parsers grab the FIRST line that matches anywhere in the file,
      ignoring YAML nesting; the safe_load site requires the EXACT nested
      path resources.compute.max_parallel_agents.
    * Regex parsers tolerate trailing comments and any indentation.
    * Empty file: regex returns DEFAULT; safe_load returns None and the
      script falls back to its hard-coded default of 5.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.unit,
    # Pin all subprocess-spawning tests in this file to the same xdist worker
    # so parallel runs don't fight for CPU on dispatch_gate_check.py startup
    # (Python interpreter cold start + import graph). Without this, a 15s
    # subprocess timeout becomes flaky under -n auto on 8+ workers.
    pytest.mark.xdist_group("dispatch_gate_check_subprocess"),
]

# Make the project's lib/ importable without installing anything.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from lib import agent_health_monitor as ahm  # noqa: E402
from lib import dispatch_helper as dh  # noqa: E402

_DISPATCH_GATE_CHECK = _PROJECT_ROOT / "hooks" / "_lib" / "dispatch_gate_check.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def _run_dispatch_gate_check(project_dir: Path) -> dict:
    """Invoke hooks/_lib/dispatch_gate_check.py as a subprocess.

    The script reads stdin (JSON) and writes a single JSON object to stdout.
    We feed it an empty payload so only the config-reading branch is exercised.

    Retries once on TimeoutExpired: under heavy parallel xdist load with 8
    workers, the python interpreter cold-start + import graph resolution
    occasionally exceeds the timeout on the unlucky worker. A second attempt
    after the first cold-start has primed the filesystem cache nearly always
    succeeds.
    """
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project_dir)}

    def _attempt(timeout_s: int) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(_DISPATCH_GATE_CHECK)],
            input="{}",
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout_s,
        )

    try:
        proc = _attempt(120)
    except subprocess.TimeoutExpired:
        proc = _attempt(120)
    assert proc.returncode == 0, f"stderr={proc.stderr}"
    return json.loads(proc.stdout)


# ===========================================================================
# Site 1a: lib/dispatch_helper._find_config_path()
# ===========================================================================


class TestFindConfigPath:
    """Lock the EXACT candidate-path order used by _find_config_path()."""

    def test_returns_none_when_no_candidate_exists(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("COGNITIVE_OS_PROJECT_DIR", raising=False)
        assert dh._find_config_path() is None

    def test_cwd_yaml_wins_when_no_project_dir_env(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("COGNITIVE_OS_PROJECT_DIR", raising=False)
        cwd_cfg = _write(tmp_path / "cognitive-os.yaml", "x: 1\n")
        assert dh._find_config_path() == "cognitive-os.yaml"
        # absolute equivalence sanity check
        assert (tmp_path / "cognitive-os.yaml").samefile(cwd_cfg)

    def test_cognitive_os_dir_used_when_cwd_missing(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("COGNITIVE_OS_PROJECT_DIR", raising=False)
        _write(tmp_path / ".cognitive-os" / "cognitive-os.yaml", "x: 1\n")
        result = dh._find_config_path()
        assert result == os.path.join(".cognitive-os", "cognitive-os.yaml")

    def test_claude_project_dir_takes_precedence_over_cwd(
        self, tmp_path, monkeypatch
    ):
        # cwd has its own cognitive-os.yaml AND project dir has one.
        # Project-dir candidate is INSERTED AT INDEX 0, so it wins.
        monkeypatch.chdir(tmp_path)
        _write(tmp_path / "cognitive-os.yaml", "x: 1\n")
        proj = tmp_path / "proj"
        proj_cfg = _write(proj / "cognitive-os.yaml", "x: 2\n")
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(proj))
        monkeypatch.delenv("COGNITIVE_OS_PROJECT_DIR", raising=False)
        assert dh._find_config_path() == str(proj_cfg)

    def test_cognitive_os_project_dir_used_when_claude_unset(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        proj = tmp_path / "proj"
        proj_cfg = _write(proj / "cognitive-os.yaml", "x: 3\n")
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(proj))
        assert dh._find_config_path() == str(proj_cfg)

    def test_claude_project_dir_wins_over_cognitive_os_project_dir(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        cp = tmp_path / "cp"
        op = tmp_path / "op"
        cp_cfg = _write(cp / "cognitive-os.yaml", "x: claude\n")
        _write(op / "cognitive-os.yaml", "x: oldenv\n")
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(cp))
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(op))
        assert dh._find_config_path() == str(cp_cfg)

    def test_empty_project_dir_env_treated_as_unset(
        self, tmp_path, monkeypatch
    ):
        # Empty string is falsy in `or`, so neither env var inserts a candidate.
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "")
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", "")
        _write(tmp_path / "cognitive-os.yaml", "x: 1\n")
        assert dh._find_config_path() == "cognitive-os.yaml"


# ===========================================================================
# Site 1b: lib/dispatch_helper._read_max_parallel_agents()
# ===========================================================================


class TestReadMaxParallelAgents:
    """Regex line-by-line parser; default is 5.

    Locked behaviors:
      * No file / unfindable -> default (5).
      * Key missing -> default (5).
      * First matching line wins, regardless of YAML nesting.
      * Trailing comments are tolerated.
      * Any leading whitespace is allowed by `^\\s*`.
    """

    DEFAULT = 5

    def test_default_constant_is_five(self):
        # Lock the default so a refactor cannot silently change it.
        assert dh._DEFAULT_MAX_PARALLEL == 5

    def test_happy_path_top_level_key(self, tmp_path):
        cfg = _write(tmp_path / "c.yaml", "max_parallel_agents: 12\n")
        assert dh._read_max_parallel_agents(str(cfg)) == 12

    def test_key_missing_returns_default(self, tmp_path):
        cfg = _write(tmp_path / "c.yaml", "project:\n  phase: x\n")
        assert dh._read_max_parallel_agents(str(cfg)) == self.DEFAULT

    def test_no_path_returns_default(self, monkeypatch, tmp_path):
        # No config_path arg, no file findable -> default.
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("COGNITIVE_OS_PROJECT_DIR", raising=False)
        assert dh._read_max_parallel_agents() == self.DEFAULT

    def test_nonexistent_path_returns_default(self, tmp_path):
        # OSError from open() is swallowed -> default.
        missing = tmp_path / "nope.yaml"
        assert dh._read_max_parallel_agents(str(missing)) == self.DEFAULT

    def test_nested_under_resources_compute_still_matches_first(
        self, tmp_path
    ):
        # DIVERGENCE: regex grabs the line regardless of nesting.
        # safe_load would require resources.compute.max_parallel_agents.
        cfg = _write(
            tmp_path / "c.yaml",
            "resources:\n"
            "  compute:\n"
            "    max_parallel_agents: 7\n",
        )
        assert dh._read_max_parallel_agents(str(cfg)) == 7

    def test_first_match_wins_even_when_top_level_appears_later(
        self, tmp_path
    ):
        # DIVERGENCE: nested value listed first wins; YAML semantics would
        # treat the deeply-nested key as a different key entirely.
        cfg = _write(
            tmp_path / "c.yaml",
            "worker:\n"
            "  max_parallel_agents: 99\n"
            "max_parallel_agents: 3\n",
        )
        assert dh._read_max_parallel_agents(str(cfg)) == 99

    def test_inline_comment_on_value_line(self, tmp_path):
        # Regex `(\d+)` stops at the first non-digit, so trailing comments
        # are tolerated; the integer is parsed correctly.
        cfg = _write(
            tmp_path / "c.yaml",
            "max_parallel_agents: 10  # cap for laptops\n",
        )
        assert dh._read_max_parallel_agents(str(cfg)) == 10

    def test_empty_file_returns_default(self, tmp_path):
        cfg = _write(tmp_path / "c.yaml", "")
        assert dh._read_max_parallel_agents(str(cfg)) == self.DEFAULT

    def test_indented_key_still_matches(self, tmp_path):
        # `^\\s*` allows arbitrary leading whitespace.
        cfg = _write(tmp_path / "c.yaml", "      max_parallel_agents: 4\n")
        assert dh._read_max_parallel_agents(str(cfg)) == 4

    def test_zero_is_returned_as_int_not_default(self, tmp_path):
        # 0 is a valid int and should NOT be coerced to the default.
        cfg = _write(tmp_path / "c.yaml", "max_parallel_agents: 0\n")
        assert dh._read_max_parallel_agents(str(cfg)) == 0


# ===========================================================================
# Site 2: lib/agent_health_monitor._read_timeout_seconds()
# ===========================================================================


class TestReadTimeoutSeconds:
    """Regex line-by-line parser; default is 300.

    Locked candidate-path order (DIFFERENT from dispatch_helper):
      1. ${CLAUDE_PROJECT_DIR or COGNITIVE_OS_PROJECT_DIR}/cognitive-os.yaml
      2. config_path argument (if provided)
      3. _DEFAULT_CONFIG_PATH == "cognitive-os.yaml"  (relative to cwd)
    """

    DEFAULT = 300

    def test_default_constant_is_three_hundred(self):
        assert ahm._DEFAULT_TIMEOUT_SECONDS == 300
        assert ahm._DEFAULT_CONFIG_PATH == "cognitive-os.yaml"

    def test_happy_path_via_explicit_config_path(self, tmp_path, monkeypatch):
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("COGNITIVE_OS_PROJECT_DIR", raising=False)
        monkeypatch.chdir(tmp_path)
        cfg = _write(tmp_path / "c.yaml", "agent_timeout_seconds: 600\n")
        assert ahm._read_timeout_seconds(str(cfg)) == 600

    def test_key_missing_returns_default(self, tmp_path, monkeypatch):
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("COGNITIVE_OS_PROJECT_DIR", raising=False)
        monkeypatch.chdir(tmp_path)
        cfg = _write(tmp_path / "c.yaml", "project:\n  phase: x\n")
        assert ahm._read_timeout_seconds(str(cfg)) == self.DEFAULT

    def test_no_candidates_returns_default(self, tmp_path, monkeypatch):
        # No env, no config_path arg, and no cwd file -> default.
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("COGNITIVE_OS_PROJECT_DIR", raising=False)
        monkeypatch.chdir(tmp_path)
        assert ahm._read_timeout_seconds() == self.DEFAULT

    def test_nonexistent_explicit_path_falls_through_to_default(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("COGNITIVE_OS_PROJECT_DIR", raising=False)
        monkeypatch.chdir(tmp_path)
        # Both candidates are missing files -> isfile() filter, then default.
        missing = tmp_path / "missing.yaml"
        assert ahm._read_timeout_seconds(str(missing)) == self.DEFAULT

    def test_project_dir_yaml_takes_precedence_over_explicit_arg(
        self, tmp_path, monkeypatch
    ):
        # ORDER LOCK: project-dir candidate is appended FIRST.
        proj = tmp_path / "proj"
        _write(proj / "cognitive-os.yaml", "agent_timeout_seconds: 111\n")
        explicit = _write(
            tmp_path / "explicit.yaml", "agent_timeout_seconds: 222\n"
        )
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(proj))
        monkeypatch.delenv("COGNITIVE_OS_PROJECT_DIR", raising=False)
        assert ahm._read_timeout_seconds(str(explicit)) == 111

    def test_cognitive_os_project_dir_used_when_claude_unset(
        self, tmp_path, monkeypatch
    ):
        proj = tmp_path / "proj"
        _write(proj / "cognitive-os.yaml", "agent_timeout_seconds: 444\n")
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(proj))
        monkeypatch.chdir(tmp_path)
        assert ahm._read_timeout_seconds() == 444

    def test_claude_project_dir_wins_over_cognitive_os_project_dir(
        self, tmp_path, monkeypatch
    ):
        cp = tmp_path / "cp"
        op = tmp_path / "op"
        _write(cp / "cognitive-os.yaml", "agent_timeout_seconds: 11\n")
        _write(op / "cognitive-os.yaml", "agent_timeout_seconds: 22\n")
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(cp))
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(op))
        monkeypatch.chdir(tmp_path)
        assert ahm._read_timeout_seconds() == 11

    def test_nested_value_still_matches_first(self, tmp_path, monkeypatch):
        # DIVERGENCE: regex ignores YAML nesting.
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("COGNITIVE_OS_PROJECT_DIR", raising=False)
        monkeypatch.chdir(tmp_path)
        cfg = _write(
            tmp_path / "c.yaml",
            "agents:\n  health:\n    agent_timeout_seconds: 77\n",
        )
        assert ahm._read_timeout_seconds(str(cfg)) == 77

    def test_first_match_wins_when_key_appears_twice(
        self, tmp_path, monkeypatch
    ):
        # DIVERGENCE: nested-then-top-level: regex returns first occurrence.
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("COGNITIVE_OS_PROJECT_DIR", raising=False)
        monkeypatch.chdir(tmp_path)
        cfg = _write(
            tmp_path / "c.yaml",
            "worker:\n"
            "  agent_timeout_seconds: 999\n"
            "agent_timeout_seconds: 30\n",
        )
        assert ahm._read_timeout_seconds(str(cfg)) == 999

    def test_inline_comment_on_value_line(self, tmp_path, monkeypatch):
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("COGNITIVE_OS_PROJECT_DIR", raising=False)
        monkeypatch.chdir(tmp_path)
        cfg = _write(
            tmp_path / "c.yaml",
            "agent_timeout_seconds: 45  # short for tests\n",
        )
        assert ahm._read_timeout_seconds(str(cfg)) == 45

    def test_empty_file_returns_default(self, tmp_path, monkeypatch):
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("COGNITIVE_OS_PROJECT_DIR", raising=False)
        monkeypatch.chdir(tmp_path)
        cfg = _write(tmp_path / "c.yaml", "")
        assert ahm._read_timeout_seconds(str(cfg)) == self.DEFAULT

    def test_indented_key_still_matches(self, tmp_path, monkeypatch):
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("COGNITIVE_OS_PROJECT_DIR", raising=False)
        monkeypatch.chdir(tmp_path)
        cfg = _write(tmp_path / "c.yaml", "    agent_timeout_seconds: 90\n")
        assert ahm._read_timeout_seconds(str(cfg)) == 90


# ===========================================================================
# Site 3: hooks/_lib/dispatch_gate_check.py (yaml.safe_load + nested access)
# ===========================================================================


class TestDispatchGateCheckYaml:
    """Top-level script using yaml.safe_load.

    Locked behaviors:
      * Reads ${CLAUDE_PROJECT_DIR}/cognitive-os.yaml first, then
        ${CLAUDE_PROJECT_DIR}/.cognitive-os/cognitive-os.yaml.
      * Requires the EXACT nested path
        resources.compute.max_parallel_agents.
      * Top-level max_parallel_agents is IGNORED (key-precedence divergence
        from the regex parsers).
      * Inline comments are stripped by yaml.safe_load.
      * COGNITIVE_OS_MAX_PARALLEL_AGENTS overrides the YAML value.
      * Default is 5 from the result dict initializer; on config parse
        exceptions the default is preserved and an entry is added to
        result["error"].
    """

    DEFAULT = 5

    def test_happy_path_nested_value(self, tmp_path):
        _write(
            tmp_path / "cognitive-os.yaml",
            "resources:\n  compute:\n    max_parallel_agents: 9\n",
        )
        result = _run_dispatch_gate_check(tmp_path)
        assert result["max_agents"] == 9
        assert "config:" not in result["error"]

    def test_top_level_key_is_ignored(self, tmp_path):
        # DIVERGENCE: the regex sites would return 17; safe_load + nested
        # .get() chain returns the default because the nested path is absent.
        _write(tmp_path / "cognitive-os.yaml", "max_parallel_agents: 17\n")
        result = _run_dispatch_gate_check(tmp_path)
        assert result["max_agents"] == self.DEFAULT

    def test_key_missing_returns_default(self, tmp_path):
        _write(
            tmp_path / "cognitive-os.yaml",
            "project:\n  phase: stabilization\n",
        )
        result = _run_dispatch_gate_check(tmp_path)
        assert result["max_agents"] == self.DEFAULT

    def test_no_config_file_returns_default(self, tmp_path):
        # No yaml file anywhere under PROJECT_DIR -> default; no error
        # because the cfg_path.exists() check short-circuits.
        result = _run_dispatch_gate_check(tmp_path)
        assert result["max_agents"] == self.DEFAULT
        assert "config:" not in result["error"]

    def test_dot_cognitive_os_path_used_as_fallback(self, tmp_path):
        # DIVERGENCE: candidate order vs site 1 differs. Here the fallback
        # is .cognitive-os/cognitive-os.yaml UNDER the project dir.
        _write(
            tmp_path / ".cognitive-os" / "cognitive-os.yaml",
            "resources:\n  compute:\n    max_parallel_agents: 8\n",
        )
        result = _run_dispatch_gate_check(tmp_path)
        assert result["max_agents"] == 8

    def test_top_level_yaml_takes_precedence_over_dot_cognitive_os(
        self, tmp_path
    ):
        # If both files exist, the top-level cognitive-os.yaml wins because
        # cfg_path is only reassigned when the first one does NOT exist.
        _write(
            tmp_path / "cognitive-os.yaml",
            "resources:\n  compute:\n    max_parallel_agents: 1\n",
        )
        _write(
            tmp_path / ".cognitive-os" / "cognitive-os.yaml",
            "resources:\n  compute:\n    max_parallel_agents: 99\n",
        )
        result = _run_dispatch_gate_check(tmp_path)
        assert result["max_agents"] == 1

    def test_inline_comment_is_stripped_by_safe_load(self, tmp_path):
        _write(
            tmp_path / "cognitive-os.yaml",
            "resources:\n"
            "  compute:\n"
            "    max_parallel_agents: 6  # six is enough\n",
        )
        result = _run_dispatch_gate_check(tmp_path)
        assert result["max_agents"] == 6

    def test_empty_file_returns_default_no_error(self, tmp_path):
        # safe_load returns None; the script's `or {}` coerces to {} so
        # the .get() chain yields the default and NO error is recorded.
        _write(tmp_path / "cognitive-os.yaml", "")
        result = _run_dispatch_gate_check(tmp_path)
        assert result["max_agents"] == self.DEFAULT
        assert "config:" not in result["error"]

    def test_partial_nesting_returns_default(self, tmp_path):
        # resources.compute exists but max_parallel_agents is missing.
        _write(
            tmp_path / "cognitive-os.yaml",
            "resources:\n  compute:\n    other: 1\n",
        )
        result = _run_dispatch_gate_check(tmp_path)
        assert result["max_agents"] == self.DEFAULT

    def test_only_resources_root_returns_default(self, tmp_path):
        # resources exists but compute is missing -> .get("compute", {})
        # returns {} -> .get("max_parallel_agents", 5) returns 5.
        _write(
            tmp_path / "cognitive-os.yaml",
            "resources:\n  storage: ssd\n",
        )
        result = _run_dispatch_gate_check(tmp_path)
        assert result["max_agents"] == self.DEFAULT

    def test_indented_top_level_key_still_ignored(self, tmp_path):
        # safe_load parses indentation; an indented "max_parallel_agents"
        # at the top would be a syntax error or interpreted as a different
        # structure. We use an unambiguous nested-but-wrong-section variant.
        _write(
            tmp_path / "cognitive-os.yaml",
            "worker:\n  max_parallel_agents: 42\n",
        )
        result = _run_dispatch_gate_check(tmp_path)
        assert result["max_agents"] == self.DEFAULT

    def test_malformed_yaml_records_error_and_keeps_default(self, tmp_path):
        # Malformed YAML triggers the except branch which appends to
        # result["error"] and leaves max_agents at the initialized default.
        _write(
            tmp_path / "cognitive-os.yaml",
            "resources:\n  compute:\n    max_parallel_agents: [unclosed\n",
        )
        result = _run_dispatch_gate_check(tmp_path)
        assert result["max_agents"] == self.DEFAULT
        assert "config:" in result["error"]

    def test_env_var_beats_yaml_value(self, tmp_path):
        # D2.2 regression: COGNITIVE_OS_MAX_PARALLEL_AGENTS env var must take
        # precedence over the value read from cognitive-os.yaml.
        _write(
            tmp_path / "cognitive-os.yaml",
            "resources:\n  compute:\n    max_parallel_agents: 3\n",
        )
        env = {
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(tmp_path),
            "COGNITIVE_OS_MAX_PARALLEL_AGENTS": "42",
        }
        proc = subprocess.run(
            [sys.executable, str(_DISPATCH_GATE_CHECK)],
            input="{}",
            capture_output=True,
            text=True,
            env=env,
            timeout=15,
        )
        assert proc.returncode == 0, f"stderr={proc.stderr}"
        result = json.loads(proc.stdout)
        # Env var (42) must win over YAML value (3)
        assert result["max_agents"] == 42
