from __future__ import annotations

import json
import shutil

import pytest

from lib.sandbox_adapter import SandboxUnavailable, build_sandbox_command


def test_strict_seccomp_requires_compiled_profile_path(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/bwrap" if name == "bwrap" else None)
    monkeypatch.delenv("COS_BWRAP_SECCOMP_PROFILE_PATH", raising=False)
    with pytest.raises(SandboxUnavailable):
        build_sandbox_command(["echo", "ok"], workspace=tmp_path, backend="bubblewrap", seccomp_profile="strict")


def test_strict_seccomp_wraps_bwrap_with_fd_loader(tmp_path, monkeypatch) -> None:
    profile = tmp_path / "strict.bpf"
    profile.write_bytes(b"compiled-bpf-placeholder")
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/bwrap" if name == "bwrap" else None)
    monkeypatch.setenv("COS_BWRAP_SECCOMP_PROFILE_PATH", str(profile))

    plan = build_sandbox_command(["echo", "ok"], workspace=tmp_path, backend="bubblewrap", seccomp_profile="strict")

    assert plan.seccomp_profile == "strict"
    assert plan.command[:3] == ["bash", "-lc", 'profile="$1"; shift; exec 3<"$profile"; exec "$@"']
    assert "--seccomp" in plan.command
    assert "3" in plan.command


def test_seccomp_policy_manifest_lists_blocked_syscalls(project_root) -> None:
    manifest = json.loads((project_root / "manifests" / "bwrap-seccomp-strict.json").read_text())
    assert manifest["status"] == "opt-in"
    assert "ptrace" in manifest["blocked_syscalls"]
    assert manifest["requires_compiled_bpf_path_env"] == "COS_BWRAP_SECCOMP_PROFILE_PATH"
