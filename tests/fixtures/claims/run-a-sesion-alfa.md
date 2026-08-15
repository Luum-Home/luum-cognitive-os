# Sesión A — medición independiente del repo (fixture)

Fixture de demostración para `scripts/verify_claims.py` y
`scripts/compare_claim_runs.py`. Representa lo que mediría un agente con su
propio contexto. Los comandos corren contra el repo real desde la raíz.

No es un informe: es el lado A de la verificación cruzada.

## Hooks

La capa de hooks del OS, contada sobre `.claude/settings.json`.

```claim
id: hooks-registrados-a
topic: hooks/registrados-en-settings
claim: settings.json registra 324 hooks
cmd: grep -c '"command"' .claude/settings.json
expect: 324
match: numeric
```

El número publicado en la conversación de hoy es otro, y no reproduce:

```claim
id: hooks-publicados-255
topic: hooks/cifra-publicada-255
claim: la capa son 255 hooks registrados
cmd: grep -c '"command"' .claude/settings.json
expect: 255
match: numeric
```

## ADRs

```claim
id: adrs-total-a
topic: adrs/total
claim: el repo tiene 501 ADRs
cmd: ls docs/02-Decisions/adrs/ADR-*.md | wc -l
expect: 501
match: numeric
```

## Imports envueltos en try/except

Patrón textual: bloques `try:` seguidos de un `except` a dos líneas.

```claim
id: imports-guardados-a
topic: imports/guardados-try-except
claim: hay 844 imports envueltos en try/except en cos_lib, scripts y hooks
cmd: grep -rn -A2 --include='*.py' '^\s*try:\s*$' cos_lib scripts hooks | grep -cE 'except.*:'
expect: 844
match: numeric
```

## Solo A

```claim
id: scripts-python-a
topic: scripts/python-en-scripts
claim: scripts/ tiene archivos Python
cmd: ls scripts/*.py | wc -l
expect: '[0-9]+'
match: regex
```
