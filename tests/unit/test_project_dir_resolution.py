"""Characterization tests for the 13 sites that resolve project-dir env vars.

A previous audit catalogued 11 sites; foreground re-grep found 13 because
queue_drainer.py has a second site at line 316 and lib/telemetry.py uses a
DIFFERENT precedence order. Together they exhibit FOUR distinct patterns:

  Pattern A  — `CLAUDE or COGNITIVE_OS or ""`         (default empty string)
  Pattern A' — `CLAUDE or COGNITIVE_OS or "."`        (default current dir)
  Pattern C  — `CLAUDE or "."`                        (NO COGNITIVE_OS fallback)
  Pattern D  — `COGNITIVE_OS or CLAUDE or os.getcwd()` (REVERSE precedence)

The tests here:

1. Lock in each pattern's behavior in isolation (Section 1).
2. Pin the literal expression in each source site so a refactor that
   changes wording surfaces explicitly (Section 2).
3. Where feasible, exercise the actual source function with mocked
   side effects to confirm the env-var resolution wires through to the
   observable output (Section 3).

When the planned `lib/paths.py::project_root()` refactor lands, these tests
must continue to pass — or the refactor has changed semantics and the
caller behavior at one of the 13 sites needs explicit reconciliation.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]


# ── Helpers ─────────────────────────────────────────────────────────────


def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.delenv("COGNITIVE_OS_PROJECT_DIR", raising=False)


def _pattern_a(default: str = "") -> str:
    """Reproduce the 10 sites that use Pattern A literally."""
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get(
        "COGNITIVE_OS_PROJECT_DIR", default
    )


def _pattern_c() -> str:
    """Reproduce the 2 sites that use only CLAUDE_PROJECT_DIR with `.` default."""
    return os.environ.get("CLAUDE_PROJECT_DIR", ".")


def _pattern_d() -> str:
    """Reproduce telemetry's reverse precedence."""
    return (
        os.environ.get("COGNITIVE_OS_PROJECT_DIR")
        or os.environ.get("CLAUDE_PROJECT_DIR")
        or os.getcwd()
    )


# ─────────────────────────────────────────────────────────────────────────
# Section 1 — Per-pattern behavior
# ─────────────────────────────────────────────────────────────────────────


class TestPatternA:
    """`CLAUDE_PROJECT_DIR or COGNITIVE_OS_PROJECT_DIR or ""`.

    10 sites: dispatch_helper:47, dispatch_model_advisor:97 and :136,
    rate_limiter:71, sdd_pipeline:133, queue_drainer:66,
    agent_health_monitor:96, :125, :404, :433.
    """

    def test_both_unset_returns_empty_string(self, monkeypatch):
        _clear_env(monkeypatch)
        assert _pattern_a() == ""

    def test_claude_only_returns_claude(self, monkeypatch):
        _clear_env(monkeypatch)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/from-claude")
        assert _pattern_a() == "/from-claude"

    def test_cognitive_os_only_returns_it(self, monkeypatch):
        _clear_env(monkeypatch)
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", "/from-cognitive-os")
        assert _pattern_a() == "/from-cognitive-os"

    def test_both_set_claude_wins(self, monkeypatch):
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/claude")
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", "/cognitive")
        assert _pattern_a() == "/claude"

    def test_claude_empty_string_falls_back(self, monkeypatch):
        """`""` is falsy → `or` falls through to COGNITIVE_OS_PROJECT_DIR."""
        _clear_env(monkeypatch)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "")
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", "/fallback")
        assert _pattern_a() == "/fallback"

    def test_both_empty_returns_default(self, monkeypatch):
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "")
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", "")
        assert _pattern_a() == ""


class TestPatternAPrime:
    """Pattern A with `"."` default — 1 site: model_router:321."""

    def test_both_unset_returns_dot(self, monkeypatch):
        _clear_env(monkeypatch)
        assert _pattern_a(default=".") == "."

    def test_claude_set_overrides_dot(self, monkeypatch):
        _clear_env(monkeypatch)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/claude")
        assert _pattern_a(default=".") == "/claude"

    def test_only_cognitive_os_returns_it_not_dot(self, monkeypatch):
        _clear_env(monkeypatch)
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", "/cog")
        assert _pattern_a(default=".") == "/cog"


class TestPatternC:
    """`CLAUDE_PROJECT_DIR or "."` — NO COGNITIVE_OS fallback.

    2 sites: hooks/_lib/dispatch_gate_check.py:22, queue_drainer.py:316.
    """

    def test_unset_returns_dot(self, monkeypatch):
        _clear_env(monkeypatch)
        assert _pattern_c() == "."

    def test_claude_set_returns_claude(self, monkeypatch):
        _clear_env(monkeypatch)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/claude")
        assert _pattern_c() == "/claude"

    def test_cognitive_os_alone_does_NOT_help(self, monkeypatch):
        """The audit's surprise: this pattern ignores COGNITIVE_OS_PROJECT_DIR."""
        _clear_env(monkeypatch)
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", "/cog")
        assert _pattern_c() == "."

    def test_claude_empty_string_returns_empty_not_dot(self, monkeypatch):
        """os.environ.get(KEY, default) returns "" not the default when KEY is set to ""."""
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "")
        assert _pattern_c() == ""


class TestPatternD:
    """telemetry._project_root: REVERSE precedence + cwd default."""

    def test_both_unset_returns_cwd(self, monkeypatch, tmp_path):
        _clear_env(monkeypatch)
        monkeypatch.chdir(tmp_path)
        assert _pattern_d() == str(tmp_path)

    def test_cognitive_os_wins_when_both_set(self, monkeypatch):
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/claude")
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", "/cog")
        assert _pattern_d() == "/cog"

    def test_claude_only_returns_claude(self, monkeypatch):
        _clear_env(monkeypatch)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/claude")
        assert _pattern_d() == "/claude"

    def test_cognitive_os_empty_falls_back_to_claude(self, monkeypatch):
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", "")
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/claude")
        assert _pattern_d() == "/claude"


# ─────────────────────────────────────────────────────────────────────────
# Section 2 — Source pinning (catch refactors that change the literal)
# ─────────────────────────────────────────────────────────────────────────


PATTERN_A_LITERAL = (
    'os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get(\n'
    '        "COGNITIVE_OS_PROJECT_DIR", ""'
)
PATTERN_A_LITERAL_INDENTED = (
    'os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get(\n'
    '                "COGNITIVE_OS_PROJECT_DIR", ""'
)
PATTERN_A_PRIME_LITERAL = (
    'os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get(\n'
    '            "COGNITIVE_OS_PROJECT_DIR", "."'
)
PATTERN_C_LITERAL = 'os.environ.get("CLAUDE_PROJECT_DIR", ".")'


PATTERN_A_MIGRATED_CALL = "project_root()"
PATTERN_A_MIGRATED_IMPORT = "from lib.paths import project_root"


@pytest.mark.parametrize(
    "relpath",
    [
        "lib/dispatch_helper.py",
        "lib/dispatch_model_advisor.py",
        "lib/rate_limiter.py",
        "lib/sdd_pipeline.py",
        "lib/queue_drainer.py",
        "lib/agent_health_monitor.py",
    ],
)
def test_pattern_a_literal_present_in_source(relpath):
    """Each Pattern A consumer MUST import and call project_root() (Lote-3, R1 migration).

    Previously checked for the inline env-var expression.  After the R1 refactor
    all 10 Pattern A sites were migrated to ``lib.paths.project_root()``.
    """
    src = (REPO_ROOT / relpath).read_text()
    assert PATTERN_A_MIGRATED_IMPORT in src, (
        f"{relpath} does not import project_root from lib.paths — "
        "either the R1 migration was reverted or the file was excluded by mistake."
    )
    assert PATTERN_A_MIGRATED_CALL in src, (
        f"{relpath} does not call project_root() — "
        "the R1 migration must replace all Pattern A inline expressions."
    )
    # Verify the OLD inline Pattern A expression is GONE (migration complete).
    assert PATTERN_A_LITERAL not in src, (
        f"{relpath} still contains the old Pattern A literal — "
        "the R1 migration is incomplete for this file."
    )


def test_pattern_a_literal_appears_4_times_in_agent_health_monitor():
    """agent_health_monitor.py was migrated: 0 old literals, 4 project_root() calls.

    Previously the 4 Pattern A sites used the inline expression at :96, :125,
    :404, :433.  After R1 all 4 are replaced by project_root() calls.
    """
    src = (REPO_ROOT / "lib/agent_health_monitor.py").read_text()
    old_total = src.count(PATTERN_A_LITERAL) + src.count(PATTERN_A_LITERAL_INDENTED)
    assert old_total == 0, (
        f"agent_health_monitor.py: found {old_total} old Pattern A literals — "
        "expected 0 after R1 migration to project_root()."
    )
    new_total = src.count(PATTERN_A_MIGRATED_CALL)
    assert new_total == 4, (
        f"agent_health_monitor.py: expected 4 project_root() calls (was 4 Pattern A sites), "
        f"found {new_total}."
    )


def test_pattern_a_literal_appears_twice_in_dispatch_model_advisor():
    """dispatch_model_advisor.py was migrated: 0 old literals, 2 project_root() calls."""
    src = (REPO_ROOT / "lib/dispatch_model_advisor.py").read_text()
    assert src.count(PATTERN_A_LITERAL) == 0, (
        "dispatch_model_advisor.py: still contains old Pattern A literals — "
        "expected 0 after R1 migration."
    )
    assert src.count(PATTERN_A_MIGRATED_CALL) == 2, (
        "dispatch_model_advisor.py: expected 2 project_root() calls (was 2 Pattern A sites)."
    )


def test_model_router_uses_pattern_a_prime_with_dot_default():
    """model_router:321 is the lone Pattern A' (dot default) — refactor MUST preserve."""
    src = (REPO_ROOT / "lib/model_router.py").read_text()
    assert PATTERN_A_PRIME_LITERAL in src, (
        "model_router.py no longer uses '.' default for project_dir at line ~321. "
        "Other sites use '' default — silently changing the default would change "
        "metrics_dir behavior when both env vars are unset."
    )


def test_dispatch_gate_check_uses_pattern_c():
    src = (REPO_ROOT / "hooks/_lib/dispatch_gate_check.py").read_text()
    assert PATTERN_C_LITERAL in src, (
        "hooks/_lib/dispatch_gate_check.py no longer uses Pattern C "
        "(CLAUDE only, default '.'). This site has no COGNITIVE_OS fallback "
        "by design — verify any new resolution preserves that contract."
    )


def test_queue_drainer_line_316_uses_pattern_c():
    """queue_drainer.py has 2 sites: :66 uses Pattern A, :316 uses Pattern C."""
    src = (REPO_ROOT / "lib/queue_drainer.py").read_text()
    assert PATTERN_C_LITERAL in src, (
        "queue_drainer.py:316 (inside select_top, advisor branch) no longer "
        "uses Pattern C. Refactor must preserve the divergence from :66."
    )


def test_telemetry_uses_pattern_d_reverse_precedence():
    src = (REPO_ROOT / "lib/telemetry.py").read_text()
    assert 'os.environ.get("COGNITIVE_OS_PROJECT_DIR")' in src
    assert 'os.environ.get("CLAUDE_PROJECT_DIR")' in src
    cog_idx = src.find('os.environ.get("COGNITIVE_OS_PROJECT_DIR")')
    claude_idx = src.find('os.environ.get("CLAUDE_PROJECT_DIR")')
    assert cog_idx < claude_idx, (
        "telemetry._project_root REVERSED its precedence — "
        "CLAUDE now wins over COGNITIVE_OS. Refactor must reconcile with the "
        "10 Pattern A sites where the opposite is true."
    )


# ─────────────────────────────────────────────────────────────────────────
# Section 3 — Behavior of source functions when env vars resolve through
# ─────────────────────────────────────────────────────────────────────────


class TestDispatchHelperFindConfigPath:
    """lib/dispatch_helper._find_config_path() — exercises Pattern A at line 47."""

    def test_finds_yaml_under_claude_project_dir(self, monkeypatch, tmp_path):
        from lib import dispatch_helper

        _clear_env(monkeypatch)
        monkeypatch.chdir(tmp_path / ".." if not tmp_path.exists() else tmp_path)
        (tmp_path / "cognitive-os.yaml").write_text("")
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        result = dispatch_helper._find_config_path()
        assert result is not None
        assert Path(result).resolve() == (tmp_path / "cognitive-os.yaml").resolve()

    def test_falls_back_to_cognitive_os_project_dir(self, monkeypatch, tmp_path):
        from lib import dispatch_helper

        _clear_env(monkeypatch)
        monkeypatch.chdir(tmp_path)
        (tmp_path / "cognitive-os.yaml").write_text("")
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(tmp_path))
        result = dispatch_helper._find_config_path()
        assert result is not None

    def test_no_env_returns_None_when_no_files_exist(self, monkeypatch, tmp_path):
        from lib import dispatch_helper

        _clear_env(monkeypatch)
        monkeypatch.chdir(tmp_path)
        # No cognitive-os.yaml present.
        assert dispatch_helper._find_config_path() is None


class TestModelRouterMetricsDirResolution:
    """lib/model_router.get_consequence_override: line 321 builds metrics_dir from env."""

    def test_no_env_uses_dot_relative_metrics_dir(self, monkeypatch):
        from lib import model_router

        _clear_env(monkeypatch)
        observed: list[Path] = []
        original_exists = Path.exists

        def fake_exists(self):
            observed.append(self)
            return False  # short-circuit: history file "doesn't exist" → no-override

        monkeypatch.setattr(Path, "exists", fake_exists)
        try:
            model_router.get_consequence_override(skill_name="x", metrics_dir=None)
        finally:
            monkeypatch.setattr(Path, "exists", original_exists)

        assert observed, "get_consequence_override didn't reach the exists() check"
        path = observed[0]
        # With project_dir == "." the metrics_dir is "./.cognitive-os/metrics".
        # Path normalises this to ".cognitive-os/metrics/consequence-history.jsonl".
        assert ".cognitive-os" in path.parts, (
            f"Expected '.cognitive-os' in path parts; got {path!r}."
        )
        assert not path.is_absolute(), (
            f"Expected relative path under '.' default; got absolute {path!r}."
        )

    def test_claude_env_overrides_dot_default(self, monkeypatch, tmp_path):
        from lib import model_router

        _clear_env(monkeypatch)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        observed: list[Path] = []
        original_exists = Path.exists

        def fake_exists(self):
            observed.append(self)
            return False

        monkeypatch.setattr(Path, "exists", fake_exists)
        try:
            model_router.get_consequence_override(skill_name="x", metrics_dir=None)
        finally:
            monkeypatch.setattr(Path, "exists", original_exists)

        assert observed
        assert str(tmp_path) in str(observed[0])


class TestQueueDrainerReadMaxParallelAgents:
    """lib/queue_drainer._read_max_parallel_agents — Pattern A at line 66."""

    def test_finds_value_via_claude_project_dir(self, monkeypatch, tmp_path):
        from lib import queue_drainer

        _clear_env(monkeypatch)
        (tmp_path / "cognitive-os.yaml").write_text("max_parallel_agents: 7\n")
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        # The default config path is also searched, but should not be hit first.
        assert queue_drainer._read_max_parallel_agents() == 7

    def test_no_env_uses_default(self, monkeypatch, tmp_path):
        from lib import queue_drainer

        _clear_env(monkeypatch)
        monkeypatch.chdir(tmp_path)  # ensure default path doesn't accidentally exist
        # The site falls back to the package default _DEFAULT_MAX_PARALLEL.
        result = queue_drainer._read_max_parallel_agents()
        assert isinstance(result, int)
        assert result > 0


class TestTelemetryProjectRoot:
    """lib/telemetry._project_root — Pattern D (reverse precedence)."""

    def test_cognitive_os_wins_when_both_set(self, monkeypatch, tmp_path):
        from lib import telemetry

        cog_dir = tmp_path / "cog"
        cog_dir.mkdir()
        claude_dir = tmp_path / "claude"
        claude_dir.mkdir()
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(cog_dir))
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(claude_dir))
        assert telemetry._project_root() == Path(str(cog_dir))

    def test_falls_back_to_claude_when_cognitive_os_unset(self, monkeypatch, tmp_path):
        from lib import telemetry

        _clear_env(monkeypatch)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        assert telemetry._project_root() == Path(str(tmp_path))

    def test_falls_back_to_cwd_when_both_unset(self, monkeypatch, tmp_path):
        from lib import telemetry

        _clear_env(monkeypatch)
        monkeypatch.chdir(tmp_path)
        # macOS resolves /private/var/.../tmp_path; compare via Path resolution.
        result = telemetry._project_root()
        assert result.resolve() == tmp_path.resolve()


class TestDispatchGateCheckProjectDirConstant:
    """hooks/_lib/dispatch_gate_check.PROJECT_DIR — Pattern C, captured at import."""

    def _reload_module(self, monkeypatch):
        """Re-import the module so the module-level constant re-reads env."""
        sys.modules.pop("hooks._lib.dispatch_gate_check", None)
        # The module isn't a normal package; load it via path.
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "hooks._lib.dispatch_gate_check_test_reload",
            REPO_ROOT / "hooks" / "_lib" / "dispatch_gate_check.py",
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_unset_resolves_to_dot(self, monkeypatch):
        _clear_env(monkeypatch)
        module = self._reload_module(monkeypatch)
        assert module.PROJECT_DIR == "."

    def test_claude_set_resolves_to_claude(self, monkeypatch):
        _clear_env(monkeypatch)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/from-claude")
        module = self._reload_module(monkeypatch)
        assert module.PROJECT_DIR == "/from-claude"

    def test_cognitive_os_alone_resolves_to_dot(self, monkeypatch):
        """Locks the absence of COGNITIVE_OS_PROJECT_DIR fallback at this site."""
        _clear_env(monkeypatch)
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", "/from-cognitive-os")
        module = self._reload_module(monkeypatch)
        assert module.PROJECT_DIR == "."


# ─────────────────────────────────────────────────────────────────────────
# Section 4 — Cross-pattern divergence summary (codifies the audit findings)
# ─────────────────────────────────────────────────────────────────────────


def test_audit_count_of_sites_per_pattern():
    """Sanity asserts so the audit catalogue stays in sync with reality.

    After the Lote-3 R1 migration:
    - All 10 Pattern A inline expressions have been replaced by project_root() calls.
      The count of the OLD Pattern A literal is now 0; the 10 sites are tracked
      instead by test_pattern_a_literal_present_in_source (which checks for the
      project_root() call and import).
    - Pattern A' (1 site, model_router:321) is unchanged — different default.
    - Pattern C (2 sites) is unchanged — different semantics.
    - Pattern D (1 site, telemetry) is unchanged — reversed precedence.
    """
    counts: dict[str, int] = {"A": 0, "A_prime": 0, "C": 0, "D": 0}
    for relpath in [
        "lib/dispatch_helper.py",
        "lib/dispatch_model_advisor.py",
        "lib/rate_limiter.py",
        "lib/sdd_pipeline.py",
        "lib/queue_drainer.py",
        "lib/agent_health_monitor.py",
        "lib/model_router.py",
        "hooks/_lib/dispatch_gate_check.py",
        "lib/telemetry.py",
    ]:
        src = (REPO_ROOT / relpath).read_text()
        counts["A"] += src.count(PATTERN_A_LITERAL) + src.count(PATTERN_A_LITERAL_INDENTED)
        counts["A_prime"] += src.count(PATTERN_A_PRIME_LITERAL)
        counts["C"] += src.count(PATTERN_C_LITERAL)
        # Pattern D detection is the reversed precedence in telemetry only.
        if relpath == "lib/telemetry.py":
            cog_idx = src.find('os.environ.get("COGNITIVE_OS_PROJECT_DIR")')
            claude_idx = src.find('os.environ.get("CLAUDE_PROJECT_DIR")')
            if cog_idx >= 0 and claude_idx >= 0 and cog_idx < claude_idx:
                counts["D"] += 1

    # After R1 migration: Pattern A inline literals are 0 (migrated to project_root()).
    # Pattern A', C, D outliers are unchanged.
    assert counts == {"A": 0, "A_prime": 1, "C": 2, "D": 1}, (
        f"Audit count drift: {counts}. Expected 0+1+2+1 after R1 migration. "
        "Pattern A sites (10) now use project_root() from lib.paths — "
        "the inline expression count should be 0. If a site reverted to inline "
        "or a new site was added, update this assertion explicitly."
    )


# ─────────────────────────────────────────────────────────────────────────
# Section 5 — lib.paths.project_root() matches Pattern A semantics exactly
# ─────────────────────────────────────────────────────────────────────────


class TestLibPathsProjectRoot:
    """``lib.paths.project_root()`` must match Pattern A semantics exactly.

    These assertions mirror ``TestPatternA`` (Section 1) but call
    ``project_root()`` instead of the inline ``_pattern_a()`` helper.
    If ``project_root()`` ever diverges from Pattern A, these tests surface it.
    """

    def test_both_unset_returns_none(self, monkeypatch):
        """Both env vars absent → None (falsy, matches Pattern A '' default)."""
        from lib.paths import project_root

        _clear_env(monkeypatch)
        assert project_root() is None

    def test_claude_only_returns_path(self, monkeypatch):
        from lib.paths import project_root

        _clear_env(monkeypatch)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/from-claude")
        result = project_root()
        assert result is not None
        assert result == Path("/from-claude")

    def test_cognitive_os_only_returns_path(self, monkeypatch):
        from lib.paths import project_root

        _clear_env(monkeypatch)
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", "/from-cognitive-os")
        result = project_root()
        assert result is not None
        assert result == Path("/from-cognitive-os")

    def test_both_set_claude_wins(self, monkeypatch):
        from lib.paths import project_root

        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/claude")
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", "/cognitive")
        result = project_root()
        assert result == Path("/claude")

    def test_claude_empty_string_falls_back(self, monkeypatch):
        """``""`` is falsy → ``or`` falls through to COGNITIVE_OS_PROJECT_DIR."""
        from lib.paths import project_root

        _clear_env(monkeypatch)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "")
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", "/fallback")
        result = project_root()
        assert result == Path("/fallback")

    def test_both_empty_returns_none(self, monkeypatch):
        from lib.paths import project_root

        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "")
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", "")
        assert project_root() is None

    def test_returns_pathlib_path_not_str(self, monkeypatch):
        from lib.paths import project_root

        _clear_env(monkeypatch)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/some/dir")
        result = project_root()
        assert isinstance(result, Path), f"Expected Path, got {type(result)!r}"

    def test_idempotent(self, monkeypatch):
        """Repeated calls with the same env vars return equal paths."""
        from lib.paths import project_root

        _clear_env(monkeypatch)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/stable")
        assert project_root() == project_root()

    def test_truthy_when_configured(self, monkeypatch):
        """Callers rely on ``if project_dir:`` — must be truthy when set."""
        from lib.paths import project_root

        _clear_env(monkeypatch)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/some/path")
        assert project_root()  # truthy

    def test_falsy_when_not_configured(self, monkeypatch):
        """Callers rely on ``if project_dir:`` — must be falsy (None) when unset."""
        from lib.paths import project_root

        _clear_env(monkeypatch)
        result = project_root()
        assert not result  # None is falsy
