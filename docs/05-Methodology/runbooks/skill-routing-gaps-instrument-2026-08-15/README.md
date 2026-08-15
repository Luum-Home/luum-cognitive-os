# `skill-md-routing-validator`: darle un artefacto

**Estado: parche verificado, NO aplicado.** `git apply --check` limpio sobre `HEAD`.
Aplicarlo requiere `COS_ALLOW_PROTECTED_CONFIG_WRITE=1`, que solo el operador puede
poner — ver "Cómo aplicarlo" abajo.

## El defecto

**1028 invocaciones que no llegan a ningún lado.**

```bash
# corridas
grep -c 'skill-md-routing-validator' .cognitive-os/metrics/hook-timing.jsonl
# artefactos: ninguno — el hook no escribe archivos
```

El hook detecta una skill que se escribe sin bloque `routing_patterns:` — invisible
para el sistema de sugerencia del orquestador (ADR-174). Es un hallazgo real y útil.
Lo emite por `stderr` con `exit 0`, y ahí muere:

- Está registrado **`async: true`** (línea 12 de su propio encabezado). Un hook async
  tiene su exit code ignorado y su stderr sin garantía de entrega.
- En `PreToolUse`, el stderr de un `exit 0` no se le muestra al modelo. Solo el
  stderr de un `exit 2` llega.
- No escribe ningún archivo.

Su propio texto lo dice: *"This warning is non-blocking. The write will proceed."*
Es correcto — pero entonces no es ni gate ni instrumento. Es la única primitiva del
censo clasificada **"ninguno de los dos"** con costo real.

## Por qué la salida elegida es la más barata

Había tres:

| Salida | Costo | Efecto |
|---|---|---|
| `exit 2` → se vuelve gate | cambio de comportamiento; bloquea escrituras de skills | desproporcionado para un aviso de metadatos |
| **escribir a archivo → instrumento** | **una línea de `printf`, cero cambio de comportamiento** | **el hallazgo sobrevive y se puede consultar** |
| borrarlo | pierde una detección real | la detección vale, el canal no |

El parche toma la del medio. **No toca el exit code, no toca el evento, no toca el
matcher.** Solo agrega la fila JSONL antes del aviso, que se conserva tal cual.

## Qué escribe

`.cognitive-os/metrics/skill-routing-gaps.jsonl`, una fila por hallazgo:

```json
{"timestamp":"…Z","hook":"skill-md-routing-validator","skill":"…","file":"…","finding":"missing-routing-patterns","adr":"ADR-174"}
```

Detalles de robustez, porque el hook corre con `set -euo pipefail` y **no puede
fallar la escritura del usuario bajo ninguna circunstancia**:

- La ruta se resuelve con la misma cadena que usa el driver de Codex
  (`COGNITIVE_OS_PROJECT_DIR` → `CLAUDE_PROJECT_DIR` → `$PWD`), así que no depende de
  una variable de un solo harness.
- `mkdir -p` guardado en un `if`: si falla, no se intenta escribir.
- El append termina en `|| true`: con `set -e` activo, un disco lleno o un permiso
  denegado no puede tumbar el hook.

## Lo que este parche NO hace

- **No agrega un consumidor.** El JSONL nace sin lector. Eso es deliberado: el
  hallazgo primero tiene que existir en algún lado para que valga la pena consultarlo,
  y un consumidor inventado ahora sería otra primitiva sin uso medido. Cuando el
  archivo tenga filas, el conteo dice si vale un reporte.
- **No usa el lock de `safe_jsonl_append`.** Un append de una línea corta es atómico
  en la práctica, y sourcear el helper agregaría una dependencia a un hook que hoy es
  puro bash sin `source`. Si aparecen filas entremezcladas, ahí sí corresponde.

## Cómo aplicarlo

El guard `protected-config-write-guard` protege `hooks/**` y exige revisión humana
explícita. **Un agente no puede saltearlo**: el hook corre en su propio proceso antes
del comando, así que un `export` escrito dentro de la línea del agente no le llega.
Bloqueó este cambio con `exit 2`, como corresponde.

```bash
git apply docs/05-Methodology/runbooks/skill-routing-gaps-instrument-2026-08-15/skill-md-routing-validator.patch
```

```bash
COS_ALLOW_PROTECTED_CONFIG_WRITE=1 git commit --only -m "feat(skill-md-routing-validator): give the advisory an artifact" -- hooks/skill-md-routing-validator.sh
```

## Verificación después de aplicar

```bash
printf '{"tool_name":"Write","tool_input":{"file_path":"skills/demo/SKILL.md","content":"---\nname: demo\n---\n"}}' \
  | bash hooks/skill-md-routing-validator.sh; echo "exit=$?"
```

Esperado: `exit=0` (sigue sin bloquear), el aviso por stderr **sin cambios**, y una
fila nueva en `.cognitive-os/metrics/skill-routing-gaps.jsonl`.
