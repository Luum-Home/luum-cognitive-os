# Lote 2 — clasificación por comportamiento de los 68 hooks ambiguos

**Fecha:** 2026-08-15
**Alcance:** clasificación. No se borró, desregistró ni movió ningún hook.
**Evidencia ejecutable:** `scripts/classify_ambiguous_hooks.py`

```bash
.venv/bin/python scripts/classify_ambiguous_hooks.py          # tabla
.venv/bin/python scripts/classify_ambiguous_hooks.py --json   # filas con sitios de bloqueo
.venv/bin/python scripts/classify_ambiguous_hooks.py --all    # los 256, no sólo los ambiguos
```

Exit 0 = ningún `neither`; 1 = hay al menos uno; 2 = error. Read-only, determinista.

---

## Lo que del encargo no reprodujo

**1. "Son ambiguos porque se llaman `-check` / `-detector` / `-validator`" — cierto en 66 de 68, no en 68.**
Dos entran por otra puerta: `context-budget-meter` y `token-budget-monitor` tienen nombre de
instrumento (`meter`, `monitor`) y el clasificador padre los mandó a "ambiguo" porque su código
sí emite bloqueo. Los dos resultaron gates reales sobre eventos bloqueantes. La regla que los
atrapó es la correcta; la descripción del lote es la que estaba incompleta.

**2. "Gate = existe un camino que sale con código 2 y es alcanzable con el cableado actual" — el
criterio, tal como está escrito, da falsos en las dos direcciones.**

- *Falso negativo:* `secret-detector` y `session-summary-reminder` **nunca salen 2**. Bloquean
  emitiendo JSON (`permissionDecision: "block"` / `"decision": "block"`) y saliendo **0**. Un
  criterio de exit-code puro los clasifica como instrumentos. Son gates.
- *Falso positivo:* "salir 2" no es lo mismo en todos los eventos. En `PostToolUse` el exit 2 se
  le muestra al modelo **después de que la herramienta ya corrió**: no previene nada. Siete hooks
  con emisor de bloqueo están cableados únicamente ahí. Alcanzables sí; capaces de impedir, no.

Por eso la tabla tiene cinco categorías y no tres.

**3. La medición del propio lote 1 no tiene, acá, el defecto que tenía en el lote 1.**
Se verificó: `.claude/settings.json` menciona 155 hooks a nivel texto y registra 155 dentro de
`hooks{}`. Cero fantasmas. El grep de texto del audit padre no está inflando nada **hoy**; el
parser estricto quedó igual en el script nuevo para que siga siendo cierto si mañana alguien
comenta un bloque.

---

## Taxonomía usada

| Veredicto | Definición |
|---|---|
| `gate-effective` | Emisor de bloqueo + cableado sobre un evento que efectivamente frena algo (`PreToolUse`, `UserPromptSubmit`, `Stop`, `SubagentStop`). |
| `gate-advisory` | Emisor de bloqueo cableado **sólo** sobre eventos no bloqueantes (`PostToolUse`). Le avisa al modelo después del hecho; no lo impide. |
| `gate-unreachable` | Emisor de bloqueo sin ningún evento del harness que lo dispare en este repo. |
| `instrument` | Sin emisor de bloqueo; escribe un artefacto persistente (JSONL, reporte, `.cognitive-os/`) o inyecta contexto estructurado. |
| `neither` | Ni bloquea, ni persiste, ni su salida llega a alguien. |

## Resultado

```
gate-effective      9
gate-advisory       7
gate-unreachable    5
instrument         42
neither             5
                   ──
                   68
telemetría: 42/68 observados corriendo; 3 observados saliendo 2
```

### gate-effective (9)

| Hook | Evento | Corridas | ¿Salió 2? |
|---|---|---|---|
| `secret-detector` | PreToolUse | 13454 | no — bloquea por JSON, exit 0 |
| `provenance-scan` | PreToolUse | 1028 | **sí (3)** |
| `plan-claim-validator` | PreToolUse | 1028 | no |
| `control-plane-audit` | PreToolUse, Stop | 1199 | **sí** |
| `context-budget-meter` | UserPromptSubmit | 375 | no |
| `session-summary-reminder` | Stop | 292 | no — bloquea por JSON, exit 0 |
| `token-budget-monitor` | PreToolUse | 170 | **sí** |
| `predev-completeness-check` | PreToolUse | 170 | no |
| `completeness-check` | PreToolUse | 170 | no — 16 líneas que hacen `exec` del anterior |

### gate-advisory (7) — declaran bloqueo, están sobre `PostToolUse`

`adr-section-validator` (995), `hook-header-validator` (995), `rule-frontmatter-validator` (995),
`scope-creep-detector` (995), `skill-frontmatter-validator` (995), `claim-validator` (275),
`trust-score-validator` (270).

Los siete corren muy seguido y ninguno salió 2 nunca en la ventana medida. No es que fallen: es
que su `exit 2` está sobre un evento donde el efecto es contarle al modelo lo que ya pasó. Si la
intención es *impedir*, están sobre el evento equivocado; si la intención es *avisar*, el `exit 2`
sobra y confunde a quien lee el código.

### gate-unreachable (5)

| Hook | Cableado declarado | Evento real |
|---|---|---|
| `aguara-scan` | settings, profile, consumer-install | ninguno |
| `parry-scan` | profile | ninguno |
| `subagent-input-schema-validator` | profile | ninguno |
| `dry-run-preview` | consumer-install | ninguno |
| `secret-audit-pre-commit` | **ninguna de las 4 superficies** | ninguno |

`aguara-scan` es el caso a mirar: figura en `.claude/settings.json` según el grep de texto del
audit padre, pero no aparece dentro de ningún bloque de evento de `hooks{}` con ese nombre —
llega ahí por otro camino (perfil / proyección), no por registro directo. Corridas observadas: 0.

### neither (5) — ni bloquean ni dejan rastro

| Hook | Evento | Corridas | Qué hace realmente |
|---|---|---|---|
| `skill-md-routing-validator` | PreToolUse | **1028** | `cat >&2 <<WARNING`, `exit 0`. Su propio texto dice "This warning is non-blocking". En PreToolUse con exit 0, stderr no llega ni al modelo ni a un archivo. |
| `dangerous-env-flag-detector` | SessionStart | 160 | Corre `scripts/dangerous_env_flag_detector.py --json`, imprime el resultado **a stderr**, exit 0. El script sólo hace `print`. Nada persiste. |
| `code-review-on-commit` | — | 0 | Sin cableado en las 4 superficies. Manda la review a stderr. |
| `pattern-check` | — | 0 | Sin cableado. Avisa de referencias rotas por stdout. |
| `tool-loop-detector` | — | 0 | Sin cableado. Lo único que escribe es `/tmp/claude-tool-history-$PPID.log`, que se borra solo. |

El más caro es el primero: **1028 invocaciones en la ventana medida para producir un aviso que no
lee nadie**. Los otros cuatro no cuestan nada porque no corren.

---

## Defectos que tenía el instrumento antes de creerle

El primer corte de este mismo script daba **13 `neither`**. Ocho eran del medidor, no del SO:

1. **Bloqueo multilínea.** `secret-detector` arma su `permissionDecision: "block"` con un `jq -n`
   de siete líneas. Un escaneo línea por línea lo declaraba instrumento puro. Se agregó escaneo
   sobre el texto completo.
2. **Wrappers finos.** `completeness-check.sh` son 16 líneas que hacen `exec` de
   `predev-completeness-check.sh`. Mirando sólo el wrapper, es inerte. Se sigue **un salto** de
   delegación.
3. **Delegación por variable.** `SCRIPT="$PROJECT_DIR/scripts/state_retention_audit.py"` y después
   `python3 "$SCRIPT"`: ninguna regex sobre el sitio de llamada lo resuelve. Se pasó a resolver
   *cualquier* referencia a un archivo del repo que exista.
4. **Delegación por módulo Python.** `skill-drift-detector.sh` son 50 líneas de guardas alrededor de
   `from cos_lib.skill_drift_detector import main`. Sin resolver el import, "no escribe nada"
   mientras llena `skill-drift.jsonl` (632 KB).
5. **`.cognitive-os/checkpoints`** no era `metrics|state|reports`, así que `auto-checkpoint`
   —6235 corridas— figuraba como que no escribía.

Cada uno de esos cinco es la misma familia de verde barato del lote 1: la herramienta comparaba
forma y no comportamiento.

---

## Lo que no se pudo medir

- **Bloqueos por JSON no dejan huella en la telemetría.** `hook-timing.jsonl` guarda `exit_code`.
  `secret-detector` y `session-summary-reminder` bloquean saliendo **0**. Para esos dos, la
  pregunta "¿bloqueó alguna vez?" no tiene respuesta con la telemetría actual. Se sabe que
  `secret-redactions.jsonl` tiene 2 filas, lo que confirma que el camino de redacción se ejecutó,
  pero no que el camino de bloqueo total se haya ejecutado.
- **La ventana de telemetría es de un día.** `hook-timing.jsonl` va de `2026-08-15T04:42Z` a
  `2026-08-15T16:42Z` (34 124 filas, 155 hooks distintos). Los `.archive/*.gz` se leen, pero los
  de julio son de otras rotaciones. "0 corridas" significa "0 en esta ventana", no "nunca".
- **Hay una quinta superficie de cableado que no está enumerada.** `resource-check` registra 122
  corridas y `auto-verify` 2, y las cuatro superficies del censo los dan como no cableados. Algo
  los invoca —otro script, un dispatcher en Python— que no está en `settings.json`, ni en el
  fan-out del hot path, ni en `DEFAULT_HOOKS`, ni en los `cos-package.yaml`. Mientras eso no se
  enumere, "no cableado" es una hipótesis, no un veredicto.
- **Alcanzabilidad interna.** El script dice si existe un emisor de bloqueo y si el evento permite
  bloquear. No dice si la condición que lleva a ese emisor es alcanzable en la práctica (p. ej.
  `secret-detector` sólo bloquea si el input entero era secretos). Eso requiere ejercitar el hook,
  no leerlo.
- **`--all` no fue auditado a mano.** El script corre sobre los 256, pero sólo se verificaron a
  ojo las filas de los 68 ambiguos.

## Lo que este lote NO hizo

No se borró ni desregistró nada. Las tres decisiones que quedan planteadas para el operador —y que
son decisiones, no limpieza— son: qué hacer con los 7 `gate-advisory` (mover de evento o sacarles el
`exit 2`), con los 5 `gate-unreachable`, y con `skill-md-routing-validator`, que es el único
`neither` que cuesta plata.
