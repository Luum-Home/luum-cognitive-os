---
title: "Anexo F — Compliance & Clean-Room Protocol"
date: 2026-05-11
annex: F
parent: holaos-comparison-2026-05-10.md
status: operational-policy
---

# Anexo F — Compliance & Clean-Room Protocol

## §1. Resumen ejecutivo

holaOS está licenciado bajo Apache 2.0 modificada con cláusulas de tipo BSL (secciones 1.a y 2.a del LICENSE). La sec. 1.a prohíbe usar el código fuente de holaOS para proveer un servicio hosted a terceros o embeber holaOS en un producto comercialmente distribuido. La sec. 2.a permite a Holaboss endurecer la licencia unilateralmente en cualquier momento.

La postura obligatoria de luum-agent-os es **patterns-only con clean-room obligatorio**: ningún agente implementador lee código fuente de holaOS; solo lee specs abstractas producidas por agentes de research en aislamiento. Esta postura se fundamenta en 17 USC §102(b), que excluye las ideas, procedimientos, procesos y sistemas de la protección del derecho de autor.

Los agentes de research (que ya corrieron en la fase de investigación de este repo) pueden leer `/tmp/holaOS-investigation` libremente y producen únicamente documentos abstractos (Anexos A–F). Los agentes implementadores consumen esos anexos y nunca acceden a paths holaOS. Los reviewers pueden leer ambos mundos exclusivamente para verificar que no haya transcripción literal.

Se requiere escalation a review humano o legal ante cualquier copia literal mayor a 5 tokens consecutivos, cualquier identificador no-genérico coincidente, o ante cualquier cambio de modelo de distribución de luum hacia SaaS o embebido comercial. Este documento operativiza la postura establecida en el Anexo E.

---

## §2. Niveles de adopción permitidos

### Nivel 1 — Patrones e ideas (libre)

Los patrones, ideas, algoritmos, taxonomías, state machines, políticas y workflows son **adoptables sin restricción**. La ley de derechos de autor no protege las ideas en sí mismas.

> **17 USC §102(b):** "In no case does copyright protection for an original work of authorship extend to any idea, procedure, process, system, method of operation, concept, principle, or discovery, regardless of the form in which it is described, explained, illustrated, or embodied in such work."

Ejemplos concretos del top-10 de holaOS adoptables en Nivel 1:

| # | Patrón holaOS | Equivalente luum permitido |
|---|---------------|---------------------------|
| 1 | Taxonomía de skills por prioridad (project > global > auto) | Jerarquía de resolución de skills ya existente |
| 2 | State machine PENDING→RUNNING→DONE→FAILED | `AgentLifecycle` states en `packages/agent-lifecycle` |
| 3 | Política de retry con límite de 3 intentos | `retry-contract` + ADR-228 |
| 4 | Presupuesto de tokens por sesión y resource governor | `lib/resource_governor.py` |
| 5 | Workflow explore→propose→spec→apply→verify | Pipeline SDD existente |
| 6 | Aislamiento de credenciales en env vars | `credential-management` rule |
| 7 | Logging estructurado de eventos de agentes | `lib/harness_adapter/` + `agent-heartbeat.jsonl` |
| 8 | Clasificación de componentes CORE vs PACKAGE | `component-classification` rule |
| 9 | Kill-switches de features por variable de entorno | `COS_DISABLE_LLM_FALLBACK`, `COS_FORCE_CLAUDE_PRIMARY` |
| 10 | ADR umbrella como registro de adopciones de patrones | ADR a crear por cada adopción clean-room |

### Nivel 2 — Re-implementación clean-room (seguro)

La re-implementación clean-room es el mecanismo que permite trasladar **comportamientos** sin trasladar **expresión**. El protocolo de dos actores funciona así:

1. **Research agent** (ya completado en este proyecto): lee el código fuente de holaOS, extrae el comportamiento observable, las invariantes y las políticas. Produce un documento de especificación **puramente abstracto** (los Anexos A–E de este research). No incluye identificadores, fragmentos ni estructura de archivos del original.
2. **Implementer agent**: recibe **únicamente** el documento de spec. Nunca ve el código fuente original. Escribe la implementación desde cero, guiado por la especificación abstracta.

Este protocolo replica el método que Compaq utilizó en 1982 para re-implementar la BIOS de IBM PC: un equipo documentó el comportamiento observable de la BIOS (entradas, salidas, condiciones de error) sin ver el código; un segundo equipo, completamente separado y sin contacto con el primero, escribió una BIOS compatible. La corte en *Phoenix Technologies v. NEC* (1984) validó que este proceso producía trabajo original no infractor.

**Condiciones de aislamiento para luum:**

- Los prompts enviados a implementer agents NO deben contener paths que comiencen con `/tmp/holaOS`.
- Si un prompt incluye accidentalmente referencias a archivos holaOS, el implementer agent DEBE rechazar la tarea y emitir `NEEDS_CLARIFICATION: el prompt contiene referencias a fuentes holaOS; proporcionar solo la spec abstracta`.
- Los reviewers son el único rol que puede comparar spec + implementación + fuente para verificar ausencia de transcripción literal.

### Nivel 3 — Copia literal (BLOCK)

Los siguientes artefactos están **bloqueados** bajo cualquier circunstancia, independientemente del contexto de distribución:

- Headers de archivos con copyright holaOS / Holaboss
- Nombres de funciones o variables reveladores del original (p. ej., `signGrant`, `evolveSkillReview`, `HarnessTodoState`, `HarnessAdapter`)
- Estructura de directorios replicada (p. ej., `desktop/` como nombre de módulo frontend)
- Comentarios inline o docstrings copiados, incluidos los que describen algoritmos
- Fixtures de tests copiadas de holaOS (datos de ejemplo, valores hardcodeados específicos)
- Fragmentos de documentación copiados, incluyendo README, ADRs y comentarios de PR
- Archivos enteros o sustancialmente similares (>30% de contenido idéntico)
- Mensajes de log o error verbatim que identifiquen a holaOS como origen
- Strings de UI o mensajes de sistema copiados del frontend holaOS

---

## §3. Matriz de uso × permitido/prohibido

| Artefacto | Uso interno cerrado | OSS (pip install) | SaaS comercial | Embed redistribuible |
|-----------|--------------------|--------------------|----------------|----------------------|
| Idea / algoritmo / patrón | ALLOW | ALLOW | ALLOW | ALLOW |
| API signature (nombres idénticos) | PATTERN-ONLY¹ | PATTERN-ONLY¹ | BLOCK² | BLOCK² |
| Identificadores no-genéricos | BLOCK³ | BLOCK³ | BLOCK³ | BLOCK³ |
| Fixtures de tests | BLOCK | BLOCK | BLOCK | BLOCK |
| Texto de documentación | BLOCK | BLOCK | BLOCK | BLOCK |
| Fragmento de código (<10 líneas) | BLOCK | BLOCK | BLOCK | BLOCK |
| Archivo entero o sustancial | BLOCK | BLOCK | BLOCK | BLOCK |

**Notas:**

1. PATTERN-ONLY: la firma puede inspirarse en el diseño de la API de holaOS, pero los nombres de métodos deben ser re-escritos con identidad propia (p. ej., `issue_token` en vez de `signGrant`).
2. BLOCK bajo sec. 1.a del LICENSE: distribución comercial (SaaS, embed vendido) requiere licencia comercial de Holaboss.
3. Identificadores no-genéricos idénticos son evidencia prima facie de copia; bloqueados en todos los contextos.

---

## §4. Reglas de aislamiento entre agentes

### 4.1 Roles y permisos de acceso

| Rol | Puede leer `/tmp/holaOS*` | Puede leer Anexos A–F | Puede leer impl luum | Propósito |
|-----|--------------------------|----------------------|---------------------|-----------|
| Research agent | SÍ | SÍ (produce) | NO | Extraer patterns abstractos |
| Implementer agent | **NO** | SÍ (consume) | SÍ | Escribir código desde specs |
| Reviewer agent | SÍ (solo-lectura) | SÍ | SÍ | Verificar no-transcripción |
| Orchestrator | NO (excepto metadatos) | SÍ | SÍ | Coordinar fases |

La separación es físicamente forzada por el contenido del prompt de cada agente: el orchestrator es responsable de no incluir en el prompt del implementer ningún contenido proveniente de `/tmp/holaOS-investigation`. El reviewer recibe ambos mundos pero su único output permitido es un informe de verificación, no código.

### 4.2 Archivos holaOS y su clasificación por ADR

Los ADRs que adopten patrones de holaOS deben declarar en su frontmatter:

```yaml
pattern_source: "holaos-comparison-2026-05-10.md::Annex<X>::<section>"
holaos_files_read_by_research: []     # lista de archivos leídos en research
holaos_files_blocked_for_impl: ["ALL"] # implementer agent siempre bloquea ALL
```

Ningún ADR de implementación debe listar archivos holaOS en sus inputs. Si se requiere consulta adicional sobre comportamiento de holaOS, debe pasar a través de un Research agent intermediario que produzca una spec suplementaria.

Clasificación nominal de archivos holaOS relevantes del research:

| Archivo holaOS (path relativo) | Research puede leer | Implementer puede leer | Reviewer puede leer |
|-------------------------------|--------------------|-----------------------|---------------------|
| Cualquier archivo en `/tmp/holaOS-investigation/` | SÍ | **NO** | SÍ (read-only) |
| Docs/research/holaos-annex-*.md (este proyecto) | SÍ | SÍ | SÍ |
| Archivos intermedios en `/tmp/holaOS*` | SÍ | **NO** | SÍ (read-only) |

### 4.3 Protocolo de rechazo del implementer agent

Si el prompt de un implementer agent contiene cualquiera de los siguientes indicadores, el agente DEBE detener la ejecución inmediatamente y emitir `NEEDS_CLARIFICATION:` antes de hacer cualquier otra acción:

- Cualquier path que coincida con `/tmp/holaOS*` o `/tmp/hola*`
- Cualquier referencia explícita a un archivo del repositorio holaOS (p. ej., nombres de módulos, rutas de directorio del repo fuente)
- Cualquier fragmento de código que el agente reconozca como no proveniente de la spec abstracta del research
- Cualquier instrucción que diga "basándote en el código de holaOS" sin referencia a un Anexo específico

Mensaje de rechazo estándar:

```
NEEDS_CLARIFICATION: Este prompt contiene referencias a fuentes holaOS
(path o fragmento de código fuente). Por política de clean-room, el
implementer agent solo puede recibir specs abstractas (Anexos A–F).
Por favor reenviar el prompt con solo la referencia al Anexo relevante.
```

---

## §5. Checklist pre-commit por adopción

Cada commit que adopte un patrón de holaOS debe ser verificado contra esta checklist. Los items marcados con `[grep]` incluyen el comando de verificación.

- [ ] **No strings literales compartidos** `[grep]`: `grep -rF "<string_clave>" /tmp/holaOS-investigation` — si hay match, el string no puede aparecer en el diff.
- [ ] **Identificadores renombrados**: ningún identificador en el diff coincide con nombres no-genéricos de holaOS (p. ej., `signGrant` → `issue_token`, `evolveSkillReview` → `review_skill_evolution`).
- [ ] **Comentarios originales**: todos los comentarios inline y docstrings fueron escritos desde cero por el implementer; no contienen frases copiadas de comentarios holaOS.
- [ ] **No fixtures copiadas**: los archivos de fixtures/test data del diff no tienen origen en `/tmp/holaOS-investigation/tests/`.
- [ ] **No paths holaOS en docs ni código**: `grep -r "holaOS\|holaboss\|Holaboss" <files_in_diff>` — solo se permiten menciones en `docs/research/` y `docs/compliance/`.
- [ ] **Commit message cita pattern-source**: el mensaje incluye `Pattern adopted from holaOS` y referencia al anexo correspondiente (ver §6).
- [ ] **Spec abstracta existente**: el patrón adoptado está documentado en uno de los Anexos A–F antes del commit de implementación.
- [ ] **Engram observation creada**: existe observación `compliance/holaos-adoption/<feature>` en Engram con status `verified`.
- [ ] **Registry actualizado**: `docs/compliance/holaos-adoptions.md` tiene fila append-only para esta adopción.
- [ ] **Revisión de blast radius**: si la adopción modifica >5 archivos, se ejecutó `scripts/blast_radius_check.py` antes del commit.
- [ ] **No copia de estructura de directorios**: la estructura de `packages/` y `lib/` no replica la jerarquía de directorios de holaOS.
- [ ] **Licencia del archivo nueva**: si se crea un archivo nuevo, el header refleja la licencia de luum-agent-os, no holaOS.

---

## §6. Plantilla de commit message

Todo commit que adopte un patrón de holaOS DEBE usar exactamente esta estructura:

```
<scope>: <change>

Pattern adopted from holaOS (clean-room rewrite).
Refs: docs/research/holaos-comparison-2026-05-10.md
Source-pattern: <annex>::<section>
License: Apache-2.0 modified (BSL-like). No source code copied.
```

**Variables:**

- `<scope>`: módulo de luum afectado (p. ej., `agent-lifecycle`, `cost-budget`, `security`)
- `<change>`: descripción imperativa del cambio (p. ej., `add token budget governor`)
- `<annex>`: identificador del anexo fuente (p. ej., `AnnexB`, `AnnexD`)
- `<section>`: sección del anexo (p. ej., `§3.2`, `§4`)

**Ejemplo concreto:**

```
agent-lifecycle: add three-tier retry policy with exponential backoff

Pattern adopted from holaOS (clean-room rewrite).
Refs: docs/research/holaos-comparison-2026-05-10.md
Source-pattern: AnnexC::§2.retry-policy
License: Apache-2.0 modified (BSL-like). No source code copied.
```

---

## §7. Audit trail y evidence

### 7.1 Observación Engram por adopción

Por cada feature adoptada, crear una observación Engram con los siguientes campos exactos:

- **title**: `clean-room adoption: <feature>` (p. ej., `clean-room adoption: token budget governor`)
- **topic_key**: `compliance/holaos-adoption/<feature>` (p. ej., `compliance/holaos-adoption/token-budget`)
- **type**: `policy`
- **scope**: `project`
- **content** (secciones requeridas):
  - `What`: descripción del patrón adoptado en 2–3 oraciones
  - `Why`: por qué este patrón fue elegido sobre alternativas nativas
  - `Where`: archivos de luum creados o modificados
  - `Annex`: referencia al anexo y sección fuente
  - `Grep result`: output del comando grep de verificación (PASS/FAIL + count)
  - `Date`: fecha ISO de la adopción
  - `Implementer agent`: ID del agente que escribió la implementación
  - `Reviewer`: ID del agente o persona que verificó la ausencia de copia literal

Llamar `mem_save` inmediatamente después de cada commit de adopción verificado, antes de cerrar la sesión.

### 7.2 Registry append-only

Mantener `docs/compliance/holaos-adoptions.md` con la siguiente estructura de tabla. **Solo se permiten filas nuevas; nunca editar ni borrar filas existentes.** El archivo es evidencia legal de due diligence.

```markdown
| Feature | Fecha | ADR ref | Implementer agent ID | Grep verify | Status |
|---------|-------|---------|----------------------|-------------|--------|
| token-budget-governor | 2026-05-11 | ADR-XXX | agent-abc123 | PASS (0 matches) | verified |
```

El campo `Grep verify` documenta el resultado del comando grep de la checklist §5 (PASS = sin matches en `/tmp/holaOS-investigation`). Cualquier fila con status `pending` debe resolverse antes del siguiente release.

Si el archivo `docs/compliance/` no existe aún, crearlo con el header de tabla antes del primer commit de adopción.

### 7.3 Pre-commit hook propuesto (diseño, no implementar aún)

**Archivo:** `hooks/holaos-cleanroom-gate.sh`

**Comportamiento esperado:**

1. Obtiene la lista de archivos en el diff staged: `git diff --cached --name-only`.
2. Filtra archivos excluyendo `docs/research/` y `docs/compliance/` (referencias documentales permitidas).
3. Para cada archivo restante, extrae tokens alfanuméricos de longitud >5 del diff (`git diff --cached -- <file>`).
4. Para cada token, ejecuta `grep -qrF "<token>" /tmp/holaOS-investigation 2>/dev/null`.
5. Si encuentra un match para un token no-genérico: imprime `BLOCK: string literal holaOS detectado en diff: "<token>" en <archivo>` y sale con código 1.
6. Si no encuentra matches: imprime `OK: holaOS clean-room gate passed` y sale con código 0.
7. Loggear cada ejecución a `.cognitive-os/audit/holaos-cleanroom-gate.jsonl` con schema:
   ```json
   {"ts": "<ISO>", "files_checked": [...], "tokens_checked": N, "matches": [], "result": "pass|fail"}
   ```
8. Si `/tmp/holaOS-investigation` no existe (p. ej., CI limpio): el hook pasa con warning `WARN: /tmp/holaOS-investigation no encontrado, gate omitido`.

**Lista de tokens genéricos excluidos del chequeo** (no provocan BLOCK): `true`, `false`, `null`, `error`, `result`, `status`, `config`, `name`, `type`, `value`, `data`, `path`, `file`, `agent`, `model`, `skill`, `session`, `token`, `user`, `message`.

**Activación propuesta** (cuando se implemente): añadir a `hooks/self-install.sh` bajo el profile `standard` y `paranoid`, omitir en `minimal`. Registrar en `.claude/settings.json` bajo `hooks.PreToolUse` para ejecución automática en commits.

---

## §8. Escalation: cuándo pedir review humano/legal

Los siguientes eventos requieren **detener la implementación** y solicitar revisión humana (o asesoría legal si el contexto es comercial). Ningún agente debe continuar implementando hasta que se resuelva el trigger.

### Triggers de escalation obligatorios

1. **Copia literal >5 tokens consecutivos**: cualquier secuencia de más de 5 tokens idénticos entre el diff y cualquier archivo en `/tmp/holaOS-investigation`. El hook `holaos-cleanroom-gate.sh` detectará esto automáticamente cuando esté implementado.
2. **Identificador idéntico no-genérico**: aparición en el diff de `signGrant`, `evolveSkillReview`, `HarnessTodoState`, `HarnessAdapter`, `SkillTaxonomy`, o cualquier otro identificador específico de holaOS que no sea una palabra común del dominio de software.
3. **Fragmento de docs o comentarios**: cualquier frase de más de 8 palabras que aparezca literalmente en la documentación o comentarios de holaOS (incluyendo README, ADRs, inline comments).
4. **Intento de distribución SaaS**: cualquier cambio de arquitectura que implique exponer luum-agent-os como servicio gestionado a terceros (requiere licencia comercial de Holaboss según sec. 1.a del LICENSE).
5. **Embed redistribuible comercial**: cualquier plan de empaquetar luum-agent-os como componente de un producto vendido a terceros, sea como SDK, plugin vendido, o producto SaaS (misma restricción sec. 1.a).
6. **Cambio de licencia de luum**: cualquier propuesta de cambiar la licencia de luum-agent-os hacia un modelo comercial o propietario que pudiera entrar en tensión con la sec. 1.a de holaOS o requerir declaraciones de independencia.
7. **Contribuciones upstream a holaOS**: si algún miembro del equipo desea contribuir código de luum-agent-os upstream a holaOS, aplica sec. 2.a (el código contribuido puede usarse comercialmente por Holaboss); revisar implicaciones antes de hacer PR.
8. **Actualización del LICENSE de holaOS**: si Holaboss publica una nueva versión del LICENSE (posible bajo sec. 2.a), todas las adopciones futuras deben re-evaluarse contra los nuevos términos.

### Proceso de escalation

```
[TRIGGER DETECTADO]
        ↓
Detener agente en curso (no hacer commit)
        ↓
Crear issue en tracker con label "compliance-review" + descripción del trigger
        ↓
Notificar lead técnico con contexto (qué se detectó, en qué archivo, qué ADR)
        ↓
¿Involucra distribución comercial / SaaS / embed?
    SÍ → Contactar asesor legal antes de continuar
    NO → Lead técnico puede resolver internamente
        ↓
Documentar decisión final en Engram bajo:
  topic_key: "compliance/holaos-escalation/<YYYY-MM-DD>-<trigger-type>"
  type: decision
        ↓
[REANUDAR o ABANDONAR adopción según decisión]
```

---

## §9. Apéndice: texto literal relevante del LICENSE

El siguiente texto es citado literalmente del archivo `/tmp/holaOS-investigation/LICENSE` (Copyright © 2026 Holaboss):

### Sección 1.a — Hosted or embedded service

> "Unless explicitly authorized by Holaboss in writing, you may not use the holaOS source code to provide a hosted service to third parties, or embed holaOS as a component of a product or service that is sold, licensed, or otherwise commercially distributed to third parties.
>
> - This restriction applies to offering holaOS (in whole or substantial part) as a SaaS platform, a managed service, or as an integrated component within another commercial offering.
> - Internal use within a single organization (including multiple workspaces) does not require a commercial license."

**Implicación para luum**: luum-agent-os no utiliza código fuente de holaOS, solo patrones abstractos re-implementados en clean-room. La restricción de sec. 1.a aplica al *source code* de holaOS, no a comportamientos re-implementados independientemente. Sin embargo, si en el futuro luum-agent-os se distribuye como SaaS y se descubre que contiene código copiado (Nivel 3 según §2), sec. 1.a se activaría.

### Sección 1.b — LOGO and copyright information

> "In the process of using holaOS's frontend, you may not remove or modify the LOGO or copyright information in the holaOS console or applications. This restriction is inapplicable to uses of holaOS that do not involve its frontend.
>
> - Frontend Definition: For the purposes of this license, the 'frontend' of holaOS includes all components located in the `desktop/` directory when running holaOS from the raw source code, or the packaged desktop application when running a distributed build."

**Implicación para luum**: luum-agent-os no utiliza el frontend de holaOS (`desktop/`), por lo que sec. 1.b no aplica en ningún escenario actual.

### Sección 2.a — Cambio unilateral de licencia

> "The producer can adjust the open-source agreement to be more strict or relaxed as deemed necessary."

**Implicación para luum**: Holaboss puede endurecer los términos en cualquier momento. Los patrones adoptados bajo clean-room en la fecha de este documento (2026-05-11) están documentados como basados en la licencia vigente a esa fecha. Si Holaboss endurece la licencia posteriormente, las adopciones ya documentadas y verificadas como clean-room no se ven retroactivamente afectadas (el clean-room produce obra original independiente). Sin embargo, cualquier adopción futura debe verificarse contra la versión de licencia vigente en ese momento.

---

## §10. UNSURE / HUMAN-CHECK

Las siguientes áreas requieren cautela adicional y, en contextos de distribución comercial, asesoría legal profesional antes de proceder:

1. **Este documento no es asesoría legal.** El análisis de los Anexos A–F fue producido por agentes de IA aplicando principios generales de derecho de autor de EE.UU. (17 USC §102(b)) y referencias al caso Compaq/IBM BIOS como precedente de clean-room. La interpretación de licencias modificadas no estándar puede variar significativamente según jurisdicción: la Unión Europea aplica la Directiva 2009/24/CE sobre protección de programas de ordenador (que tiene disposiciones específicas sobre interfaces e interoperabilidad que pueden diferir de 17 USC), el Reino Unido post-Brexit tiene su propio régimen bajo la CDPA 1988, y otras jurisdicciones pueden no reconocer el clean-room de la misma forma que los tribunales de EE.UU. Antes de cualquier distribución comercial o publicación OSS de luum-agent-os que involucre patrones derivados de holaOS, se recomienda **consultar a un abogado especializado en propiedad intelectual de software** para el mercado objetivo.

2. **La sección 1.a de holaOS no es Apache 2.0 estándar, y su alcance exacto sobre re-implementaciones clean-room es ambiguo.** La cláusula dice literalmente "use the holaOS source code to provide a hosted service" — esta redacción condiciona la restricción al uso del *source code*, lo que sugiere que una re-implementación clean-room que no usa el source code no cae dentro de sec. 1.a. Sin embargo, la frontera entre "usar el source code" y "usar un sistema funcionalmente equivalente al source code" no está definida en el LICENSE y no existe jurisprudencia publicada directamente sobre este texto específico de Holaboss. Un tribunal podría interpretar la cláusula de forma más expansiva si la similitud funcional entre luum-agent-os y holaOS es suficientemente alta y el contexto es distribución comercial. El proceso clean-room de §2 mitiga significativamente este riesgo, pero no lo elimina al 100% en escenarios de SaaS o embed comercial.

3. **La cláusula 2.a (cambio unilateral) introduce incertidumbre temporal.** No está claro si Holaboss podría aplicar retroactivamente términos más estrictos a adopciones clean-room ya realizadas bajo la versión vigente de la licencia. La doctrina general de derecho de contratos sugiere que los términos al momento de la acción son los aplicables, pero esto es un área de riesgo no resuelta sin asesoría legal específica.

---

---

## Referencias cruzadas

| Documento | Relación |
|-----------|----------|
| `docs/research/holaos-comparison-2026-05-10.md` | Documento padre — análisis comparativo completo |
| `docs/research/holaos-annex-a-memory.md` | Patrón de memoria — fuente de adopciones candidatas |
| `docs/research/holaos-annex-b-cost-budget.md` | Patrón de presupuesto — fuente de adopciones candidatas |
| `docs/research/holaos-annex-c-evolution.md` | Patrón de evolución — fuente de adopciones candidatas |
| `docs/research/holaos-annex-d-security-plan.md` | Patrón de seguridad — fuente de adopciones candidatas |
| `docs/research/holaos-annex-e-architecture-risks.md` | Análisis de riesgos — establece postura patterns-only |
| `docs/compliance/holaos-adoptions.md` | Registry append-only de adopciones verificadas (crear al primer commit de adopción) |
| `hooks/holaos-cleanroom-gate.sh` | Pre-commit hook propuesto (diseño en §7.3, implementar en sprint posterior) |
| `lib/resource_governor.py` | Primer candidato a adopción clean-room (Nivel 2) |

---

*Documento producido como parte del research de adopción de patrones holaOS para luum-agent-os. Status: operational-policy. Revisión recomendada ante cualquier cambio de modelo de distribución de luum, ante actualizaciones del LICENSE de holaOS (posible bajo sec. 2.a), o ante nuevas adopciones que alcancen el umbral de escalation de §8.*
