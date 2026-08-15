# ADRs contra la realidad del código — censo 2026-08-15

**Pregunta:** de los 502 ADRs, ¿cuáles todavía describen el código?

**Criterio,** el de ADR-342 trasladado una capa arriba: *un ADR describe la
realidad cuando lo que afirma se puede verificar contra el código, y la
verificación no sale del propio ADR.*

**Entregable principal:** `scripts/audit_adr_path_reality.py` — el censo que
faltaba. Antes de hoy ningún script verificaba que un ADR siguiera
describiendo el código.

---

## 1. Cuántos ADRs afirman algo verificable

Un ADR sólo puede estar desfasado si afirma algo comprobable. Primera
medición, sobre el campo `implementation_files` del frontmatter:

| Clase | ADRs |
|---|---|
| `implementation_files` ausente o vacío | 353 |
| `implementation_files` apuntando **sólo al propio ADR** | 2 |
| `implementation_files` nombrando código real | 147 |

```console
$ python3 - <<'EOF'   # (script completo al pie de esta sección)
... recorre docs/02-Decisions/adrs/ADR-*.md y clasifica el frontmatter
EOF
no frontmatter......................... 0
implementation_files empty/absent...... 353
implementation_files ONLY the ADR itself 2
implementation_files naming real code.. 147
```

**El 70% del corpus (353/502) no hace ninguna afirmación verificable por
frontmatter.** No es un defecto en sí — muchos son decisiones de política sin
archivo asociado — pero define el techo de cualquier auditoría automática que
se apoye sólo en ese campo.

Los 2 auto-referenciales son la forma más pura del problema que ADR-342
describe: **la única respuesta sale de la primitiva misma.** Uno de ellos es
ADR-008 (ver §5).

El campo, cuando existe, es confiable: **de los 3088 pares (ADR, ruta)
detectados, cero hallazgos provienen del frontmatter — los 129 salen de la
prosa.** Lo que se mantiene a máquina no derivó; lo que se escribió a mano, sí.

---

## 2. El censo construido: `audit_adr_path_reality.py`

Cubre la señal 1 del encargo (rutas fantasma), que es la más barata y la más
concluyente: un ADR que nombra un archivo inexistente es detectable
mecánicamente.

```console
$ python3 scripts/audit_adr_path_reality.py --ignore-baseline
ADRs scanned................ 502
ADRs asserting a repo path.. 472
path claims (adr,path)...... 3088
distinct paths named........ 1706
suppressed (with reason).... 0
illustrative placeholders... 4
runtime artifacts (ignored). 99
PHANTOM PATHS............... 129
  of which relocated........ 16
historical mentions (info).. 57
```

**129 rutas fantasma en 60 ADRs** (113 desaparecidas, 16 con el mismo basename
en otro lado). Determinista:

```console
$ a=$(python3 scripts/audit_adr_path_reality.py --ignore-baseline --json | shasum -a 256)
$ b=$(python3 scripts/audit_adr_path_reality.py --ignore-baseline --json | shasum -a 256)
$ [ "$a" = "$b" ] && echo DETERMINISTIC
DETERMINISTIC
```

### Qué NO cuenta, y por qué

El encargo advertía sobre el verde barato de este lote: *marcar ADRs como
desfasados por coincidencia de texto sin abrir el código*. La medición cruda
daba **275**. Los 146 descartados salieron de cuatro reglas, cada una
mecánica y con motivo escrito:

| Descartado | Cantidad | Motivo |
|---|---|---|
| Artefactos de runtime (`git check-ignore`) | 99 | `.cognitive-os/metrics/*.jsonl` y similares se generan al correr. Su ausencia en un checkout es el comportamiento esperado, no deriva documental. |
| Lado izquierdo de tablas de renombre | 52 | Una fila `\| viejo \| nuevo \|` nombra la ruta de la que se renombró. Que falte es el registro funcionando, no pudriéndose. |
| Prosa explícitamente histórica | (dentro de los 57) | "removed", "no longer", "replaced by", "ya no". |
| Basenames de ejemplo | 4 | `hooks/x.sh`, `tests/unit/test_foo.py` — marcadores en ejemplos, no rutas. |

Dos decisiones más, contra el mismo riesgo:

- **Bloques cercados (```` ``` ````) no se escanean.** Contienen YAML de
  ejemplo y salida de muestra; sus rutas son ilustrativas por construcción.
- **El primer segmento de la ruta tiene que ser una entrada real del repo.**
  Elimina URLs, nombres de módulo con puntos, y rutas de otros proyectos antes
  de que puedan convertirse en un falso "archivo faltante".

### Symlinks — la trampa que el encargo señaló

`hooks/` es una granja de symlinks hacia `packages/*/hooks/`. La existencia se
resuelve con `os.path.exists`, que **sigue** los enlaces; nunca contra el
índice de git. Control positivo y negativo:

```console
$ readlink -f hooks/inject-phase-context.sh    # existe vía symlink
<repo>/hooks/inject-phase-context.sh
$ python3 scripts/audit_adr_path_reality.py --ignore-baseline --json | grep -c inject-phase-context
0                                               # correctamente NO reportado

$ ls hooks/rotate-metrics.sh
ls: hooks/rotate-metrics.sh: No such file or directory   # reportado, y es real
```

### El ratchet, medido después de medir

```console
$ python3 scripts/audit_adr_path_reality.py --write-baseline
baseline written: max_findings=129
$ python3 scripts/audit_adr_path_reality.py; echo "exit=$?"
exit=0
```

Baseline en `manifests/adr-path-reality-baseline.json` = **129**, el número
medido, no uno elegido. El script implementa la contracara que `gates-sin-trampa`
exige: **un baseline por encima de la realidad es un colchón, y acá es un error,
no un pase.**

```console
$ # baseline manipulado a 139 (10 por encima de la realidad)
$ python3 scripts/audit_adr_path_reality.py; echo "exit=$?"
ERROR: baseline 139 sits above reality 129 -- a ratchet above the
measurement is a cushion. Re-run with --write-baseline.
exit=2
```

Códigos de salida: `0` sin hallazgos nuevos, `1` por encima del baseline, `2`
error o colchón. Las supresiones viven en
`manifests/adr-path-reality-suppressions.json` y **el script falla si una
supresión no trae motivo escrito**.

---

## 3. Alto impacto: la contradicción que se inyecta a cada sub-agente

**ADR-064 — confirmado, y peor de lo que decía el encargo.**

El ADR afirma (Surface 2) que `cognitive-os.yaml > harness.hooks` es el
registro canónico de hooks, proyectado por un settings driver por harness. Es
cierto para el driver de Codex y **falso para el que corre**:

```console
$ grep -n 'CONFIG_FILE' scripts/_lib/settings-driver-claude-code.sh
39:CONFIG_FILE="$PROJECT_DIR/cognitive-os.yaml"
$ grep -cE 'yq |yaml\.safe_load|import yaml' scripts/_lib/settings-driver-claude-code.sh
0
$ grep -cE 'yaml|yq' scripts/_lib/settings-driver-codex.sh
9
$ wc -l < scripts/_lib/settings-driver-claude-code.sh
614
```

`CONFIG_FILE` se asigna en la línea 39 y no se vuelve a leer en 614 líneas.
Los grupos de hooks son literales de bash (línea 124 en adelante). Registrar un
hook sólo en `cognitive-os.yaml` **no lo hace disparar bajo Claude Code**.

La parte que importa: ese mismo texto se inyecta en el contexto de los agentes.

```console
$ grep -n 'ADR-064' hooks/inject-phase-context.sh
204:NOTE: .claude/settings.json is GENERATED (ADR-064): the canonical hook
     registry is cognitive-os.yaml > harness.hooks ..., projected by
     scripts/_lib/settings-driver-claude-code.sh ...
210:NOTE: New hooks are registered in cognitive-os.yaml > harness.hooks ...
     then projected into .claude/settings.json by
     scripts/_lib/settings-driver-claude-code.sh ...
```

**Corrección al encargo:** el brief dice que el texto viaja como `KNOWN TRAPS`.
No: ADR-040 reemplazó el bloque fijo `KNOWN TRAPS` por búsqueda semántica
(`hooks/query-tailored-context-inject.sh:8`). El texto viaja como las NOTE de
`hooks/inject-phase-context.sh`. La sustancia del hallazgo se sostiene entera —
la vía de inyección es otra.

Segundo hallazgo sobre el mismo ADR, éste del detector:

```console
$ ls scripts/_lib/ | grep settings-driver
settings-driver-bare.sh
settings-driver-claude-code.sh
settings-driver-codex.sh
settings-driver-opencode.sh
settings-driver.sh
```

`scripts/_lib/settings-driver-cursor.sh`, listado en el ADR, nunca se creó.
`settings-driver-opencode.sh`, que sí existe, no está listado.

Se agregó una **nota de verificación** al final de ADR-064 con estas dos
mediciones. **No se tocó el campo `status`.**

### El resto de los de alto impacto

**43 de los 60 ADRs con rutas fantasma están citados por código vivo de cara
al agente** (`hooks/`, `rules/`, `skills/`, `templates/`, `.claude/`,
`packages/`) — es decir, su contenido desfasado tiene una vía de propagación,
no se queda en el archivo:

```console
$ # por cada ADR con hallazgos: git grep -lI -E 'ADR-0*<n>[^0-9]' -- \
$ #   templates hooks rules skills .claude packages
ADRs with phantom paths ALSO cited in agent-facing/live surfaces: 43 of 60
```

Los peores por volumen:

| ADR | Rutas fantasma | Citado desde |
|---|---|---|
| `ADR-028.md` | 12 | `hooks/adr-detector.sh`, `hooks/_lib/killswitch_check.sh`, … |
| `ADR-116-multi-session-coordination-primitives.md` | 11 | `hooks/destructive-git-blocker.sh`, `hooks/direct-main-guard.sh`, … |
| `ADR-047-session-lifecycle-management.md` | 9 | `hooks/session-heartbeat.sh`, `hooks/session-watchdog-launcher.sh`, … |
| `ADR-027.md` | 8 | `hooks/global-verify.sh`, `hooks/inject-phase-context.sh`, `hooks/pre-commit-gate.sh` |
| `ADR-087-adr-namespace-consolidation.md` | 6 | — |
| `ADR-064-harness-agnostic-cognitive-os.md` | 3 | `hooks/inject-phase-context.sh`, `hooks/goal-stop-gate.sh`, … |

**ADR-087 merece mención aparte**, porque es el caso donde la regla de
descarte podría haber tapado algo real. Es una tabla de renombres: 26 de sus
32 hallazgos crudos son la columna "desde" y se descartaron con razón. Los
**5 que quedan son la columna "hacia" y están equivocados** — el ADR dice a
dónde fue cada archivo, y no fue ahí:

```console
$ python3 scripts/audit_adr_path_reality.py --ignore-baseline | grep ADR-087
ADR-087...:354 [prose/missing] docs/02-Decisions/adrs/ADR-088-headless-clustered-runtime-direction.md
ADR-087...:360 [prose/missing] docs/02-Decisions/adrs/ADR-089-harness-skills-sync-path.md
ADR-087...:361 [prose/missing] docs/02-Decisions/adrs/ADR-090-simplify-profiles.md
ADR-087...:362 [prose/missing] docs/02-Decisions/adrs/ADR-091-agent-git-safety.md
ADR-087...:337 [prose/missing] docs/02-Decisions/adrs/ADR-011-dual-gateway.md

$ ls docs/02-Decisions/adrs/ | grep -E '^ADR-(088|089|090|091)'
ADR-088-provenance-trailer-ppid-chain.md
ADR-089-multi-session-git-coordination.md
ADR-090-auto-skill-repair.md
ADR-091-headless-clustered-runtime-direction.md
```

El "027-headless-clustered-runtime-direction" que ADR-087 mapea a ADR-088 está
hoy en **ADR-091**, y ADR-088 es otra cosa. Quien siga la tabla aterriza en el
ADR equivocado.

---

## 4. Rutas fantasma más citadas

| Ruta | ADRs que la nombran |
|---|---|
| `hooks/rotate-metrics.sh` | 5 |
| `scripts/so-agent-status.sh` | 3 |
| `hooks/agent-launch-preamble.sh` | 2 |
| `hooks/_lib/agent-preamble.md` | 2 (relocalizada a `.cognitive-os/templates/agent-preamble.md`) |
| `hooks/_lib/heartbeat.sh` | 2 |
| `rules/hook-contracts.md` | 2 |
| `scripts/reinvention-query.sh` | 2 |

Listado completo: `python3 scripts/audit_adr_path_reality.py --ignore-baseline`.

---

## 5. Qué del encargo era falso

El encargo se declaró refutable. Tres correcciones:

**a) ADR-008 no está desfasado por la señal que el encargo propone — es
inverificable, que es otra cosa.** El brief dice que "su premisa es que los
harnesses divergen" y que la convergencia medida entre Codex y Claude Code la
tumba. Leído el ADR, su Context es la *fragmentación del ecosistema y el
lock-in del usuario*, y su Decision son tres capas de portabilidad (adapters,
MCP como puente, portabilidad de reglas). Que dos harnesses converjan no
refuta "soportar varias herramientas"; refuta, como mucho, la necesidad de una
capa de adapters pesada **para esos dos**. Aplicando el criterio de la pregunta
"¿un cambio en el código debería haber obligado a tocar este ADR?": no
necesariamente, así que por la señal 1 es **coincidencia y se deja**.

Lo que sí es un hallazgo real sobre ADR-008 es otro: su `implementation_files`
lista **únicamente al propio ADR**. Es uno de los 2 casos del corpus donde la
única evidencia de la decisión sale de la decisión misma — exactamente lo que
ADR-342 prohíbe para una primitiva. Cero rutas fantasma porque no hay ninguna
ruta que verificar.

**b) La vía de inyección de ADR-064 no es `KNOWN TRAPS`.** ADR-040 reemplazó
ese bloque fijo por búsqueda semántica. El texto viaja por las NOTE de
`hooks/inject-phase-context.sh:204,210`. El hallazgo se sostiene; la ruta de
propagación citada en el brief está vencida. (Detalle irónico: el brief
reprodujo una descripción desactualizada del mecanismo, que es la misma forma
que vino a medir.)

**c) "502 ADRs".** El directorio tiene **506 archivos**; 502 hacen match con
`ADR-*.md`. Los 4 restantes son otros archivos del directorio. La diferencia no
cambia ninguna conclusión, pero el número del brief no es el que devuelve
`ls docs/02-Decisions/adrs/ | wc -l`.

**Confirmado sin corrección:** ADR-064 (§3) y ADR-055b. Este último se
contradice a sí mismo dentro del mismo archivo: la línea 88 dice que
`git reset --hard HEAD~1 --allow-destructive` funciona, y la 129 admite que
"el flag `--allow-destructive` no es reconocido por git". La vía inline
documentada rompe el comando.

---

## 6. Lo que este censo NO cubre

Se construyó la señal 1. Las otras tres del encargo quedan sin censo:

- **Señal 2 (contradicción con un censo vivo).** ADR-064 se encontró a mano.
  No hay script que cruce afirmaciones de ADRs contra
  `audit_gate_registration.py` / `hook_behavior.py` /
  `audit_payload_field_contracts.py`.
- **Señal 3 (superado por un ADR posterior sin que ninguno lo diga).** Dominio
  del agente de estado y enlaces de ADRs.
- **Señal 4 (nunca implementado).** Los 353 ADRs sin `implementation_files` son
  el techo: no hay superficie mecánica sobre la que medirlos.

El detector construido acota el problema a lo que se puede probar hoy, y deja
el ratchet en el número medido para que la próxima sesión vea si sube.

---

## Reproducir

```console
$ python3 scripts/audit_adr_path_reality.py                 # contra el ratchet
$ python3 scripts/audit_adr_path_reality.py --ignore-baseline --historical
$ python3 scripts/audit_adr_path_reality.py --ignore-baseline --json
```

Nada se borró y ningún campo `status` se tocó. El único ADR modificado es
ADR-064, con una nota de verificación al pie.
