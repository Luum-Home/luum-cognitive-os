# Juez — la ausencia mal medida

> **Clase auditada:** concluir que algo no existe porque una búsqueda por patrón
> no lo encontró, cuando la búsqueda corría sobre el artefacto equivocado.
>
> Fecha: 2026-08-15 · Alcance: `docs/06-Daily/reports/*-2026-08-15.md` (50 informes)
> · Método: verificación por ejecución, no por relectura.

## Resumen

Seis instancias verificadas. **Una refuta el propio diagnóstico** que me dieron como
calibración. **Dos negativas resultaron verdaderas** y se reportan como tales. **Una
es la forma extrema de la clase**: un instrumento cuyo cero no puede ser otra cosa.
Y una la cometí yo, en la call 18 de esta auditoría.

El hallazgo transversal: **de los seis casos, cinco los detectó alguien que recontó
un encargo ajeno, no alguien que midió mejor la primera vez.** Eso ordena la
recomendación del final.

---

## 1. Máximo — la negativa que está por ordenar un borrado

**Afirmación.** `docs/06-Daily/reports/depuracion-quirurgica-2026-08-15.md:52`, en una
tabla titulada *lo que se va*:

> `trust-score-validator` | **953 corridas**, `trust-scores.jsonl` no existe en
> ninguna de las 21 instalaciones

**Estado de la acción.** No ejecutada todavía — el mismo informe dice *"Espera al
arquitecto de gates de autoevaluación"*. Por eso es el hallazgo más valioso del
barrido: **es la única negativa del lote que todavía puede evitar un borrado.**

**El hecho es cierto. La inferencia es falsa.**

`trust-scores.jsonl` efectivamente no está:

```bash
ls .cognitive-os/metrics/ | grep -i trust    # → vacío
```

Pero el hook **no está inerte**. Intervino cuatro veces:

```bash
grep -c 'trust-score-validator' .cognitive-os/metrics/primitive-interventions.jsonl
# → 4     (todas 2026-07-20, action=warn, reason=trust_report_missing)
```

Y ejecutado contra un payload bien formado, en un `PROJECT_DIR` de sandbox:

```bash
echo '{"tool_name":"Agent","tool_result":"Trust Report\nEvidence: x\nConfidence: 0.9\nUncertainty: y\n"}' \
  | TOOL_NAME=Agent CLAUDE_PROJECT_DIR="$SB" PROJECT_DIR="$SB" bash hooks/trust-score-validator.sh
# exit=5 · escribe hook-health.jsonl · NO escribe trust-scores.jsonl
```

El hook llega a `safe_jsonl_append "$TRUST_LOG"`
(`packages/consequence-system/hooks/trust-score-validator.sh:137`) por un camino que
**aborta antes, con exit 5 y `duration_ms: 0`**.

**Qué significa.** Las 953 corridas no son 953 pasadas de un hook sin trabajo: son
**953 fallas silenciosas**. El artefacto ausente es el síntoma de un bug de
ejecución, no la prueba de que nadie lo use. Matarlo por "su log no existe" borra un
warner vivo y entierra la causa — el verde barato exacto que describe
`gates-sin-trampa`: se apaga la medición, no el problema.

**Qué habría que hacer.** No borrar. Diagnosticar el exit 5 primero. Si después de
arreglarlo el hook sigue sin aportar, ahí sí se discute matarlo — pero con el
artefacto que hoy no puede producir.

---

## 2. Máximo — el instrumento cuyo cero no puede ser positivo

`scripts/aspirational_audit.py` existe para encontrar primitivas aspiracionales.
Reproducido de forma independiente en este barrido:

```bash
.venv/bin/python scripts/aspirational_audit.py --dry-run --json --project-root .
# counts = {'REAL': 142, 'ON_DEMAND': 690, 'METADATA': 89, 'DORMANT': 6}
# dormant_aspirational_ratio = 0.0065
# 'graphify' in output → False
```

**No encuentra graphify**, que el mismo día se probó que es la primitiva más muerta
del repo (`docs/06-Daily/reports/graphify-vs-codebase-memory-2026-08-15.md`, commit
`5deecf23a`): `graph.json` inexistente, dos JSONL de métricas en 0 bytes, cero
invocaciones, binario ABSENT.

Y sus cinco *worst offenders* son scripts de medición **construidos hoy**:

```bash
for f in scripts/audit_adr_path_reality.py scripts/audit_decision_backing.py \
         scripts/docs_reader_audit.py scripts/scope_closure_gate.py; do
  git log --diff-filter=A --format=%ad --date=short -1 -- "$f"
done
# 2026-08-15 · 2026-08-15 · 2026-08-15 · 2026-08-15
# (el quinto, scripts/hook-io-overhead-bench.sh, ni siquiera está commiteado)
```

**Por qué es la forma extrema de la clase.** Mide un proxy —apariciones en
telemetría— en vez del hecho —¿la primitiva produce su artefacto?—. Por eso
**premia la antigüedad y castiga la evidencia recién producida**: lo que lleva tres
meses muerto acumuló corridas; lo que se escribió hoy para medir la realidad, no. El
`0.0065` se lee como salud y es una propiedad del instrumento, no del repo.

**Advertencia sobre el arreglo.** No prometer "esto va a encontrar N muertas" antes
de correrlo. Hoy otro agente unificó tres censos por comportamiento y el teatro pasó
de 22 a 12 — la reclasificación puede ir en cualquier dirección. Prometer el
resultado antes de medirlo sería repetir la clase una capa más arriba.

---

## 3. Alto — el diagnóstico de la clase tiene la clase adentro

Esto refuta la calibración que me dieron. **La instancia 2 del encargo está mal
contada.**

El encargo afirma que sobre `.codex/hooks.json` *"el literal nunca aparecía"* en
`scripts/cos_init.py`. Medido:

```bash
grep -c "\.codex" scripts/cos_init.py    # → 5, no 0
```

Aparece en las líneas 211, 212, 232, 1640 y 1750 — todas de **detección de harness y
mensajes**, ninguna de escritura. Así que el `grep` original no devolvió cero:
devolvió cinco líneas que no eran la que importaba, y alguien las leyó como "no lo
escribe".

Peor: **el encargo también ubica mal dónde vive la verdad.** Dice que el camino
genérico es `:2015 → :1567 → :1576 → :1610`. La ruta no se construye ahí — se
**resuelve desde un manifiesto**:

```bash
grep -n "primary_settings_path" manifests/harness-projection-registry.json | sed -n 2p
# 51:      "primary_settings_path": ".codex/hooks.json"

.venv/bin/python -c "import sys; sys.path.insert(0,'scripts'); \
  from cos_init import HARNESS_SETTINGS; print(HARNESS_SETTINGS['codex'])"
# → ('.codex/hooks.json', '.codex/hooks.json')
```

`HARNESS_SETTINGS` (`scripts/cos_init.py:87-90`) es un dict comprehension sobre filas
del registro. La verdad está en un **JSON de manifiesto**, no en el Python.

**Conclusión.** La corrección publicada (`d64a676bb`, *"the installer does write the
file"*) llegó al resultado correcto por un razonamiento que vuelve a errarle al
artefacto. La clase se reprodujo dentro del acto de diagnosticarla.

---

## 4. Alto — confirmadas, con matiz

**Instancia 1 (shim).** Confirmada. `scripts/cos-init.sh` son 15 líneas que terminan
en `exec "$PYTHON_BIN" "$SCRIPT_DIR/cos_init.py" "$@"`; el parser está en
`scripts/cos_init.py:588-594`.

*Matiz que el encargo omite:* no son "cinco flags que existen". `--minimal`,
`--standard` y `--lean` son **alias legacy remapeados a `--default`**
(`cos_init.py:590-592`, `:1669-1677`). Los modos canónicos son dos: `--default` y
`--full`. Quien lea el encargo tal como está creerá que hay cinco perfiles.

**Instancia 3 (censo por nombre).** Confirmada y con el número exacto:

```bash
ls hooks/*.sh | wc -l          # → 257
ls hooks/ | grep -c -- "-gate" # →  23
```

234 hooks no llevan el token `-gate`, y `hooks/secret-detector.sh` bloquea sin
tenerlo.

**Trampa 4 (telemetría truncada).** Confirmada, y **generaliza más de lo que el
encargo dice**:

```bash
grep -c '"hook":"[^"]*\.sh"' .cognitive-os/metrics/hook-timing.jsonl  # → 0
wc -l < .cognitive-os/metrics/hook-timing.jsonl                       # → 57934
```

Cero de 57.934. Y no es sólo `hook-timing.jsonl`: `hook-health.jsonl` escribe el
mismo campo truncado (`{"hook":"trust-score-validator",...}`, verificado en el
sandbox del hallazgo 1). Cualquier filtro con `.sh` sobre telemetría de hooks
devuelve cero perfecto.

---

## 5. Negativas que resultaron VERDADERAS

El encargo pide explícitamente no contar como hallazgo una negativa cierta. Estas
dos llevaron a una acción y **la acción está bien**.

**`skill-metrics-tracker` (commit `15c7b7428`, borrado de tres listas de install).**

```bash
find . -name "*skill-metrics-tracker*" -not -path "./.git/*"   # → vacío
grep -c 'skill-metrics-tracker' .cognitive-os/metrics/hook-timing.jsonl  # → 0
```

El fantasma no existe. Además el commit **acotó su propio alcance a mano** —*"el
fantasma NO llegaba a ningún settings.json"*— en vez de inflar el hallazgo. Es el
contraejemplo del lote.

**`lib/` → `cos_lib/` (commit `0bbd3b3db`, 96 sustituciones en 43 archivos).**

```bash
ls -d lib cos_lib     # lib: No such file or directory · cos_lib
ls cos_lib/*.py | wc -l   # → 369
```

`lib/` no existe. Y el plan previo clasificó antes de scriptear: preservó cinco casos
que una sustitución ciega habría corrompido, incluido
`packages/agent-coordination/lib/`, que sí existe. Método correcto sobre una negativa
correcta.

---

## 6. La que cometí yo, mientras auditaba esto

Call 18 de este barrido:

```bash
timeout 300 .venv/bin/python scripts/aspirational_audit.py --dry-run --json ... > /tmp/asp.json
# exit=127 · archivo vacío
```

`timeout` no existe en macOS. Un `exit 127` con salida vacía, que si no lo miraba se
convertía en "el audit no produce JSON". La sexta trampa nace de acá, y no es
novedad en el repo: hoy mismo se commiteó `11f83af53 fix(auto-verify): stop reporting
"command not found" as a failed criterion`.

---

# El criterio — antes de publicar una negativa

> **La pregunta:** *¿el artefacto que grepeé es donde vive la verdad, o es el que
> lleva el nombre?*

Una afirmación negativa —*no existe*, *nadie lo lee*, *nunca dispara*, *cero
ocurrencias*— no se publica sin pasar estos dos filtros.

## Filtro A — las seis trampas

Antes de leer un cero como ausencia, descartá las seis, por nombre:

1. **Shim / delegación.** El archivo que lleva el nombre no hace el trabajo.
   `wc -l` + buscar `exec`/`source`/`import`. Un archivo de <30 líneas que termina en
   `exec` no es donde vive la verdad. *(Caso: `cos-init.sh`, 15 líneas.)*
2. **Ruta construida por variable o resuelta por manifiesto.** El literal no aparece
   porque se arma en runtime. Si buscás una ruta y no está, buscá el **último
   segmento** y el mapa que la produce. *(Caso: `.codex/hooks.json` vive en
   `manifests/harness-projection-registry.json`.)*
3. **Symlinks.** `hooks/*.sh` apunta a `packages/*/hooks/`. `readlink -f` antes de
   declarar nada ausente.
4. **Campo de telemetría truncado.** En `hook-timing.jsonl` y `hook-health.jsonl` el
   campo `hook` **no lleva `.sh`**. Filtrar con la extensión devuelve 0 de 57.934.
   Regla: antes de filtrar un JSONL, `head -1` y mirá la forma real del valor.
5. **Filtro por extensión sobre ejecutables sin extensión.** `--include='*.py'
   --include='*.sh'` excluye 301 de los 751 archivos de `scripts/` en este repo.
   Chequeo de forma, una línea:
   ```bash
   ls scripts/ | grep -vc '\.'   # → 301 archivos sin extensión. Este repo tiene esa forma.
   ```
6. **Comando que falló, no hecho que falta.** `exit 127` (binario ausente), `exit 5`,
   stdout vacío. **Un cero con exit code distinto de 0 no es un cero: es un error.**
   Siempre `echo "exit=$?"`.

## Filtro B — las tres preguntas que decide quién publica

Contestar las tres por escrito. Si no hay comando, la negativa no sale.

1. **¿Qué comando la produjo?** Sin comando citado, no es una negativa: es una
   impresión. *(Ése ya es el hallazgo.)*
2. **¿Ese comando podía ver la verdad?** Recorré las seis trampas por nombre. Si la
   afirmación es sobre **comportamiento** —dispara, bloquea, escribe, se invoca— el
   grep no alcanza: **hay que correr la cosa**, en sandbox si escribe.
3. **¿La ausencia del artefacto prueba la ausencia del comportamiento?** La pregunta
   del hallazgo 1. Un log que no existe puede ser un hook que no corre **o un hook
   que falla al escribir**. Son diagnósticos opuestos y llevan a acciones opuestas.
   Distinguirlos exige ejecutar.

## La categoría aparte — el instrumento estructuralmente incapaz

Cuando el cero lo produce **una herramienta de censo** y no un grep, hay una pregunta
previa: *¿este instrumento mide el hecho, o un proxy del hecho?*

Un instrumento que mide **apariciones en telemetría** no puede encontrar una
primitiva que nunca corrió — y ésa es exactamente la que busca. **Su cero no puede
ser positivo.** Test barato, una línea: tomá un caso que ya sabés positivo por otra
vía y verificá que el instrumento lo encuentra. `aspirational_audit.py` no encuentra
graphify. Un censo que no encuentra el caso conocido no reporta salud: reporta su
propio punto ciego.

---

# Sobre un gate ejecutable

**Lo propongo con reservas explícitas, no como entregable.** Hoy se midió que de
46.396 invocaciones de hook salieron 244 bloqueos, y que 22 gates no pueden bloquear.
Agregar un gate #23 que tampoco bloquee empeoraría el problema que audito.

Lo que **sí** es detectable de forma barata y honesta, sobre informes en
`docs/06-Daily/reports/`, es la **trampa 5 y el filtro B.1** — ambos son propiedades
del texto, no del mundo:

- un `grep`/`rg` citado con `--include='*.<ext>'` en un repo cuyo `scripts/` tiene
  301 archivos sin extensión → **advertir**, no bloquear;
- una frase negativa (*no existe*, *cero ocurrencias*, *nunca dispara*) en un informe
  **sin ningún bloque de comando en el archivo** → advertir.

El barrido de hoy con esa segunda heurística devolvió **un** archivo
(`depuracion-quirurgica-2026-08-15.md`) — y resultó ser el hallazgo de daño máximo.
Señal alta, volumen bajo: buen candidato a advisory.

Las trampas 1, 2, 3 y 6 **no son detectables desde el texto** del informe. Requieren
ejecutar. Proponer un gate que las cubra sería vender cobertura que no existe.

**Conclusión operativa, y es la principal:** de las seis instancias, cinco las
encontró alguien que **recontó un encargo ajeno**, no alguien que midió mejor la
primera vez. Ninguna de las cuatro de graphify llegó a una acción destructiva porque
el agente refutó la premisa **antes** de ejecutar. Lo que contiene esta clase no es
un gate: es que quien recibe una afirmación tenga **permiso y mandato de
recontarla** — el encargo refutable (`597f835f9`, `c32e0539c`). El gate es advisory;
la recontada es el control.

---

# Qué de este encargo era falso

Sección obligatoria por [`encargo-refutable`].

1. **"El literal nunca aparecía" (instancia 2) es falso.** `grep -c "\.codex"
   scripts/cos_init.py` → **5**. Y la verdad tampoco vive en las líneas citadas
   (`:1567 → :1576 → :1610`): vive en `manifests/harness-projection-registry.json:51`.
   El diagnóstico de la clase contiene la clase. Es el mejor hallazgo del barrido y
   sale de recontar la calibración, no de barrer informes.
2. **"Los cinco flags existen" (instancia 1) es engañoso.** Tres son alias legacy
   remapeados a `--default`. Los modos reales son dos.
3. **"189 de 256 hooks" (instancia 3) no reproduce con esos números.** Hoy hay
   **257** hooks y **23** con el token `-gate`. La dirección del hallazgo se sostiene;
   los dígitos no. Un número sin comando es opinión con dígitos, incluso en el
   encargo que exige comandos.
4. **La trampa 4 está subdeclarada.** No es sólo `hook-timing.jsonl`:
   `hook-health.jsonl` trunca el mismo campo.
5. **"Hay más de una docena de informes"** — hay **50** con fecha de hoy. No cambia
   nada del método; cambia el alcance de lo que un barrido de ~50 tool calls puede
   cubrir. **Este informe verifica seis casos a fondo; no es un censo exhaustivo de
   los 50.** Preferí seis verificados a cincuenta marcados, según el encargo.

## Lo que NO se hizo

Ningún informe ajeno fue borrado, revertido ni reescrito. No se tocó
`docs/00-MOCs/entrypoints/` ni los commits `958845a18` / `7725a0917`. No se tocó
`hooks/**`. La única escritura fuera de este archivo fue en el scratchpad de sesión.

**Correcciones pendientes de asentar** (como nota o entrada en
`manifests/documentation-truth-claims.yaml`, §16 / ADR-277 — no ejecutadas por este
encargo):

| Afirmación | Dónde | Corrección medida |
|---|---|---|
| `trust-score-validator` inerte, candidato a borrar | `depuracion-quirurgica-2026-08-15.md:52` | Intervino 4 veces; sale por `exit 5` sin escribir. Bug, no desuso. |
| `dormant_aspirational_ratio: 0.0065` como señal de salud | salida de `scripts/aspirational_audit.py` | El instrumento no encuentra graphify; sus 5 peores son de hoy. |
