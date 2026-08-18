# El scaffold de portabilidad generaba pruebas que no podían pasar

**Fecha:** 2026-08-18
**Artefacto:** `scripts/cos-portability-proof-scaffold`
**Pruebas del arreglo:** `tests/unit/test_portability_proof_scaffold_families.py`

## 1. La reproducción

La plantilla por default emitía, para todo lo que no fuera `.py` ni un skill:

```python
command = [sys.executable, str(ARTIFACT), "--help"] if ARTIFACT.suffix == ".py" else [str(ARTIFACT), "--help"]
```

Es decir: para un `.md` intentaba **ejecutar el Markdown**. Reproducido en un
repo de juguete, sin tocar el repo real:

```
$ ./scripts/cos-portability-proof-scaffold --repo-root $SB --artifact docs/demo-rule.md
[portability-proof-scaffold] created tests/red_team/portability/test_demo-rule.py

$ .venv/bin/python -m pytest $SB/tests/red_team/portability/test_demo-rule.py -q
E   PermissionError: [Errno 13] Permission denied: '.../sbrepo/docs/demo-rule.md'
1 failed, 1 passed
```

Las dos mitades de ese `1 failed, 1 passed` son el problema completo:

- `test_runs_from_arbitrary_project_root` **no podía pasar nunca** (exec de un `.md`).
- `test_demo_rule_artifact_exists` — `assert ARTIFACT.exists()` — **no podía fallar
  nunca**. Es exactamente el verde barato que la norma de la casa prohíbe: un test
  que no ejecuta nada y no verifica conducta.

`tests/red_team/portability/test_codebase-memory-directive.py` salió de ahí. Hoy
está reescrito a mano; el commit `18ede12be` lo muestra como el único de la tanda
con líneas borradas (`73 ++++ / 12 ---`), las 12 líneas del scaffold roto.

## 2. Las ramas por tipo de artefacto

No hay más una plantilla única. `build_template()` rutea por familia, y las
familias ejecutables se **miden** antes de elegir plantilla (se corre el
artefacto desde un cwd ajeno, con timeout) porque las dos cosas que deciden la
forma del test —si `--help` es un contrato real y si stdout es determinista— no
se leen del código con un grep.

| Familia | Qué ejercita la prueba generada |
|---|---|
| `hooks/**.sh` | Le mete un payload JSON desde una raíz de proyecto ajena y desde el repo, y exige **el mismo veredicto**. Compara el exit code en vez de assertar `0`: un gate que bloquea correctamente rompería un `assert rc == 0`, y esa aserción sería sobre la política del gate, no sobre su portabilidad. |
| `.py` / `.sh` con `--help` real (medido: sale 0 **y** imprime `usage`) | `--help` desde cwd ajeno sale 0 y trae banner, y la corrida desde el repo y desde afuera dan stdout byte-idéntico. |
| `.py` / `.sh` sin `--help` real | Se corre entero desde ambos cwds: mismo exit code, mismo stdout, y stdout no vacío. **No** se assertan códigos absolutos. |
| `.md` (reglas, skills, docs) | Tres cosas reales: que el texto no lleva un path absoluto a este checkout (reusa `SOURCE_PATH_RE` de `scripts/primitive_scope_health.py`), que el frontmatter **parsea después de relocalizar** el archivo a una raíz ajena, y que el script que el documento nombra **sigue corriendo** desde un cwd ajeno con el mismo exit code. |
| `.yaml` / `.yml` / `.json` | Instalado bajo una raíz ajena tiene que parsear a la **misma estructura**, y la estructura no puede quedar vacía. |

Detalles que salieron de los casos medidos por quien escribió las 29 pruebas a mano:

- **`--help` no se asume, se mide.** Un script sin argparse corre la auditoría
  entera bajo `--help` y sale 1; assertar `--help → 0` sobre él prueba un no-evento.
  El scaffold clasifica como "contrato de help" sólo si sale 0 **y** imprime `usage`.
- **El intérprete va siempre nombrado**: `["bash", str(ARTIFACT)]` /
  `[sys.executable, str(ARTIFACT)]`, nunca `[str(ARTIFACT)]`. Con eso el modo del
  archivo deja de importar: `scripts/hook-io-overhead-bench.sh` y
  `scripts/verify_claims.py` son **644** y un exec directo devuelve 126.
- **Enmascarado de dígitos conservador.** Si las dos corridas de sondeo difieren,
  se enmascara (`re.sub(r"\d+", "#", ...)`) y el docstring dice *"medido, no
  asumido"*. Si dan idénticas pero el stdout **tiene dígitos**, igual se enmascara:
  un sondeo de dos segundos no prueba que un contador no avance entre las dos
  corridas del test dentro de una semana. Sólo el stdout sin dígitos —donde no hay
  nada que pueda derivar— se compara byte a byte.

## 3. Lo que el scaffold ahora se niega a generar

Rechazar es una salida correcta. La CLI sale con **exit code 3** (distinto del 2
de argparse) y escribe a stderr:

```
[portability-proof-scaffold] REFUSING to generate a proof for <artefacto>
  reason: <por qué>
  a generated proof here would be a false green. Instead: <qué hay que escribir a mano>
```

| Caso | `reason` | Hacia dónde apunta |
|---|---|---|
| `.md` sin frontmatter y sin ningún script existente nombrado | *the document declares no frontmatter and names no existing gate script* | No hay nada que ejercitar sin colapsar en un file-exists; escribir a mano contra el contrato que el documento sí hace (plantilla de delivery, comando, tabla de exit codes). |
| Artefacto que no termina dentro del timeout | *the artifact did not terminate within Ns from a foreign cwd* | Prueba de streaming: arrancar desde raíz ajena, leer hasta el primer header, terminar el proceso — señala `tests/red_team/portability/test_hook-io-overhead-bench.py` por nombre. |
| Dos corridas en el **mismo** cwd difieren aun con dígitos enmascarados | *two consecutive runs at the SAME cwd disagree even after digit masking* | Assertar el subconjunto estable (paths, veredictos, headers), no stdout. |
| Extensión sin rama | *no branch handles the <ext> family* | Escribirla a mano o agregar la rama. |
| `--no-probe` sobre una familia ejecutable | *this family cannot be classified statically* | "whether `--help` is a real contract and whether stdout is deterministic are measurements, not greps". |
| El artefacto no se puede lanzar (`OSError`) | *artifact could not be launched (...)* | Verificar que sea contenido ejecutable. |

Verificado contra el repo real: **`scripts/hook-io-overhead-bench.sh` es rechazado**
por no terminar. Es el resultado correcto — su prueba a mano es justamente una de
streaming que lee hasta `PART A` y mata el proceso.

## 4. Comparación con las pruebas hechas a mano

Se pasaron por el scaffold nuevo los 29 artefactos que tienen prueba a mano en
`18ede12be`: **22 salen con la misma forma**, 7 difieren.

| Artefacto | A mano | Generado ahora | Diferencia |
|---|---|---|---|
| `scripts/verify_claims.py` | `--help` → 0 + `usage`, y stdout byte-idéntico repo vs. ajeno | Igual | Ninguna. La rama de `--help` reproduce la prueba a mano. |
| `scripts/classify_ambiguous_hooks.py` | 1 test: sin args, dígitos enmascarados, mismo rc, stdout no vacío | 2 tests: lo mismo, partido en "corre entero y habla" + "cwd-invariante" | Aditiva. Mi sondeo midió **drift real** en este script en una corrida y estabilidad en otra — la prueba a mano tenía razón, y por eso el default quedó conservador. |
| `rules/encargo-refutable.md` | 3 tests: sin path absoluto; frontmatter tras relocalizar con **valores** (`meta["rule"] == "encargo-refutable"`); y que `templates/agent-mandatory-rules.md` —la vía de delivery que la regla declara— efectivamente la lleva | 3 tests: sin path absoluto; frontmatter tras relocalizar con **presencia de claves**; y que el primer script nombrado corre desde cwd ajeno | Un generador no puede saber qué valor *debería* tener `rule:`, así que assertar presencia es lo honesto. Pierde la verificación de delivery; gana la de "el comando documentado sigue corriendo". |
| `rules/codebase-memory-directive.md` | 4 tests, incluido el contrato de exit codes `0 READY / 1 NOT_READY / 2 ERROR` leído del JSON del gate | 2 tests | **Más débil.** El scaffold ve que la regla nombra `scripts/check_codebase_memory_readiness.py` y prueba que corre igual desde afuera, pero no puede inferir la tabla de exit codes. Sigue siendo real; no reemplaza la escrita a mano. |
| `scripts/hook-io-overhead-bench.sh` | Prueba de streaming, no assertea números | **RECHAZADO** | El scaffold se niega y nombra ese archivo como referencia. |

Ninguna de las 29 fue tocada. Corren:

```
$ .venv/bin/python -m pytest <las 29 + test_cos-portability-proof-scaffold.py> -q
55 passed in 34.10s
```

## 5. Verificación

```
$ .venv/bin/python -m pytest tests/unit/test_portability_proof_scaffold_families.py \
      tests/unit/test_portability_proof_scaffold.py -q
13 passed in 4.16s

$ .venv/bin/python -m pytest tests/behavior/test_scope_portability_precommit.py \
      tests/behavior/test_cos_primitive_harvester.py -q
12 passed in 6.55s
```

Las pruebas del scaffold **corren el generador de verdad** y después **corren lo
generado** con un pytest hijo. Cubren: `.py` con argparse, `.py` sin argparse
(que no reciba la aserción `--help → 0`), `.sh` ejecutable, `.sh` en **modo 644**
(el fixture verifica primero que un `/bin/sh -c` sobre él da 126), `.md` con
frontmatter, `.md` sólo-prosa (rechazo), exit code 3 en la CLI, `--no-probe`,
artefacto que no termina, y que **ninguna** plantilla emita un test de existencia.

Además, generado contra artefactos reales y corrido: 14 passed sobre
`verify_claims.py`, `classify_ambiguous_hooks.py`, `probe-hook-git-adjacency.sh`,
`rules/encargo-refutable.md`, `rules/codebase-memory-directive.md`,
`templates/confidentiality.yaml` y `hooks/scope-marker-portability-gate.sh`.

## 6. Correcciones a las premisas del encargo

1. **"28 pruebas escritas a mano" — son 29 archivos de prueba.** El commit
   `18ede12be` toca 30 archivos: 1 manifest y **29** proofs. De esos, 28 son
   nuevos y 1 (`test_codebase-memory-directive.py`) es la **reescritura** del
   archivo que había generado el scaffold roto — de ahí las 12 líneas borradas del
   diffstat. El número 28 describe lo nuevo, no el contenido del directorio.

2. **"`tests/red_team/portability/` son la referencia" — el directorio tiene 955
   entradas, no 29.** Las 29 de esta tanda son un subconjunto; el resto es de
   otras tandas y de otras familias (`.bats`, `_test.py`). Para leer la referencia
   hay que filtrar por el commit, no por el directorio.

3. **"Un `.sh` en modo 644 falla con 126 al ejecutarlo directo" — cierto en un
   shell, falso desde Python.** `subprocess.run([str(path)])` levanta
   `PermissionError`, no devuelve 126; el 126 lo produce `/bin/sh -c`. Como el
   scaffold genera pruebas en Python, el síntoma que iban a ver era el mismo
   `PermissionError` del `.md`. El fixture del test lo deja escrito con las dos
   formas.

4. **"Salidas no deterministas: hay un script que imprime contadores" — hay al
   menos dos, y el no-determinismo es intermitente.** `classify_ambiguous_hooks.py`
   y `probe-hook-git-adjacency.sh` llevan los dos el `_normalise` a mano. Mi primer
   sondeo los midió **estables** (dos corridas idénticas) y un sondeo posterior
   midió el drift. O sea que "medí y dio determinista" no alcanza como evidencia:
   por eso el default quedó en enmascarar cualquier salida con dígitos, y el
   docstring generado distingue *"medido"* de *"posible"*.

5. **"El verde barato sería que para un `.md` genere un test que sólo verifica que
   el archivo existe" — ese verde ya estaba emitido, para *todas* las familias.**
   `test_<módulo>_artifact_exists` estaba en la plantilla base, no sólo en la rama
   `.md`. Cada proof generado por el scaffold viejo traía uno. No era un riesgo a
   evitar; era deuda ya colocada.

6. **`scripts/` no es config protegida — pero el guard igual dispara.**
   `protected-config-write-guard` bloqueó dos comandos de esta sesión que sólo
   **leían** `rules/…` y `hooks/…`: alcanza con que el path aparezca en el texto
   del comando (un heredoc de Python que los nombra como strings). El prefijo
   `COS_ALLOW_PROTECTED_CONFIG_WRITE=1 <cmd>` funciona como decía el encargo.

7. **Ningún consumidor parsea el exit code del scaffold**, así que agregar el 3
   fue seguro. Verificado sobre los tres que lo mencionan
   (`tests/behavior/test_scope_portability_precommit.py`,
   `tests/behavior/test_cos_primitive_harvester.py` y el proof del propio
   scaffold): sólo chequean que el string del comando aparezca en un mensaje.

## 7. Deuda que queda escrita

- El nombre `scripts/cos-portability-proof-scaffold` es kebab-case sin extensión
  para un script Python, contra `rules/python-naming.md`. No se renombró porque
  el path está escrito en el mensaje de error de
  `hooks/scope-marker-portability-gate.sh` y en dos tests de comportamiento.
- La rama `.md` assertea **presencia** de claves de frontmatter, no valores. Para
  reglas con un contrato semántico fuerte (tabla de exit codes, plantilla de
  delivery), la prueba generada es un piso, no un techo — la de
  `rules/codebase-memory-directive.md` hecha a mano sigue siendo estrictamente
  mejor y no debe reemplazarse por la generada.
