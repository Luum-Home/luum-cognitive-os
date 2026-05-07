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


def test_microvm_and_contree_adapter_contracts_are_declared() -> None:
    from lib.sandbox_adapter import adapter_plan

    microvm = adapter_plan("microvm")
    contree = adapter_plan("contree")
    assert microvm["status"] == "adapter_contract"
    assert "opt-in only" in microvm["dependency_policy"]
    assert contree["command_contract"][0] == "contree"


def test_microvm_runner_env_builds_active_command(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("COS_SANDBOX_MICROVM_RUNNER", "/opt/cos/bin/microvm-runner")
    plan = build_sandbox_command(["echo", "ok"], workspace=tmp_path, backend="microvm", network=True)
    assert plan.backend == "microvm"
    assert plan.adapter_status == "active"
    assert plan.network is True
    assert plan.command[:3] == ["/opt/cos/bin/microvm-runner", "--workspace", str(tmp_path.resolve())]


def test_contree_runner_env_builds_active_command(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("COS_SANDBOX_CONTREE_RUNNER", "/opt/cos/bin/contree")
    plan = build_sandbox_command(["pytest"], workspace=tmp_path, backend="contree")
    assert plan.backend == "contree"
    assert plan.adapter_status == "active"
    assert plan.command[:3] == ["/opt/cos/bin/contree", "--workspace", str(tmp_path.resolve())]
