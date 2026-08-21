# SCOPE: os-only
"""Proof pareado de portabilidad + falsacion para scripts/audit_registration_reverse.py.

El gate camina la direccion INVERSA a audit_hook_registration.py: no pregunta si
un componente esta registrado, pregunta si cada ENTRADA de registro apunta a algo
que pueda correr. El modo de fallo que persigue lo documenta el vendor
(https://code.claude.com/docs/en/hooks, leido 2026-08-21): "a mistyped path in
settings.json leaves the gate silently disabled".

FALSACION -- las dos ramas tienen que dar distinto
    Sembrar una entrada con ruta inexistente y verificar que la CAZA no alcanza:
    una sonda que devuelve rojo siempre tambien la caza. Asi que cada
    contrafactico se corre en pareja -- con el defecto y sin el -- y lo que se
    fija es que las dos ramas NO coinciden.

    Se falsan cuatro dimensiones distintas, porque un checker puede discriminar
    en una y estar ciego en las otras tres:
      1. ruta inexistente
      2. bit de ejecucion ausente CUANDO hace falta, y presente-innecesario
         cuando el invocador es `bash <ruta>` (las dos mitades: sin la segunda,
         un checker que exige +x siempre pasa la primera)
      3. matcher fuera de la enumeracion documentada del evento
      4. envoltorio -- el script real es el SEGUNDO argumento de
         hook-timing-wrapper.sh; un parser que valide solo el primer path da
         verde sobre todo y no prueba nada

ANTI-VACIO
    Un checker que recorre cero entradas sale verde igual que uno sano. Se fija
    que el vacio salga 2, no 0, en sus tres formas: sin superficies, superficie
    presente que no parsea nada, y parser degradado a todo-UNVERIFIABLE.

TERCER ESTADO
    VALIDA / ROTA / NO PUDE VERIFICAR. Se fija que una entrada irresoluble caiga
    en el tercero y NO en el primero: colapsarlo en VALIDA es fail-open, que es
    exactamente el defecto que este gate existe para cazar.

PORTABILIDAD
    El script resuelve su raiz desde __file__ y acepta un arbol ajeno por --root.
    Un auditor anclado en cwd no falla: audita el arbol equivocado y sale verde
    por vacio.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "audit_registration_reverse.py"

WRAPPER = 'bash "$CLAUDE_PROJECT_DIR/scripts/hook-timing-wrapper.sh" {event} "$CLAUDE_PROJECT_DIR/{script}"'


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent),  # deliberately NOT the repo root
    )


def build_root(tmp_path: Path, groups: list[dict]) -> Path:
    """A minimal but structurally real tree: the wrapper plus some hooks."""
    root = tmp_path / "tree"
    (root / "hooks").mkdir(parents=True)
    (root / "scripts").mkdir(parents=True)

    wrapper = root / "scripts" / "hook-timing-wrapper.sh"
    wrapper.write_text("#!/usr/bin/env bash\nexit 0\n")
    wrapper.chmod(wrapper.stat().st_mode | stat.S_IXUSR)

    # One healthy hook so the "zero VALID" vacuum guard does not mask the result.
    good = root / "hooks" / "healthy.sh"
    good.write_text("#!/usr/bin/env bash\nexit 0\n")
    good.chmod(good.stat().st_mode | stat.S_IXUSR)

    settings = root / ".claude"
    settings.mkdir()
    (settings / "settings.json").write_text(json.dumps({"hooks": {"SessionStart": groups}}))
    return root


def group(matcher: str, *commands: str) -> dict:
    return {
        "matcher": matcher,
        "hooks": [{"type": "command", "command": c} for c in commands],
    }


HEALTHY = group("", WRAPPER.format(event="SessionStart", script="hooks/healthy.sh"))


# ── 0. el arbol real ─────────────────────────────────────────────────────────


def test_runs_on_the_real_repo_and_reports_a_populated_census():
    """El gate corre sobre este repo y no sale verde por vacio."""
    proc = run("--root", str(REPO), "--json")
    assert proc.returncode in (0, 1), proc.stderr
    data = json.loads(proc.stdout)
    assert data["vacuum_guard"] == [], data["vacuum_guard"]
    assert data["totals"]["entries"] > 100
    assert data["totals"]["valid"] > 100
    # Cada superficie presente tiene que haber parseado algo.
    for name, info in data["surfaces"].items():
        assert info["state"] in ("PARSED", "ABSENT", "NO-REGISTRY"), (name, info)


# ── 1. ruta inexistente: la pareja tiene que dar distinto ────────────────────


def test_dead_path_is_caught_and_its_removal_is_clean(tmp_path):
    dead = group("", WRAPPER.format(event="SessionStart", script="hooks/does-not-exist.sh"))

    with_defect = run("--root", str(build_root(tmp_path / "a", [HEALTHY, dead])), "--json")
    without = run("--root", str(build_root(tmp_path / "b", [HEALTHY])), "--json")

    assert with_defect.returncode == 1, with_defect.stdout
    assert without.returncode == 0, without.stdout
    assert with_defect.returncode != without.returncode

    broken = json.loads(with_defect.stdout)["broken"]
    assert [e["target"] for e in broken] == ["hooks/does-not-exist.sh"]
    assert any("does not exist" in r for r in broken[0]["reasons"])
    assert json.loads(without.stdout)["broken"] == []


def test_dangling_symlink_is_broken_not_missing(tmp_path):
    """hooks/ del repo usa symlinks: un enlace colgado no es 'no existe'."""
    root = build_root(tmp_path, [HEALTHY,
                                 group("", WRAPPER.format(event="SessionStart",
                                                          script="hooks/linked.sh"))])
    os.symlink(root / "hooks" / "gone.sh", root / "hooks" / "linked.sh")

    proc = run("--root", str(root), "--json")
    assert proc.returncode == 1
    broken = json.loads(proc.stdout)["broken"]
    assert any("dangling symlink" in r for e in broken for r in e["reasons"]), broken


# ── 2. bit de ejecucion: las DOS mitades ─────────────────────────────────────


def test_missing_exec_bit_is_broken_only_when_the_caller_needs_it(tmp_path):
    """`bash <ruta>` no necesita +x; invocar la ruta pelada, si.

    Sin esta segunda mitad, un checker que exigiera +x a todo pasaria la primera
    y marcaria en rojo los 162 hooks que este repo invoca via wrapper.
    """
    root = build_root(tmp_path, [
        HEALTHY,
        # via bash -> el bit no hace falta
        group("", 'bash "$CLAUDE_PROJECT_DIR/hooks/no-exec-bit.sh"'),
        # ruta pelada -> el bit SI hace falta
        group("", '"$CLAUDE_PROJECT_DIR/hooks/no-exec-bit-direct.sh"'),
    ])
    for name in ("no-exec-bit.sh", "no-exec-bit-direct.sh"):
        p = root / "hooks" / name
        p.write_text("#!/usr/bin/env bash\nexit 0\n")
        p.chmod(0o644)

    data = json.loads(run("--root", str(root), "--json").stdout)
    broken_targets = {e["target"] for e in data["broken"]}
    assert broken_targets == {"hooks/no-exec-bit-direct.sh"}, data["broken"]
    assert any("execute bit" in r for e in data["broken"] for r in e["reasons"])


def test_exec_guarded_caller_requires_the_bit(tmp_path):
    """El driver de Codex envuelve cada hook en `[ -x <ruta> ]` y falla en silencio."""
    root = build_root(tmp_path, [HEALTHY])
    codex = root / ".codex"
    codex.mkdir()
    p = root / "hooks" / "codex-style.sh"
    p.write_text("#!/usr/bin/env bash\nexit 0\n")
    p.chmod(0o644)
    (codex / "hooks.json").write_text(json.dumps({"hooks": {"SessionStart": [{"hooks": [{
        "type": "command",
        "command": 'if [ -x "$PWD/hooks/codex-style.sh" ]; then bash "$PWD/hooks/codex-style.sh"; fi',
    }]}]}}))

    data = json.loads(run("--root", str(root), "--json").stdout)
    assert [e["target"] for e in data["broken"]] == ["hooks/codex-style.sh"]

    p.chmod(0o755)
    data = json.loads(run("--root", str(root), "--json").stdout)
    assert data["broken"] == []


# ── 3. matcher ───────────────────────────────────────────────────────────────


def test_matcher_outside_the_documented_enumeration_is_broken(tmp_path):
    bad = group("stratup", WRAPPER.format(event="SessionStart", script="hooks/healthy.sh"))
    with_defect = run("--root", str(build_root(tmp_path / "a", [HEALTHY, bad])), "--json")
    without = run("--root", str(build_root(tmp_path / "b", [HEALTHY])), "--json")

    assert with_defect.returncode == 1
    assert without.returncode == 0
    reasons = [r for e in json.loads(with_defect.stdout)["broken"] for r in e["reasons"]]
    assert any("enumeration" in r and "stratup" in r for r in reasons), reasons


def test_matcher_on_an_event_that_takes_none_is_broken(tmp_path):
    root = tmp_path / "t"
    (root / "hooks").mkdir(parents=True)
    (root / "scripts").mkdir(parents=True)
    for rel in ("scripts/hook-timing-wrapper.sh", "hooks/healthy.sh"):
        p = root / rel
        p.write_text("#!/usr/bin/env bash\nexit 0\n")
        p.chmod(0o755)
    (root / ".claude").mkdir()
    (root / ".claude" / "settings.json").write_text(json.dumps({"hooks": {
        "SessionStart": [HEALTHY],
        "Stop": [group("Bash", WRAPPER.format(event="Stop", script="hooks/healthy.sh"))],
    }}))
    data = json.loads(run("--root", str(root), "--json").stdout)
    assert any("takes no matcher" in r for e in data["broken"] for r in e["reasons"]), data


def test_empty_matcher_is_valid_on_every_event(tmp_path):
    """El repo real usa matcher "" en 10 eventos: si esto fuese rojo el gate seria inutil."""
    proc = run("--root", str(build_root(tmp_path, [HEALTHY])), "--json")
    assert proc.returncode == 0, proc.stdout


# ── 4. el envoltorio ─────────────────────────────────────────────────────────


def test_wrapper_second_argument_is_the_one_that_matters(tmp_path):
    """El primer path del comando es el wrapper (sano); el segundo es el hook.

    Un parser que validara solo el primero saldria VERDE aca, que es justamente
    el modo de fallo que hace inutil a un chequeo de este tipo.
    """
    root = build_root(tmp_path, [
        HEALTHY,
        group("", WRAPPER.format(event="SessionStart", script="hooks/ghost.sh")),
    ])
    data = json.loads(run("--root", str(root), "--json").stdout)
    targets = {e["target"] for e in data["broken"]}
    assert targets == {"hooks/ghost.sh"}, data["broken"]
    # y el wrapper mismo fue efectivamente inspeccionado, no ignorado
    assert data["totals"]["valid"] >= 2


def test_a_dead_wrapper_is_itself_caught(tmp_path):
    root = build_root(tmp_path, [HEALTHY])
    (root / "scripts" / "hook-timing-wrapper.sh").unlink()
    data = json.loads(run("--root", str(root), "--json").stdout)
    assert "scripts/hook-timing-wrapper.sh" in {e["target"] for e in data["broken"]}


# ── 5. el tercer estado ──────────────────────────────────────────────────────


def test_unresolvable_entry_is_unverifiable_not_valid(tmp_path):
    """Colapsar el tercer estado en el primero es fail-open."""
    root = build_root(tmp_path, [
        HEALTHY,
        group("", 'bash "$SOME_UNKNOWN_ROOT/hooks/whatever.sh"'),
    ])
    data = json.loads(run("--root", str(root), "--json").stdout)
    assert data["totals"]["unverifiable"] == 1, data["totals"]
    assert data["unverifiable"][0]["target"] is None
    assert any("UNVERIFIABLE" in r for r in data["unverifiable"][0]["reasons"])
    # no contamina el conteo de validas
    assert data["totals"]["valid"] + data["totals"]["broken"] + 1 == data["totals"]["entries"]


def test_strict_makes_unverifiable_gate(tmp_path):
    root = str(build_root(tmp_path, [HEALTHY, group("", 'bash "$SOME_UNKNOWN_ROOT/x.sh"')]))
    assert run("--root", root).returncode == 0
    assert run("--root", root, "--strict").returncode == 1


# ── 6. anti-vacio ────────────────────────────────────────────────────────────


def test_no_surfaces_at_all_exits_2(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    proc = run("--root", str(empty))
    assert proc.returncode == 2, proc.stdout
    assert "zero registration entries" in proc.stdout


def test_present_surface_that_parses_nothing_exits_2(tmp_path):
    root = build_root(tmp_path, [HEALTHY])
    (root / ".cursor").mkdir()
    (root / ".cursor" / "hooks.json").write_text(json.dumps({"hooks": {}}))
    proc = run("--root", str(root))
    assert proc.returncode == 2, proc.stdout
    assert "parser found zero entries" in proc.stdout


def test_all_unverifiable_exits_2_not_0(tmp_path):
    """Parser degradado: todo cae en el tercer estado y nada quedo verificado."""
    root = build_root(tmp_path, [group("", 'bash "$SOME_UNKNOWN_ROOT/x.sh"')])
    proc = run("--root", str(root))
    assert proc.returncode == 2, proc.stdout
    assert "degenerated" in proc.stdout


def test_unparseable_surface_exits_2(tmp_path):
    root = build_root(tmp_path, [HEALTHY])
    (root / ".cursor").mkdir()
    (root / ".cursor" / "hooks.json").write_text("{ not json")
    proc = run("--root", str(root))
    assert proc.returncode == 2, proc.stdout
    assert "UNPARSED" in proc.stdout


# ── 7. portabilidad ──────────────────────────────────────────────────────────


def test_default_root_is_the_repo_not_the_cwd():
    """Corrido desde otro directorio, tiene que auditar SU repo."""
    from_elsewhere = run("--json")
    anchored = run("--root", str(REPO), "--json")
    assert from_elsewhere.returncode == anchored.returncode
    assert json.loads(from_elsewhere.stdout)["root"] == str(REPO)
    assert (json.loads(from_elsewhere.stdout)["totals"]
            == json.loads(anchored.stdout)["totals"])


def test_missing_root_exits_2(tmp_path):
    proc = run("--root", str(tmp_path / "nope"))
    assert proc.returncode == 2


# ── 8. contrafactico sobre una COPIA del settings.json REAL ──────────────────


def _real_settings_copy(tmp_path: Path) -> Path:
    """Clona el arbol real lo suficiente como para auditarlo, sin tocarlo.

    Los tests sinteticos de arriba prueban que la sonda discrimina sobre un
    fixture que yo arme. Este prueba que discrimina sobre las 162 entradas
    reales, con sus envoltorios y sus diez eventos -- que es donde un parser
    puede pasar los fixtures y equivocarse igual.
    """
    root = tmp_path / "clone"
    (root / ".claude").mkdir(parents=True)
    src = json.loads((REPO / ".claude" / "settings.json").read_text())
    (root / ".claude" / "settings.json").write_text(json.dumps(src))
    # symlinks al arbol real: los scripts son los mismos archivos, no copias.
    # `packages/` queda AFUERA a proposito: el clon aisla la superficie bajo
    # prueba, y arrastrar packages/ meteria en la rama "limpia" los hallazgos
    # reales de OTRA superficie -- el contrafactico dejaria de discriminar.
    for rel in ("hooks", "scripts"):
        os.symlink(REPO / rel, root / rel)
    return root


def test_counterfactual_on_a_copy_of_the_real_settings(tmp_path):
    """Sembrar la ruta muerta la CAZA; sacarla sale limpio. Las dos ramas difieren."""
    clean_root = _real_settings_copy(tmp_path / "clean")
    clean = run("--root", str(clean_root), "--json")
    clean_data = json.loads(clean.stdout)
    assert clean.returncode == 0, clean.stdout
    assert clean_data["broken"] == []
    assert clean_data["totals"]["valid"] > 300, clean_data["totals"]

    seeded_root = _real_settings_copy(tmp_path / "seeded")
    settings = seeded_root / ".claude" / "settings.json"
    data = json.loads(settings.read_text())
    data["hooks"]["SessionStart"][0]["hooks"].append({
        "type": "command",
        "command": WRAPPER.format(event="SessionStart", script="hooks/seeded-ghost.sh"),
    })
    settings.write_text(json.dumps(data))

    seeded = run("--root", str(seeded_root), "--json")
    seeded_data = json.loads(seeded.stdout)

    assert seeded.returncode == 1, seeded.stdout
    assert seeded.returncode != clean.returncode
    assert [e["target"] for e in seeded_data["broken"]] == ["hooks/seeded-ghost.sh"]
    # El resto del censo no se movio: la sonda no reclasifico nada mas. La UNICA
    # validez que aparece es el envoltorio del comando sembrado -- que es la
    # prueba de que el parser miro los DOS paths del comando y no solo el
    # primero: si mirara solo el primero, este +1 seria el unico resultado y el
    # fantasma del segundo argumento no aparecia en broken.
    assert seeded_data["totals"]["valid"] == clean_data["totals"]["valid"] + 1
    assert seeded_data["totals"]["unverifiable"] == clean_data["totals"]["unverifiable"]


# ── 9. la entrada rota que este gate encontro de verdad ──────────────────────


@pytest.mark.parametrize("surface", ["cursor"])
def test_regression_cursor_prompt_quality_path(surface):
    """hooks/prompt-quality.sh fue archivado y .cursor/hooks.json quedo apuntando ahi.

    Archivado por 725c4fe84 a docs/99-Archive/archive/hooks/. Vive hoy como
    hooks/prompt-quality-llm.sh y packages/prompt-quality-gate/hooks/prompt-quality.sh.
    Este test se vuelve verde-por-ausencia cuando la entrada se arregle: es
    intencional, y por eso afirma la CONDICION, no el hallazgo.
    """
    data = json.loads(run("--root", str(REPO), "--json").stdout)
    dead = [e for e in data["broken"] if e["surface"] == surface]
    for e in dead:
        assert not (REPO / e["target"]).exists(), (
            f"{e['target']} existe: el gate reporto un falso positivo"
        )
