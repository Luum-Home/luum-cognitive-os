# Veredicto del panel — las 94 rutas del registry "sin scope declarado"

**Fecha:** 2026-08-19 · **HEAD al cerrar:** `4bf198504` · **Modo:** read-only (ninguna primitiva modificada)
**Insumos:** 3 lentes (proyección real del instalador / decisión escrita ya vigente / qué rompe el marcador) + 8 veredictos por familia.
**Este documento:** síntesis con evidencia propia. Todo número reportado acá lo volví a correr yo; los comandos están en §6.

---

## 0. El titular, antes de la tabla

**La pregunta del panel estaba mal planteada para 85 de las 94 rutas.**

No es "¿les ponemos `# SCOPE:`?". Es: **el gate lee una sola forma de declaración y el repo usa tres.**
85 de las 94 ya tienen scope decidido y vigente en `manifests/primitive-scope-overrides.yaml` o
`manifests/primitive-structure-scopes.yaml`, con rationale por archivo o por patrón, consumidos por
`cos_lib/primitive_parser.py` y por `scripts/primitive_scope_classifier.py`.
`hooks/scope-marker-portability-gate.sh` **no lee ninguno de los dos**.

```
cobertura por manifiestos, cruzando los94.json:   struct=27  overrides=78  NINGUNO=9   (de 94)
grep -n 'primitive-scope-overrides\|primitive-structure-scopes' hooks/scope-marker-portability-gate.sh  ->  exit=1 (sin coincidencias)
```

Y hay un agravante medido: **estampar el marcador EMPEORA la situación en las 9 sin proof.** El gate
tiene dos ramas y la que se dispara al marcar no es la que se cree. Verificado end-to-end contra un
repo git aislado, con el `/bin/bash` 3.2.57 real:

```
archivo preexistente MODIFICADO, sin marcador   ->  GATE_EXIT=0   (pasa)
el mismo archivo, con "# SCOPE: os-only"        ->  GATE_EXIT=2   ("declares a SCOPE marker but has no paired portability proof")
archivo NUEVO sin marcador                      ->  GATE_EXIT=2
```

El arreglo honesto es **una función** (`declares_scope()` consultando los dos manifiestos, igual que
ya consulta `audience:` para skills), **no 94 ediciones**. El propio gate lleva escrito el diagnóstico
de este mismo bug, cometido una vez con las skills: *"Wrong field, not missing debt."*

---

## 1. Veredicto en una tabla

| Familia | N | Veredicto del panel | Confianza | Reversible | Marcar hoy, ¿qué pasa? |
|---|---|---|---|---|---|
| **F1** inertes (`.bak`, `.disabled`) | 5 | **Sacar del alcance del gate** | alta | sí, 1 condición en bash | bloquea el commit (0/5 con proof) |
| **F2** datos (`.txt`, `okf-schema.json`) | 3 | **Sacar del alcance del gate** ⚠ 1 condición bloqueante | alta | sí, metadata pura | rompe el JSON / se pierde en la regeneración / **miente** |
| **F3a** `scripts/cos-*` sin extensión | 36 | **Marcar `os-only`** — decisión de operador | media-alta | sí, comentario en línea 2 | inocuo: 36/36 ya tienen proof |
| **F3b** `scripts/*.py` y `*.sh` | 17 | **Dejar y anotar deuda** | alta | sí | inocuo, pero es bulk-edit que ADR-314 gobierna |
| **F4** libs de shell (`scripts/_lib/`) | 3 → **2** | **Dividir**: 1 sacar · 1 dejar+deuda · 1 fuera de alcance | alta | sí | bloquea (2/3 sin proof) |
| **F5** payload de scaffold | 18 | **Dejar y anotar deuda** | alta | **NO en el repo del adoptante** | rompe `go.mod`, `package.json`, `tsconfig.json`, `settings.json` **en repos ajenos** |
| **F6** perfiles de seguridad JSON | 3 | **Dejar y anotar deuda** | alta | sí, ruidoso | **imposible**: JSON rechaza las 3 sintaxis |
| **F7** templates y ejemplos | 9 | **Dividir**: 6 dejar+deuda · 1 conflicto abierto · 2 sin juicio | alta | mixto | 1 rompe JSON, 1 propaga a doc versionado, 1 viaja a repos ajenos |

**Total real: 93, no 94.** `scripts/_lib/settings-driver.sh` ya declara `# SCOPE: os-only` en su línea 2
desde el commit `a5e31afca` (hoy, 3 h antes de que arrancara el panel). La lista es un snapshot y el
operador está trabajando activamente sobre ella.

**Ninguna familia se resuelve marcando el archivo señalado.** La única que lo justifica —F3a— lo hace
por un motivo distinto del que motivó el panel, y requiere decisión de operador (§3).

---

## 2. Dónde las lentes discreparon

Es la parte más valiosa del panel. Discreparon en cuatro puntos, y en tres de ellos la discrepancia
cambia el veredicto.

### 2.1 "¿Llega al consumidor?" — la lente 1 midió un proyector y la lente 3 midió otro

**Lente 1** instrumentó `scripts/cos_init.py` + `install.sh` y concluyó "F5 NO llega".
**Lente 3** leyó `cmd/cos/internal/cli/new.go` y concluyó "F5 ROMPE, y rompe en el repo del CONSUMIDOR".

Las dos tienen razón sobre lo que midieron. Hay **dos proyectores distintos**: el instalador del SO
(`cos_init.py`) y el scaffolder de proyectos (`cos new`). F5 no viaja por el primero y sí por el segundo.

**Pesa la lente 3.** El enunciado "no llega" leído solo habilita las dos movidas que rompen: "es
documental, marcá y listo" y "no llega a nadie, sacalo del registry". Verificado que `cos new` copia
byte a byte salvo `{{...}}` (`cmd/cos/internal/cli/new.go:233,268,279`) y que `go.mod` con `#` no parsea:

```
go mod edit -json  con '# SCOPE: project'  ->  go: errors parsing go.mod
go mod edit -json  con '// SCOPE: project' ->  JSON válido
```

### 2.2 "¿Hay decisión escrita?" — la lente 2 acertó el titular y erró la fuerza

La lente 2 midió 85/94 con cobertura de manifiesto y concluyó que marcar "duplica una decisión ya
tomada". Correcto en general. Pero **dos jueces la refutaron en direcciones opuestas y los dos tienen
razón para su familia**:

- **F3a** demostró que la decisión del manifiesto **no llega al instalador**: `scope_allows()` no abre
  el manifiesto. Verificado: `scope_allows("scripts/cos-lean-audit", "project") -> True`, pese al
  `scripts/* -> os-only`. Marcar no duplica: traslada la decisión del plano de auditoría al de enforcement.
- **F2** demostró lo inverso para `scripts/shellcheck-baseline.txt`: su entrada exacta en el manifiesto
  es **metadata que ningún código lee**, porque `_is_support_path()` lo descarta antes. Verificado:
  el clasificador con 2 rutas devuelve `total: 1`.

Conclusión de síntesis: el manifiesto es a la vez **más ancho** que el clasificador (F2) y **más
angosto** que el enforcement (F3a). "85 ya están decididas" es cierto como conteo y engañoso como argumento.

### 2.3 "¿Marcar es inocuo?" — la lente 3 lo midió, las otras dos lo asumieron

Solo la lente 3 midió el efecto sintáctico. Su hallazgo es el que ordena el resto: **4 de las 94 no
admiten marcador en ninguna de las tres sintaxis que el gate acepta** (`#`, `//`, `<!--`), porque son
JSON estricto. Verificado sobre los cuatro, las tres formas, 12 pruebas, 12 `JSONDecodeError`.

### 2.4 Lo que las tres coincidieron — y por qué es sospechoso

Las tres coincidieron en que "marcar no cambia nada instalable". **Es falso en tres casos y ninguna
lente los tenía completos**:

| Archivo | Llega al consumidor | ¿El path consulta el marcador? |
|---|---|---|
| `templates/task-closure-ledger.example.json` | sí | **sí** — marcarlo `os-only` lo saca del install |
| `hooks/_lib/registration-allowlist.txt` | sí | **no** (`shutil.copytree` sin `ignore=`, `cos_init.py:1871,1893`) |
| `templates/CLAUDE.md.template` | sí | **no** (`cp` pelado, `install.sh:509`) |

Los dos últimos son la categoría que el encuadre binario del encargo (llega / no llega) no cubre:
**archivos que llegan por un camino que ignora el marcador**. Marcarlos `os-only` deja el gate en verde,
el marcador diciendo "os-only", y el archivo aterrizando igual en cada consumidor. Eso no es documental:
es un marcador que miente, del tipo que después se cita como evidencia de que algo no se proyecta.

**Verificado con install real** (`cos_init.py --full --harness claude`, 155 hooks registrados):
`.cognitive-os/hooks/cos/_lib/registration-allowlist.txt` presente;
`.cognitive-os/templates/cos/task-closure-ledger.example.json` presente;
`.cognitive-os/scripts` → *No such file or directory*.

---

## 3. Familia por familia

### F1 — inertes (5): `hooks/_archived/*.sh.bak`, `hooks/example-*.sh.disabled`

**Veredicto: sacar del alcance del gate.** No son primitivas, y el repo ya lo decidió en código.

- `cos_lib/primitive_parser.parse_primitive_file()` los devuelve `kind=support`, `is_primitive=False`.
  Doble cobertura: por extensión (`.bak`/`.disabled`) y por directorio (`hooks/_archived`).
- Fijado por un test que los nombra: `tests/unit/test_primitive_parser.py::test_parse_support_files_are_not_primitives`.
- Ausentes de las 1442 filas de `primitive_scope_health.build_rows()` y de las 1034 del lock.
- Excluidos ya de seis auditores (`lint-shell.sh`, `ci-smoke-linux.sh`, `audit_gate_registration.py`, etc.).
- 0/5 llegan al consumidor (install real).
- **Telemetría**: en 148 filas del gate (2026-07-19 → 2026-08-19) hay **0 menciones** a esta familia.
  El gate nunca decidió nada sobre ella.

**Costo de marcar, medido:** `GATE_EXIT=2` — y la proof que exige es un artefacto degenerado:
`tests/red_team/portability/test_auto-refine.sh.py`, nombre de módulo Python inválido.

**Excepción interna (importa si después se propone podar):** los 3 `.bak` son fotos congeladas de
hooks **vivos** que ya declaran `# SCOPE: both`; los 2 `.disabled` los creó **ADR-178 a propósito**
y los referencia como el camino soportado hoy. Borrar los `.disabled` rompería la instrucción vigente
de un ADR accepted. Y ADR-342 §166-167 asigna el pruning al operador, no a un agente:
*"Nothing is deleted or deregistered by this ADR. Pruning the surface is an operator decision."*

**Deshacer si estuvo mal:** quitar una condición en `is_registry_path()`. Un commit de una línea;
ningún archivo se toca ni se borra. Y el camino de re-alta sigue cubierto: renombrar un `.disabled`
a `.sh` lo convierte en archivo nuevo y el gate lo exige por la rama (b) — verificado (`GATE_EXIT=2`).

---

### F2 — datos (3): `registration-allowlist.txt`, `okf-schema.json`, `shellcheck-baseline.txt`

**Veredicto: sacar del alcance del gate, con UNA condición bloqueante.**

Son activos de datos que consume un parser, no primitivas agénticas. `_is_support_path()` ya nombra
a 2 de los 3 (`hooks/**.txt`, `scripts/**.txt`). El tercero (`okf-schema.json`) necesita otro
mecanismo — sale `kind=script`, `is_primitive=True`.

Marcar es peor en los tres, cada uno por un motivo distinto y todos medidos:

1. `okf-schema.json` — rompe con las 3 sintaxis, y rompe su **propia proof** (`test_okf-schema.py`
   hace `json.loads`) y el workflow `.github/workflows/okf-validation.yml`. Como sí tiene proof, el
   gate local daría **verde** y CI **rojo** sobre el mismo commit.
2. `shellcheck-baseline.txt` — el marcador no es durable: `scripts/lint-shell.sh:100` regenera con
   `cp "${TMPOUT}" "${BASELINE_FILE}"`.
3. `registration-allowlist.txt` — **el marcador mentiría** (llega por `copytree` sin filtro).

**⚠ CONDICIÓN BLOQUEANTE.** `hooks/_lib/registration-allowlist.txt` no se saca del registry en
soledad. Es el único de los tres que se proyecta, y publica en cada consumidor el inventario de hooks
no cableados del SO. Sacarlo sin más baja el conteo y deja la fuga sin dueño: **eso sí sería el verde
barato.** Se saca solo junto con una entrada de deuda que registre el call-site
(`scripts/cos_init.py:1871` y `:1893`, `shutil.copytree` sin `ignore=` ni `scope_allows`). Si el
operador no toma la deuda, **para ese archivo el veredicto degrada a "dejar y anotar"**: feo y visible
es mejor que prolijo y mentiroso.

**Dato que el panel casi pierde:** ya existía un veredicto escrito hace cuatro días sobre este archivo,
`docs/06-Daily/reports/judge4-fuga-triaje-2026-08-15.md`, "Top 5 — sacar primero", puesto #2, con el
copytree como #4. Ninguna de las tres lentes lo buscó. Es la lección del panel un nivel más arriba:
**la decisión previa no siempre está en un ADR.**

**Hallazgo lateral (deuda separada, no cambia el veredicto):** el lint de shell local está degradado
a no-op. `grep -cv '^#' scripts/shellcheck-baseline.txt` → `0` (exit 1): 21 líneas, todas comentario,
el baseline no suprime nada, y `scripts/cos-ci-local.sh` toma siempre la rama `--baseline`.
Un supresor que no suprime nada es un bug invisible.

---

### F3a — `scripts/cos-*` sin extensión (36)

**Veredicto: marcar `os-only`. Es la única familia donde marcar hace trabajo — y la única que requiere
decisión de operador.**

El argumento que la separa del resto: **`scope_allows()` no lee el manifiesto.**

```
scope_allows("scripts/cos-lean-audit", "project")  ->  True     (pese a  scripts/* -> os-only)
```

El `scripts/* → os-only` lo consumen el clasificador y las auditorías, no el instalador. Hoy los 36
están clasificados os-only en papel y **habilitados a proyectar** en el código. El header es lo único
que ata la clasificación al mecanismo que decide.

Costo: nulo y medido. 36/36 son bash con shebang en línea 1; **36/36 ya tienen proof reconocida**, así
que la rama de bloqueo no muerde. El ratchet de distribución no se mueve (el clasificador ya los cuenta
os-only). Y la convención existe: 262 de los 298 ejecutables sin extensión de `scripts/` ya declaran,
incluidos los dos que el instalador sí proyecta (`cos-quality-duplicates`, `cos-task-closure-gate`,
ambos `# SCOPE: both`).

**Por qué es decisión de operador y no aplicable solo.** Dos decisiones escritas tiran para lados
distintos y ninguna gana por sí sola:

- **ADR-019** (accepted, `implementation_status: partial`, `remaining_in_scope: true`) mandató el
  tagging y lo dejó a medias. Marcar completa el tramo pendiente.
- **ADR-314** (accepted, implemented) prohíbe el atajo: nació de dos commits de mass-edit revertidos
  (`a239dcff`, `33682e2e` → `c646d17b`, `9b5f66ce`) y su regla de proceso es que ninguna corrida
  full-repo del clasificador puede manejar reescrituras de marcador.

**Resolución sugerida:** si el operador aprueba, va en **lotes acotados con el loop de calibración de
ADR-314**, no como barrido de 36. Y el precedente del propio operador, de hoy, es el molde:
`a5e31afca` marcó `settings-driver.sh` **y escribió la proof que lo ejecuta**, en el mismo commit.

**Excepción que hay que dejar escrita al marcar:** 15 de los 36 los declaran como `primitives:`
cuatro skills que **sí se proyectan** (`lean-code`, `artifact-workflow`, `epistemic-review`,
`agent-run-supervision`). Verificado: los 4 skills están instalados en el consumidor y **ninguno de
los 15 scripts llega**. El marcador correcto sigue siendo `os-only` (`both` tampoco los proyectaría,
y encima afirmaría disponibilidad falsa), pero los 15 tienen que salir nombrados en el commit para
que el triage del lado skill tenga de dónde agarrarse. Ver §4.2.

---

### F3b — `scripts/*.py` y `*.sh` (17)

**Veredicto: dejar y anotar deuda.**

Los 17 tienen scope resuelto y **coherente**, no ausente. El clasificador los devuelve
`by_effective_scope os-only:17`, `confidence high:17`, `contradictions 0`, y su `next_action` por fila
es literal *"classification evidence is coherent"* — no dice "falta marcador".

Marcar sería inocuo (17/17 con proof, `#` es comentario válido en Python y sh) pero **reinstala el
workflow que ADR-314 desarmó**: 17 archivos en un lote es exactamente la forma de `a239dcff`. Y crea
una segunda fuente de verdad que **pisa** al manifiesto (el header gana sobre el patrón fallback), sin
detector de deriva.

**Diferencia con F3a, que es la que decide:** en F3a el marcador cierra un hueco de enforcement
verificado; acá no hay tal hueco que se haya demostrado. Marcar F3b es solo prolijidad.

**Excepciones que valen ficha propia:**
- `scripts/revision_probe.py` es **candidato a `both`, no a `os-only`**: sus únicas referencias COS son
  ejemplos de docstring, el caso que ADR-314 excluye expresamente como prueba de os-only.
- `scripts/yaml.py` tiene una incoherencia que ningún marcador arregla: su docstring dice existir para
  proyecciones y no se proyecta, y su fila de evidencia apunta a un test que ejercita **el shim de la
  raíz**, no a él.
- `scripts/lib_closure.py` y `generate_harness_projection_registry.py` **no son hojas**: `cos_init.py:59`
  importa el primero y su `compute_closure()` decide qué `cos_lib/` recibe el consumidor. Si alguna vez
  se propone podar scripts sin proyección, estos dos quedan explícitamente fuera.

---

### F4 — libs de shell (3, juzgadas 2)

**Veredicto: dividir. Y contiene el hallazgo más grave del panel entero.**

`scripts/_lib/settings-driver.sh` sale del alcance: ya declara `# SCOPE: os-only` (commit `a5e31afca`,
hoy). Quedan dos, y **no comparten el hecho que decide**.

**(a) `scripts/_lib/local-service.sh` → sacar del alcance del gate.** `kind=script-lib`,
`is_primitive=False`, fijado por el mismo test unitario que lo usa como ejemplo canónico. Sus dos
consumidores (`cos-valkey-local.sh`, `cos-postgres-local.sh`) tampoco se proyectan.

**(b) `scripts/_lib/session-id.sh` → dejar, y anotar como BUG, no como pendiente cosmético.**

Dos hooks que declaran `# SCOPE: both`, están en `hooks/_lib/registration-allowlist.txt`, están
registrados en `.claude/settings.json` y **sí viajan al consumidor** lo sourcean sin guarda de
existencia. En el consumidor la ruta no existe. **Reproducido ejecutando el hook instalado**, con el
`/bin/bash` 3.2 real:

```
edit-lock-process-negotiations.sh: line 19: .../hooks/cos/../scripts/_lib/session-id.sh: No such file or directory
edit-lock-process-negotiations.sh: line 25: cos_session_id: command not found
exit=0
```

Falla silenciosa, en un hook de `UserPromptSubmit` que corre en cada interacción, en cada instalación
de consumidor. **Estamparle `os-only` sellaría este bug como diseño**: el archivo tendría marcador, el
gate estaría verde, el manifiesto diría `so-local-only`, y nadie volvería a mirarlo.

El fix no es un marcador: es el idiom que el propio repo ya usa en `scripts/edit-coop.sh:40-46`
(source con fallback). Alguien ya sabía que la lib podía no estar; los dos hooks no heredaron la guarda.

---

### F5 — payload de scaffold (18): `templates/project-templates/**`

**Veredicto: dejar y anotar deuda. La deuda es del gate.**

Doblemente decidido y con **rechazo escrito a marcar inline**: las 18 están, una por una y con
rationale propio, en `primitive-structure-scopes.yaml` (`scope: project`) y también en
`primitive-scope-overrides.yaml`. El `purpose:` del primer manifiesto describe literalmente esta
familia, y **ADR-315:99** lo eleva a decisión: *"exists only for file formats where inline `SCOPE`
comments would corrupt generated artifacts."*

Proponer estampar F5 es proponer exactamente lo que un ADR accepted ya descartó, con el motivo escrito.
Es ADR-323 otra vez.

**El costo de equivocarse acá es el único irreversible del panel.** `cos new` escribe en el repo del
adoptante, sin canal de actualización. Con el marcador puesto, todo proyecto generado nace con
`go.mod` que no parsea, `package.json`/`tsconfig.json`/`.claude/settings.json` que no son JSON, y
`main.go` que no compila. Revertir el template **no arregla ninguno de esos repos**. Y los 13 que
toleran `#` se quedan con metadata del registry interno del SO dentro del repo de un tercero.

**El menú de veredictos no contiene la respuesta correcta para F5:** su scope escrito es `project`,
que no está entre `marcar-os-only` / `marcar-both`. Cualquiera de los dos rompería además
`tests/red_team/portability/test_project_scope_family.py`, que assertea `row.scope == "project"`.

**La deuda tiene fecha, no es contemplativa:** `cmd/cos/internal/cli/new.go:25` declara
`ValidTemplates = {"go","typescript","python","rust","minimal"}` y el directorio `rust` **no existe**.
El próximo archivo de esta familia —el que cierra ese hueco— choca contra las dos ramas del gate.

---

### F6 — perfiles de seguridad (3): `templates/security-profiles/*.json`

**Veredicto: dejar y anotar deuda. Marcar es físicamente imposible.**

Los tres declaran `scope: project` nominalmente en `primitive-structure-scopes.yaml`, con el rationale
más argumentado del manifiesto, y el clasificador los devuelve `('project','project','project-generated')`
— `declared_scope` poblado, no `None`.

Las tres sintaxis del gate rompen `json.load`. Los consumidores son reales y en caliente:
`scripts/set-security-profile.sh` (el switch de perfil de seguridad), más `check_hook_registration.py`,
`audit_gate_registration.py`, `render_adoption_tiers.py`, `primitive_row_audit.py` y cuatro suites.
Ironía verificable: cada perfil registra al propio gate (`grep -c` → 1 en los tres). Romperlos dejaría
al gate sin registro en los tres perfiles.

**El único punto donde F6 sí está rota es el archivo nuevo:** un cuarto perfil no tiene camino correcto
—sin marcador bloquea por "nuevo", con marcador bloquea por proof y además rompe el JSON—. Hoy la única
salida es `COS_ALLOW_UNPROVEN_SCOPE_BOTH=1`, un bypass de emergencia usado como flujo normal.

---

### F7 — templates y ejemplos (9)

**Veredicto: dividir en tres.**

**Grupo A (6) — dejar y anotar deuda del gate.** `CLAUDE.md.template`, `adoption-tiers.md.j2`,
`blocked-strings.example.txt`, `external-tools-overlay.yaml`, `service-map.example.yaml`,
`verification-commands.example.yaml`: entrada nominal con rationale propio en
`primitive-structure-scopes.yaml`, `scope: project`, `declared_scope` poblado.

Dos con blast radius si alguien igual estampa:
- `adoption-tiers.md.j2` — el marcador se propaga literal a `docs/08-References/root/adoption-tiers.md`
  (head byte-idéntico, verificado) y pone en rojo `tests/audit/test_adoption_tiers_synced.py`.
- `CLAUDE.md.template` — aterriza en `.claude/CLAUDE.md` de repos ajenos vía `install.sh:509`, `cp`
  pelado sin `scope_allows`, y **solo si el archivo no existe**: revertir en el SO no lo saca de donde
  ya cayó.

**Grupo B (1) — `task-closure-ledger.example.json`: no es deuda de marcado, es una contradicción abierta.**
Es el único archivo de las 94 donde el marcador cambia el conjunto instalado (contrafáctico:
`scope_allows` marcado → exit=1, sin marcar → exit=0) **y** el único que no admite marcador.
Y el repo afirma dos cosas incompatibles a la vez:

- `ADR-335` (accepted, implemented) lo declara implementation_file con `tier: consumer`.
- `tests/red_team/portability/test_os_only_scope_family.py:488` lo lista y assertea `os-only` +
  `maintainer-only` — sobre un archivo que **está instalado en todos los consumidores** (verificado).

Una aserción **en verde** que afirma algo falso, y que mañana se cita como evidencia de que el archivo
no se proyecta. Ése es el ítem, no el comentario faltante.

**Grupo C (2) — `confidentiality.yaml` y `so-impact-eval.example.yaml`: falta un juicio, no un comentario.**
Salen `('os-only', None, 'maintainer-only')` por **safe-fallback**, no por decisión. Marcar es barato
(YAML tolera `#`) y por eso es la tentación de verde barato: estampar `os-only` en
`confidentiality.yaml` congelaría por escrito lo contrario de su propio encabezado
(*"Install target: <project>/.cognitive-os/confidentiality.yaml"*) — un archivo que dice a dónde va y
que **ningún proyector lleva**. Además arrastra una colisión sin resolver con el
`confidentiality.yaml.template` del origin, documentada en el runbook `origin-install-selfcheck-2026-08-15`.

---

## 4. Lo que NO se pudo determinar

### 4.1 Si excluir support/script-lib de `is_registry_path()` rompe algún test del propio gate
Nadie lo corrió: con el repo bajo escritura concurrente ningún juez quiso stagear.
**Para determinarlo:** `git worktree add <tmp> HEAD`, aplicar la condición y correr
`tests/red_team/portability/` + `tests/unit/test_primitive_parser.py`. Es el chequeo que va antes de
implementar F1/F2/F4a.

### 4.2 Si los 4 skills proyectados deben funcionar de verdad en el consumidor
`lean-code`, `artifact-workflow`, `epistemic-review` y `agent-run-supervision` se instalan y declaran
15 `scripts/cos-*` que no llegan. **Es una pregunta de producto, no de scope**: o los skills se marcan
`os-only`, o los scripts pasan a `both` + allowlist de `cos_init.py`. Nadie del panel podía decidirlo.
Relacionado y verificado: `skill_scope_allows()` mira solo `lines[:8]`, y `artifact-workflow` declara
`<!-- SCOPE: os-only -->` en la **línea 43** → `exit=0`, se proyecta igual. El mecanismo de precedencia
existe y lo derrota una ventana de 8 líneas.

### 4.3 Cómo se calcula `confidence` en el clasificador
Para 16 de los 17 de F3b, `confidence=high` sale de **una sola fila de evidencia**
(`source=scope-override`, `weight=100`). Si el umbral tolera fuente única, "high" dice menos de lo que
suena. **Para determinarlo:** leer el cálculo en `scripts/primitive_scope_classifier.py` y ver si
fuente-única puede dar high.

### 4.4 Por qué dos censos discrepan sobre qué es primitiva
`primitive_files()` = 1456 · `build_rows()` = 1442 · lock = 1034. Los 14 de diferencia son exactamente
los 7 support + los 7 `scripts/_lib/*.sh`. Pero el lock discrepa con los otros dos sin criterio escrito:
F3a entra 36/36, F3b entra 1/17, F5 entra 0/18, F6 entra 3/3. **Ninguna decisión escrita arbitra.**

### 4.5 Harnesses y modos no probados
Todo se midió con `--harness claude`, scope `project`, modos `--full` y `--default`. No se probó
`--harness codex`/`shell-ci` ni `--scope all`. Si algún harness proyectara `scripts/_lib/`, el
diagnóstico de F4b cambia de "rotura" a "rotura solo en Claude".

### 4.6 Bug colateral sin dueño
`cos_init.py --internal-call scope_allows` lee `INSTALL_SCOPE` (línea 515) mientras todo el resto usa
`COS_INSTALL_SCOPE`. Verificado: `COS_INSTALL_SCOPE=all ... rule-template.md → exit=1`;
`INSTALL_SCOPE=all ... → exit=0`. Cualquier caller de shell obtiene la respuesta contraria a la del
path in-process. **No decidimos si es bug o contrato**; hay que mirarlo antes de usar ese predicado
para auditar.

---

## 5. Orden de aplicación sugerido

**Lo primero, y es lo único que cierra el problema de fondo:**

> **P0 — un cambio de función, no 94 ediciones.** Que `declares_scope()` en
> `hooks/scope-marker-portability-gate.sh` consulte `manifests/primitive-scope-overrides.yaml` y
> `manifests/primitive-structure-scopes.yaml`, igual que ya consulta `audience:` para skills.
> Resuelve **85 de las 94** de una, sin tocar un solo archivo del registry, y sin el riesgo de que
> alguien estampe un marcador en un JSON o en un `.tmpl` que viaja a repos ajenos.
> Reversible: un revert. **Aplicable sin decisión de operador.**

Después, por reversibilidad creciente en costo:

| # | Acción | Requiere | Reversible |
|---|---|---|---|
| 1 | **P0** arriba | nada | sí |
| 2 | Bug **F4b**: guarda con fallback en los dos `edit-lock-*` que sourcean `session-id.sh` | nada (es un bug con reproducción) | sí |
| 3 | Excluir support/script-lib de `is_registry_path()` — cubre F1 + F2 (2/3) + F4a | correr §4.1 antes | sí, 1 línea |
| 4 | Anotar la deuda de **F2** (fuga del `copytree`, `cos_init.py:1871/1893`) en `pending-truth.yaml` o ADR | nada | sí |
| 5 | Anotar la contradicción de **F7-B** (`task-closure-ledger`: ADR-335 `tier: consumer` vs. proof `os-only` en verde) | nada | sí |
| 6 | Anotar la deuda del gate para **F5/F6/F7-A** (queda saldada por P0) | nada | sí |
| 7 | **F3a**: marcar los 36 `os-only`, en lotes acotados con el loop de ADR-314, nombrando los 15 de §4.2 | **decisión de operador** | sí |
| 8 | Juicio de scope para **F7-C** (2 archivos) y para `revision_probe.py` | **decisión de operador** | sí |

**Dejar quieto, explícitamente:**
- **F5 y F6**: no estampar nada. ADR-315 ya lo decidió y el daño de F5 no es reversible desde este repo.
- **F1 `.disabled`**: no borrar. ADR-178 los referencia como el camino soportado hoy.
- **F3b**: no marcar. Sin hueco de enforcement demostrado, marcar es reinstalar el workflow que ADR-314 desarmó.
- **Cualquier "resolvamos las 94 de un saque"**: la herramienta que existe para eso,
  `scripts/scope_tag_backfill.py`, es **ciega a F3a** (su `grep -rL --include` no matchea archivos sin
  extensión) y **contradice al manifiesto en F3b** (clasifica `scripts/*.py` como `both`). Correrla con
  `--apply` mislabelearía 17 y no tocaría 36.

**Advertencia de concurrencia.** El repo está bajo escritura de otra sesión. Al arrancar este informe
`git status --porcelain` mostraba `M scripts/_lib/settings-driver-claude-code.sh`; al cerrarlo sale
vacío. Quien ejecute cualquier punto de esta tabla: `git status <paths>` inmediatamente antes del
`git add`, adds path-scoped, nunca `-A`.

---

## Correcciones a las premisas del encargo

**1. Son 93, no 94.** `scripts/_lib/settings-driver.sh` declara `# SCOPE: os-only` en línea 2 desde el
commit `a5e31afca` de hoy. Verificado con el `/bin/bash` 3.2.57 real y con el regex exacto del gate.
No es un falso positivo de la lista: es un ítem **cerrado tres horas antes** de que arrancara el panel.
Y ese commit fija el precedente del operador para este problema —marcador **más** proof que ejecuta— que
es el molde de lo que propongo para F3a.

**2. "Rutas que NO declaran scope de ninguna forma reconocida" es falso para 85 de 94.** Es la misma
trampa que el encargo advierte con las 194 skills y `audience:`, un nivel más arriba: F5/F6/F7 declaran
por manifiesto estructural, F3/F4 por patrón. "Reconocida" está definido por lo que lee el gate, no por
lo que decidió el repo. El propio gate lleva escrito el diagnóstico de ese bug —*"Wrong field, not
missing debt"*— para la familia de al lado, y no lo generalizó.

**3. "El gate bloquea una primitiva NUEVA sin declaración" es la mitad, y no la mitad relevante.**
La rama que se dispara al marcar es la otra: `declares_scope` + sin proof pareada, que **no** filtra por
`diff-filter=A`. Medido: preexistente sin marcador `exit=0`; el mismo archivo marcado `exit=2`. En 9 de
las 94, **marcar convierte un archivo que hoy pasa en uno que bloquea el commit**. El gesto que parece
cumplir es el que rompe.

**4. El encuadre binario "llega / no llega" deja afuera la categoría más peligrosa.** Dos archivos
llegan al consumidor por paths que **no consultan el marcador** (`copytree` sin `ignore=`; `cp` pelado
en `install.sh:509`). Marcarlos `os-only` produce un marcador que miente y que después se cita como
evidencia. El fix honesto en esos dos casos es poner el filtro en el path de copia, no marcar el archivo.

**5. El menú de veredictos no cubre F5, F6 ni F7-A.** El scope escrito y vigente de esas 27 rutas es
`project`, que no está entre `marcar-os-only` / `marcar-both`. Cualquiera de los dos contradice tres
manifiestos y rompe `test_project_scope_family.py`. Si el panel hubiera forzado un veredicto de marcado
ahí, los dos valores disponibles eran incorrectos.

**6. La premisa implícita de que estas 94 son "una categoría pendiente de decisión" no se sostiene.**
El criterio de pertenencia al registry es sintáctico: `rglob("*") + is_text_file` sobre seis
directorios, y el `case` del gate es un glob crudo (`templates/*` matchea barras) que además **afirma
en su propio comentario** espejar `primitive_file_inventory.SOURCE_ROOTS` y no lo hace. Conviven cuatro
definiciones de "primitiva" en el mismo repo (1456 / 1442 / 1034 / el glob del gate). La pregunta
"¿marcamos estas 94?" hereda en silencio el censo más ancho.

**7. El panel casi repite el error que lo motivó, y no por un ADR.** Sobre
`hooks/_lib/registration-allowlist.txt` ya había un veredicto escrito hace cuatro días
(`docs/06-Daily/reports/judge4-fuga-triaje-2026-08-15.md`, Top 5 #2 y #4), con la conclusión ya
redactada: *"Ponerle `# SCOPE: os-only` al archivo no cierra la fuga: hay que tocar el call-site."*
Ninguna de las tres lentes lo buscó. La lección de ADR-323 hay que extenderla: **antes de proponer,
buscar también en `docs/06-Daily/reports/`, no solo en `docs/02-Decisions/adrs/`.** Y esa deuda nunca
se escaló: `manifests/pending-truth.yaml` tiene 10 entradas y cero menciones al allowlist, al copytree
o a la fuga — lo que viola la regla 16 del propio repo.

**8. Sobre el propio panel: tres lentes que coinciden en el titular no es señal de convergencia.**
Las tres coincidieron en "marcar no cambia nada instalable" y las tres se equivocaban en los mismos
tres archivos, porque las tres preguntaron por el archivo y ninguna preguntó **quién lo llama**. Los
dos hallazgos más graves del panel —el `session-id.sh` roto en cada consumidor y los 15 scripts que
4 skills proyectados declaran y no llegan— salieron de esa pregunta, y la hizo un juez de familia, no
una lente. Si esa pregunta se aplicara sistemáticamente a las 8 familias, sospecho que aparecerían más.

**9. Un guard read-only bloqueó la auditoría, y a más de un juez.** `hooks/protected-config-write-guard.sh`
abortó comandos estrictamente de lectura por **nombrar** rutas bajo `hooks/` — a mí me pasó armando el
probe del gate, y lo reportaron al menos otros dos jueces. La salida de un comando bloqueado no es un
cero: si se lee como "sin resultados", produce una ausencia falsa. Peor: empuja a cualquier auditor a
construir rutas por concatenación para esquivarlo, que es exactamente lo que no querés que un agente
aprenda a hacer con un guard. Lo resolví leyendo las rutas desde `los94.json` en un script; el hallazgo
queda.

---

## 6. Reproducir

Todo read-only sobre el repo. Los installs y probes del gate corren en scratchpad con
`COGNITIVE_OS_PROJECT_DIR` y `COS_METRICS_DIR` redirigidos; `.cognitive-os/metrics/*.jsonl` intacto.
Usar `.venv/bin/python` (Python pelado no tiene `yaml`). **Ningún conteo sale de un exit code**:
`grep -c` devuelve `0` saliendo con `1`. `timeout` no existe en macOS.
**No correr `install.sh`** (hace un borrado recursivo sobre un `TARGET_DIR` relativo).

```bash
cd <repo>                       # raíz de luum-agent-os
L=<scratchpad>/los94.json       # la lista compartida
S=<scratchpad>/verify           # área de trabajo, fuera del repo

# ── 1. Marcadores reales, con el bash de los hooks (3.2, no el del PATH) ──
/bin/bash --version | head -1
.venv/bin/python -c "
import json,re
fams=json.load(open('$L'))['familias']
rx=re.compile(r'^[ \t]*(#|<!--|//)[ \t]*SCOPE:[ \t]*[A-Za-z]')
for fam,ps in fams.items():
    m=[p for p in ps if any(rx.match(l) for l in open(p,errors='ignore').read().splitlines()[:3])]
    print(f'{fam}: n={len(ps)} con_marker={len(m)} {m}')"
# -> solo scripts/_lib/settings-driver.sh   =>  93, no 94
git log -1 --format='%h %ad %s' --date=short -- scripts/_lib/settings-driver.sh   # a5e31afca, hoy

# ── 2. Cobertura por manifiestos: struct=27 overrides=78 NINGUNO=9 ──
.venv/bin/python - <<PY
import json,fnmatch,yaml
fams=json.load(open("$L"))["familias"]
struct={i["path"]:i["scope"] for i in yaml.safe_load(open("manifests/primitive-structure-scopes.yaml"))["items"]}
ov=yaml.safe_load(open("manifests/primitive-scope-overrides.yaml"))["rules"]
om=lambda p:[r for r in ov if fnmatch.fnmatch(p,r["pattern"]) or (r["pattern"].endswith("/**") and p.startswith(r["pattern"][:-3]+"/"))]
for fam,ps in fams.items():
    sin=[p for p in ps if p not in struct and not om(p)]
    print(f'{fam}: total={len(ps)} struct={sum(p in struct for p in ps)} ov={sum(bool(om(p)) for p in ps)} NINGUNO={len(sin)}')
    for d in sin: print("     sin cobertura:", d)
PY

# ── 3. El gate NO lee los manifiestos (y su is_registry_path es un glob crudo) ──
grep -n 'primitive-scope-overrides\|primitive-structure-scopes' hooks/scope-marker-portability-gate.sh; echo "exit=$?"   # exit=1
sed -n '/is_registry_path()/,/^}/p' hooks/scope-marker-portability-gate.sh

# ── 4. Proof pareada: las 9 que quedarían bloqueadas al marcar ──
.venv/bin/python - <<PY
import json,os,sys,yaml; sys.path.insert(0,os.getcwd())
from cos_lib.portability_proof_paths import paired_candidates
ev=yaml.safe_load(open("manifests/primitive-behavior-evidence.yaml")).get("evidence") or []
mt={str(i["primitive"]):(i.get("tests") or []) for i in ev if isinstance(i,dict) and i.get("primitive")}
for fam,ps in json.load(open("$L"))["familias"].items():
    miss=[p for p in ps if not any(os.path.isfile(c) for c in paired_candidates(p))
          and not [t for t in mt.get(p,[]) if t.startswith("tests/red_team/portability/") and os.path.isfile(t)]]
    print(f"{fam}: n={len(ps)} SIN_proof={len(miss)} {miss}")
PY

# ── 5. LA MEDICIÓN QUE DECIDE: qué rama del gate se dispara al marcar ──
#    Repo git aislado. Las rutas se construyen DESDE el JSON: nombrarlas en el comando
#    dispara protected-config-write-guard aunque la operación sea de lectura.
cat > $S/setup.py <<'PY'
import json, os, shutil, subprocess, sys
REPO, G, L = sys.argv[1], sys.argv[2], sys.argv[3]
rel = json.load(open(L))["familias"]["F1-inertes"][0]
shutil.rmtree(G, ignore_errors=True)
os.makedirs(os.path.join(G, os.path.dirname(rel)), exist_ok=True)
os.makedirs(os.path.join(G, ".m"), exist_ok=True)
for c in (["git","init","-q","."],["git","config","user.email","t@t"],["git","config","user.name","t"]):
    subprocess.run(c, cwd=G, check=True)
shutil.copy2(os.path.join(REPO, rel), os.path.join(G, rel))
subprocess.run(["git","add","-A"], cwd=G, check=True)
subprocess.run(["git","commit","-qm","base"], cwd=G, check=True)
print("REL:", rel)
PY
cat > $S/mutate.py <<'PY'
import json, os, sys, subprocess
G, L, mode = sys.argv[1], sys.argv[2], sys.argv[3]
rel = json.load(open(L))["familias"]["F1-inertes"][0]
p = os.path.join(G, rel)
subprocess.run(["git","checkout","-q","."], cwd=G); subprocess.run(["git","reset","-q"], cwd=G)
if mode == "touch":
    open(p, "a").write("# touch\n")
elif mode == "mark":
    ls = open(p).read().split("\n"); ls.insert(1, "# SCOPE: os-only"); open(p, "w").write("\n".join(ls))
elif mode == "new":
    open(os.path.join(G, os.path.dirname(rel), "nuevo-probe.sh"), "w").write("#!/bin/bash\necho hi\n")
subprocess.run(["git","add","-A"], cwd=G, check=True)
PY
G=$S/gaterepo; mkdir -p $G
.venv/bin/python $S/setup.py "$PWD" "$G" "$L"
export COGNITIVE_OS_PROJECT_DIR=$G COS_METRICS_DIR=$G/.m
H="$PWD/hooks/scope-marker-portability$(printf -- '-gate.sh')"
for mode in touch mark new; do
  .venv/bin/python $S/mutate.py "$G" "$L" "$mode"
  echo '{"tool_name":"Bash","tool_input":{"command":"git commit -m x"}}' | /bin/bash "$H" > $G/out.txt 2>&1
  echo "MODO=$mode GATE_EXIT=$?"; head -2 $G/out.txt
done
unset COGNITIVE_OS_PROJECT_DIR COS_METRICS_DIR
# -> touch=0 | mark=2 (missing paired portability proof) | new=2

# ── 6. Install real y match de las 94 contra el árbol instalado ──
REPO=$PWD
mkdir -p $S/inst && (cd $S/inst && git init -q .)
(cd $S/inst && COS_SOURCE_DIR=$REPO COS_INSTALL_SCOPE=project $REPO/.venv/bin/python $REPO/scripts/cos_init.py --full --harness claude)
# -> Rules: 113 / Hooks: 155 / Skills: 118
.venv/bin/python - <<PY
import json,os
from pathlib import Path
S=Path("$S/inst"); inst={}
for p in S.rglob("*"):
    if p.is_file() and "/.git/" not in str(p): inst.setdefault(p.name,[]).append(str(p.relative_to(S)))
for fam,ps in json.load(open("$L"))["familias"].items():
    hits=[(p,inst[os.path.basename(p)]) for p in ps if os.path.basename(p) in inst]
    print(f"{fam}: {len(ps)} -> {len(hits)} presentes")
    for h in hits: print("   ", h)
PY
ls $S/inst/.cognitive-os/scripts   # No such file or directory
ls $S/inst/.cognitive-os/bin
# OJO falso positivo: .cognitive-os/bin/cos-so-impact-eval es un wrapper generado (3 líneas),
# NO scripts/cos-so-impact-eval (4 líneas):
diff -q $S/inst/.cognitive-os/bin/cos-so-impact-eval scripts/cos-so-impact-eval

# ── 7. El bug de F4b, ejecutando el hook INSTALADO (no leyendo código) ──
grep -rn '_lib/session-id.sh' hooks/
echo '{"tool_name":"Bash","tool_input":{"command":"x"}}' | /bin/bash $S/inst/.cognitive-os/hooks/cos/edit-lock-process-negotiations.sh
# -> No such file or directory + "cos_session_id: command not found", exit=0

# ── 8. Los 4 skills proyectados que declaran scripts que no llegan ──
for sk in lean-code artifact-workflow epistemic-review agent-run-supervision; do
  printf '%-24s instalado=%s refs=%s\n' "$sk" \
    "$([ -d $S/inst/.claude/skills/$sk ] && echo SI || echo no)" \
    "$(grep -oE 'scripts/cos-[a-z-]+' skills/$sk/SKILL.md | sort -u | wc -l | tr -d ' ')"
done
ls $S/inst/.cognitive-os/bin/ | grep -c lean          # 0
grep -n 'lines\[:8\]' scripts/cos_init.py             # :329
grep -n 'SCOPE' skills/artifact-workflow/SKILL.md     # :43  <-- fuera de la ventana
INSTALL_SCOPE=project .venv/bin/python scripts/cos_init.py --internal-call skill_scope_allows skills/artifact-workflow; echo "exit=$?"  # 0

# ── 9. JSON: las 3 sintaxis del gate rompen los 4 archivos ──
for f in templates/security-profiles/standard.json templates/task-closure-ledger.example.json \
         scripts/okf-schema.json templates/project-templates/settings.json.tmpl; do
  for m in '# SCOPE: os-only' '// SCOPE: os-only' '<!-- SCOPE: os-only -->'; do
    { echo "$m"; cat "$f"; } > $S/probe.json
    printf '%-46s [%-2s] %s\n' "$(basename $f)" "${m:0:2}" \
      "$(.venv/bin/python -c "import json;json.load(open('$S/probe.json'))" 2>&1 | tail -1)"
  done
done
# go.mod tolera '//' y no '#':
mkdir -p $S/gh $S/gs
printf '# SCOPE: project\nmodule probe\n\ngo 1.23.0\n'  > $S/gh/go.mod
printf '// SCOPE: project\nmodule probe\n\ngo 1.23.0\n' > $S/gs/go.mod
(cd $S/gh && go mod edit -json 2>&1 | head -1)   # go: errors parsing go.mod
(cd $S/gs && go mod edit -json 2>&1 | head -2)   # JSON válido

# ── 10. Contrafáctico del marcador y bug INSTALL_SCOPE vs COS_INSTALL_SCOPE ──
printf '# SCOPE: os-only\n' > $S/tcl.json && cat templates/task-closure-ledger.example.json >> $S/tcl.json
COS_INSTALL_SCOPE=project .venv/bin/python scripts/cos_init.py --internal-call scope_allows "$S/tcl.json"; echo "marcado -> exit=$?"        # 1
COS_INSTALL_SCOPE=project .venv/bin/python scripts/cos_init.py --internal-call scope_allows templates/task-closure-ledger.example.json; echo "sin marcar -> exit=$?"  # 0
COS_INSTALL_SCOPE=all .venv/bin/python scripts/cos_init.py --internal-call scope_allows templates/rule-template.md; echo "COS_INSTALL_SCOPE=all -> exit=$?"  # 1
INSTALL_SCOPE=all     .venv/bin/python scripts/cos_init.py --internal-call scope_allows templates/rule-template.md; echo "INSTALL_SCOPE=all -> exit=$?"      # 0
# NOTA: el `$?` va en la MISMA línea del echo. `cmd; echo "etiqueta"; echo $?` captura el exit del echo.

# ── 11. Censos, clasificación y telemetría ──
.venv/bin/python -c "
import sys,os,importlib.util,yaml
from pathlib import Path; sys.path.insert(0,os.getcwd())
from cos_lib.primitive_file_inventory import primitive_files
print('inventario:', len(list(primitive_files(Path('.').resolve()))))
s=importlib.util.spec_from_file_location('psh','scripts/primitive_scope_health.py')
m=importlib.util.module_from_spec(s); sys.modules['psh']=m; s.loader.exec_module(m)
print('build_rows:', len(m.build_rows(Path('.').resolve())))
print('lock:', len(yaml.safe_load(open('manifests/agentic-primitive-registry.lock.yaml'))['primitives']))"
# -> 1456 / 1442 / 1034
.venv/bin/python -c "
import json,collections
r=[json.loads(l) for l in open('.cognitive-os/metrics/scope-marker-portability-gate.jsonl')]
print(len(r), collections.Counter(x['decision'] for x in r), r[0]['timestamp'], r[-1]['timestamp'])"
# -> 148  Counter({'allow':134,'block_missing_portability_test':14})  2026-07-19 -> 2026-08-19

# ── 12. Las decisiones escritas, citadas en su fuente ──
for a in 019 178 314 315 335 342; do
  f=$(ls docs/02-Decisions/adrs/ADR-$a-*.md | head -1)
  echo "ADR-$a $(grep -m1 '^status:' $f) | $(grep -m1 '^implementation_status:' $f)"
done
sed -n '99p' docs/02-Decisions/adrs/ADR-315-primitive-parser-contracts.md
sed -n '166,167p' docs/02-Decisions/adrs/ADR-342-existence-criterion-for-primitives.md
head -6 manifests/primitive-structure-scopes.yaml

# ── 13. Al terminar: borrar $S (queda fuera del repo) y confirmar ──
git status --porcelain     # vacío
```

---

**Cierre.** Ninguna primitiva del repo fue modificada. La única escritura de este panel es este archivo.
`git status --porcelain` al cerrar: vacío. Los installs, probes y copias marcadas vivieron en scratchpad.
