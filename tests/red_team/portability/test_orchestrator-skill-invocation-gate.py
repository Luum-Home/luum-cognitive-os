# SCOPE: os-only
"""Portability proof for hooks/orchestrator-skill-invocation-gate.sh."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = Path(
    os.environ.get("COS_SKILL_GATE_HOOK")
    or (REPO_ROOT / "hooks/orchestrator-skill-invocation-gate.sh")
)


def test_orchestrator_skill_invocation_gate_passes_unrelated_tool_from_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: hook must not depend on OS repo cwd for passthrough input."""
    payload = {"tool_name": "Read", "tool_input": {"file_path": str(tmp_path / "probe.txt")}}
    env = os.environ.copy()
    env.update({
        "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
        "CODEX_PROJECT_DIR": str(tmp_path),
        "CLAUDE_PROJECT_DIR": str(tmp_path),
        "COS_METRICS_DIR": str(tmp_path / ".cognitive-os" / "metrics"),
        "COS_PRIVATE_MODE": "0",
    })
    result = subprocess.run(
        ["bash", str(ARTIFACT)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=tmp_path,
        env=env,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    # 2026-08-20 — `rc == 0` solo no probaba nada: sobre este payload TODOS los
    # caminos del hook devuelven 0, incluido el de un hook que ignore el filtro
    # de `tool_name`. Lo que hace falsable la sonda es que un tool NO gobernado
    # salga por el corto y no deje NINGUN rastro en el proyecto ajeno: ni
    # auditoria, ni contador, ni bucket anonimo.
    assert result.stderr == "", result.stderr
    cos = tmp_path / ".cognitive-os"
    escrituras = sorted(p.name for p in cos.rglob("*") if p.is_file()) if cos.exists() else []
    assert escrituras == [], f"un tool no gobernado no escribe nada: {escrituras}"
