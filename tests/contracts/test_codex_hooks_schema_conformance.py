"""Conformance of the Codex projection against the PUBLISHED Codex schema.

This is deliberately not a test of the driver against itself. The assertions
read ``manifests/codex-hooks-schema.yaml`` — a transcription of the upstream
Codex docs with the source URLs and verification date recorded in the file —
and check that what the driver emits is something Codex would actually accept.

If Codex changes its contract, the manifest is the single place to update and
these tests start failing on their own. If the driver drifts, these tests fail
without the manifest moving.

Covered: the mandatory ``hooks`` root namespace, valid event names, which events
may carry a matcher, matcher semantics (tool-name regex vs enum), allowed
handler fields, and the write-side (``apply_patch``) coverage floor.

Run:
    python3 -m pytest tests/contracts/test_codex_hooks_schema_conformance.py -q
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPO_ROOT / "manifests" / "codex-hooks-schema.yaml"
DRIVER = REPO_ROOT / "scripts" / "_lib" / "settings-driver-codex.sh"
GENERATOR = REPO_ROOT / "scripts" / "generate-project-settings.sh"
PROJECTION = REPO_ROOT / ".codex" / "hooks.json"


@pytest.fixture(scope="module")
def schema() -> dict:
    assert MANIFEST.exists(), f"missing published-schema manifest: {MANIFEST}"
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))


def _emit_driver() -> dict:
    """Run the driver's emitter and return the parsed projection."""
    out = subprocess.run(
        ["bash", "-c", f'source "{DRIVER}" >/dev/null 2>&1; codex_driver_emit'],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert out.returncode == 0, f"driver failed: {out.stderr[-2000:]}"
    return json.loads(out.stdout)


def _emit_generator() -> dict:
    out = subprocess.run(
        ["bash", str(GENERATOR), "--harness", "codex", "--default"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert out.returncode == 0, f"generator failed: {out.stderr[-2000:]}"
    return json.loads(out.stdout)


def _sources() -> list[dict]:
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))["sources"]


# Every producer of a Codex hooks file must satisfy the same schema.
PRODUCERS = {
    "settings-driver-codex.sh": _emit_driver,
    "generate-project-settings.sh --harness codex": _emit_generator,
    ".codex/hooks.json (checked-in projection)": lambda: json.loads(
        PROJECTION.read_text(encoding="utf-8")
    ),
}


# ── The manifest itself must stay auditable ──────────────────────────────────
def test_manifest_cites_its_sources(schema):
    """A schema manifest with no cited source is one agent's memory, not a contract."""
    sources = schema.get("sources") or []
    cited = [s for s in sources if s.get("url")]
    assert cited, "manifest must cite at least one upstream URL"
    for src in cited:
        assert src.get("verified"), f"source {src['url']} has no verification date"


# ── Root namespace ───────────────────────────────────────────────────────────
@pytest.mark.parametrize("producer", sorted(PRODUCERS))
def test_root_hooks_namespace_present(producer, schema):
    """Without the top-level `hooks` key Codex ignores the whole file."""
    root_key = schema["file"]["root_key"]
    if not schema["file"].get("root_key_required"):
        pytest.skip("manifest no longer requires the root namespace")
    data = PRODUCERS[producer]()
    assert root_key in data, (
        f"{producer}: missing mandatory top-level '{root_key}' namespace — "
        "Codex would not parse this file as a hook registry, leaving every "
        "projected guard inert"
    )
    assert isinstance(data[root_key], dict)


# ── Event names ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize("producer", sorted(PRODUCERS))
def test_only_published_event_names(producer, schema):
    data = PRODUCERS[producer]()[schema["file"]["root_key"]]
    unknown = sorted(set(data) - set(schema["events"]))
    assert not unknown, f"{producer}: events not in the published Codex schema: {unknown}"


# ── Matcher support ──────────────────────────────────────────────────────────
@pytest.mark.parametrize("producer", sorted(PRODUCERS))
def test_matcherless_events_carry_no_matcher(producer, schema):
    """UserPromptSubmit and Stop take no matcher; emitting one matches nothing."""
    data = PRODUCERS[producer]()[schema["file"]["root_key"]]
    for event, spec in schema["events"].items():
        if spec.get("matcher") != "unsupported":
            continue
        for group in data.get(event, []):
            assert "matcher" not in group, (
                f"{producer}: {event} does not accept a matcher, got "
                f"{group['matcher']!r}"
            )


@pytest.mark.parametrize("producer", sorted(PRODUCERS))
def test_matcher_semantics_respected(producer, schema):
    """Tool events must match on tool NAME; enum events on published values."""
    data = PRODUCERS[producer]()[schema["file"]["root_key"]]
    tool_names = {
        t["name"] for t in schema["tool_names"] if "name" in t
    }
    for event, spec in schema["events"].items():
        semantics = spec.get("matcher_semantics")
        for group in data.get(event, []):
            matcher = group.get("matcher")
            if matcher is None:
                continue
            if semantics == "enum":
                assert matcher in spec["matcher_values"], (
                    f"{producer}: {event} matcher {matcher!r} not in "
                    f"{spec['matcher_values']}"
                )
            elif semantics == "tool_name_regex":
                # Invented names like "bash" compile fine as regex but match no
                # tool. The matcher has to actually select a real Codex tool.
                compiled = re.compile(matcher)
                assert any(compiled.search(name) for name in tool_names) or matcher.startswith(
                    "^mcp__"
                ), (
                    f"{producer}: {event} matcher {matcher!r} matches no known "
                    f"Codex tool name {sorted(tool_names)} — it would never fire"
                )


# ── Handler fields ───────────────────────────────────────────────────────────
@pytest.mark.parametrize("producer", sorted(PRODUCERS))
def test_handler_fields_allowed(producer, schema):
    data = PRODUCERS[producer]()[schema["file"]["root_key"]]
    allowed = set(schema["handler"]["allowed_fields"])
    required = set(schema["handler"]["required_fields"])
    type_values = set(schema["handler"]["type_values"])
    for event, groups in data.items():
        for group in groups:
            for handler in group.get("hooks", []):
                extra = set(handler) - allowed
                assert not extra, f"{producer}: {event} handler has non-schema fields {sorted(extra)}"
                missing = required - set(handler)
                assert not missing, f"{producer}: {event} handler missing {sorted(missing)}"
                assert handler["type"] in type_values


@pytest.mark.parametrize("producer", sorted(PRODUCERS))
def test_async_not_emitted(producer, schema):
    """Codex parses `async` but does not honour it — emitting it is a false promise."""
    if schema["handler"]["async"].get("supported"):
        pytest.skip("manifest now records async as supported")
    data = PRODUCERS[producer]()[schema["file"]["root_key"]]
    offenders = [
        (event, handler.get("command", "")[:60])
        for event, groups in data.items()
        for group in groups
        for handler in group.get("hooks", [])
        if "async" in handler
    ]
    assert not offenders, f"{producer}: async emitted but not honoured by Codex: {offenders}"


# ── Write-side coverage floor ────────────────────────────────────────────────
@pytest.mark.parametrize("producer", sorted(PRODUCERS))
def test_apply_patch_write_coverage_is_not_zero(producer, schema):
    """Edit/Write guards must land on apply_patch or Codex has no write governance.

    This is the regression that motivated the manifest: the projection carried
    zero apply_patch registrations while the canonical registry held dozens of
    Edit/Write hooks.
    """
    data = PRODUCERS[producer]()[schema["file"]["root_key"]]
    count = sum(
        len(group.get("hooks", []))
        for event in ("PreToolUse", "PostToolUse")
        for group in data.get(event, [])
        if "apply_patch" in str(group.get("matcher", ""))
    )
    assert count > 0, (
        f"{producer}: zero apply_patch registrations — every write-side guard "
        "is absent on Codex"
    )


# ── Trust gate ───────────────────────────────────────────────────────────────
def test_trust_gate_is_surfaced_by_the_installer(schema):
    """An install that leaves every hook inert must say so out loud."""
    if not schema.get("trust", {}).get("required"):
        pytest.skip("manifest no longer records a trust requirement")
    action = schema["trust"]["operator_action"]
    candidates = [
        REPO_ROOT / "scripts" / "cos_init.py",
        REPO_ROOT / "scripts" / "_lib" / "settings-driver-codex.sh",
    ]
    hits = [
        p.name
        for p in candidates
        if p.exists()
        and action in p.read_text(encoding="utf-8")
        and "trust" in p.read_text(encoding="utf-8").lower()
    ]
    assert hits, (
        "no installer/driver surface mentions the Codex trust gate "
        f"({action}); a silent install leaves every projected hook inert"
    )
