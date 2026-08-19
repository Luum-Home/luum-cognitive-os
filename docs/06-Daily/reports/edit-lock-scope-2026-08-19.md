# El scope de edit-lock: qué era contradicción, qué era yo leyendo mal

**Fecha:** 2026-08-19
**Estado:** un defecto real acotado, **decisión pendiente del operador**. No se cambió ningún scope.

## Lo que dije y estaba mal

Reporté que "los 4 hooks de edit-lock dicen `both` en la cabecera y `os-only` en el
yaml, uno de los dos está mal". **No hay tal contradicción**: son dos campos con el
mismo nombre y propósitos distintos.

| fuente | qué gobierna | verificación |
|---|---|---|
| cabecera `# SCOPE:` del archivo | **la proyección**: si el archivo se copia al consumidor | `cos_init.scope_allows` y `generate-project-settings.sh:114` leen `head -3` |
| `cognitive-os.yaml > harness.hooks[].scope` | **metadato de auditoría** | lo consume `hook_quality_audit.py`; los drivers `bare` y `opencode` lo preservan "for debugging / kill-switch logic" y no filtran; codex ni lo toca |

O sea que la cabecera es la única autoridad de proyección. El `scope` del yaml no
contradice nada porque no decide nada. Que dos campos distintos se llamen igual sí
es una trampa, pero es de nomenclatura, no de estado.

## Y el `both` tampoco era un descuido

`manifests/primitive-consumer-availability.yaml` declara los cinco componentes como
`status: shared-surface`, con rationale escrito por archivo:

- los 4 hooks: *"Manual scope review iteration 029: … is generic concurrent-edit safety"*
- `scripts/edit-coop.sh`: *"Manual scope calibration batch 002 confirmed shared COS/consumer-project surface"*

Es una revisión manual documentada. Cambiar esos scopes es revertir una decisión
escrita, no corregir un olvido — el mismo error que ya cometí hoy con ADR-323.

Nota sobre ADR-098: su frontmatter dice `tier: maintainer` y su cuerpo lleva
`<!-- SCOPE: OS -->`, pero ese marcador gobierna **el documento ADR**, no los
componentes. Su tabla de arquitectura no tiene columna de scope. No es evidencia
en contra de `shared-surface`.

## El defecto real, uno solo

**`scripts/edit-coop.sh` está declarado superficie compartida y ningún instalador lo
copia.** `cos_init.py` no lo nombra, `install.sh` tampoco, y `scripts/` no se copia
entero. Los 4 hooks que lo usan sí viajan. La disponibilidad declarada no se entrega.

## Lo que ya está arreglado (commit `eae107e36`)

Dos de los cuatro hooks sourceaban `scripts/_lib/session-id.sh` sin guarda y
escupían tres líneas en stderr en cada `UserPromptSubmit` del consumidor, con
`session=` vacío — lo que colapsaba el buzón a la raíz de negociaciones. Los otros
dos ya guardaban (`[ -x "$COOP" ] || exit 0`). Ahora los cuatro salen limpios.

## La escala, medida ejecutando y no leyendo

Textualmente, 39 hooks que viajan referencian 65 rutas que no viajan. Ejecutados
en un árbol con forma de consumidor, **solo 2 se rompen**: 37 guardan bien. El
conteo textual exageraba por ~19×, y `context-budget-meter.sh` (traceback de
Python) y `session-init.sh` (`flock` ausente, que es tema de host, no de scope) son
los únicos casos vivos.

Vale registrar también un supuesto mío que era falso: creí que `cos_lib/` no viaja.
Sí viaja — `cos_init.py:1902` proyecta *"the cos_lib.\* dependency closure for the
installed hooks"*. Sin corregir eso, el número habría sido 85 en vez de 65.

## La decisión

**(a) Entregar lo declarado.** Agregar `scripts/edit-coop.sh` y
`scripts/_lib/session-id.sh` a la lista de scripts que el instalador copia por
nombre — el mecanismo ya existe (`hook-timing-wrapper.sh`, `project_shell_ci.py`,
etc.). Consecuencia a mirar de frente: activa `edit-lock-pre-tool.sh`, un
`PreToolUse[Edit|Write]` que **sale con exit 2 y bloquea la edición** ante
conflicto, en proyectos de terceros.

**(b) Corregir la declaración.** Pasar los cinco a `os-only` y ajustar
`primitive-consumer-availability.yaml`. Revierte iteration 029 / batch 002, así que
necesita quedar escrito por qué.

**Recomendación: (b)**, por una razón que no es de gusto — el sistema coordina
*sesiones de agente concurrentes sobre el mismo checkout*, que es la situación del
repo del SO, y su skill de introspección (`skills/coordination-status/SKILL.md`) y
su plantilla de respuesta (`templates/edit-conflict-response.md`) **ya son
`os-only`**. Entregar (a) shippearía el enforcement sin la documentación que le dice
al agente qué hacer cuando lo bloquean.

No se aplicó ninguna de las dos: activar un gate bloqueante en proyectos ajenos, o
revertir una revisión manual, son decisiones del operador.

## Reproducir

Qué gobierna cada campo:

```bash
grep -n "scope" scripts/_lib/settings-driver-bare.sh | head -3
grep -rn 'entry\["scope"\]\|entry.get("scope")' scripts/ | head
```

Que `edit-coop.sh` no lo copia nadie:

```bash
grep -n "edit-coop" scripts/cos_init.py install.sh || echo "no aparece en ningun instalador"
```

Devuelve vacío **con exit code 1**: el vacío es el resultado, el 1 es `grep`
diciendo "sin coincidencias".

Los cuatro hooks en un consumidor, que es la prueba de que ya no ensucian:

```bash
.venv/bin/python -m pytest tests/red_team/portability/test_edit-lock-process-negotiations.py \
  tests/red_team/portability/test_edit-lock-drain-parked.py -q
```
