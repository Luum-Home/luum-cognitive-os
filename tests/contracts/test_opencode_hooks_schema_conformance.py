"""Conformance of the OpenCode projection against the PUBLISHED OpenCode contract.

This is deliberately not a test of the driver against itself. The assertions read
``manifests/opencode-hooks-schema.yaml`` — a transcription of the upstream docs
and of the upstream ``Hooks`` interface, with source URLs and verification dates
recorded in the file — and check that what the driver emits and what the plugin
classifies are things OpenCode would actually honour.

Sibling of ``test_codex_hooks_schema_conformance.py``; same contract, different
harness. It exists because the pre-existing OpenCode contract test
(``test_opencode_native_adapter_design.py``) asserts that a design DOC repeats
the same identifiers the driver invented — a closed loop that cannot detect a
wrong identifier.

Known, currently-unrepaired gaps are encoded as ``xfail(strict=True)`` keyed to
``known_projection_gaps`` ids in the manifest. That way the defect is executable
(not a bullet in a report), and closing it turns the suite red until the manifest
is updated to match.

Run:
    python3 -m pytest tests/contracts/test_opencode_hooks_schema_conformance.py -q
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPO_ROOT / "manifests" / "opencode-hooks-schema.yaml"
DRIVER = REPO_ROOT / "scripts" / "_lib" / "settings-driver-opencode.sh"
PLUGIN = REPO_ROOT / "packages" / "opencode-adapter" / "plugins" / "cos-primitive-guard.js"
PROJECTION = REPO_ROOT / ".opencode" / "cos-hooks.json"
CONFIG = REPO_ROOT / "opencode.json"


def _schema() -> dict:
    assert MANIFEST.exists(), f"missing published-schema manifest: {MANIFEST}"
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))


SCHEMA = _schema()
GAP_IDS = {g["id"] for g in SCHEMA.get("known_projection_gaps", [])}


def gap(gap_id: str, reason: str):
    """xfail keyed to a manifest gap id, so the two cannot drift apart."""
    assert gap_id in GAP_IDS, f"unknown gap id {gap_id!r}; add it to {MANIFEST.name}"
    return pytest.mark.xfail(strict=True, reason=f"[{gap_id}] {reason}")


def _run(snippet: str) -> dict:
    out = subprocess.run(
        ["bash", "-c", f'source "{DRIVER}" >/dev/null 2>&1; {snippet}'],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert out.returncode == 0, f"driver failed: {out.stderr[-2000:]}"
    return json.loads(out.stdout)


def _emit_projection() -> dict:
    return _run("opencode_driver_emit")


def _emit_config() -> dict:
    return _run("opencode_config_emit")


PROJECTION_PRODUCERS = {
    "settings-driver-opencode.sh": _emit_projection,
    ".opencode/cos-hooks.json (checked-in)": lambda: json.loads(
        PROJECTION.read_text(encoding="utf-8")
    ),
}

CONFIG_PRODUCERS = {
    "settings-driver-opencode.sh": _emit_config,
    "opencode.json (checked-in)": lambda: json.loads(CONFIG.read_text(encoding="utf-8")),
}


def _plugin_source() -> str:
    return PLUGIN.read_text(encoding="utf-8")


def _plugin_tool_names() -> set[str]:
    """Tool identifiers the plugin's classifiers compare against."""
    src = _plugin_source()
    names = set(re.findall(r'toolName\s*===\s*"([^"]+)"', src))
    for arr in re.findall(r'\[([^\]]*)\]\.includes\(toolName\)', src):
        names |= set(re.findall(r'"([^"]+)"', arr))
    return names


def _plugin_write_gated_tools() -> set[str]:
    """Tool identifiers guarding the write-side classifier branch."""
    src = _plugin_source()
    arrays = re.findall(r'\[([^\]]*)\]\.includes\(toolName\)', src)
    for arr in arrays:
        names = set(re.findall(r'"([^"]+)"', arr))
        if {"write", "edit"} & names:
            return names
    return set()


# ── The manifest itself must stay auditable ──────────────────────────────────
def test_manifest_cites_its_sources():
    """A schema manifest with no cited source is one agent's memory, not a contract."""
    cited = [s for s in SCHEMA.get("sources") or [] if s.get("url")]
    assert cited, "manifest must cite at least one upstream URL"
    for src in cited:
        assert src.get("verified"), f"source {src['url']} has no verification date"


# ── opencode.json shape ──────────────────────────────────────────────────────
@pytest.mark.parametrize("producer", sorted(CONFIG_PRODUCERS))
def test_config_top_level_keys_are_published(producer):
    allowed = set(SCHEMA["config_file"]["allowed_top_level_keys_used_by_cos"])
    data = CONFIG_PRODUCERS[producer]()
    unknown = sorted(set(data) - allowed)
    assert not unknown, (
        f"{producer}: top-level keys not in the published opencode.json schema: "
        f"{unknown} (the schema sets additionalProperties: false)"
    )


@pytest.mark.parametrize("producer", sorted(CONFIG_PRODUCERS))
def test_permission_keys_are_published_tools(producer):
    allowed = set(SCHEMA["config_file"]["permission"]["allowed_keys"])
    data = CONFIG_PRODUCERS[producer]()
    unknown = sorted(set(data.get("permission") or {}) - allowed)
    assert not unknown, f"{producer}: permission keys are not OpenCode tools: {unknown}"


@gap(
    "experimental-cognitive-os-hooks-stripped",
    "`experimental` is a closed object upstream; cognitive_os_hooks is dropped at load",
)
@pytest.mark.parametrize("producer", sorted(CONFIG_PRODUCERS))
def test_experimental_keys_are_published(producer):
    allowed = set(SCHEMA["config_file"]["experimental"]["allowed_keys"])
    data = CONFIG_PRODUCERS[producer]()
    unknown = sorted(set(data.get("experimental") or {}) - allowed)
    assert not unknown, (
        f"{producer}: experimental keys {unknown} are not in the published schema; "
        "OpenCode strips them silently, so the declaration is inert"
    )


def test_plugin_directory_matches_published_autoload_path():
    expected = SCHEMA["plugin_directory"]["project"].rstrip("/")
    src = DRIVER.read_text(encoding="utf-8")
    assert f"{expected}/" in src or expected in src, (
        f"driver does not install the plugin into the published autoload dir {expected}"
    )


# ── Projection bucket names ──────────────────────────────────────────────────
@pytest.mark.parametrize("producer", sorted(PROJECTION_PRODUCERS))
def test_only_published_surface_names(producer):
    surfaces = set(SCHEMA["surfaces"])
    data = PROJECTION_PRODUCERS[producer]()
    unknown = sorted(set(data.get("events") or {}) - surfaces)
    assert not unknown, (
        f"{producer}: projection buckets named after surfaces OpenCode does not "
        f"publish: {unknown}"
    )


@gap(
    "user-prompt-submit-mapped-to-tui-event",
    "UserPromptSubmit is bucketed under tui.prompt.append, a TUI widget event",
)
@pytest.mark.parametrize("producer", sorted(PROJECTION_PRODUCERS))
def test_populated_buckets_target_lifecycle_surfaces(producer):
    """A bucket named after a non-lifecycle surface is a silent no-op."""
    surfaces = SCHEMA["surfaces"]
    data = PROJECTION_PRODUCERS[producer]()
    offenders = sorted(
        name
        for name, hooks in (data.get("events") or {}).items()
        if hooks and surfaces.get(name, {}).get("usable_as") == "none"
    )
    assert not offenders, (
        f"{producer}: hooks projected onto non-lifecycle surfaces {offenders} — "
        "nothing subscribes to them, so every hook in those buckets is inert"
    )


@pytest.mark.parametrize("producer", sorted(PROJECTION_PRODUCERS))
def test_tool_events_stay_native_only(producer):
    """Latency policy: tool-call governance is inline in the plugin, not projected.

    Guards the documented decision rather than second-guessing it: if these
    buckets ever fill up, 130+ bash spawns land on every tool call.
    """
    data = PROJECTION_PRODUCERS[producer]()
    for name in ("tool.execute.before", "tool.execute.after"):
        assert not (data.get("events") or {}).get(name), (
            f"{producer}: {name} carries script projections; the driver's stated "
            "latency policy says tool-call governance is native-only"
        )


# ── Plugin-side tool identifiers ─────────────────────────────────────────────
@gap(
    "agent-family-classifiers-unreachable",
    'plugin classifies on toolName === "agent" / "multiedit"; neither is an OpenCode tool',
)
def test_plugin_classifies_only_published_tool_ids():
    published = set(SCHEMA["tools"]["published_ids"])
    used = _plugin_tool_names()
    unknown = sorted(used - published)
    assert not unknown, (
        f"cos-primitive-guard.js branches on tool ids OpenCode never emits: "
        f"{unknown} — every guard behind them is unreachable code"
    )


@gap(
    "no-write-coverage-on-apply-patch",
    "write-side classifier enumerates write/edit/multiedit; apply_patch is unguarded",
)
def test_write_side_guards_cover_every_file_mutating_tool():
    """The Codex regression, re-armed for OpenCode: zero coverage on the patch tool."""
    mutating = {t["id"] for t in SCHEMA["tools"]["file_mutating"]}
    gated = _plugin_write_gated_tools()
    assert gated, "could not locate the write-side classifier branch in the plugin"
    missing = sorted(mutating - gated)
    assert not missing, (
        f"file-mutating tools with no write-side guard: {missing} — "
        "secret-detector and protected-config-write-guard cannot fire on them"
    )


def test_manifest_gap_ids_are_all_exercised():
    """Every recorded gap must be reachable from a test, or it is just prose."""
    src = Path(__file__).read_text(encoding="utf-8")
    unexercised = sorted(g for g in GAP_IDS if f'"{g}"' not in src)
    documented_only = {"permission-ask-unused", "no-subagent-budget-enforcer"}
    assert set(unexercised) <= documented_only, (
        f"gaps recorded in the manifest with no executable check: "
        f"{sorted(set(unexercised) - documented_only)}"
    )
