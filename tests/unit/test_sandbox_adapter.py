from __future__ import annotations

import shutil

import pytest

from lib.sandbox_adapter import SandboxUnavailable, build_sandbox_command


@pytest.mark.unit
def test_explicit_fallback_is_marked(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("COS_SANDBOX_DISABLE_NATIVE", "1")
    plan = build_sandbox_command(["echo", "ok"], workspace=tmp_path, allow_fallback=True)
    assert plan.backend == "none"
    assert plan.fallback_used is True
    assert plan.command == ["echo", "ok"]


@pytest.mark.unit
def test_no_backend_without_fallback_blocks(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: None)
    with pytest.raises(SandboxUnavailable):
        build_sandbox_command(["echo"], workspace=tmp_path)


@pytest.mark.unit
def test_bubblewrap_command_defaults_network_off(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/bwrap" if name == "bwrap" else None)
    plan = build_sandbox_command(["echo", "ok"], workspace=tmp_path, backend="bubblewrap")
    assert plan.backend == "bubblewrap"
    assert "--unshare-net" in plan.command
    assert "--bind" in plan.command
