# Tests que no corren donde viven

Fecha: 2026-08-20 · Alcance: os-only · Instrumento:
`scripts/audit_test_import_resolvability.py`

## Resumen ejecutivo

Censo sobre **2.319 archivos de test versionados**: **2.275 de 2.276 medibles**
resuelven sus imports de nivel de módulo con el intérprete del repo. **1 archivo
en 1 directorio** no: `packages/agent-service/tests/conftest.py`, que importa
`httpx`. **43 archivos quedan declarados ciegos** (40 sólo importan módulos de
primera parte que resuelve un `sys.path.insert`, 3 sólo importan en cuerpo de
función). **0 archivos** importan algo no declarado en ningún `pyproject.toml`.

El defecto no es "falta instalar httpx". `httpx` **está declarado** en
`packages/agent-service/pyproject.toml` → `[project.optional-dependencies]
testing`. Lo que falta es el **consumidor**: ningún camino de instalación del
repo lee ese pyproject, y `pytest.ini` declara `testpaths = tests`, así que esos
36 tests tampoco entran en la colección por defecto. Son dos desconexiones
apiladas — un extra declarado que nadie instala y un directorio de tests que
nadie colecta.

Puse el arreglo en **el consumidor que faltaba**: un censo ejecutable
(`--gate`, exit 0/1/2) y un test de contrato que lo consume con **igualdad
exacta** contra `manifests/test-import-exceptions.yaml`. El gate no llega a
verde por instalación: llega a **rojo honesto declarado**. Es el entregable.

## Correcciones a las premisas del encargo

1. **"~2.295 archivos de test"** → son **2.319** (`git ls-files` + filtro
   `test_*.py` / `*_test.py` / `conftest.py` bajo un directorio de tests). El
   número se movió de 2.318 a 2.319 **durante mi propia corrida**: hay otra
   sesión escribiendo en el mismo checkout. Cualquier número de este informe es
   de la ventana `HEAD` del 2026-08-20, no de un repo quieto.

2. **"7 tests versionados"** → son **7 archivos** (`__init__.py`, `conftest.py`
   y 6 módulos `test_*.py`) que contienen **36 funciones de test**
   (`grep -rn "^\s*\(async \)\?def test_" packages/agent-service/tests/ | wc -l`).
   El costo del defecto es 36, no 7.

3. **La premisa más cara: "declarado y no instalado vs no declarado en ningún
   lado" no era la partición correcta.** Mi primera corrida —el censo ingenuo
   que el encargo describe— dio **52 archivos en 10 directorios**. Ese número
   está mal, y publicarlo hubiera mandado a instalar paquetes de PyPI que no
   existen. Tres clases de falso positivo, ninguna de las cuales estaba en el
   encargo (que sólo nombraba `try/except ImportError` e `importorskip`):

   - **Módulos de primera parte** (40 archivos): `from claude_executor import …`
     después de un `sys.path.insert(0, str(ROOT / "cos_lib"))` en el propio
     archivo. No lo satisface ninguna dependencia instalada — lo satisface un
     archivo del repo.
   - **Imports en el cuerpo de una función** (3 archivos): `import psycopg2`
     dentro de un fixture, con `pytestmark = [pytest.mark.skipif(...)]` arriba.
     No corren en la colección; no rompen nada.
   - **Imports dentro del `except ImportError:`** (p. ej. `import tomli as
     tomllib` como fallback de `tomllib`). El encargo exceptuaba el `try:`; el
     `except:` es la otra mitad del mismo idioma y mi primera versión lo contaba
     como defecto.

   Corregidas las tres, quedan **1 archivo y 1 directorio**. El hallazgo es
   mucho más chico y mucho más nítido de lo que decía el encargo.

4. **"Cuántos de esos imports están declarados y simplemente no se instalan"**:
   la respuesta útil no es cuántos, es **quién los lee**. Ninguno de los tres
   caminos de instalación del repo lee `packages/*/pyproject.toml`. Verificable:
   `grep -rn "uv sync\|uv pip install" scripts/*.sh .github/workflows/*.yml`.

5. **"En la instalación … averiguá si ya intenta hacer esto y falla, o si nunca
   lo contempló"** → **nunca lo contempló**, y además **no alcanzaría**: aunque
   se instalara `httpx`, `testpaths = tests` deja `packages/agent-service/tests`
   fuera de la colección. El arreglo de instalación solo, que era la opción que
   el encargo ponía primera, no hace correr un solo test.

6. **`git worktree` está bloqueado, `git archive` no** — confirmado, usé
   `git archive`. Pero el hook `block-destructive-bash` **también bloquea un
   `rm -rf` sobre el scratchpad** cuando la ruta llega resuelta como
   `/private/tmp/...`: la lista de permitidos reconoce `/tmp` literal. Trabajé
   con `mktemp -d /tmp/...`. No lo arreglé: no es mi encargo y el hook está en
   `~/.claude/hooks/`, fuera del repo.

## El censo: población, medibles, ciegos

```
python3 scripts/audit_test_import_resolvability.py          # texto
python3 scripts/audit_test_import_resolvability.py --json   # JSON
python3 scripts/audit_test_import_resolvability.py --gate   # exit 1 si hay defectos
```

| | archivos |
|---|---|
| **Población** (tests versionados) | **2.319** |
| medibles | 2.276 |
| — resuelve | 2.275 |
| — declarado-no-instalado | **1** |
| — no-declarado | **0** |
| **ciegos** | **43** |
| — sólo falta primera parte (`sys.path.insert`) | 40 |
| — sólo falta en cuerpo de función | 3 |
| — no parsea | 0 |

Directorios afectados: **1** (`packages/agent-service/tests`).

La ceguera está declarada porque es real, no por trámite: de los 40 de primera
parte no puedo afirmar que resuelven —dependería de modelar cada manipulación de
`sys.path`—, sólo que **el módulo existe en el repo** y por lo tanto no es una
dependencia faltante. Contarlos como "resuelve" sería un verde por ceguera.

Lo que el censo **no** cuenta como defecto, por diseño: `try/except ImportError`,
`pytest.importorskip("x")`, `importlib.util.find_spec("x")` como guarda, e
imports dentro de funciones. Son la forma **correcta** de declarar una
dependencia opcional. El control que lo prueba está versionado en
`tests/contracts/test_test_import_resolvability.py::TestGateNoEsParanoico`.

## Declarado y no instalado vs no declarado en ningún lado

- **No declarado en ningún lado: 0.** Ningún test versionado importa, a nivel de
  módulo, algo que ningún `pyproject.toml` del repo prometa.
- **Declarado y no instalado: 1** — `httpx`, en
  `packages/agent-service/tests/conftest.py`.

Y acá la partición del encargo se queda corta. "Declarado y no instalado" sugiere
que el arreglo es instalar. No lo es: **un extra declarado que ningún camino de
instalación lee no es una dependencia faltante, es un invariante escrito que
nada ejecuta**. Misma familia que el hook declarado en un yaml que ningún driver
lee. La pregunta que ordena el arreglo no es *¿está declarado?* sino
**¿qué consume esa declaración?**

Respuesta medida, con su comando:

```
grep -rn "uv sync\|uv pip install" scripts/*.sh .github/workflows/*.yml
```

- `scripts/setup.sh` → `uv pip install -e ".[dev]"` (raíz)
- `scripts/cos-update.sh` → `uv sync` (raíz)
- `.github/workflows/{scope-portability,cos-binary-release}.yml` →
  `uv sync --extra testing --locked` (raíz)

Cero lectores de `packages/*/pyproject.toml`. La declaración existe desde el 20
de mayo y nunca tuvo consumidor.

Dicho como criterio reusable: una declaración de dependencias sin consumidor no es una dependencia faltante, es un invariante escrito que nada ejecuta.

## Dónde puse el arreglo y por qué ahí

**En el consumidor faltante, no en la instalación.**

1. `scripts/audit_test_import_resolvability.py` — censo estático (AST +
   `find_spec`), sin ejecutar la suite. Exit 0/1/2, `--json`, `--gate`.
2. `manifests/test-import-exceptions.yaml` — la inhabilidad **declarada**, con
   motivo escrito, el consumidor que falta y cómo se resolvería. Igualdad exacta
   en las dos direcciones: una ruta detectada y no listada rompe el gate, y una
   ruta listada que ya resuelve **también** lo rompe. Sin esa segunda mitad el
   manifiesto se vuelve un colchón.
3. `tests/contracts/test_test_import_resolvability.py` — el consumidor. Lee el
   censo, exige la igualdad exacta, y contiene el control de tres corridas que
   impide el gate paranoico.

**Por qué no en la instalación.** Lo evalué y lo dejo medido y sin implementar,
por dos razones verificables:

- `uv sync --extra testing --locked` en CI falla si `uv.lock` no está al día.
  Agregar `httpx>=0.27` al extra `testing` de la raíz exige `uv lock` — red, y
  una sesión de agente re-lockeando el repo mientras corre una suite de 24k
  tests es un riesgo mayor que el defecto que arregla.
- **No alcanzaría igual**: `testpaths = tests` deja esos tests fuera de la
  colección. Instalar `httpx` los dejaría instalables y seguirían sin correr.

El arreglo de instalación completo son dos pasos, escritos en
`manifests/test-import-exceptions.yaml` bajo `how_to_resolve`: (1) que el install
itere `packages/*/pyproject.toml`, o que el extra suba a la raíz + `uv lock`;
(2) que `packages/*/tests` entre en `testpaths` o en una lane propia. Los dos
tocan superficie compartida y ninguno es verificable sin red.

## Las tres corridas

**1 · El caso conocido, árbol de solo-trackeados.**

```
T=$(mktemp -d /tmp/tracked-agentsvc-XXXX) && git archive HEAD packages/agent-service | tar -x -C "$T" \
  && cd "$T/packages/agent-service" && .venv/bin/python -m pytest tests/ --collect-only -q
```

```
ImportError while loading conftest '…/packages/agent-service/tests/conftest.py'.
tests/conftest.py:12: in <module>
    from httpx import ASGITransport, AsyncClient
E   ModuleNotFoundError: No module named 'httpx'
```

Sigue igual después del arreglo, **a propósito**: no instalé nada. Lo que cambió
es que ahora está **declarado y gateado** en vez de descubierto por accidente.

**2 · El gate, en las dos direcciones.**

```
python3 scripts/audit_test_import_resolvability.py --gate ; echo $?     # 0  (con el manifiesto)
mv manifests/test-import-exceptions.yaml /tmp/ && python3 scripts/audit_test_import_resolvability.py --gate ; echo $?
#   SIN ACEPTAR (1):
#     packages/agent-service/tests/conftest.py: falta httpx
#   1
```

**3 · El control de tres, que impide el gate paranoico.**

```
.venv/bin/python -m pytest tests/contracts/test_test_import_resolvability.py -q
9 passed
```

- import imposible → **detectado**
- import satisfecho → **no detectado**
- `pytest.importorskip("…")`, `try/except ImportError`, fallback dentro del
  `except:`, e import en cuerpo de función → **no detectados, sin tocarlos**

## Lo que corregí en la documentación

Agregué el claim `test_environment_contract` a
`manifests/documentation-truth-claims.yaml`, con `required_docs` — una frase
prohibida sin superficie donde buscarla se chequea contra cero archivos y pasa.

No toqué `docs/00-MOCs/entrypoints/getting-started.md`, que presenta
`python3 -m pytest tests/ -n auto` como "correr los tests" sin decir que
`packages/*/tests` queda afuera. **Está modificado por otra sesión** en este
mismo checkout (`git status` lo muestra en ` M`), y mezclar mi edición con la
suya en un commit sería peor que la imprecisión. Queda como deuda nombrada: la
frase correcta es que `pytest tests/` corre la superficie declarada en
`testpaths`, no todos los tests versionados del repo.

## Lo que NO hice y por qué

- **No instalé `httpx` en el venv local.** Arregla mi máquina y nada más; es
  exactamente el verde barato que el encargo prohíbe.
- **No agregué `importorskip` al conftest de agent-service.** Habría dejado la
  colección limpia y **habría borrado el hallazgo del censo**: `importorskip` es
  una declaración de opcionalidad, y estos tests no son opcionales, son
  inalcanzables. Convertirlos habría cambiado un rojo honesto por un verde por
  ceguera.
- **No toqué `pytest.ini` ni `testpaths`.** Sumar `packages/*/tests` a la
  colección, con una corrida de 24k tests en curso y varias sesiones escribiendo
  el mismo checkout, es un cambio de superficie compartida que no puedo verificar
  acá.
- **No corrí la suite entera.** El censo es estático a propósito: AST +
  `find_spec`. La única ejecución fue `--collect-only` sobre 7 archivos y el
  test de contrato nuevo.
- **No toqué** el gate de skills (`hooks/orchestrator-skill-invocation-gate.sh`,
  `hooks/skill-router-prompt-suggest.sh`, `cos_lib/skill_router.py`, ADR-188,
  `rules/skill-invocation-mandatory.md`), que tienen dueño en esta sesión.
