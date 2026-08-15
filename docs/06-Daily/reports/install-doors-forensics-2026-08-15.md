# Forense de la consolidación de puertas de instalación — 2026-08-15

> Auditoría de `958845a18` y `7725a0917`, que colapsaron tres puertas de
> instalación en una. Uno de los dos defectos que los justificaron es falso.
> Método: **ejecutar, no grepear**. Cada veredicto de acá abajo lleva el comando
> que lo produce.

## Resumen

| Afirmación del registro | Veredicto | Cómo se sabe |
|---|---|---|
| `quickstart.md` clonaba `luum-home/luum-agent-os`, remoto real `Luum-Home/luum-cognitive-os` | **VERDADERO** | `git remote -v` |
| `cos-init.sh --full/--minimal/--standard` son «flags que el script no parsea» | **FALSO** | los cinco flags parsean; `--help` sale con `exit=0` |
| El Docker matrix de `quickstart.md` era subconjunto del de `getting-started.md` | **VERDADERO** | diff de las dos tablas |
| «Todo lo de `getting-started-quick.md` quedó absorbido, sin cambios» | **CASI** | tres bloques no llegaron |
| «El camino de clon local sigue documentado» (redirect de `quickstart.md`) | **FALSO** | no estaba en ningún lado hasta esta corrección |

Hallazgo propio, no visto por ninguno de los dos commits: **`--minimal` y
`--standard` son alias de `--default`**, así que la línea de `quickstart.md`
presentaba tres perfiles donde el programa tiene dos. El defecto existía; el
commit lo describió mal.

---

## 1. Los dos defectos: cuál era real

### 1.1 La URL del clon — real

```bash
git remote -v
# origin  git@github.com:Luum-Home/luum-cognitive-os.git (fetch)
```

`quickstart.md` clonaba `https://github.com/luum-home/luum-agent-os.git`. Nombre
de repo distinto, no sólo de organización. Defecto confirmado.

### 1.2 Los flags — falso

`scripts/cos-init.sh` tiene 15 líneas y no parsea nada:

```bash
wc -l scripts/cos-init.sh                              # 15
grep -c 'exec .*cos_init.py' scripts/cos-init.sh       # 1
```

Es un shim que hace `exec "$PYTHON_BIN" "$SCRIPT_DIR/cos_init.py" "$@"`. Por eso
el grep que el registro cita como prueba no devuelve nada — no porque los flags
no existan, sino porque está mirando el archivo equivocado:

```bash
grep -nE 'minimal|standard|full' scripts/cos-init.sh ; echo "exit=$?"
# exit=1   ← sin salida, y sin significado
```

El parser está en `scripts/cos_init.py:588-594`. Ejecutándolo:

```bash
python3 -c "
import importlib.util
s=importlib.util.spec_from_file_location('c','scripts/cos_init.py')
m=importlib.util.module_from_spec(s); s.loader.exec_module(m); p=m._build_parser()
for f in ['--default','--full','--minimal','--standard','--lean','--nonsense']:
    parsed,extra=p.parse_known_args([f])
    print(f'{f:12} -> mode={parsed.mode!r:12} extra={extra}')"
```

```
--default    -> mode='--default'  extra=[]
--full       -> mode='--full'     extra=[]
--minimal    -> mode='--default'  extra=[]
--standard   -> mode='--default'  extra=[]
--lean       -> mode='--default'  extra=[]
--nonsense   -> mode=None         extra=['--nonsense']
```

Y de punta a punta, desde el shim, en un directorio descartable:

```bash
cd "$(mktemp -d)"
for f in --help --full --minimal --standard --lean; do
  bash /path/to/repo/scripts/cos-init.sh "$f" --help >/dev/null 2>&1
  echo "$f exit=$?"
done
# todos: exit=0
```

**Los flags funcionan.** La afirmación del registro es falsa, y lo es por método:
tanto el agente que commiteó como el orquestador que lo confirmó grepearon el
shim. El segundo no verificó al primero, repitió su medición.

### 1.3 El defecto que sí había, y que nadie nombró

`--minimal`, `--standard` y `--lean` son `store_const` al mismo valor que
`--default`. La única diferencia observable es una nota en stderr:

```
--default    -> effective=--default  stderr=(no note)
--minimal    -> effective=--default  stderr=Note: ADR-093 collapsed '--minimal' into '--default'.
--standard   -> effective=--default  stderr=Note: ADR-093 collapsed '--standard' into '--default'.
--lean       -> effective=--default  stderr=Note: ADR-093 collapsed '--lean' into '--default'.
--full       -> effective=--full     stderr=(no note)
```

Ese `Note:` es todo lo que distingue a un alias de `--default`. El programa tiene
**dos** perfiles. `quickstart.md` ofrecía `--full # or --minimal / --standard`,
o sea tres — dos de los cuales son el default que ya te tocaba sin escribir nada.
Eso sí era engañoso, y es lo que quedó escrito ahora.

Nota lateral, sin arreglar acá: `--nonsense` no es rechazado. Cae en
`parse_known_args` como `extra`, y `main()` hace `mode = parsed.mode or "--default"`,
así que un flag mal escrito instala silenciosamente el perfil default. Es
divergente con `install.sh`, que sí rechaza lo desconocido con `exit 1`
(`install.sh:279-284`, leído, no ejecutado — la regla del encargo prohíbe correrlo).

---

## 2. Qué se perdió en la consolidación

Comparación línea por línea entre `git show 958845a18^:<archivo>` y el
`getting-started.md` resultante.

### 2.1 Lo que sí llegó

De `getting-started-quick.md`: instalación de 30 segundos (`install-cos.sh`,
`go install`), `cos new` / `cos init` con la lista de templates, la tabla
«You say / COS does», los comandos esenciales, las claves de `cognitive-os.yaml`,
el bloque de auto-update y `installations.json`. De `quickstart.md`: `upgrade.sh`,
`uninstall.sh`, y el Docker matrix — que efectivamente era subconjunto (11 filas
contra 12; la puerta única agrega la fila `cos CLI`).

### 2.2 Lo que no llegó — y una es una instrucción que funcionaba

**El camino de instalación desde clon local.** `quickstart.md` documentaba:

```bash
git clone <source> ~/.cognitive-os-src
cd /path/to/your/project
bash ~/.cognitive-os-src/scripts/cos-init.sh
```

Ese camino no quedó en ningún lado:

```bash
grep -n "cos-init.sh" docs/00-MOCs/entrypoints/getting-started.md
# 266: Re-runs `cos-init.sh` ...        ← describe el auto-update, no instala
# 596: If you installed from a local clone of the source (`scripts/cos-init.sh`)
```

La línea 596 **presupone** que ya instalaste así, y nunca dice cómo. El redirect
de `quickstart.md` afirmaba que «that path still works and is documented in
Upgrade and uninstall» — esa sección documenta `upgrade.sh` y `uninstall.sh`, no
la instalación. Era una promesa falsa.

Y era una instrucción que funcionaba: lo único roto era la URL del clon. El
mecanismo (`cos-init.sh` en el cwd del proyecto) está probado arriba. La
consolidación tiró el mecanismo entero en vez de corregir la URL.

**Corregido.** Restaurado en `getting-started.md` como
«Installation → From a local clone of the source», con la URL correcta y la
tabla de dos perfiles.

Lo demás que no llegó, menor y sin comando adentro:

- «This creates a Go project with COS pre-configured» (4 bullets de qué trae `cos new`).
- «What Runs Behind the Scenes» (5 bullets) — cubierto en espíritu por «Key Concepts».
- Los links de «Learn More»: `skills/CATALOG.md`, `rules/RULES-COMPACT.md`,
  `04-Concepts/root/security-stack.md`. El «Next Steps» de la puerta única apunta
  a otros cuatro documentos, así que el catálogo de skills y la referencia de
  reglas dejaron de estar linkeados desde la puerta de entrada.

### 2.3 ¿Un usuario que hoy sigue `getting-started.md` puede instalar?

Sí. Los cuatro caminos que ofrece existen en el repo:

```bash
for s in scripts/install-cos.sh install.sh scripts/upgrade.sh \
         scripts/uninstall.sh scripts/cos-init.sh cmd/cos; do
  [ -e "$s" ] && echo "PRESENT  $s" || echo "MISSING  $s"
done
# los seis: PRESENT
```

Antes de esta corrección podía instalar por `install-cos.sh`, `go install` o
`install.sh`, pero no por el clon local — y si ya había instalado así, la sección
de upgrade le hablaba de un camino que la página no le había enseñado.

---

## 3. Correcciones aplicadas al registro

Sin `revert`, sin `reset`, sin `rebase`, sin force-push. Todo aditivo.

| Superficie | Qué se hizo |
|---|---|
| `docs/06-Daily/reports/docs-carga-cognitiva-2026-08-15.md` | Bloque **ERRATA** arriba de todo + reescritura puntual de la sección «¿Competían?» con el defecto real y su comando + corrección de la línea de conclusión |
| `docs/00-MOCs/entrypoints/quickstart.md` | Sacada la afirmación falsa y el grep que la «probaba»; puesto el defecto real (dos perfiles, no tres) + nota de corrección fechada |
| `docs/00-MOCs/entrypoints/getting-started.md` | Restaurado el camino de clon local; `minimal/standard/full` corregido a `--default`/`--full` en las dos prosas del registro de instalaciones |
| `manifests/documentation-truth-claims.yaml` | Claim nuevo `cos_init_flag_surface` (ADR-277 §16) |
| Este informe | El registro corregido, con el comando de cada veredicto |

El audit del control plane pasa entero con el claim nuevo:

```bash
python3 scripts/documentation_truth_audit.py --json --no-write
# {"status": "pass", ... "by_status": {"pass": 152}}
```

Efecto colateral: el bloque generado de `documentation-truth-control.md` **ya
estaba desactualizado en HEAD**. Declaraba 6 claims cuando el manifiesto tenía 7
— `volatile_number_prose` entró en `28524697a` sin regenerar el bloque. Al
regenerarlo por el claim nuevo quedó en 8, así que este commit arrastra esa
corrección ajena. Se deja anotado para que el `+2` del diff no se lea como que
agregamos dos claims.

### Lo que no se puede corregir en el lugar

Los mensajes de commit de `958845a18` y `7725a0917` contienen la afirmación
falsa y **no se tocan**: corregirlos exige reescribir historia, que este repo
prohíbe. Quedan superseded por este informe, y el claim
`cos_init_flag_surface` es lo que impide que la afirmación vuelva a la
documentación viva: declara como `forbidden_phrases` las dos formas exactas en
que se escribió —la del redirect en inglés y la del mensaje de commit—, de modo
que reponerlas pone el audit en rojo.

El verde barato que se evitó: corregir el informe y dejar el redirect mintiendo
—o al revés—, y «resolver» la contradicción borrando el párrafo. Los tres
párrafos siguen ahí, corregidos, y la contradicción quedó declarada.

---

## 4. ¿Se sostiene la consolidación?

**Sí. No hay que revertir nada.** Los motivos que quedan en pie alcanzan solos:

1. **Nueve puertas en `entrypoints/`**, más dos en la raíz con nombre repetido y
   contenido distinto. No depende del defecto falso.
2. **Tres comandos de instalación mutuamente contradictorios** para el mismo
   producto, medidos y tabulados en el informe original.
3. **La URL del clon no resolvía** — defecto verificado, en la puerta más corta y
   por eso la más probable de seguir.
4. **El defecto de los flags existía igual**, sólo que era otro: dos perfiles
   presentados como tres.

O sea: la puerta más corta estaba efectivamente rota, en dos puntos. El registro
describió mal el segundo, no lo inventó. Revertir una consolidación correcta
porque uno de sus cuatro motivos estaba mal redactado sería el segundo error.

Lo que sí había que arreglar hoy —y se arregló— es la instrucción que se perdió
en el camino, §2.2.

---

## 5. Qué de este encargo era falso

El encargo venía del orquestador, que ya se había equivocado una vez en este
tema. Recontado:

- **«El primero es verdadero, el segundo es FALSO»** — confirmado, y por el
  motivo que el encargo daba. Recontado ejecutando, no heredado.
- **«`cos_init.py:588-594`, los tres últimos: `store_const` a `--default`»** —
  correcto, salvo que son *tres* los remapeados (`--minimal`, `--standard`,
  `--lean`), y el encargo listaba cinco flags nombrando «los tres últimos», que
  es la lectura correcta. Sin corrección.
- **«`install.sh:416` y `:425` hacen `rm -rf "$TARGET_DIR"`»** — **impreciso en la
  ruta**: el encargo lo ubicaba en `scripts/install.sh`, que no existe.
  `sed -n '405,435p' scripts/install.sh` devuelve *No such file or directory*. El
  archivo está en la **raíz** del repo. El `rm -rf` sí está donde decía
  (`install.sh:415` y `:424`, ±1 línea) y la advertencia era correcta y valiosa:
  `TARGET_DIR` es relativo (`install.sh:14`), así que corre contra el cwd. No se
  ejecutó `install.sh` en ningún momento.
- **«El commit message y el informe afirman el defecto»** — incompleto. La
  afirmación falsa estaba también en **`quickstart.md`**, un documento vivo que
  un usuario lee, y ahí venía con el grep roto explicitado como prueba. Es la
  copia que más daño hacía y el encargo no la listaba.
- **«¿Son equivalentes o hay diferencia observable?»** — hay una, mínima: la nota
  en stderr. El modo efectivo es idéntico.
- **«Si se perdió una instrucción que funcionaba, eso es daño activo»** — se
  perdió una, §2.2, y el encargo no sabía cuál. Además, el redirect afirmaba que
  no se había perdido nada, lo que la hacía más difícil de encontrar.

Ninguna de estas correcciones cambia el veredicto del encargo. La premisa
central era correcta y está reverificada por ejecución.

---

## Anexo: observación incidental, fuera de alcance

Hay un directorio `--help/` sin trackear en la raíz del repo, con un
`.cognitive-os/` adentro, fechado 2026-07-28:

```bash
ls -la './--help'
```

Precede a los commits auditados por más de dos semanas, así que no es de este
trabajo. `install.sh` sí maneja `--help|-h` (`install.sh:277`), de modo que no
sale de ahí. No se investigó; queda anotado para quien barra el árbol.

## Anexo: por qué no hay script de evidencia nuevo

La norma de evidencia ejecutable pide que la medición quede reproducible. Acá
quedó como comandos citados en línea, no como script nuevo, a propósito: agregar
un `scripts/*.py` a este repo lo mete en el gobierno de primitivas (naming,
readiness ledger, harness coverage), que es más costo que el que justifica una
verificación de cinco flags. El comando corto —`bash scripts/cos-init.sh --help`—
ya es la evidencia ejecutable, y quedó declarado como `verify_command` del claim
`cos_init_flag_surface`.
