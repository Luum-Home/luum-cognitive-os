# Sesión B — medición independiente del repo (fixture)

Lado B de la verificación cruzada. Mismo repo, contexto disjunto, otros
comandos. Lo que interesa no es que B tenga razón: es dónde A y B no coinciden.

## Hooks

Contados sobre la estructura del JSON, no sobre el texto.

```claim
id: hooks-estructurales-b
topic: hooks/registrados-en-settings
claim: settings.json registra 162 hooks
cmd: python3 -c "import json;d=json.load(open('.claude/settings.json'));print(sum(len(h.get('hooks',[])) for ev in d.get('hooks',{}).values() for h in ev))"
expect: 162
match: numeric
```

## ADRs

Mismo total, otro comando.

```claim
id: adrs-total-b
topic: adrs/total
claim: el repo tiene 501 ADRs
cmd: find docs/02-Decisions/adrs -name 'ADR-*.md' -type f | wc -l
expect: 501
match: numeric
```

## Imports envueltos en try/except

Recorrido AST, no textual: cuenta sentencias `try` cuyo cuerpo son solo imports
y que tienen al menos un handler.

```claim
id: imports-guardados-b
topic: imports/guardados-try-except
claim: hay 297 imports envueltos en try/except en todo el repo
cmd: |
  python3 -c "
  import ast, pathlib
  SKIP={'.venv','node_modules','.git','__pycache__','.cognitive-os'}
  n=0
  for p in pathlib.Path('.').rglob('*.py'):
      if any(part in SKIP for part in p.parts) or not p.is_file(): continue
      try: tree=ast.parse(p.read_text(encoding='utf-8',errors='ignore'))
      except (SyntaxError, OSError): continue
      for node in ast.walk(tree):
          if isinstance(node, ast.Try) and node.body and node.handlers and all(isinstance(s,(ast.Import,ast.ImportFrom)) for s in node.body):
              n+=1
  print(n)
  " 2>/dev/null
expect: 297
match: numeric
```

## Solo B

```claim
id: manifests-yaml-b
topic: manifests/yaml-en-manifests
claim: manifests/ tiene archivos YAML
cmd: ls manifests/*.yaml | wc -l
expect: '[0-9]+'
match: regex
```
