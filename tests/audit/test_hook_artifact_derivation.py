# SCOPE: os-only
"""La derivación del artefacto: qué escribe cada hook, sacado de su código.

Lo que se fija acá es sobre todo lo que el script tiene que NEGARSE a afirmar.
Un hook cuya ruta se arma en runtime no es "sin artefacto": es no clasificable,
y colapsar esos dos casos es el error que esta familia de mediciones repite.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from hook_artifact_derivation import derive_artifacts  # noqa: E402


def test_a_static_redirect_is_derived() -> None:
    derived, undecidable = derive_artifacts(
        'METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"\n'
        'echo "{}" >> "$METRICS_DIR/demo.jsonl"\n'
    )
    assert ".cognitive-os/metrics/demo.jsonl" in derived
    assert undecidable == set()


def test_a_runtime_built_path_is_undecidable_not_absent() -> None:
    """`$(basename "$0" .sh)` no se puede resolver estáticamente. El script debe
    decir "no puedo clasificarlo", nunca "no escribe nada"."""
    derived, undecidable = derive_artifacts(
        'echo x >> "$METRICS_DIR/$(basename "$0" .sh).jsonl"\n'
    )
    assert derived == set()
    assert undecidable, "una ruta dinámica tiene que quedar declarada como ceguera"


def test_devnull_and_fd_redirects_are_not_artifacts() -> None:
    derived, undecidable = derive_artifacts(
        'echo hi >/dev/null 2>&1\nprintf x >&2\n'
    )
    assert derived == set()


def test_a_redirect_inside_a_comment_is_not_a_write() -> None:
    """Un ejemplo documentado en la cabecera es prosa. Contarlo fabricaba el
    hallazgo en vez de medirlo (34 falsos positivos en la primera corrida)."""
    derived, _ = derive_artifacts(
        '# Ejemplo de uso: comando > .cognitive-os/reports/ejemplo.md\n'
        'echo real >> "$PROJECT_DIR/.cognitive-os/metrics/real.jsonl"\n'
    )
    assert derived == {".cognitive-os/metrics/real.jsonl"}


def test_report_publishes_a_census_with_its_blindness() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "hook_artifact_derivation.py")],
        capture_output=True, text=True, cwd=str(ROOT), timeout=300, check=False,
    )
    assert result.returncode in (0, 1), result.stderr[-2000:]
    assert "ceguera declarada:" in result.stdout
    assert "ruta_no_derivable" in result.stdout
    assert "CANDIDATOS, no veredictos" in result.stdout
