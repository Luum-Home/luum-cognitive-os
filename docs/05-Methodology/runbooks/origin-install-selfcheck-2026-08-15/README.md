# Parche externo: self-check de instalación (2026-08-15)

**Estado: NO aplicado. Choca con `HEAD`. Rescatado de `/tmp` para que exista.**

## Qué es

Producido el 2026-08-15 por una sesión que auditaba `FinOpenPOS`, un repo
consumidor, sobre un clon bajo `/tmp` — nunca sobre este working tree. Su
entregable principal no son los tres arreglos puntuales sino
`scripts/cos_install_selfcheck.py`: un chequeo cableado al paso 13 de
`cos_init.py` que **falla la instalación** cuando los módulos enviados no pueden
satisfacer sus propios imports en el destino. No es advisory.

Demostrado fallando de cuatro formas distintas: sobre la instalación baseline sin
parchear (12 hallazgos), borrando un módulo del install, borrando el módulo del
fuente y corriendo un install real, e inyectando un hook fantasma en
`settings.json`. Control intacto (`exit=0`) antes y después de cada una.

```
 cos_lib/record_completion.py               |   15 +      <-- CHOCA
 manifests/install-selfcheck-allowlist.yaml |   28 ++
 scripts/cos_init.py                        |  165 ++++
 scripts/cos_install_selfcheck.py           |  497 ++++++     <-- el entregable
 scripts/hook-timing-wrapper.sh             |   43 ++
 scripts/lib_closure.py                     |   25 +
 templates/confidentiality.yaml.template    |   41 ++      <-- COLISIONA
```

## Por qué no se aplicó

```bash
git apply --check docs/05-Methodology/runbooks/origin-install-selfcheck-2026-08-15/origin-fix.patch
# error: patch failed: cos_lib/record_completion.py:53
```

Dos incompatibilidades con lo que se commiteó el mismo día, ninguna de fondo:

1. **`cos_lib/record_completion.py`** — el parche y el commit `6bb75a580` arreglan
   el mismo defecto (el import de un módulo `os-only` a nivel de módulo que dejaba
   muerto el circuit breaker en todo consumidor) por caminos distintos. Hay que
   elegir uno; el commiteado ya está verificado con una prueba antes/después bajo
   un bloqueador que se autoprueba.
2. **`templates/confidentiality.yaml.template`** — colisiona conceptualmente con
   `templates/confidentiality.yaml`, del commit `05a852f7a`. **El del repo es más
   completo**: el parche corrige la plantilla pero no el parser, así que con el
   parche solo, cualquier config ya escrita contra el esquema viejo sigue cargando
   cero términos en silencio — el defecto original, intacto para lo ya instalado.

## Qué sigue valiendo, y es la mayor parte

- `scripts/cos_install_selfcheck.py` — archivo nuevo, sin conflicto. Sus categorías
  (`missing_shipped` / `scope_conflict` / `dangling`) son exactamente lo que el
  panel pidió como acción #2 del juez de scope. Su allowlist exige motivo escrito y
  **ignora las entradas en blanco**, así que el verde barato no es el camino corto.
- `scripts/lib_closure.py` (+25) — conviene contrastarlo con el defecto medido en
  `lib_closure.py:92-96`, que descarta `from cos_lib import x` entero (6 módulos,
  16 usos).
- `scripts/hook-timing-wrapper.sh` (+43) — inline del `cos-root` que el instalador
  no puede enviar por contrato (`# SCOPE: os-only`). Preserva la precedencia de
  variables de entorno y agrega un walk-up que en un consumidor encuentra la raíz
  que `cos-root` jamás encontraría.

## Lo que NO cubre

Verificado por el juez de diseño: no cierra el call-site del `__init__.py`
(`cos_init.py:1886-1892` sigue copiando sin consultar `scope_allows`), no cubre los
`.pyc` que viajan por el `copytree` de `hooks/_lib/`, y no ve el caso de
`skills/cos-status/SKILL.md`, cuyo marcador está en la línea 30 y por lo tanto es
invisible a los dos parsers. Vuelve el problema **detectable**, no imposible.

## Cómo seguir

Rebasar los dos hunks en conflicto sobre `HEAD` y aplicar el resto, o extraer solo
el self-check y su allowlist, que es la pieza sin conflicto y la de mayor valor:

```bash
git apply --exclude=cos_lib/record_completion.py \
          --exclude=templates/confidentiality.yaml.template \
          docs/05-Methodology/runbooks/origin-install-selfcheck-2026-08-15/origin-fix.patch
```

Ese comando no se corrió: la decisión de aplicarlo es del operador.

`addendum.txt` es la nota que acompañaba al parche, tal como llegó.
