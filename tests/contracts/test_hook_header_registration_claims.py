"""Las cabeceras de `hooks/**/*.sh` que afirman algo sobre el REGISTRO.

Sibling de ``test_claude_code_hooks_schema_conformance.py``, con una diferencia
que es la razón de existir de este archivo: aquel test lee UNA fuente de
registro, ``.claude/settings.json``. Ese archivo es GENERADO (ADR-064). El
registro canónico es ``cognitive-os.yaml > harness.hooks``, y hay una tercera
fuente que ninguno de los dos mira: ``templates/security-profiles/*.json``, que
``scripts/set-security-profile.sh`` **copia encima** de ``settings.json``
("Copy the profile JSON as the new settings.json", línea 87).

Consecuencia medida el 2026-08-19: cuatro emisores de contexto
(``skill-router-prompt-suggest``, ``rule-router-prompt-suggest``,
``adr-relevance-suggest``, ``subagent-context-injector``) tenían ``async: true``
en las tres plantillas de perfil mientras su cabecera y el ``settings.json``
vivo decían ``false``. El defecto que se corrigió el 16 y el 19 de agosto seguía
guardado en el molde: aplicar cualquier perfil lo reinyectaba. El test de
conformance estaba verde porque miraba la copia, no el molde.

Qué cubre:

* ``# Event:`` — el evento declarado debe existir en alguna de las tres fuentes.
* ``# Matcher:`` — idem para el matcher.
* ``# Async:`` — debe coincidir con TODAS las registraciones del hook, en las
  cuatro fuentes. Clave ``async`` ausente == ``false`` (es el default del host).
* Una cabecera de registro sobre un hook que no está registrado en NINGUNA
  fuente: sólo se acepta si el hook figura en
  ``hooks/_lib/registration-allowlist.txt``, el ratchet que este repo ya usa
  para declarar "deliberadamente no registrado".

Qué NO cubre, dicho para que nadie se confíe: no valida latencia. Las cabeceras
de latencia se eliminaron el 2026-08-19 — no tenían un solo lector en el código
y 9 de las 13 medibles se contradecían con el p50 real. La autoridad de
latencia es ``scripts/hook_timing_report.py`` (presupuesto por EVENTO, medido).

Censo derivado del árbol: ``sorted(HOOKS_DIR.rglob("*.sh"))``. Un hook nuevo
entra solo; ninguna lista curada decide qué se revisa.

Run:
    .venv/bin/python3 -m pytest tests/contracts/test_hook_header_registration_claims.py -q
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

# Leído por scripts/hook_quality_audit.py: el corpus sale de _hook_sources(),
# un walk de hooks/, así que cubre todos sin nombrar a ninguno.
HOOK_QUALITY_COVERAGE = "census"

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS_DIR = REPO_ROOT / "hooks"
COS_YAML = REPO_ROOT / "cognitive-os.yaml"
SETTINGS = REPO_ROOT / ".claude" / "settings.json"
PROFILES_DIR = REPO_ROOT / "templates" / "security-profiles"
ALLOWLIST = HOOKS_DIR / "_lib" / "registration-allowlist.txt"
# Cuarto molde, encontrado el 2026-08-19 por el rojo de
# test_cross_session_event_taxonomy: un generador en bash que emite el bloque
# `hooks` de settings.json con la forma `"hooks/NAME.sh"  "true|false"`.
SETTINGS_DRIVER = REPO_ROOT / "scripts" / "_lib" / "settings-driver-claude-code.sh"

# ── Baselines ────────────────────────────────────────────────────────────────
# Los cuatro están VACÍOS y el vacío ES la aserción. Igualdad exacta, no
# contención: un baseline por encima de la realidad es colchón que una regresión
# futura ocupa gratis (regla `gates-sin-trampa`). Cada uno se verifica en tres
# direcciones — no absorbe uno nuevo, no deja listado uno ya corregido, y no
# guarda asientos apuntando a archivos que no existen.

KNOWN_EVENT_HEADER_DRIFT: set[str] = set()
KNOWN_MATCHER_HEADER_DRIFT: set[str] = set()

# Vaciado el 2026-08-19 sacando `"async": true` de las 12 registraciones
# (4 hooks × 3 plantillas de perfil) en templates/security-profiles/. El
# settings.json vivo ya decía false desde el 16 y el 19; las plantillas no.
KNOWN_ASYNC_HEADER_DRIFT: set[str] = set()

# Un hook con cabecera de registro y sin registro en ninguna fuente. Vacío
# porque los dos casos vivos —adr-detector.sh y clean-room-ast-similarity-gate.sh—
# están en registration-allowlist.txt, que es donde este repo declara la
# excepción, con motivo escrito y ratchet que sólo achica.
KNOWN_ORPHAN_REGISTRATION_HEADER: set[str] = set()

_HEADER_RE_CACHE: dict[str, re.Pattern[str]] = {}


def _header(text: str, key: str) -> str | None:
    pattern = _HEADER_RE_CACHE.setdefault(
        key, re.compile(rf"^#\s*{key}:\s*(.+)$", re.MULTILINE | re.IGNORECASE)
    )
    match = pattern.search(text)
    return match.group(1).strip() if match else None


def _hook_sources() -> list[Path]:
    return sorted(HOOKS_DIR.rglob("*.sh"))


def _add(reg: dict[str, list[dict]], name: str, event, matcher, is_async, origin) -> None:
    reg.setdefault(name, []).append(
        {
            "event": event,
            "matcher": str(matcher or ""),
            "async": bool(is_async),
            "origin": origin,
        }
    )


@pytest.fixture(scope="module")
def registrations() -> dict[str, list[dict]]:
    """Unión de las CUATRO fuentes de registro, cada asiento con su origen.

    Mirar una sola es cómo un defecto corregido en la copia sobrevive en el
    molde. `settings.json` es la copia; `cognitive-os.yaml` es el canónico;
    `templates/security-profiles/*.json` son los moldes que la sobrescriben.
    """
    reg: dict[str, list[dict]] = {}

    data = yaml.safe_load(COS_YAML.read_text(encoding="utf-8"))
    for entry in (data.get("harness", {}).get("hooks") or {}).values():
        if isinstance(entry, dict) and "script" in entry:
            _add(
                reg,
                Path(entry["script"]).name,
                entry.get("event"),
                entry.get("matcher", ""),
                entry.get("async", False),
                "cognitive-os.yaml",
            )

    if SETTINGS_DRIVER.exists():
        driver_re = re.compile(r'"hooks/([A-Za-z0-9_.-]+\.sh)"\s+"(true|false)"')
        for name, flag in driver_re.findall(SETTINGS_DRIVER.read_text(encoding="utf-8")):
            _add(reg, name, None, "", flag == "true", "scripts/_lib/settings-driver-claude-code.sh")

    json_sources = [SETTINGS] + sorted(PROFILES_DIR.glob("*.json"))
    for path in json_sources:
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        origin = str(path.relative_to(REPO_ROOT))
        for event, matchers in (payload.get("hooks") or {}).items():
            for matcher in matchers:
                for handler in matcher.get("hooks", []):
                    command = handler.get("command", "")
                    for name in re.findall(r"hooks/([A-Za-z0-9_.-]+\.sh)", command):
                        _add(
                            reg,
                            name,
                            event,
                            matcher.get("matcher", ""),
                            handler.get("async", False),
                            origin,
                        )
    return reg


@pytest.fixture(scope="module")
def allowlisted() -> set[str]:
    if not ALLOWLIST.exists():
        return set()
    return {
        line.strip()
        for line in ALLOWLIST.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def _assert_baseline(offenders: set[str], baseline: set[str], label: str, fix: str) -> None:
    """Las tres aserciones que hacen del baseline un ratchet y no un colchón."""
    unexpected = offenders - baseline
    assert not unexpected, f"{label}: {sorted(unexpected)}\nArreglo: {fix}"

    stale = baseline - offenders
    assert not stale, (
        f"{label}: entradas ya corregidas que siguen en el baseline: "
        f"{sorted(stale)}. Borralas. Un baseline por encima de la realidad es "
        "colchón que la próxima regresión ocupa sin encender el rojo."
    )

    ghosts = {name for name in baseline if not (HOOKS_DIR / name).exists()}
    assert not ghosts, (
        f"{label}: el baseline nombra archivos inexistentes: {sorted(ghosts)}. "
        "Un asiento sobre un archivo borrado no suprime nada y da sensación de "
        "cobertura."
    )


# ── Registration source count ────────────────────────────────────────────────


def test_all_registration_sources_are_all_present(registrations):
    """Si una fuente desaparece, este gate pierde alcance en silencio.

    El defecto de las plantillas vivió porque el gate anterior leía una sola
    fuente. Un gate que mira dos de tres tiene la misma forma.
    """
    origins = {seat["origin"] for seats in registrations.values() for seat in seats}
    assert "cognitive-os.yaml" in origins, "el registro canónico (ADR-064) no aportó asientos"
    assert ".claude/settings.json" in origins, "la proyección viva no aportó asientos"
    assert "scripts/_lib/settings-driver-claude-code.sh" in origins, (
        "el generador en bash de .claude/settings.json no aportó asientos. Es el "
        "cuarto molde y el más fácil de olvidar: no es JSON ni YAML, así que "
        "ningún parser de config lo encuentra."
    )
    profiles = {o for o in origins if o.startswith("templates/security-profiles/")}
    assert len(profiles) >= 3, (
        f"se esperaban las 3 plantillas de perfil, se leyeron {sorted(profiles)}. "
        "set-security-profile.sh copia esas plantillas encima de settings.json: "
        "una plantilla no leída es un defecto que sobrevive al arreglo."
    )


# ── Event ────────────────────────────────────────────────────────────────────


def test_event_header_names_a_real_registration(registrations):
    """`# Event: X` sobre un hook que no está registrado en X."""
    offenders: set[str] = set()
    detail: list[str] = []
    for path in _hook_sources():
        declared_raw = _header(path.read_text(encoding="utf-8", errors="ignore"), "Event")
        if declared_raw is None:
            continue
        seats = registrations.get(path.name)
        if not seats:
            continue  # cubierto por test_registration_header_without_registration
        declared = {
            token.strip().strip(".,`")
            for token in re.split(r"[,/ ]+", declared_raw.split("(")[0])
            if token.strip()
        }
        actual = {seat["event"] for seat in seats if seat["event"]}
        if not declared & actual:
            offenders.add(path.name)
            detail.append(f"  {path.name}: cabecera dice {sorted(declared)}, registrado en {sorted(actual)}")

    _assert_baseline(
        offenders,
        KNOWN_EVENT_HEADER_DRIFT,
        "cabecera `# Event:` contradice el registro\n" + "\n".join(detail),
        "corregí la cabecera si el registro dice la verdad, o agregá/corregí el "
        "asiento en cognitive-os.yaml si la cabecera dice la verdad. Decidí cuál "
        "miente con evidencia (telemetría en .cognitive-os/metrics/hook-timing.jsonl "
        "más sus rotados), no por conveniencia de que el gate pase.",
    )


# ── Matcher ──────────────────────────────────────────────────────────────────


def test_matcher_header_names_a_real_registration(registrations):
    """`# Matcher: Bash` sobre un hook registrado con otro matcher."""
    offenders: set[str] = set()
    detail: list[str] = []
    for path in _hook_sources():
        declared_raw = _header(path.read_text(encoding="utf-8", errors="ignore"), "Matcher")
        if declared_raw is None:
            continue
        seats = registrations.get(path.name)
        if not seats:
            continue
        declared = declared_raw.split("(")[0].strip().strip('`"')
        if not declared:
            continue
        actual = {seat["matcher"] for seat in seats}
        # Un matcher del host es un regex alternado ("Bash|Write|Edit"): la
        # cabecera nombra una de las alternativas, no la expresión entera.
        if not any(declared == a or declared in a or a in declared for a in actual if a):
            offenders.add(path.name)
            detail.append(f"  {path.name}: cabecera dice {declared!r}, registrado con {sorted(actual)}")

    _assert_baseline(
        offenders,
        KNOWN_MATCHER_HEADER_DRIFT,
        "cabecera `# Matcher:` contradice el registro\n" + "\n".join(detail),
        "alineá la cabecera con el matcher registrado, o corregí el registro.",
    )


# ── Async, en las tres fuentes ───────────────────────────────────────────────


def test_async_header_matches_every_registration(registrations):
    """`# Async:` debe valer para TODOS los asientos, plantillas incluidas.

    Éste es el que encontró el defecto de 2026-08-19: cuatro cabeceras decían
    `false`, el settings.json vivo decía `false`, y las tres plantillas de
    perfil seguían diciendo `true`. Aplicar un perfil reinyectaba el defecto.

    La clave `async` ausente ES un registro de `async: false` — es el default
    del host —, así que "sin clave" y `"async": false` son lo mismo acá.
    """
    offenders: set[str] = set()
    detail: list[str] = []
    for path in _hook_sources():
        declared_raw = _header(path.read_text(encoding="utf-8", errors="ignore"), "Async")
        if declared_raw is None:
            continue
        declared = declared_raw.split()[0].lower().strip("().,")
        if declared not in {"true", "false"}:
            continue
        for seat in registrations.get(path.name, []):
            if (declared == "true") != seat["async"]:
                offenders.add(path.name)
                detail.append(
                    f"  {path.name}: cabecera dice Async: {declared} pero "
                    f"{seat['origin']} lo registra en {seat['event']} con async={seat['async']}"
                )

    _assert_baseline(
        offenders,
        KNOWN_ASYNC_HEADER_DRIFT,
        "cabecera `# Async:` contradice alguna registración\n" + "\n".join(detail),
        "si el origen es templates/security-profiles/*.json, sacá la clave "
        "`async` de esa registración: aplicar el perfil copia la plantilla "
        "encima de .claude/settings.json y reinyecta el defecto. Si el origen "
        "es el canónico, decidí con evidencia cuál de los dos dice la verdad.",
    )


# ── Cabecera de registro sin registro ────────────────────────────────────────


def test_registration_header_without_registration(registrations, allowlisted):
    """Un hook que documenta su registro y no está registrado en ningún lado.

    La excepción legítima ya la declara este repo en
    `hooks/_lib/registration-allowlist.txt`, un ratchet que sólo achica. Un
    huérfano fuera de esa lista es una cabecera que le miente al lector sobre
    cuándo corre el archivo que está leyendo.
    """
    offenders: set[str] = set()
    detail: list[str] = []
    for path in _hook_sources():
        text = path.read_text(encoding="utf-8", errors="ignore")
        claimed = [key for key in ("Event", "Matcher", "Async") if _header(text, key)]
        if not claimed:
            continue
        if registrations.get(path.name):
            continue
        if path.name in allowlisted:
            continue
        offenders.add(path.name)
        detail.append(f"  {path.name}: declara {claimed} y no figura en ninguna fuente de registro")

    _assert_baseline(
        offenders,
        KNOWN_ORPHAN_REGISTRATION_HEADER,
        "cabecera de registro sobre un hook no registrado\n" + "\n".join(detail),
        "registralo en cognitive-os.yaml, o sacá la cabecera, o —si la falta de "
        "registro es deliberada— agregalo a hooks/_lib/registration-allowlist.txt "
        "con el motivo escrito.",
    )
