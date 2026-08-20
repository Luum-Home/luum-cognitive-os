# SCOPE: os-only
"""Portability proof for scripts/proof-event-cadence-gate.sh.

Es un script de PRUEBA, asi que su propiedad portable mas importante no es que
corra en cualquier lado: es que NO deje el repo mutado si algo sale mal. Las
sondas de abajo lo falsifican: sintaxis bajo bash 3.2, resolucion del repo por
`git rev-parse` y no por una ruta escrita, negativa limpia fuera de un repo git,
y —la que importa— que el `trap` de restauracion cubra tambien las salidas
anormales, no solo EXIT.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "scripts" / "proof-event-cadence-gate.sh"


def test_scope_marker_and_no_absolute_checkout_path() -> None:
    text = ARTIFACT.read_text(encoding="utf-8")
    assert text.splitlines()[1].strip() == "# SCOPE: os-only"
    assert str(REPO_ROOT) not in text
    assert "/Users/" not in text and "/home/" not in text


def test_syntax_is_valid_under_the_system_bash() -> None:
    """macOS trae bash 3.2.57. Un `local -n` o un array asociativo muere aca."""
    proc = subprocess.run(["/bin/bash", "-n", str(ARTIFACT)],
                          capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr


def test_repo_is_resolved_by_git_not_by_a_written_path() -> None:
    text = ARTIFACT.read_text(encoding="utf-8")
    assert "git rev-parse --show-toplevel" in text, (
        "resolver el repo por ruta relativa a $0 rompe cuando el script se invoca "
        "por symlink o desde un worktree"
    )


def test_restore_trap_covers_abnormal_exits() -> None:
    """Sonda de falsificacion del contrato central: si el trap fuera solo EXIT,
    un Ctrl-C durante pytest dejaria los manifiestos mutados en el arbol."""
    text = ARTIFACT.read_text(encoding="utf-8")
    trap_lines = [ln for ln in text.splitlines() if ln.strip().startswith("trap ")]
    assert trap_lines, "no hay trap de restauracion"
    señales = trap_lines[0]
    for s in ("EXIT", "INT", "TERM"):
        assert s in señales, f"el trap no cubre {s}: {señales!r}"


def test_refuses_cleanly_outside_a_git_repo(tmp_path: Path) -> None:
    """Corre de verdad, fuera de un repo: tiene que salir 2 y NO tocar nada."""
    copia = tmp_path / "proof.sh"
    copia.write_text(ARTIFACT.read_text(encoding="utf-8"), encoding="utf-8")
    proc = subprocess.run(
        ["/bin/bash", str(copia)],
        cwd=tmp_path, capture_output=True, text=True, timeout=120,
        env={"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(tmp_path),
             "GIT_CEILING_DIRECTORIES": str(tmp_path)},
    )
    assert proc.returncode == 2, (
        f"esperaba exit 2 (error de entorno), obtuve {proc.returncode}. "
        f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    )
    assert list(tmp_path.iterdir()) == [copia], "dejo residuo fuera del repo"
