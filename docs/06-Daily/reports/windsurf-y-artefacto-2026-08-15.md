# Windsurf en el manifiesto de arneses y el artefacto en 0 bytes — 2026-08-15

Dos ítems chicos y desconectados, repetidos de informes de otros agentes sin
verificar. Los dos se recontaron antes de tocar nada.

## Ítem 1 — Windsurf en `manifests/ai-agent-harness-landscape.yaml`

### Recuento

```bash
$ git grep -lw Windsurf | wc -l
6
```

6 archivos, no 8, y **ninguno es script** — los seis son `.md` en
`docs/04-Concepts/` y `docs/06-Daily/reports/`.

Ampliando a case-insensitive con límite de palabra:

```bash
$ git grep -ilw windsurf | wc -l
9
```

9 archivos. Los tres adicionales sí son scripts, y sí mencionan Windsurf en
minúscula:

- `scripts/audit_gate_registration.py:137` — `".windsurf/hooks.json"` en una lista de paths de config por arnés.
- `scripts/cos_efficiency_primitives.py:166` — `AdapterCapability("windsurf", [".windsurf", ".windsurfrules"], ...)`.
- `scripts/volatile_number_audit.py:57` — `windsurf` dentro de una regexp de nombres de arnés.

Entonces el conteo real es **9**, no 8, pero la proporción "tres son scripts
de auditoría" resulta **correcta** una vez que se cuenta case-insensitive.
El número exacto del encargo (8) era falso; la afirmación cualitativa que lo
acompañaba, no.

### Para qué existe el manifiesto (leído su encabezado)

```yaml
schema_version: ai-agent-harness-landscape.v1
purpose: Candidate inventory for AI coding IDEs, CLIs, hosted agents, and provider/tool
  surfaces relevant to Cognitive OS harness projection. This is not an implementation
  claim.
```

Es un **inventario de candidatos**, no una lista de "lo soportado". Lo confirma
el propio esquema: `status` admite `candidate`, `deprecated-candidate`,
`hosted-candidate`, `lab-candidate`, `lifecycle-investigation`,
`planned`, `provider-candidate`, `research-candidate` — además de
`implemented`. Hay entradas explícitamente no implementadas y sin intención
inmediata de estarlo (`trae`: `status: research-candidate`,
`next_action: Wait for stable official syntax docs before projection`; `roo-code`:
`status: deprecated-candidate`, `next_action: Do not implement until
shutdown/successor path is resolved`).

Conclusión: la ausencia de Windsurf **no** se explica por "no está
soportado" — el manifiesto lista activamente candidatos no soportados. Es un
gap real, no ruido. Lo refuerza `scripts/cos_efficiency_primitives.py`, que
ya trata a `windsurf` como candidato de la misma familia que `cursor`
(`AdapterCapability` con la misma forma, mismo `proof_level`) sin que el
manifiesto lo refleje — dos fuentes de verdad divergiendo.

### Qué es Windsurf, verificado

`WebFetch` a `https://docs.windsurf.com/` devolvió un **307 redirect** a
`https://docs.devin.ai/desktop/getting-started`. Siguiendo el redirect y
cruzando con búsqueda web (fuentes: `devin.ai/blog/windsurf-is-now-devin-desktop`,
`cognition.com/blog/windsurf`):

- Windsurf era un IDE de IA (fork de VS Code), no una CLI — coincide con lo
  que el propio censo de terminología ya había señalado como error de tipo
  frecuente.
- Cognition AI (dueña de Devin) adquirió Windsurf el 2025-07-14.
- El 2026-06-02 Cognition relanzó el producto como **Devin Desktop**;
  `docs.windsurf.com` redirige a la documentación de Devin desde entonces.

Esto cambia el fix correcto: agregar una fila "Windsurf" como si fuera un
producto vivo e independiente habría sido dato plausible pero **ya viejo** a
la fecha de hoy — exactamente el tipo de dato inventado con forma de dato
verificado que el encargo pedía evitar.

### Fix aplicado

Se agregó la fila con `status: deprecated-candidate` (mismo patrón que
`roo-code`, que ya usa ese estado para "no implementar hasta que se resuelva
el camino de sucesión"), `category: ide`, `projection_surface` tomado
literalmente de lo que ya usa `scripts/cos_efficiency_primitives.py`
(`.windsurfrules`, `.windsurf`), fuentes oficiales verificadas, y un
`next_action` que documenta el rebrand y remite a la entrada `devin`
existente (`category: hosted-agent`, `status: planned`) como el lugar donde
debería vivir la superficie local de Devin Desktop una vez que se distinga
de la superficie de agente hosteado.

```
git diff --stat manifests/ai-agent-harness-landscape.yaml
 1 file changed, 18 insertions(+)
```

Validado:

```bash
$ python3 -c "import yaml; d=yaml.safe_load(open('manifests/ai-agent-harness-landscape.yaml')); print(len(d['candidates']))"
39
$ .venv/bin/python -m pytest tests/contracts/test_ai_agent_harness_landscape.py -q
6 passed in 0.10s
```

## Ítem 2 — artefacto en 0 bytes en `~/.local/share/claude/versions/`

**Fuera del repo, del entorno del operador. No se borró ni se modificó —
solo se leyó.**

```bash
$ ls -la ~/.local/share/claude/versions
-rwxr-xr-x  214210080  2026-05-27  2.1.152
-rw-r--r--          0  2026-06-27  2.1.195
```

Confirmado: existe, está en 0 bytes, y es la única otra versión al lado de
`2.1.152` (204 MB, con permiso de ejecución). No hay `.gz` hermano en
`~/.local/share/claude/` ni en `versions/` — a diferencia de otros casos
medidos hoy, acá no hay histórico truncado deliberadamente al lado; es
simplemente un archivo vacío.

Diagnóstico: `2.1.195` no tiene permiso de ejecución (`rw-r--r--` vs
`rwxr-xr-x` de `2.1.152`) y `file` lo reporta `empty`. Es consistente con una
descarga de auto-update interrumpida antes de escribir contenido — no con un
truncado intencional.

Impacto sobre el binario activo: el `claude` que resuelve por `PATH`
(`~/.local/bin/claude`, 214210080 bytes — mismo tamaño que `2.1.152`, inode
distinto, no es hardlink) sigue siendo una copia funcional de `2.1.152`. El
CLI en uso hoy no pasa por el archivo roto.

### ¿Algún script del repo lee ese directorio?

```bash
$ git grep -niE "\.local/share/claude|claude/versions|versions/[0-9]+\.[0-9]+\.[0-9]+" .
docs/06-Daily/reports/investigacion-a2a-interop-2026-08-15.md:105:  (mención del hallazgo original, no código)
docs/09-Quality/testing/README.md: 3 matches de "$HOME/.goenv/versions/1.25.6" — gestor de versiones de Go, sin relación
```

```bash
$ git grep -lniE "claude.{0,15}(auto.?update|self.?update|update.?check)" -- '*.sh' '*.py'
(sin resultados)
```

Ningún script de este repositorio enumera versiones instaladas de Claude Code
ni lee ese directorio. El hallazgo original venía de
`docs/06-Daily/reports/investigacion-a2a-interop-2026-08-15.md:105`, como
observación al margen de una auditoría de `.well-known/` sobre el binario
`2.1.152` — no de código que dependa de la ruta.

**Cierre: residuo del entorno, probable descarga de auto-update interrumpida,
sin impacto en el repo ni en el binario activo.** No se tocó el archivo.

## Corrections to the brief's premises

- El conteo de "8 archivos" para `Windsurf` era falso: `git grep -lw Windsurf`
  da **6**, y los seis son documentos, no scripts. Ampliando a
  case-insensitive con límite de palabra (`git grep -ilw windsurf`) el total
  real es **9**, y ahí sí aparecen los tres scripts que el encargo
  mencionaba — la cifra puntual estaba mal, la composición cualitativa
  ("tres son scripts de auditoría") resultó correcta una vez recontada bien.
- La premisa implícita de "agregar la fila si corresponde" resultó más
  matizada de lo planteado: Windsurf como marca independiente **dejó de
  existir** el 2026-06-02 (rebrand a Devin Desktop por Cognition AI,
  verificado por redirect 307 de `docs.windsurf.com` y por dos fuentes
  externas). Agregar una fila "Windsurf" viva habría sido el propio error que
  el encargo pedía evitar — dato plausible pero desactualizado. Se agregó
  igual, pero como `deprecated-candidate` con el rebrand documentado y un
  puente explícito hacia la entrada `devin` ya existente.
- Sobre el ítem 2, la pista de "hoy se midió dos veces un 0 bytes con `.gz`
  hermano" no aplicó acá — se verificó explícitamente que no hay `.gz` ni
  ningún otro sibling relacionado a `2.1.195`. Se registra para no dar por
  sentado el patrón sin comprobarlo.
- El resto de premisas del encargo (para qué existe el manifiesto, qué campos
  exige el esquema, restricción de no tocar `hooks/**`/`rules/**`, no borrar
  el artefacto) se sostuvieron sin corrección.
