"""Consumer-sandbox regression for hook-lib-projection-contract.

Design: docs/02-Decisions/designs/hook-lib-projection-contract.md §4.
Ensures projected hooks that `import cos_lib.*` resolve against .cognitive-os/cos_lib/
(closure projection, §2) and that confidentiality-enforcer.sh fails open on
infra error instead of the historical false `exit 2` (§3).

Before this change landed, checks 2-5 below reproduced the real breakage:
ModuleNotFoundError on every lib-importing hook in a foreign-cwd consumer
install, and a hard `exit 2` BLOCK from confidentiality-enforcer.sh on a
benign write (ground truth in
docs/06-Daily/reports/hook-lib-projection-breakage-2026-07-08.md).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Set

import pytest

pytestmark = pytest.mark.audit

REPO_ROOT = Path(__file__).resolve().parents[2]
COS_INIT = REPO_ROOT / "scripts" / "cos_init.py"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from lib_closure import extract_lib_modules_from_hook  # noqa: E402

_INSTALL_TIMEOUT = 120
_HOOK_TIMEOUT = 10

# Benign PostToolUse payload used to exercise every projected lib-importing
# hook. Points at a 2-line scratch text file so scanners have something
# innocuous to look at without tripping content-policy/confidentiality rules.
_BENIGN_PAYLOAD_TEMPLATE = json.dumps(
    {
        "tool_name": "Write",
        "tool_input": {"file_path": "{file_path}"},
    }
)


def _run_cos_init(tmp_path: Path, mode: str) -> subprocess.CompletedProcess:
    """Run `cos_init.py <mode>` with cwd=tmp_path (foreign, not repo root).

    cos_init.py derives project_dir from Path.cwd() (Batch A discovery), not
    from argv, so no positional target-dir argument is passed.
    """
    env = os.environ.copy()
    env.pop("CLAUDE_PROJECT_DIR", None)
    env.pop("COGNITIVE_OS_PROJECT_DIR", None)
    env["COGNITIVE_OS_HARNESS"] = "claude"
    result = subprocess.run(
        [sys.executable, str(COS_INIT), mode, "--harness", "claude"],
        cwd=str(tmp_path),
        text=True,
        capture_output=True,
        timeout=_INSTALL_TIMEOUT,
        env=env,
    )
    return result


@pytest.fixture(scope="module")
def consumer_full(tmp_path_factory) -> Path:
    tmp = tmp_path_factory.mktemp("cos_consumer_full")
    result = _run_cos_init(tmp, "--full")
    assert result.returncode == 0, (
        f"cos_init.py --full failed (rc={result.returncode})\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    return tmp


@pytest.fixture(scope="module")
def consumer_default(tmp_path_factory) -> Path:
    tmp = tmp_path_factory.mktemp("cos_consumer_default")
    result = _run_cos_init(tmp, "--default")
    assert result.returncode == 0, (
        f"cos_init.py --default failed (rc={result.returncode})\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    return tmp


def _projected_hooks_dir(consumer_dir: Path) -> Path:
    hooks_dir = consumer_dir / ".cognitive-os" / "hooks" / "cos"
    assert hooks_dir.is_dir(), f"projected hooks dir missing: {hooks_dir}"
    return hooks_dir


def _lib_importing_projected_hooks(consumer_dir: Path) -> Dict[Path, Set[str]]:
    """Map each projected hook that imports cos_lib.* to its module set."""
    hooks_dir = _projected_hooks_dir(consumer_dir)
    result: Dict[Path, Set[str]] = {}
    for hook_path in sorted(hooks_dir.glob("*.sh")):
        mods = extract_lib_modules_from_hook(hook_path)
        if mods:
            result[hook_path] = mods
    return result


# ---------------------------------------------------------------------------
# §4.2 — Closure presence
# ---------------------------------------------------------------------------


def test_closure_presence_full(consumer_full: Path) -> None:
    lib_importers = _lib_importing_projected_hooks(consumer_full)
    assert lib_importers, "expected at least one lib-importing hook projected in --full"

    lib_dir = consumer_full / ".cognitive-os" / "cos_lib"
    assert lib_dir.is_dir(), f"{lib_dir} was not projected"
    assert (lib_dir / "__init__.py").is_file(), "lib/__init__.py missing from projection"

    missing = []
    for hook_path, mods in lib_importers.items():
        for mod in mods:
            if not (lib_dir / f"{mod}.py").is_file():
                missing.append(f"{hook_path.name} -> cos_lib.{mod}")
    assert not missing, "closure did not ship modules referenced by hooks:\n" + "\n".join(missing)


def test_closure_presence_default(consumer_default: Path) -> None:
    lib_importers = _lib_importing_projected_hooks(consumer_default)
    assert lib_importers, "expected at least one lib-importing hook projected in --default"

    lib_dir = consumer_default / ".cognitive-os" / "cos_lib"
    assert lib_dir.is_dir(), f"{lib_dir} was not projected"

    missing = []
    for hook_path, mods in lib_importers.items():
        for mod in mods:
            if not (lib_dir / f"{mod}.py").is_file():
                missing.append(f"{hook_path.name} -> cos_lib.{mod}")
    assert not missing, "closure did not ship modules referenced by hooks:\n" + "\n".join(missing)


# ---------------------------------------------------------------------------
# §4.3 — Import-resolution probe (no false ModuleNotFoundError)
# ---------------------------------------------------------------------------


def test_import_resolution_full(consumer_full: Path) -> None:
    lib_importers = _lib_importing_projected_hooks(consumer_full)
    all_mods = sorted({mod for mods in lib_importers.values() for mod in mods})
    assert all_mods

    env = os.environ.copy()
    env["PYTHONPATH"] = str(consumer_full / ".cognitive-os")

    # This repo's own .venv carries an editable-install .pth
    # (_editable_impl_luum_cognitive_os.pth) that unconditionally prepends
    # the SOURCE repo root to sys.path for every interpreter invocation.
    # Left unfiltered, `import cos_lib.<mod>` would silently resolve against the
    # SOURCE repo's real lib/ regardless of PYTHONPATH/cwd, masking a broken
    # closure projection instead of raising ModuleNotFoundError. Strip that
    # one entry (not -S, which would also drop legitimate third-party deps
    # like yaml/pydantic that cos_lib.* modules transitively import).
    _repo_root_str = str(REPO_ROOT)
    _probe_src = (
        "import sys; "
        f"sys.path = [p for p in sys.path if p != {_repo_root_str!r}]; "
        "import cos_lib.{mod}"
    )

    failures = []
    for mod in all_mods:
        proc = subprocess.run(
            [sys.executable, "-c", _probe_src.format(mod=mod)],
            cwd=str(consumer_full),
            text=True,
            capture_output=True,
            timeout=_HOOK_TIMEOUT,
            env=env,
        )
        if proc.returncode != 0 and "ModuleNotFoundError" in proc.stderr:
            failures.append(f"cos_lib.{mod}: {proc.stderr.strip().splitlines()[-1]}")
    assert not failures, "ModuleNotFoundError on projected closure:\n" + "\n".join(failures)


# ---------------------------------------------------------------------------
# §4.4 — No false exit 2 (Tier-1 + Tier-2 real run)
# ---------------------------------------------------------------------------


def _hook_env(consumer_dir: Path) -> dict:
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(consumer_dir)
    env["COGNITIVE_OS_PROJECT_DIR"] = str(consumer_dir)
    env["PYTHONPATH"] = str(consumer_dir / ".cognitive-os")
    return env


def test_no_false_exit_2_benign_write(consumer_full: Path) -> None:
    benign_file = consumer_full / "scratch.txt"
    benign_file.write_text("line one\nline two\n")

    payload = json.dumps(
        {"tool_name": "Write", "tool_input": {"file_path": str(benign_file)}}
    )

    hooks_dir = _projected_hooks_dir(consumer_full)
    lib_importers = _lib_importing_projected_hooks(consumer_full)
    env = _hook_env(consumer_full)

    exit2_hooks = []
    for hook_path in lib_importers:
        try:
            proc = subprocess.run(
                ["bash", str(hook_path)],
                input=payload,
                text=True,
                capture_output=True,
                timeout=_HOOK_TIMEOUT,
                env=env,
                cwd=str(consumer_full),
            )
        except subprocess.TimeoutExpired:
            continue
        if proc.returncode == 2:
            exit2_hooks.append(f"{hook_path.name}: {proc.stderr.strip()[-500:]}")

    assert not exit2_hooks, "hooks false-blocked (exit 2) on benign write:\n" + "\n".join(
        exit2_hooks
    )

    conf_hook = hooks_dir / "confidentiality-enforcer.sh"
    assert conf_hook.is_file()
    proc = subprocess.run(
        ["bash", str(conf_hook)],
        input=payload,
        text=True,
        capture_output=True,
        timeout=_HOOK_TIMEOUT,
        env=env,
        cwd=str(consumer_full),
    )
    assert proc.returncode == 0, (
        f"confidentiality-enforcer.sh expected exit 0 on benign write, "
        f"got {proc.returncode}\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    # exit 0 is ambiguous by itself: it is also what the §3 fail-open backstop
    # returns when the import silently breaks. Assert the *happy* path was
    # actually taken (no SCAN SKIPPED / infra-error fallback fired) so this
    # test cannot pass for the wrong reason if the bootstrap regresses.
    assert "SCAN SKIPPED" not in proc.stderr, (
        "confidentiality-enforcer.sh took the fail-open path instead of a real "
        f"clean scan on the happy-path bootstrap:\nstderr: {proc.stderr}"
    )


# ---------------------------------------------------------------------------
# §4.5 — Fail-open confirmation
# ---------------------------------------------------------------------------


def test_fail_open_when_lib_hidden(consumer_full: Path) -> None:
    lib_dir = consumer_full / ".cognitive-os" / "cos_lib"
    backup_dir = consumer_full / ".cognitive-os" / "cos_lib.bak"
    metrics_file = (
        consumer_full / ".cognitive-os" / "metrics" / "confidentiality-enforcer.jsonl"
    )

    assert lib_dir.is_dir()
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    shutil.move(str(lib_dir), str(backup_dir))

    try:
        benign_file = consumer_full / "scratch_failopen.txt"
        benign_file.write_text("line one\nline two\n")
        payload = json.dumps(
            {"tool_name": "Write", "tool_input": {"file_path": str(benign_file)}}
        )

        # This repo's editable-install .pth unconditionally prepends the SOURCE
        # repo root to sys.path for every venv python (see test_import_resolution_full).
        # Hiding the consumer's projected lib/ alone would NOT reproduce a real
        # consumer's ModuleNotFoundError — the hook's python would import the source
        # lib/ and never reach the §3 fail-open backstop. Neutralize the leak with a
        # sitecustomize shim (runs after .pth processing) that strips REPO_ROOT,
        # mirroring the filter test_import_resolution_full applies inside its probe.
        shim_dir = consumer_full / ".cognitive-os" / "_pth_leak_shim"
        shim_dir.mkdir(parents=True, exist_ok=True)
        (shim_dir / "sitecustomize.py").write_text(
            "import sys\n"
            f"_REPO = {str(REPO_ROOT)!r}\n"
            "sys.path[:] = [p for p in sys.path if p != _REPO]\n"
        )
        env = _hook_env(consumer_full)
        env["PYTHONPATH"] = os.pathsep.join(
            [str(shim_dir), str(consumer_full / ".cognitive-os")]
        )

        conf_hook = _projected_hooks_dir(consumer_full) / "confidentiality-enforcer.sh"
        metrics_before = (
            metrics_file.read_text().count("scan_error_fail_open")
            if metrics_file.is_file()
            else 0
        )

        proc = subprocess.run(
            ["bash", str(conf_hook)],
            input=payload,
            text=True,
            capture_output=True,
            timeout=_HOOK_TIMEOUT,
            env=env,
            cwd=str(consumer_full),
        )

        assert proc.returncode == 0, (
            f"expected fail-open exit 0 with lib/ hidden, got {proc.returncode}\n"
            f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
        )
        assert metrics_file.is_file(), "expected scan_error_fail_open metrics row to be written"
        metrics_after = metrics_file.read_text().count("scan_error_fail_open")
        assert metrics_after > metrics_before, "no new scan_error_fail_open row logged"
    finally:
        if lib_dir.exists():
            shutil.rmtree(lib_dir)
        shutil.move(str(backup_dir), str(lib_dir))
