# SCOPE: os-only
"""Portability proof for the scripts/_lib/settings-driver* family.

Covers five primitives:

  - scripts/_lib/settings-driver.sh              (shared harness resolver)
  - scripts/_lib/settings-driver-bare.sh         (bare-CLI projection)
  - scripts/_lib/settings-driver-claude-code.sh  (Claude Code projection)
  - scripts/_lib/settings-driver-codex.sh        (Codex projection)
  - scripts/_lib/settings-driver-opencode.sh     (OpenCode projection)

The decision under proof is *harness discrimination*: given one hook registry,
each driver must emit the configuration shape of ITS harness, drop the events
its harness cannot serve, and never emit another harness's shape. None of the
four answers below is read out of the primitive itself -- every assertion runs
the driver over a synthetic `cognitive-os.yaml` fixture and inspects generated
JSON.

  trigger        : each driver runs on the fixture and produces parseable,
                   harness-shaped configuration.
  discriminator  : every driver's output is accepted by its own shape predicate
                   and REJECTED by the other three; the Codex profile branch and
                   all 22 `cos_settings_driver_relpath` branches are instantiated.
  null control   : events a harness does not support are absent from its output
                   (Codex/bare/OpenCode never project SubagentStart; bare never
                   projects PreCompact; OpenCode never projects tool-call
                   scripts; Codex never emits an `async` key), and an empty
                   project directory yields the documented default, not an error.
  mutant probe   : the SubagentStart async contract is re-run against a mutated
                   COPY of the Claude Code driver, which must fail the same
                   assertion the real driver passes.

Safety: no test writes into the repository. `--emit` (Claude Code) and the
sourced `*_driver_emit` functions print to stdout; every invocation is pinned to
a `tmp_path` PROJECT_DIR, so the operator's live `.claude/settings.json` is never
regenerated.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
LIB = REPO_ROOT / "scripts" / "_lib"

SHARED_DRIVER = LIB / "settings-driver.sh"
CC_DRIVER = LIB / "settings-driver-claude-code.sh"
CODEX_DRIVER = LIB / "settings-driver-codex.sh"
BARE_DRIVER = LIB / "settings-driver-bare.sh"
OPENCODE_DRIVER = LIB / "settings-driver-opencode.sh"

TIMEOUT = 120

# The synthetic hook registry. Each entry exists to instantiate one branch of a
# driver decision, so a driver that stopped discriminating would change output.
FIXTURE_YAML = """\
harness:
  hooks:
    probe-session:
      event: SessionStart
      script: hooks/probe-session.sh
      matcher: ""
      async: false
      scope: os-only
    probe-daemon-launcher:
      event: SessionStart
      script: hooks/probe-daemon-launcher.sh
      async: false
      scope: os-only
    probe-prompt:
      event: UserPromptSubmit
      script: hooks/probe-prompt.sh
      async: true
      scope: both
    bash-hot-path-dispatcher:
      event: PreToolUse
      matcher: Bash
      script: hooks/bash-hot-path-dispatcher.sh
      async: false
      scope: os-only
    probe-bash-guard:
      event: PreToolUse
      matcher: Bash
      script: hooks/probe-bash-guard.sh
      async: false
      scope: os-only
    probe-write-guard:
      event: PreToolUse
      matcher: Edit|Write
      script: hooks/probe-write-guard.sh
      async: false
      scope: os-only
    probe-post-bash:
      event: PostToolUse
      matcher: Bash
      script: hooks/probe-post-bash.sh
      async: false
      scope: os-only
    probe-stop:
      event: Stop
      script: hooks/probe-stop.sh
      async: false
      scope: os-only
    probe-subagent:
      event: SubagentStart
      script: hooks/probe-subagent.sh
      async: false
      scope: os-only
    probe-precompact:
      event: PreCompact
      script: hooks/probe-precompact.sh
      async: false
      scope: os-only
    probe-without-script:
      event: SessionStart
      script: ""
      async: false
      scope: os-only
"""


# ── helpers ───────────────────────────────────────────────────────────────────


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "probe-project"
    root.mkdir(parents=True, exist_ok=True)
    (root / "cognitive-os.yaml").write_text(FIXTURE_YAML, encoding="utf-8")
    return root


def _env(project_dir: Path, **extra: str) -> dict[str, str]:
    env = os.environ.copy()
    env["PROJECT_DIR"] = str(project_dir)
    env.pop("COGNITIVE_OS_HARNESS", None)
    env.pop("COGNITIVE_OS_HOOK_REGISTRY_PROJECT_DIR", None)
    env.update(extra)
    return env


def _run(argv: list[str], project_dir: Path, **extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=str(project_dir),
        env=_env(project_dir, **extra),
        text=True,
        capture_output=True,
        timeout=TIMEOUT,
        check=False,
    )


def _emit_sourced(driver: Path, func: str, project_dir: Path, **extra: str) -> dict:
    """Source a driver and call its emit function without triggering its writer."""
    # The single empty argument keeps the drivers' `for arg in "$@"` loop safe
    # under bash 3.2 `set -u`, and matches no flag branch.
    script = f'source "{driver}" ""\n{func}\n'
    result = _run(["bash", "-c", script], project_dir, **extra)
    assert result.returncode == 0, f"{driver.name}::{func} failed: {result.stderr}"
    return json.loads(result.stdout)


def _emit_claude_code(project_dir: Path, driver: Path = CC_DRIVER, **extra: str) -> dict:
    result = _run(["bash", str(driver), "--emit"], project_dir, **extra)
    assert result.returncode == 0, f"{driver.name} --emit failed: {result.stderr}"
    return json.loads(result.stdout)


def _scripts_in(payload: object) -> set[str]:
    """Every hooks/*.sh path mentioned anywhere in a generated configuration."""
    blob = json.dumps(payload)
    found = set()
    for token in blob.replace('"', " ").replace("\\", " ").split():
        if token.startswith("hooks/") and token.endswith(".sh"):
            found.add(token)
        elif "/hooks/" in token and token.endswith(".sh"):
            found.add("hooks/" + token.split("/hooks/", 1)[1])
    return found


# Shape predicates. Each returns True only for its own harness's projection.
def _is_claude_code_shape(payload: object) -> bool:
    return (
        isinstance(payload, dict)
        and isinstance(payload.get("hooks"), dict)
        and "SubagentStart" in payload["hooks"]
        and "permissions" in payload
        and "$CLAUDE_PROJECT_DIR" in json.dumps(payload)
    )


def _is_codex_shape(payload: object) -> bool:
    if not isinstance(payload, dict) or not isinstance(payload.get("hooks"), dict):
        return False
    if "permissions" in payload or "schema_version" in payload:
        return False
    return "COGNITIVE_OS_HARNESS=codex" in json.dumps(payload)


def _is_bare_shape(payload: object) -> bool:
    return (
        isinstance(payload, dict)
        and payload.get("harness") == "bare_cli"
        and isinstance(payload.get("events"), dict)
        and "session_start" in payload["events"]
    )


def _is_opencode_shape(payload: object) -> bool:
    return (
        isinstance(payload, dict)
        and payload.get("harness") == "opencode"
        and isinstance(payload.get("events"), dict)
        and "session.created" in payload["events"]
    )


SHAPES = {
    "claude-code": _is_claude_code_shape,
    "codex": _is_codex_shape,
    "bare": _is_bare_shape,
    "opencode": _is_opencode_shape,
}


# ── settings-driver.sh: the shared resolver ───────────────────────────────────

# Every branch of cos_settings_driver_relpath, plus the default arm. The gate is
# that the resolver DISCRIMINATES: an unknown harness must fall back to Claude
# Code, and no two structurally different harnesses may share a driver path by
# accident.
RELPATH_CASES = [
    ("claude", ".claude/settings.json"),
    ("codex", ".codex/hooks.json"),
    ("agents-md", "AGENTS.md"),
    ("opencode", "opencode.json"),
    ("vscode-copilot", ".github/copilot-instructions.md"),
    ("cursor", ".cursor/rules/cognitive-os.mdc"),
    ("qwen-code", ".qwen/settings.json"),
    ("kimi-code", "AGENTS.md"),
    ("gemini-cli", ".gemini/settings.json"),
    ("warp", "AGENTS.md"),
    ("amp-code", "AGENTS.md"),
    ("jetbrains-junie", ".junie/AGENTS.md"),
    ("qoder", "AGENTS.md"),
    ("factory-droid", "AGENTS.md"),
    ("cline", ".clinerules/cognitive-os.md"),
    ("continue-dev", ".continue/rules/cognitive-os.md"),
    ("kilo-code", ".kilocode/rules/cognitive-os.md"),
    ("zed-ai", ".rules"),
    ("augment-code", ".augment/rules/cognitive-os.md"),
    ("goose", ".goosehints"),
    ("aider", "CONVENTIONS.md"),
    ("shell-ci", ".cognitive-os/shell-ci-projection.json"),
    # null control: an unknown harness must not invent a path.
    ("not-a-harness", ".claude/settings.json"),
    ("", ".claude/settings.json"),
]


def test_shared_driver_resolves_every_declared_harness_path(tmp_path: Path) -> None:
    """settings-driver.sh maps each harness id to its own projection path."""
    project = _project(tmp_path)
    queries = "\n".join(
        f'printf "%s\\t%s\\n" "{harness}" "$(cos_settings_driver_relpath "{harness}")"'
        for harness, _ in RELPATH_CASES
    )
    result = _run(
        ["bash", "-c", f'source "{SHARED_DRIVER}"\n{queries}\n'],
        project,
    )
    assert result.returncode == 0, result.stderr
    got = dict(line.split("\t", 1) for line in result.stdout.strip().splitlines())
    assert got == {harness: expected for harness, expected in RELPATH_CASES}


DETECT_CASES = [
    # (files to create, extra env, expected harness, why)
    ({}, {}, "claude", "empty project falls back to claude"),
    ({".codex/hooks.json": "{}"}, {}, "codex", "codex marker alone"),
    ({".claude/settings.json": "{}"}, {}, "claude", "claude marker alone"),
    (
        {".claude/settings.json": "{}", ".codex/hooks.json": "{}"},
        {"CODEX_PROJECT_DIR": "/somewhere"},
        "codex",
        "ambiguous markers resolved by codex env hint",
    ),
    (
        {".claude/settings.json": "{}"},
        {"COGNITIVE_OS_HARNESS": "opencode"},
        "opencode",
        "explicit env overrides on-disk markers",
    ),
]


@pytest.mark.parametrize("files,extra,expected,why", DETECT_CASES)
def test_shared_driver_detects_harness_from_project_state(
    tmp_path: Path, files: dict, extra: dict, expected: str, why: str
) -> None:
    """cos_detect_harness decides from real on-disk state, not from its own text."""
    project = _project(tmp_path)
    for rel, body in files.items():
        target = project / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    result = _run(
        ["bash", "-c", f'source "{SHARED_DRIVER}"\ncos_detect_harness "{project}"\n'],
        project,
        **extra,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == expected, why


def test_shared_driver_install_meta_outranks_markers_and_rejects_garbage(tmp_path: Path) -> None:
    """install-meta.json is the durable source of truth, but only for known ids."""
    if shutil.which("jq") is None:
        pytest.skip("jq unavailable; install-meta branch is jq-gated by design")
    project = _project(tmp_path)
    (project / ".claude").mkdir(parents=True, exist_ok=True)
    (project / ".claude" / "settings.json").write_text("{}", encoding="utf-8")
    meta = project / ".cognitive-os" / "install-meta.json"
    meta.parent.mkdir(parents=True, exist_ok=True)

    meta.write_text(json.dumps({"harness": "opencode"}), encoding="utf-8")
    result = _run(
        ["bash", "-c", f'source "{SHARED_DRIVER}"\ncos_detect_harness "{project}"\n'], project
    )
    assert result.stdout.strip() == "opencode"

    # Null control: an unrecognised harness in metadata must not be echoed back.
    meta.write_text(json.dumps({"harness": "totally-made-up"}), encoding="utf-8")
    result = _run(
        ["bash", "-c", f'source "{SHARED_DRIVER}"\ncos_detect_harness "{project}"\n'], project
    )
    assert result.stdout.strip() == "claude"


# ── generator drivers: shape, coverage and drop sets ──────────────────────────


def test_bare_driver_projects_only_bare_cli_supported_events(tmp_path: Path) -> None:
    """Bare-CLI keeps its five canonical events and drops what it cannot serve."""
    project = _project(tmp_path)
    payload = _emit_sourced(BARE_DRIVER, "bare_driver_emit", project)

    assert payload["harness"] == "bare_cli"
    assert list(payload["events"]) == [
        "session_start",
        "user_prompt_submit",
        "tool_use_start",
        "tool_use_end",
        "session_end",
    ]
    assert {e["script"] for e in payload["events"]["session_start"]} == {
        "hooks/probe-session.sh",
        "hooks/probe-daemon-launcher.sh",
    }
    assert [e["script"] for e in payload["events"]["session_end"]] == ["hooks/probe-stop.sh"]
    # Bare-CLI does no Bash hot-path thinning: both PreToolUse hooks project.
    assert {e["script"] for e in payload["events"]["tool_use_start"]} == {
        "hooks/bash-hot-path-dispatcher.sh",
        "hooks/probe-bash-guard.sh",
        "hooks/probe-write-guard.sh",
    }

    scripts = _scripts_in(payload)
    # Null control: unsupported events and script-less entries never appear.
    assert "hooks/probe-subagent.sh" not in scripts
    assert "hooks/probe-precompact.sh" not in scripts
    assert "probe-without-script" not in json.dumps(payload)


def test_opencode_driver_keeps_precompact_and_never_projects_tool_scripts(tmp_path: Path) -> None:
    """OpenCode's drop set differs from bare-CLI's: PreCompact in, tool calls out."""
    project = _project(tmp_path)
    payload = _emit_sourced(OPENCODE_DRIVER, "opencode_driver_emit", project)

    assert payload["harness"] == "opencode"
    assert [e["script"] for e in payload["events"]["experimental.session.compacting"]] == [
        "hooks/probe-precompact.sh"
    ]
    assert payload["events"]["session.compacted"] == payload["events"][
        "experimental.session.compacting"
    ]
    # Null control: tool-call events stay present but empty (the plugin enforces
    # them natively); projecting them would add a bash spawn per tool call.
    assert payload["events"]["tool.execute.before"] == []
    assert payload["events"]["tool.execute.after"] == []

    scripts = _scripts_in(payload)
    assert "hooks/probe-bash-guard.sh" not in scripts
    assert "hooks/probe-write-guard.sh" not in scripts
    assert "hooks/probe-subagent.sh" not in scripts

    # Behavioural decision, not a copy of the registry: the fixture declares the
    # launcher async:false, and the driver forces it true so the plugin never
    # runs a daemon launcher on its blocking spawnSync path.
    by_id = {e["id"]: e for e in payload["events"]["session.created"]}
    assert by_id["probe-daemon-launcher"]["async"] is True
    assert by_id["probe-session"]["async"] is False


def test_codex_driver_translates_matchers_and_omits_unsupported_keys(tmp_path: Path) -> None:
    """Codex matchers are tool-name regexes; matcherless events carry no key."""
    project = _project(tmp_path)
    payload = _emit_sourced(CODEX_DRIVER, "codex_driver_emit", project)

    assert list(payload["hooks"]) == [
        "SessionStart",
        "UserPromptSubmit",
        "PreToolUse",
        "PostToolUse",
        "Stop",
    ]
    assert [g["matcher"] for g in payload["hooks"]["SessionStart"]] == ["startup"]
    # Matcherless events must not carry the key at all -- the invented
    # "prompt"/"shutdown" matchers matched nothing.
    for event in ("UserPromptSubmit", "Stop"):
        for group in payload["hooks"][event]:
            assert "matcher" not in group, event

    pre = {g.get("matcher"): g for g in payload["hooks"]["PreToolUse"]}
    assert set(pre) == {"^Bash$", "^apply_patch$"}
    # Edit|Write has no Codex equivalent and must land on apply_patch.
    assert _scripts_in(pre["^apply_patch$"]) == {"hooks/probe-write-guard.sh"}

    blob = json.dumps(payload)
    # Null controls: Codex parses but does not honour "async", and never
    # receives SubagentStart / PreCompact.
    assert '"async"' not in blob
    assert "SubagentStart" not in blob
    assert "PreCompact" not in blob
    assert "hooks/probe-subagent.sh" not in _scripts_in(payload)


def test_codex_driver_bash_hot_path_flips_with_profile(tmp_path: Path) -> None:
    """Both arms of the PROFILE decision are instantiated on the same registry."""
    project = _project(tmp_path)

    default_payload = _emit_sourced(CODEX_DRIVER, "codex_driver_emit", project, PROFILE="maintainer")
    full_payload = _emit_sourced(CODEX_DRIVER, "codex_driver_emit", project, PROFILE="full")

    def bash_scripts(payload: dict) -> set[str]:
        for group in payload["hooks"]["PreToolUse"]:
            if group.get("matcher") == "^Bash$":
                return _scripts_in(group)
        return set()

    assert bash_scripts(default_payload) == {"hooks/bash-hot-path-dispatcher.sh"}
    assert bash_scripts(full_payload) == {"hooks/probe-bash-guard.sh"}
    # apply_patch guards are never thinned by profile.
    for payload in (default_payload, full_payload):
        apply_patch = [
            g for g in payload["hooks"]["PreToolUse"] if g.get("matcher") == "^apply_patch$"
        ]
        assert _scripts_in(apply_patch) == {"hooks/probe-write-guard.sh"}


# ── the SubagentStart async contract (ADR-anchored) ───────────────────────────


def _subagent_entries(payload: dict) -> list[dict]:
    entries: list[dict] = []
    for group in payload["hooks"]["SubagentStart"]:
        for hook in group["hooks"]:
            if "subagent-context-injector.sh" in hook.get("command", ""):
                entries.append(hook)
    return entries


def test_claude_code_driver_registers_subagent_injector_synchronously(tmp_path: Path) -> None:
    """SubagentStart must be synchronous or its payload reaches no sub-agent.

    Async hook output is delivered on the NEXT conversation turn, which for a
    sub-agent never comes: registered async, this hook emitted a correct 10 KB
    payload that reached 0 of 149 sub-agent transcripts (2026-08-15). The flag is
    NOT read from cognitive-os.yaml, so the driver is the only place the contract
    can be enforced -- which is why this assertion runs the driver instead of
    reading the comment that documents it.
    """
    project = _project(tmp_path)
    payload = _emit_claude_code(project)

    entries = _subagent_entries(payload)
    assert entries, "SubagentStart lost its context injector registration"
    for hook in entries:
        assert hook.get("async") is None, f"subagent-context-injector must stay sync: {hook}"

    # Discriminating control: the same driver DOES emit async hooks elsewhere, so
    # the absent flag above is a decision, not an inability.
    async_commands = [
        hook
        for group in payload["hooks"]["SessionStart"]
        for hook in group["hooks"]
        if hook.get("async") is True
    ]
    assert async_commands, "driver never emits async:true; the sync assertion proves nothing"


def test_mutated_claude_code_driver_fails_the_subagent_contract(tmp_path: Path) -> None:
    """Falsification probe: break the contract in a COPY and the check must fire."""
    mutant = tmp_path / "settings-driver-claude-code.sh"
    original = CC_DRIVER.read_text(encoding="utf-8")
    mutated = original.replace(
        '"hooks/subagent-context-injector.sh" "false"',
        '"hooks/subagent-context-injector.sh" "true"',
        1,
    )
    assert mutated != original, "mutation anchor missing; the probe would be vacuous"
    mutant.write_text(mutated, encoding="utf-8")

    project = _project(tmp_path)
    payload = _emit_claude_code(project, driver=mutant)

    entries = _subagent_entries(payload)
    assert entries
    assert any(hook.get("async") is True for hook in entries), (
        "mutant produced a synchronous registration; the contract assertion is not "
        "sensitive to the flag it claims to protect"
    )


# ── cross-driver discrimination and repo safety ───────────────────────────────


def test_each_driver_emits_only_its_own_harness_shape(tmp_path: Path) -> None:
    """One registry, four harnesses: no driver may produce another's shape."""
    project = _project(tmp_path)
    payloads = {
        "claude-code": _emit_claude_code(project),
        "codex": _emit_sourced(CODEX_DRIVER, "codex_driver_emit", project),
        "bare": _emit_sourced(BARE_DRIVER, "bare_driver_emit", project),
        "opencode": _emit_sourced(OPENCODE_DRIVER, "opencode_driver_emit", project),
    }
    for name, payload in payloads.items():
        for shape_name, predicate in SHAPES.items():
            expected = shape_name == name
            assert predicate(payload) is expected, (
                f"{name} output was {'rejected by' if expected else 'accepted as'} "
                f"the {shape_name} shape"
            )


def test_emit_paths_write_nothing_into_the_project(tmp_path: Path) -> None:
    """Null control: emitting must never regenerate a live settings file."""
    project = _project(tmp_path)
    before = sorted(p.relative_to(project).as_posix() for p in project.rglob("*"))

    _emit_claude_code(project)
    _emit_sourced(CODEX_DRIVER, "codex_driver_emit", project)
    _emit_sourced(BARE_DRIVER, "bare_driver_emit", project)
    _emit_sourced(OPENCODE_DRIVER, "opencode_driver_emit", project)

    after = sorted(p.relative_to(project).as_posix() for p in project.rglob("*"))
    assert after == before, f"driver emit created files: {set(after) - set(before)}"
