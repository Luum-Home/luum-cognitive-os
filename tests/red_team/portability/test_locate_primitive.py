# SCOPE: both
"""Proof pareado de `scripts/locate_primitive.py`.

La sonda de falsación es el caso que originó el script: el 2026-08-20 un agente
reportó que `metrics-rotation.sh` no existía y la orquestación lo confirmó con
`ls scripts/metrics-rotation.sh`. El archivo existe como symlink de `hooks/` a
`packages/context-optimization/hooks/`. Los tests de acá abajo fallan si el
localizador vuelve a contestar "no está" en esa situación.

No hay ningún skip condicional en este archivo, a propósito: un proof que se
saltea cuando falta su sujeto es la misma patología que este censo persigue.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "locate_primitive.py"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from locate_primitive import locate, sweep  # noqa: E402


def _symlinks_into_packages() -> list[Path]:
    """Symlinks de `hooks/` cuyo destino real vive en `packages/`."""
    out = []
    hooks = REPO_ROOT / "hooks"
    for p in sorted(hooks.iterdir()):
        if p.is_symlink() and "/packages/" in os.path.realpath(p):
            out.append(p)
    return out


# ── Sonda de falsación: el caso real ──────────────────────────────────────────

def test_symlink_to_package_is_found_where_a_single_ls_fails():
    """Un symlink a un paquete se encuentra, y el `ls` ingenuo NO lo encuentra.

    Las dos mitades importan: sin la segunda, el test no probaría que el
    localizador aporta algo por encima del instrumento que ya falló.
    """
    links = _symlinks_into_packages()
    assert links, "hooks/ no tiene symlinks a packages/: cambió la premisa del repo"

    link = links[0]
    name = link.name
    result = locate(name, root=REPO_ROOT, exact=True)

    assert result["found"] is True, f"{name} existe pero el localizador dijo que no"
    paths = {h["path"] for h in result["hits"]}
    assert f"hooks/{name}" in paths
    assert any(h["symlink"] and "/packages/" in h["real"] for h in result["hits"]), (
        f"no se reportó el destino real de hooks/{name}"
    )
    # El instrumento que produjo la ausencia falsa: buscar en UN solo lugar.
    assert not (REPO_ROOT / "scripts" / name).exists(), (
        f"scripts/{name} existe: elegir otro caso para la sonda"
    )
    # ...y aun así el artefacto existe. Ésa es toda la tesis del script.
    assert len(result["distinct_targets"]) == 1, "symlink y destino deben contar como UN artefacto"


def test_directory_symlinks_are_reported(tmp_path: Path):
    """Tres directorios de `cos_lib/` son symlinks a `packages/*/lib/`."""
    result = locate("harness_adapter", root=REPO_ROOT, exact=True)
    assert result["found"] is True
    kinds = {h["kind"] for h in result["hits"]}
    assert kinds == {"dir"}, f"esperaba sólo directorios, hubo {kinds}"
    assert len(result["distinct_targets"]) == 1


# ── Comportamiento sobre un árbol construido (determinista) ───────────────────

def _tree(root: Path) -> None:
    (root / ".git").mkdir()
    (root / "packages" / "p" / "hooks").mkdir(parents=True)
    real = root / "packages" / "p" / "hooks" / "x.sh"
    real.write_text("#!/bin/sh\n")
    (root / "hooks").mkdir()
    (root / "hooks" / "x.sh").symlink_to(os.path.relpath(real, root / "hooks"))
    (root / ".cognitive-os" / "metrics").mkdir(parents=True)
    (root / ".cognitive-os" / "metrics" / "telemetry.jsonl").write_text("{}\n")
    (root / "hooks" / "roto.sh").symlink_to("../packages/p/hooks/no-existe.sh")


def test_dedup_by_real_target(tmp_path: Path):
    _tree(tmp_path)
    hits = sweep(tmp_path, "x.sh", exact=True)
    assert {h["path"] for h in hits} == {"hooks/x.sh", "packages/p/hooks/x.sh"}
    assert len({h["real"] for h in hits}) == 1


def test_runtime_state_dir_is_not_pruned(tmp_path: Path):
    """`.cognitive-os/` no se poda: podarla fue la ausencia falsa que este
    mismo script cometió en su primera versión."""
    _tree(tmp_path)
    result = locate("telemetry.jsonl", root=tmp_path, exact=True, check_path=False)
    assert result["found"] is True
    assert result["hits"][0]["path"] == ".cognitive-os/metrics/telemetry.jsonl"


def test_broken_symlink_is_present_but_flagged(tmp_path: Path):
    """Un enlace roto NO es una ausencia: es una presencia con destino muerto,
    y confundir las dos es cómo se borra un consumidor vivo."""
    _tree(tmp_path)
    result = locate("roto.sh", root=tmp_path, exact=True, check_path=False)
    assert result["found"] is True
    assert result["hits"][0]["broken"] is True


def test_true_absence_is_reported_as_absence(tmp_path: Path):
    _tree(tmp_path)
    result = locate("no-existe-en-ningun-lado.sh", root=tmp_path, exact=True, check_path=False)
    assert result["found"] is False
    assert result["hits"] == []


# ── Contrato de CLI ───────────────────────────────────────────────────────────

def test_cli_exit_codes(tmp_path: Path):
    _tree(tmp_path)
    ok = subprocess.run(
        [sys.executable, str(SCRIPT), "x.sh", "--exact", "--root", str(tmp_path), "--no-path"],
        capture_output=True, text=True, check=False,
    )
    assert ok.returncode == 0, ok.stderr
    assert "hooks/x.sh" in ok.stdout

    missing = subprocess.run(
        [sys.executable, str(SCRIPT), "zzz.sh", "--exact", "--root", str(tmp_path), "--no-path"],
        capture_output=True, text=True, check=False,
    )
    assert missing.returncode == 1
    assert "NO ENCONTRADO" in missing.stdout

    bad = subprocess.run(
        [sys.executable, str(SCRIPT), "x.sh", "--root", str(tmp_path / "no-such-dir")],
        capture_output=True, text=True, check=False,
    )
    assert bad.returncode == 2
