# Prep — superficie pública, 2026-08-15

## 1. Veredicto en una línea

Los 9 defectos se sostienen con evidencia reproducida hoy, pero 2 traen la
premisa parcialmente mal planteada (el punto 6 dice "sin fecha visible" y uno
de los dos JSON sí la tiene; el punto 9 dice que la cifra está "en la
portada" y no está — vive en otro doc y en `install.sh`); de los 9, 2 tienen
arreglo mecánico sin ambigüedad (el badge de versión del punto 1 y el
placeholder `<org>/<repo>` del punto 3) y los 7 restantes (2, 4, 5, 6, 7, 8,
9, más la mitad no textual del 3) necesitan que el operador elija entre
opciones con costos distintos — están abajo en la sección 4.

## 2. Tabla

| # | Defecto | Comando que lo confirma | Salida real de hoy | Arreglo exacto propuesto | Mecánico / decisión |
|---|---|---|---|---|---|
| 1 | Badge de versión desincronizado | `cat VERSION` / `grep -n -i version README.md` | `VERSION` = `0.29.39`; README línea 9 = `version-0.1.0-green.svg` | Reemplazar `0.1.0` por `0.29.39` en el badge | Mecánico |
| 2 | `package.json` congelado en 0.1.0 | `grep -n '"version"\|"name"' package.json` + `git log -p -- package.json` | `name: "cognitive-os"`, `version: "0.1.0"` fijados en el commit inicial `db4100405` y nunca vueltos a tocar en los 2 commits posteriores que sí modificaron el archivo | Sincronizar `version` con `VERSION` (0.29.39). El `name` no cambió nunca — no hay evidencia de colisión con otro paquete, eso no se puede verificar sin tocar el registro de npm (fuera del alcance de comandos livianos) | Decisión (política de sync) |
| 3 | 4 badges con `<org>/<repo>` sin sustituir | `grep -c '<org>/<repo>' README.md` / `ls .cognitive-os/metrics/badges/` | 4 ocurrencias (líneas 11-14); el directorio `.cognitive-os/metrics/badges/` no existe (`ls` sale con exit 1) | Sustituir `<org>/<repo>` por `luum-home/luum-cognitive-os` (ya usado en README línea 85 y en TRANSPARENCY.md línea 217, no es ambiguo) | Mecánico el texto; decisión si además hay que generar los `.json` de `badges/` |
| 4 | `npm test` apunta a script inexistente | `grep -n '"test"' package.json` / `ls tests/run-all-tests.sh` | `"test": "bash tests/run-all-tests.sh"`; `tests/run-all-tests.sh` no existe. Pero `scripts/run-all-tests.sh` sí existe, y su propio encabezado dice `CANONICAL: cos-test broad for normal validation; use this only for release hardening` | Apuntar `npm test` a `scripts/run-all-tests.sh` o al binario `cos-test broad` — son dos rutas distintas con semántica distinta | Decisión |
| 5 | CHANGELOG con entradas duplicadas de `cos-patch-release` | `grep -c 'Added the .cos-patch-release. primitive' CHANGELOG.md` + `git log --diff-filter=A -- scripts/cos-patch-release` | **22** ocurrencias (el enunciado decía 21 o 22 — es 22). La primitiva se agregó una sola vez, en el commit `414382d11` ("release: v0.29.7 patch release primitive") | Dejar una sola entrada (la de v0.29.7) y quitar el párrafo repetido de las otras 21 releases | Decisión (reescribir historia publicada de CHANGELOG) |
| 6 | Métricas públicas ~110 días sin actualizar, sin fecha visible | `git log -1 --format='%ai' -- public-metrics-*.json` + `cat` de cada uno | Ambos: último commit `f5a831aa1`, `2026-04-27 13:19:41 +0000` → **110 días** hasta hoy (2026-08-15). `public-metrics-dogfood.json` **sí** trae `"timestamp": "2026-04-27T13:19:38...Z"` visible. `public-metrics-aspirational.json` **no** trae ningún campo de fecha | Re-generar ambos con datos frescos; agregarle `timestamp` al de aspirational (el de dogfood ya lo tiene) | Decisión (correr el generador es trabajo pesado, fuera de alcance hoy) |
| 7 | Hash SHA-256 de TRANSPARENCY.md no coincide | `grep -n sha256 TRANSPARENCY.md` + `shasum -a 256 docs/01-Build-Log/history/pre-sanitization-sha-inventory-2026-05-07.txt` | TRANSPARENCY.md línea 172 declara `923170ead7ef9fd7c072089a699f867e111ead1be38a84ce41eb1a4023104997` para ese archivo. El hash real hoy es `8cd1b416ab538446066fb4ec44a31f5faef8aa15e0e3e50b741858a42dd6ba8d`. No coinciden (los dos tienen 64 caracteres hex, no es un tema de formato) | Ver sección 4 — hay dos caminos con consecuencias distintas | Decisión |
| 8 | Malla de "14 capas / 12 hooks" no coincide con lo registrado | `grep -n '14-layer' README.md`; `ls lib/`; `grep -c "hooks/<nombre>" .claude/settings.json` por cada uno de los 12 nombrados en `safety-mesh.md` | README línea 26 dice literal "12 fire as PreTool/PostTool hooks, 2 are library/conditional". `lib/` no existe (`ls: lib/: No such file or directory`) — los dos archivos de librería que cita `safety-mesh.md` (`lib/cross_verifier.py`, `lib/memory_scanner.py`) viven hoy en `cos_lib/`, no en `lib/`. De los 12 hooks nombrados en la tabla de `safety-mesh.md`, **9 están registrados** en `.claude/settings.json` (`grep -c "hooks/<nombre>"` = 1) y **3 no** (`dry-run-preview.sh`, `rate-limiter.sh`, `clarification-interceptor.sh` dan 0) | Corregir `lib/` → `cos_lib/` en las dos filas de la tabla, y decidir si el número pasa a "9" o si se registran los 3 hooks que faltan | Decisión — el "9" está confirmado por registro en settings.json (proxy barato, no telemetría de disparo real; eso sí sería medición pesada) |
| 9 | Portada anuncia 22 harnesses, 3 con prueba real | `grep -n -i harness README.md` (portada) + `manifests/harness-projection-registry.json` | El README (la portada) **no** menciona "22" en ningún lado — dice literal "Supported harnesses: Claude Code, Codex, Cursor" (3 nombrados, línea 175). "22 harnesses" está en `docs/04-Concepts/architecture/consumer-project-primitive-accessibility.md:96` y en la salida de `install.sh --help` (ya documentado en 3 informes previos de este repo: `judge3-harness-reinvencion-2026-08-15.md`, `judge-funcionamiento-2026-07-28.md`, `judge2-*-2026-08-15.md`). El registro (`manifests/harness-projection-registry.json`, 27 entradas) marca `proof_level: native-lifecycle` para 2 (`claude`, `codex`) + `governed-wrapper-enforced` para 1 (`opencode`) = **3 con prueba real**; 19 son `structural` (solo assertea que existe el archivo y contiene una cadena) y 5 son `planned/none` | Corregir la cifra donde vive de verdad (no en README) y homogeneizar `install.sh --help` | Decisión |

## 3. Texto nuevo listo para pegar, por archivo

### README.md — badge de versión (línea 9)

Reemplazo directo, sin ambigüedad:

```
[![Version](https://img.shields.io/badge/version-0.29.39-green.svg)](CHANGELOG.md)
```

### README.md — placeholders `<org>/<repo>` (líneas 11-14)

```
![Dogfood Score](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/luum-home/luum-cognitive-os/main/.cognitive-os/metrics/badges/dogfood.json)
![REAL Primitives](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/luum-home/luum-cognitive-os/main/.cognitive-os/metrics/badges/real-components.json)
![Harness Portability](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/luum-home/luum-cognitive-os/main/.cognitive-os/metrics/badges/portability.json)
![Hook Wiring](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/luum-home/luum-cognitive-os/main/.cognitive-os/metrics/badges/hook-wiring.json)
```

Esto saca el `<org>/<repo>` literal, pero los 4 badges van a seguir rotos
(404) hasta que exista `.cognitive-os/metrics/badges/*.json` — eso es aparte,
ver sección 4.

### package.json — versión (línea 3)

```
  "version": "0.29.39",
```

### package.json — script de test (línea 9), tres variantes candidatas — el operador elige una, no las tres:

Variante A (apunta al script legacy que sí existe):
```
    "test": "bash scripts/run-all-tests.sh",
```

Variante B (apunta al binario canónico según el propio encabezado de `scripts/run-all-tests.sh`):
```
    "test": "./cos-test broad",
```

Variante C (crea el archivo que falta como wrapper fino sobre el canónico — no se escribió, solo el contenido que tendría `tests/run-all-tests.sh`):
```bash
#!/usr/bin/env bash
set -euo pipefail
exec "$(cd "$(dirname "$0")/.." && pwd)/cos-test" broad "$@"
```

### CHANGELOG.md — dedup de las 22 entradas de `cos-patch-release`

No se ejecutó. Script en el scratchpad de la sesión (no en el repo) que
haría el trabajo, dejando la primera ocurrencia (la de v0.29.7, línea 11-14)
y borrando el párrafo repetido en las otras 21 releases:

```python
import re

path = "CHANGELOG.md"
text = open(path, encoding="utf-8").read()

marker_a = "- Added the `cos-patch-release` primitive for repeatable patch release preparation, validation, publishing, and diagnostics.\n"
marker_b = "- `scripts/cos-patch-release validate` is the required patch-release validation lane.\n"

# Deja la primera ocurrencia de cada línea, borra el resto
for marker in (marker_a, marker_b):
    parts = text.split(marker)
    text = parts[0] + marker + "".join(parts[1:])

open(path, "w", encoding="utf-8").write(text)
```

Resultado esperado tras correrlo:
```bash
grep -c "Added the .cos-patch-release. primitive" CHANGELOG.md   # -> 1
grep -c "cos-patch-release validate. is the required" CHANGELOG.md  # -> 1
```

### public-metrics-aspirational.json — agregar timestamp

No se puede regenerar el contenido real sin correr el auditor (pesado, fuera
de alcance). El campo que falta, agregado al JSON existente tal cual está
hoy (solo referencia — el contenido de `counts` no se tocó ni se verificó
si sigue siendo preciso):

```json
{
  "total": 597,
  "timestamp": "2026-04-27T13:19:38.697082+00:00",
  "counts": {
    "METADATA": 45,
    "ASPIRATIONAL": 69,
    "ON_DEMAND": 227,
    "DORMANT": 165,
    "REAL": 91
  },
  "dormant_aspirational_ratio": 0.392,
  "worst_offenders": [
    "hooks/adr-detector.sh",
    "hooks/agent-bus-monitor.sh",
    "hooks/agent-output-verifier.sh",
    "hooks/agent-quota-advisor.sh",
    "hooks/agent-quota-redirect.sh",
    "hooks/dequeue-notify.sh",
    "hooks/skill-frontmatter-validator.sh",
    "lib/jupyter_client.py",
    "scripts/backfill_cost_events.py",
    "scripts/check-upstream-changes.sh"
  ]
}
```

(Nótese que este JSON también tiene `worst_offenders` apuntando a
`lib/jupyter_client.py`, que es el mismo problema de ruta stale del punto 8
— ese archivo también vive en `cos_lib/` hoy, no en `lib/`.)

### TRANSPARENCY.md — hash (línea 172)

Dos textos alternativos, uno por cada camino de la sección 4. No se elige
acá cuál pegar:

Opción "recalcular y republicar" (deja el archivo actual como fuente de verdad):
```
| Pre-rewrite SHAs are publicly recorded | [`docs/01-Build-Log/history/pre-sanitization-sha-inventory-2026-05-07.txt`](docs/01-Build-Log/history/pre-sanitization-sha-inventory-2026-05-07.txt) | `shasum -a 256 docs/01-Build-Log/history/pre-sanitization-sha-inventory-2026-05-07.txt` (expect `8cd1b416ab538446066fb4ec44a31f5faef8aa15e0e3e50b741858a42dd6ba8d`) |
```
y en el bloque de comandos (línea ~229):
```
# --- 3. SHA inventory has its declared hash ---
# Expect: 8cd1b416ab538446066fb4ec44a31f5faef8aa15e0e3e50b741858a42dd6ba8d
shasum -a 256 docs/01-Build-Log/history/pre-sanitization-sha-inventory-2026-05-07.txt
```

Opción "revertir el artefacto" — no hay snippet de reemplazo posible sin
saber qué versión del archivo generó el hash `923170ead7...`; requiere
encontrar esa versión en el historial de git antes de escribir nada.

### README.md — malla de capas (línea 26) y safety-mesh.md (filas 31 y 33)

Fix mecánico de ruta (independiente de la decisión sobre el número 12 vs 9):

`docs/04-Concepts/root/safety-mesh.md` fila 31:
```
| 12 | `cos_lib/cross_verifier.py` | Library | On demand | Second model catches first model's hallucinations | N/A (library call) |
```
fila 33:
```
| 14 | `cos_lib/memory_scanner.py` | Library | Session start | Stale/contradictory Engram memories affecting decisions | N/A (library call) |
```

El texto de README.md línea 26 (cambia "12" por "9" solo si el operador
elige NO registrar los 3 hooks faltantes — ver sección 4):
```
OS: a 14-layer safety mesh ([details](docs/04-Concepts/root/safety-mesh.md): 9 fire as PreTool/PostTool hooks, 2 are cos_lib/-based library calls, 3 exist as scripts but are not wired into settings.json) intercepts each failure mode at the right lifecycle
```

## 4. Decisiones del operador

**Punto 7 — TRANSPARENCY.md, hash divergente.** Dos caminos, costos distintos:
- **Recalcular y republicar**: se acepta que `pre-sanitization-sha-inventory-2026-05-07.txt` es hoy el artefacto correcto y se actualiza el hash declarado a `8cd1b416ab538446066fb4ec44a31f5faef8aa15e0e3e50b741858a42dd6ba8d` (snippet arriba). Costo: si el archivo cambió sin que nadie lo haya notado (corrupción, edición accidental, un merge que lo tocó), este camino blanquea ese cambio sin haberlo investigado.
- **Revertir el artefacto**: se busca en el historial de git la versión del archivo cuyo SHA-256 sea `923170ead7ef9fd7c072089a699f867e111ead1be38a84ce41eb1a4023104997` y se restaura esa versión, porque el hash publicado se toma como la fuente de verdad. Costo: si el archivo actual tiene 1.775 entradas más recientes que las que agrega la reconstrucción de historia post-mayo, revertir puede borrar inventario real. Hay que ubicar esa versión en `git log -p` antes de tocar nada — no se hizo en esta pasada porque implica escribir en el árbol.

**Punto 2 — package.json, sync de versión.** ¿El campo `version` de `package.json` se sincroniza a mano en cada release, o se genera desde `VERSION` en el pipeline de release (`cos-patch-release` ya existe y toca release)? Si la respuesta es "se genera", el fix de hoy (bump manual a 0.29.39) es un parche de una vez, no la solución — falta wirearlo al primitivo de release.

**Punto 3 — badges rotos incluso después del placeholder.** Sustituir `<org>/<repo>` saca el error obvio, pero los 4 badges van a seguir devolviendo 404 porque `.cognitive-os/metrics/badges/*.json` no existe. Camino A: generar esos 4 JSON (hay métricas fuente — `public-metrics-dogfood.json`, `.cognitive-os/metrics/*.jsonl` — que podrían alimentar un generador, pero no se identificó ninguno ya escrito en esta pasada). Camino B: sacar los 4 badges del README hasta que el generador exista, para no publicar un link roto.

**Punto 4 — a qué apunta `npm test`.** Variante A (`scripts/run-all-tests.sh`) preserva el path histórico pero contradice el propio comentario `CANONICAL: cos-test broad` que ese script trae en su cabecera. Variante B (`./cos-test broad`) sigue la convención documentada en `rules/RULES-COMPACT.md` (Test Lane Taxonomy, "Escalation ladder via cos-test focused/cluster/broad") pero cambia el contrato de `npm test` de shell script a binario Go, lo que puede no ser portable en el entorno de quien corre `npm install && npm test` desde fuera del repo. Variante C solo pospone la decisión con un wrapper.

**Punto 5 — reescribir CHANGELOG.md.** El CHANGELOG es un documento público con 22 entradas idénticas ya publicadas (algunas en releases ya taggeadas, ver `git log --oneline -- '*cos-patch-release*'`: v0.29.7 a v0.29.31 y más). Borrar retroactivamente el texto de releases ya publicadas es una decisión de contenido, no un fix de código — el script de la sección 3 está listo pero no se corrió.

**Punto 6 — refrescar las métricas públicas.** Requiere correr el generador (no identificado como liviano) contra el estado real del repo — 110 días de drift no se resuelve editando el JSON a mano, porque los números (`adr_discipline`, `harness_portability`, etc.) quedarían inventados. Antes de tocar el archivo hay que decidir con qué cadencia se va a mantener esto (¿weekly como dice el nombre del último commit, `chore(metrics): weekly public update`, y por qué se cortó a los 110 días?).

**Punto 8 — ¿12 o 9?** Registrar los 3 hooks que faltan (`dry-run-preview.sh`, `rate-limiter.sh`, `clarification-interceptor.sh`) en `.claude/settings.json` haría cierta la cifra "12" — pero `rate-limiter.sh` tiene una nota de estado propia en `rules/rate-limiting.md` que dice explícitamente que no está registrado por decisión pendiente del operador, no por olvido. Registrarlo sin revisar esa nota puede activar un limitador que hoy nadie está esperando que corra. La alternativa (bajar la cifra publicada a "9") es más barata pero también más floja.

**Punto 9 — qué cifra se publica sobre harnesses.** El registro ya distingue `proof_level`; publicar "3 con prueba real / 19 estructurales / 5 planificados" es más preciso que "22 harnesses", pero también es un mensaje de producto más débil de cara afuera. Esa elección no es técnica.

## 5. Correcciones a las premisas del encargo

- **Punto 5**: el enunciado decía "21 o 22" — el número real es **22** (`grep -c` da 22, verificado dos veces).
- **Punto 6**: el enunciado decía que ambos archivos "se publican sin fecha visible". Eso es cierto para `public-metrics-aspirational.json` (no tiene ningún campo de fecha), pero **falso** para `public-metrics-dogfood.json`, que sí trae `"timestamp": "2026-04-27T13:19:38.697082+00:00"` visible en el propio JSON.
- **Punto 9**: el enunciado decía que "la portada anuncia 22 harnesses". El README (que es la portada) **no menciona el número 22 en ningún lado** — dice literal "Claude Code, Codex, Cursor" (3 harnesses nombrados). La cifra "22" está en `docs/04-Concepts/architecture/consumer-project-primitive-accessibility.md:96` y en la salida de `install.sh --help`, no en README.md. La comparación "22 vs 3 con prueba real" sigue siendo válida como hallazgo, pero no está donde el enunciado dice.
- Los puntos 1, 2 (salvo la interpretación de "mismo nombre", que el enunciado ya marcaba como ambigua y quedó resuelta como "el nombre no cambió nunca, no hay evidencia de colisión externa verificable con comandos livianos"), 3, 4, 7 y 8 se reprodujeron tal cual estaban planteados.

## 6. Comando que verifica el conjunto después de aplicar

```bash
# 1. Version badge y package.json en sync con VERSION
diff <(grep -oE 'version-[0-9.]+' README.md | head -1 | cut -d- -f2) VERSION
diff <(grep -oE '"version": "[0-9.]+"' package.json | grep -oE '[0-9.]+') VERSION

# 2. Sin placeholders sin sustituir
grep -c '<org>/<repo>' README.md   # esperado: 0

# 3. npm test apunta a algo que existe
node -e "console.log(require('./package.json').scripts.test)"
# después: correr manualmente el path que imprime y confirmar `ls` sobre él

# 4. CHANGELOG deduplicado
grep -c "Added the .cos-patch-release. primitive" CHANGELOG.md   # esperado: 1

# 5. Métricas públicas con timestamp y frescura
python3 -c "import json; d=json.load(open('public-metrics-aspirational.json')); print('timestamp' in d)"
git log -1 --format='%ai' -- public-metrics-aspirational.json public-metrics-dogfood.json

# 6. Hash de TRANSPARENCY.md coincide con el artefacto real
grep -oE '[0-9a-f]{64}' TRANSPARENCY.md | while read h; do
  shasum -a 256 docs/01-Build-Log/history/pre-sanitization-sha-inventory-2026-05-07.txt | grep -q "$h" && echo "match: $h" || echo "NO MATCH: $h"
done

# 7. Rutas lib/ vs cos_lib/ en safety-mesh.md
grep -n '`lib/' docs/04-Concepts/root/safety-mesh.md   # esperado: sin resultados

# 8. Hooks de la malla de 14 capas realmente registrados
for h in clarification-gate.sh blast-radius.sh dry-run-preview.sh rate-limiter.sh \
         scope-proportionality.sh claim-validator.sh assumption-tracker.sh \
         trust-score-validator.sh confidence-gate.sh clarification-interceptor.sh \
         auto-rollback-trigger.sh reinvention-check.sh; do
  echo "$h: $(grep -c "hooks/$h" .claude/settings.json)"
done
```

---

Informe generado el 2026-08-15 11:24 (America/Argentina/Buenos_Aires), en modo
preparación — sin tocar el árbol de trabajo.
