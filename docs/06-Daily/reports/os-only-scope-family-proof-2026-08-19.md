# La familia os-only: qué era hallazgo y qué era yo redescubriendo lo ya decidido

**Fecha:** 2026-08-19
**Estado:** **corregido el mismo día.** La primera versión de este informe recomendaba
construir un ratchet que ya existe, y encuadraba como engaño algo que el sistema
declara en voz alta. Se deja el error escrito porque el error es el hallazgo.

## Lo que afirmé, y por qué estaba mal

Afirmé que `tests/red_team/portability/test_os_only_scope_family.py` es la única
prueba de 416 primitivas, que no ejecuta ninguna, y que por lo tanto **416
primitivas figuran "probadas" sin que nadie las haya corrido nunca**. Los números
son correctos. **El encuadre no**: el sistema nunca afirmó eso.

**ADR-323 — Primitive Behavior Depth Ratchet** (accepted, implemented, 2026-05-15)
separa explícitamente las dos preguntas:

- `proof_level` responde *¿está cubierta por una prueba pareada o de familia?*
- `behavior_depth` responde *¿qué tipo de comportamiento ejercita esa prueba?*

Y dice, textual, en sus consecuencias: *no es todavía correcto decir que todas las
primitivas tienen tests funcionales individuales profundos.* El ADR además trata a
`tests/red_team/portability/*` como `projection` por defecto, y **no** como
adversarial por el solo nombre.

El estado real, medido hoy:

```
by_proof_level : {family: 658, primitive-specific: 784}
by_behavior_depth: {structural: 457, projection: 806, functional: 145,
                    adversarial: 32, smoke: 2}
findings: 0
```

O sea que el sistema **cuenta 658 primitivas como cubiertas a nivel familia** y
**457 a profundidad estructural**, y lo dice en un contador propio. No hay número
mintiendo: hay un número que yo leí como si dijera otra cosa.

## Y el ratchet que recomendé ya está puesto, más ajustado

Recomendé "reclasificar con presupuesto que solo baja". Existe:
`behavior_depth_policy.max_by_depth.structural` en
`manifests/primitive-scope-classification.yaml`. Y no tiene colchón:

```
structural: 457      # y la medición real da 457
```

Fue **reconciliado hacia abajo** el 2026-08-18, de 473 a 457, contra una medición
corregida —no aflojado—. Cero lugares libres. El patrón "baseline por encima de la
realidad" que buscaba, acá no está.

Más aún: el propio manifiesto ya registra el hallazgo, en un comentario del
2026-08-18, antes de que yo lo "encontrara":

> *632 of the 890 hang off `family` proofs, 476 of those off a single test.*

## Qué sí sobrevive como hallazgo

**19 primitivas citan el archivo como su evidencia sin figurar en su `BASELINE`.**
Su prueba de portabilidad ni siquiera las nombra. Eso no está cubierto por ADR-323
ni por el comentario del manifiesto: es un dato mal puesto, y tiene arreglo sin
decisión de por medio —o se agregan a la lista, o se les saca la cita—.

## La lección, que es el motivo de dejar esto escrito

Un número que parece una mentira suele ser un número que **no leí con su
definición al lado**. `proof_level: family` no significa "probada": significa
"cubierta a nivel familia", y hay un ADR aceptado que lo dice. Antes de proponer
reclasificar 416 filas convenía leer el ADR cuyo título es exactamente el
mecanismo que estaba por proponer.

El operador frenó esto con *"me da miedo, por algo está"*. Tenía razón, y el costo
de haber seguido era tocar 416 entradas del manifiesto para construir algo que ya
estaba construido.

## Reproducir

Los números de profundidad y cobertura:

```bash
.venv/bin/python scripts/primitive_behavior_depth_audit.py --project-dir . --json
```

El presupuesto vigente (el del texto de ADR-323 dice 471 y está desactualizado; la
autoridad es el manifiesto):

```bash
grep -A12 'max_by_depth' manifests/primitive-scope-classification.yaml
```

Las 19 huérfanas:

```bash
.venv/bin/python - <<'PY'
import importlib.util, yaml, sys
spec = importlib.util.spec_from_file_location("fam", "tests/red_team/portability/test_os_only_scope_family.py")
m = importlib.util.module_from_spec(spec); sys.modules["fam"] = m; spec.loader.exec_module(m)
base = set(m.OS_ONLY_PRIMITIVE_PROOF_BASELINE)
F = "tests/red_team/portability/test_os_only_scope_family.py"
ev = yaml.safe_load(open("manifests/primitive-behavior-evidence.yaml", encoding="utf-8"))["evidence"]
cite = {i["primitive"] for i in ev if F in (i.get("tests") or [])}
print("baseline", len(base), "| citan", len(cite), "| huerfanas", len(cite - base))
PY
```

## Deriva documental detectada de paso

El texto de ADR-323 declara `structural: 471`; el manifiesto vigente dice `457`.
El ADR es el registro de la decisión, el manifiesto es la autoridad operativa, y
hoy discrepan. Queda anotado, sin tocar: cambiar un ADR aceptado es decisión del
operador.
