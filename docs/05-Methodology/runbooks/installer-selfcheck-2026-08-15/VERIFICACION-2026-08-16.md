# Verificación del rescate contra el árbol de hoy

**Fecha:** 2026-08-16
**Contra:** `origin/main` en `022c30fde`
**Quién:** la sesión que recibió el rescate, no su autor. El `README.md` de al lado queda **sin tocar**: es el documento de ellos y su procedencia vale.

El rescate declara que fue escrito contra `8602ddc70b8bba77e47300c672a01b24f447d72c` y avisa que las ediciones pueden no aplicar limpio a un árbol posterior. Esto es ese chequeo.

## Resumen

**Dos de los tres defectos ya no aplican.** Los arreglamos el mismo día, en paralelo y sin que ninguna de las dos sesiones supiera de la otra. El tercero sigue en pie, y **el entregable principal —el self-check— conserva todo su valor**, porque su punto no es arreglar esos tres sino atrapar la clase entera.

## Defecto 1 — la plantilla de confidencialidad no viaja: **parcialmente vencido**

El rescate dice que la plantilla vive bajo `.cognitive-os/`, que el `.gitignore` del origen excluye, así que ningún camino del instalador podía levantarla; y que declaraba `protected_terms` / `protected_orgs`, claves que el parser no lee.

Hoy hay **dos** copias:

```
templates/confidentiality.yaml                 <- TRACKEADO
.cognitive-os/templates/confidentiality.yaml   <- ignorado (.gitignore:6,8)
```

Y la trackeada declara exactamente las claves que el parser sí lee:

```
verify: python3 -c "import yaml; print(sorted((yaml.safe_load(open('templates/confidentiality.yaml')) or {}).keys()))"
# 2026-08-16: ['client_names', 'org_names', 'project_names', 'repo_urls', 'scan_external_paths']
```

O sea que las dos mitades del hallazgo —ubicación no shippeable y claves equivocadas— están cubiertas en el árbol actual.

**Lo que NO verifiqué**: si el instalador efectivamente shippea `templates/confidentiality.yaml`. Que exista en un lugar shippeable no prueba que se shippee. Esa es la pregunta que el self-check de ellos contestaría.

## Defecto 2 — el circuit breaker nunca corrió en ningún consumidor: **vencido**

Es el más grave de los tres y **ya está arreglado**, por el commit `6bb75a580` de esta sesión: *"revive the agent circuit breaker and gate the closure that broke it"*.

El acoplamiento que el rescate describe —`circuit_breaker.py` importando `record_completion` en el mismo `try`, con el `except` compartido tragándose el bloque— **no existe hoy**:

```
verify: grep -c record_completion cos_lib/circuit_breaker.py     # 0
verify: grep -n learning_pipeline cos_lib/record_completion.py
# :56   comentario explicando que learning_pipeline es os-only y nunca se proyecta
# :496  el import, diferido a su único sitio de llamada
```

Ambos módulos son `SCOPE: both`; `learning_pipeline` sigue siendo `os-only` y por eso el import está diferido, que es exactamente el arreglo que el rescate proponía.

Vale registrar la coincidencia: **dos sesiones distintas, sin contacto, diagnosticaron el mismo defecto el mismo día**. Es la mejor evidencia de que era real.

## Defecto 3 — `cos-root` no puede shippear: **vigente**

```
verify: grep -m1 -n 'SCOPE:' scripts/cos-root
# 2:# SCOPE: os-only
```

Sigue marcado `os-only`, así que el proyector de scope no puede emitirlo. La consecuencia que declara el rescate —`PROJECT_DIR` vacío y telemetría escrita a `/`— **no la reproduje**; queda como afirmación de ellos, no verificada acá.

## Qué hacer con esto

**No aplicar nada sin rehacer el ciclo.** El rescate es explícito: es una reconstrucción del transcript, sólo se re-chequeó que el Python compile y los YAML parseen, y el artefacto que pasó las pruebas originales ya no existe para comparar. Esta verificación no cambia eso — sólo dice que dos de los tres motivos ya no están.

**Lo que sí conviene mirar en serio es `cos_install_selfcheck.py`.** Su valor no eran los tres defectos: es que falla el install cuando un entry point shippeado no resuelve sus imports, cuando un hook registrado apunta a un archivo que no existe, o cuando un archivo shippeado depende de otro que su scope prohíbe. Que dos de tres ya estén arreglados no lo hace menos útil — hace más creíble que la clase existe.

Y su autor declaró su propio hueco, que conviene leer antes de confiar: **marca sólo imports sin guarda**, así que es ciego a la clase "feature apagada en silencio" que lo motivó.

## Advertencia que se mantiene entera

Reinstalar un consumidor para tomar esto es **destructivo**: `install.sh` hace `rm -rf "$TARGET_DIR"` en el camino `--force` y en el interactivo, borrando `.cognitive-os/` entero —métricas, sesiones, estado de runtime y cualquier agregado local—. Un `--force` sobre la flota destruiría la telemetría que evidencia los defectos.
