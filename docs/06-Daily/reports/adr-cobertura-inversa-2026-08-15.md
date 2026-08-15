# Cobertura inversa de ADRs: qué implementó el SO que no está en ningún ADR

Fecha: 2026-08-15
Alcance: la dirección contraria a la que miden los otros tres agentes de ADRs.
Ellos preguntan *"¿este ADR describe algo real?"*. Acá la pregunta es
*"¿esta decisión implementada tiene decisión escrita?"*.

Un ADR que sobra es ruido. Una decisión implementada sin ADR es una decisión
que nadie puede revisar ni revertir: el código dice *qué* y no queda nadie que
sepa *por qué*.

---

## 1. El criterio (escrito antes de aplicarlo)

No todo archivo necesita un ADR. Si se exige uno por cada script salen 400
hallazgos y ninguno accionable. **Necesita decisión escrita lo que alguien
podría querer revertir o cuestionar.** En concreto, exactamente uno de:

| Clase | Definición | Fuente de verdad |
|---|---|---|
| **D1 — gate que bloquea** | un hook que puede denegar una acción del operador | `scripts/audit_gate_registration.py` (`can_block: true`) |
| **D2 — política codificada** | un manifiesto de `manifests/` cuyas claves de primer nivel codifican política (freeze, allowlist, denylist, budget, quota, scope, threshold, ratchet, baseline, required, forbidden) — se detecta por clave, no por nombre de archivo | claves YAML de primer nivel |
| **D3 — frontera de paquete** | `packages/*/cos-package.yaml`: qué viaja junto y qué recibe un consumidor | el propio manifiesto |

**Fuera de la población, a propósito:** scripts de evidencia read-only, tests,
informes, helpers internos, docs, e inventarios sin verbo de política.

**Qué cuenta como respaldo — se chequea en las dos direcciones**, y esto
importa más de lo que parece:

- `self_cited` — el cuerpo del archivo cita `ADR-NNN` y ese ADR existe.
- `adr_cites` — algún ADR nombra al archivo (hook / manifiesto / paquete).
- `dangling` — cita `ADR-NNN` y **no hay tal archivo**. Peor que no citar: se
  lee como respaldado y no lo está.

El criterio vive en código, en el docstring de
`scripts/audit_decision_backing.py`, no solo en esta prosa. Si alguien amplía
la población, la amplía ahí, con motivo.

---

## 2. El número

```
python3 scripts/audit_decision_backing.py
```

| Clase | Población | Sin respaldo | Cobertura |
|---|---:|---:|---:|
| gates que bloquean (D1) | 76 | **10** | 87 % |
| manifiestos de política (D2) | 65 | **12** | 82 % |
| paquetes (D3) | 32 | **18** | 44 % |
| **total** | **173** | **40** | **77 %** |

Citas colgadas: **1** (`hooks/adr-section-validator.sh` cita `ADR-000`, que no
existe).

**La cobertura es bastante mejor de lo que sugería el encargo.** En la clase
que importa —los gates que pueden bloquear al operador— 66 de 76 tienen algún
ADR que los nombra. El hueco es real pero es de decenas, no de cientos.

---

## 3. Lo prioritario: gates que bloquean y no tienen respaldo escrito

Cruzando la lista con `scripts/audit_gate_liveness.py --json` (cuadrante y
bloqueos medidos sobre 49.718 filas de telemetría):

| Gate | Cuadrante | Bloqueos medidos | Disparos | Motivo reconstruible |
|---|---|---:|---:|---|
| `provenance-scan` | **live** | **3** | 257 | sí — commit 2026-06-04 *"Add agnostic provenance scan guardrail"* |
| `untracked-work-preservation-guard` | **live** | **1** | 457 | sí — commit 2026-05-06 *"feat(safety): guard untracked artifact deletion"* |
| `session-quality-close-gate` | advisory-only | 0 | 54 | **no** — solo aparece en un commit de release (`v0.29.13`) |
| `document-ingest-guard` | untested | 0 | 62 | parcial — *"feat(context): harden context rot controls"* |
| `host-tool-doctor` | theatre | 0 | 8 | sí — *"run cached host doctor on session start"* |
| `ai-provider-identity-guard` | unmeasured | 0 | 0 | sí — *"block invented AI provider identities"* |
| `conflict-marker-guard` | unmeasured | 0 | 0 | sí — *"Add portable conflict marker guard"* |
| `cross-session-coordination-guard` | unmeasured | 0 | 0 | sí — *"feat(coordination): add cross-session message ledger"* |
| `research-compliance-guard` | unmeasured | 0 | 0 | **no** — solo commits de release (`v0.29.9`, `v0.29.11`) |
| `session-end-cleanup` | *fuera de la población de liveness* | — | — | parcial — *"hooks/session-end-cleanup.sh (unregistered)"* |

**Los dos primeros son el hallazgo accionable**: bloquean hoy, en producción,
y ninguna decisión escrita los respalda. `provenance-scan` además se proyecta
a los consumidores (aparece 5 veces en `scripts/cos_init.py`), así que bloquea
también en repos ajenos.

**Motivo perdido — no inventar ADR:** `session-quality-close-gate` y
`research-compliance-guard` no tienen ni un commit con intención propia; nacen
dentro de commits de release. Reconstruir su *por qué* sería ficción. El
hallazgo correcto es **"se implementó sin decisión escrita y el motivo se
perdió"**, no un ADR retroactivo.

### Sobre el resto: motivo reconstruible ≠ motivo escrito

Los commits que sí existen tienen **el cuerpo vacío**: solo asunto.

```
git log --format='%b' --grep="Add agnostic provenance scan guardrail" -1   # → vacío
```

El asunto dice *qué hace* y a veces insinúa *para qué*. No dice qué
alternativas se descartaron ni qué trade-off se aceptó — que es lo que se
necesita para revertir con criterio. Así que "reconstruible" acá significa
*reconstruible a nivel de intención, no de decisión*.

---

## 4. Las otras dos clases, con su matiz

**Manifiestos de política (12 sin respaldo).** Los más notables:
`network-egress-policy`, `runtime-hardcoding-allowlist`,
`credential-safe-scripts`, `provider-executor-contracts`,
`ai-provider-identity-policy`, `scope-closure-baseline`,
`exercised-coverage-baseline`. Son allowlists y baselines: exactamente el tipo
de archivo donde un número mal puesto se vuelve un colchón invisible.

**Paquetes (18 sin respaldo) — clase más débil, lo digo yo mismo.** Muestreo de
5, contando cuántos de sus `exports` aparecen nombrados en algún ADR:

| paquete | exports nombrados en ADRs |
|---|---|
| `scope-governance` | 1/1 |
| `privacy-mode` | 1/1 |
| `task-management` | 1/1 |
| `usage-monitor` | 0/1 |
| `dry-run-simulation` | 0/1 |

En 3 de 5, **el comportamiento sí está documentado; lo que no tiene respaldo es
la decisión de empaquetado** (qué viaja junto, con qué versión, hacia qué
consumidor). Es un hallazgo más blando que el de los gates y la tabla debería
leerse así. No lo saqué de la población porque la frontera de paquete sí es una
decisión revertible, pero no lo pondría arriba de `provenance-scan`.

---

## 5. El detector y su ratchet

`scripts/audit_decision_backing.py` — read-only, determinista, sin estado de
sesión. Es el control que faltaba: **ninguna herramienta del repo verificaba
que una decisión implementada tuviera decisión escrita.**

```
python3 scripts/audit_decision_backing.py                     # panel
python3 scripts/audit_decision_backing.py --kind blocking-gate --unbacked-only
python3 scripts/audit_decision_backing.py --json
```

Contrato verificado: exit **0** dentro del ratchet, **1** regresión, **2**
error. Dos corridas seguidas dan hash idéntico.

Ratchet en `manifests/decision-backing-ratchet.yaml`, **fijado en la realidad
medida** (10 / 12 / 18 / 1), sin colchón. Un baseline por encima de la realidad
acepta deuda nueva mientras informa "0 nuevas".

**El detector se encontró a sí mismo.** El propio ratchet matchea D2 (clave
`max_unbacked`) y quedó contado como el duodécimo manifiesto sin respaldo, en
vez de exceptuarlo — un gate que se excusa a sí mismo es el primer verde
barato. Si el operador decide que este control merece ADR, el número baja a 11.

### El verde barato de este lote

**Escribir 40 ADRs retroactivos para tapar el hueco.** Un ADR escrito después,
por alguien que no tomó la decisión, inventando el *por qué*, parece registro y
es ficción — y encima apagaría el detector. No escribí ninguno. El entregable
es el censo, no el relleno.

Segundo verde barato, más sutil: **subir el ratchet en vez de bajar el hueco.**
Por eso los números del manifiesto son los medidos y cada uno tiene al lado qué
acepta.

---

## 6. Qué del encargo era falso

Recontado, no heredado.

| Afirmación del encargo | Medido hoy | Veredicto |
|---|---|---|
| «502 ADRs» | 502 **archivos**, pero 150 son `.synthesis.md` (compañeros, no decisiones) y hay 342 números distintos sobre 146 números con más de un archivo | **Engañoso.** Son ~351 documentos ADR, no 502 decisiones. `ls docs/02-Decisions/adrs/ADR-*.md \| grep -vc synthesis` → 351 |
| «256 hooks canónicos» | 256 según `audit_gate_registration.py`; `ls hooks/*.sh` da 257 y la deduplicación por `readlink -f` da 255 | **Correcto con la fuente citada**, pero los tres conteos difieren — hay 42 symlinks en `hooks/` |
| `protected-config-write-guard`: 57 bloqueos | **49** | **Falso** |
| `destructive-git-blocker`: 66 bloqueos | **41** | **Falso** |
| `direct-main-guard`: 45 bloqueos | **13** | **Falso** |
| `subagent-budget-enforcer`: 66 bloqueos | **75** | **Falso** |
| «alguno de esos cuatro puede estar bloqueando sin ADR» | los **cuatro** tienen respaldo: 12, 19, 6 y 4 ADRs los nombran respectivamente | **Falso, y era la hipótesis de prioridad del encargo.** Los gates ruidosos son justamente los documentados; el hueco está en los callados |
| «ya existe un mapeo ADR↔implementación que no vi» | no existe. `audit_gate_registration.py` mapea hook↔settings, `audit_gate_liveness.py` mapea hook↔telemetría; ninguno mira ADRs | **Confirmado: el control faltaba** |

Los conteos de bloqueo del encargo salen todos de la misma corrida y todos
difieren de `scripts/audit_gate_liveness.py --json` de hoy. No sé si la
telemetría creció entre ambas corridas o si la fuente era otra; en cualquier
caso, **el número que vale es el que trae el comando al lado**, y ninguno de
los cuatro sostenía la conclusión que se le colgaba.

---

## 7. Lo que NO cubre este control

- Solo mira `hooks/`, `manifests/` y `packages/`. `skills/`, `rules/`,
  `cos_lib/` y `.claude/settings.json` quedaron fuera de D1–D3 a propósito:
  ampliar ahí sin afinar el criterio produce ruido, no hallazgos.
- El match hacia atrás es por substring del identificador. Un ADR que describa
  un gate sin nombrarlo cuenta como ausente. Verifiqué el falso positivo más
  probable —`cross-session-coordination-guard`, con 4 ADRs mencionando
  `cross-session-coordination`— y los 4 citan un doc de arquitectura, no el
  hook: el hallazgo se sostiene.
- No juzga si el ADR que existe *dice lo que el hook hace hoy*. Eso es deriva
  ADR↔implementación, y es otro control.
