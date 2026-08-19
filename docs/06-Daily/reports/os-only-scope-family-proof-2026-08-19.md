# La prueba de portabilidad de 416 primitivas no ejecuta ninguna

**Fecha:** 2026-08-19
**Estado:** hallazgo medido, **decisión pendiente del operador**. No se cambió nada.

## Qué se encontró

`manifests/primitive-behavior-evidence.yaml` registra
`tests/red_team/portability/test_os_only_scope_family.py` como evidencia de
comportamiento de un conjunto grande de primitivas. Ese archivo tiene tres
tests y **ninguno ejecuta una primitiva**:

| test | qué verifica |
|---|---|
| `..._has_maintainer_metadata_and_non_user_plane` | que el `scope`, `consumer_surface` y `plane` **declarados** de cada fila sean los esperados |
| `..._is_registered_as_behavior_evidence` | que el manifiesto apunte a este mismo archivo — **circular**: afirma la condición que convierte a esas primitivas en "probadas" |
| `..._none_budget_is_zero_after_family_proof` | corre `scripts/primitive_scope_health.py --strict`, que clasifica leyendo **metadatos de archivo** (no tiene `subprocess` ni `exec`) |

O sea: las cuatro respuestas del criterio de existencia de ADR-342 salen de la
declaración de la propia primitiva. Es exactamente lo que el criterio prohíbe.

## Los números

| | |
|---|---:|
| entradas en el manifiesto | 713 |
| citan este archivo como evidencia | 478 |
| **lo citan como su ÚNICA prueba** | **416** |
| filas en el `BASELINE` del archivo | 459 |
| **lo citan sin figurar en su lista** | **19** |

Las 19 son el caso más nítido: su prueba de portabilidad ni siquiera las nombra.

## Qué sí prueba

El archivo no es inútil: prueba **consistencia de metadatos de scope** —que lo
declarado sea coherente y que el reporte de salud no tenga hallazgos—. El
problema no es que no sirva, es que está **catalogado como otra cosa**. Un
chequeo de declaraciones registrado como evidencia de comportamiento hace que
416 primitivas figuren probadas sin que nadie las haya corrido nunca.

## La decisión, con su consecuencia

Sacarlo del manifiesto como evidencia de comportamiento deja **416 primitivas
sin prueba pareada**, y el `scope-marker-portability-gate` las bloquea en
cuanto alguien las toque. Es la deuda hecha visible de golpe: honesto, pero
disruptivo. Por eso no se hizo acá — es una decisión de diseño, no una
corrección mecánica.

Las opciones, sin recomendación encubierta:

1. **Reclasificar y absorber el rojo.** Correcto de raíz, 416 bloqueos hasta
   que cada familia tenga prueba real.
2. **Reclasificar con ratchet.** Igual que arriba pero con presupuesto que solo
   baja, como ya se hizo con `primitive_proof_execution_audit`.
3. **Dejarlo y anotarlo.** Barato hoy; el costo es que el conteo de primitivas
   probadas sigue diciendo algo que no es.

Las 19 que no están en la lista se pueden arreglar aparte y sin discusión: o se
agregan al `BASELINE`, o se les saca la cita.

## Reproducir

```bash
python3 - <<'PY'
import importlib.util, yaml, sys
spec = importlib.util.spec_from_file_location("fam", "tests/red_team/portability/test_os_only_scope_family.py")
m = importlib.util.module_from_spec(spec); sys.modules["fam"] = m; spec.loader.exec_module(m)
base = set(m.OS_ONLY_PRIMITIVE_PROOF_BASELINE)
F = "tests/red_team/portability/test_os_only_scope_family.py"
ev = yaml.safe_load(open("manifests/primitive-behavior-evidence.yaml", encoding="utf-8"))["evidence"]
cite = {i["primitive"] for i in ev if F in (i.get("tests") or [])}
only = {i["primitive"] for i in ev if (i.get("tests") or []) == [F]}
print("baseline", len(base), "| citan", len(cite), "| unica prueba", len(only),
      "| citan sin estar en la lista", len(cite - base))
PY
```

Y para el otro lado del hallazgo, que el módulo de salud no ejecuta nada:

```bash
grep -c "subprocess\|exec(\|runpy" scripts/primitive_scope_health.py
```

Devuelve `0` **con exit code 1**: el cero es el resultado, el 1 es `grep`
diciendo "no hubo coincidencias". Un lector que solo mire el exit code lee
un fallo donde hay un hallazgo.
