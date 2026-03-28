---
name: optimize-skill
description: Optimizar un skill de Claude Code iterativamente usando evals, midiendo mejoras y refinando el prompt
user_invocable: true
disable-model-invocation: true
model: claude-opus-4-6
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Agent
---

# /optimize-skill — Karpathy Loop para Skills de Claude Code

## Argumentos

```
/optimize-skill <skill-name> [iterations=3]
```

- `skill-name`: nombre del skill a optimizar (check-health, start-stack, etc.)
- `iterations`: cantidad de ciclos de optimizacion (default: 3)

## Instrucciones

Sos un optimizador autonomo de skills, inspirado en autoresearch de Karpathy.
Tu objetivo es mejorar el score compuesto de un skill sin romper lo que ya funciona.

### Paso 1: Leer estado actual

```
Leer:
  .claude/skills/{skill-name}/SKILL.md          → el skill actual
  .claude/skills/{skill-name}/evals/test-*.md    → los test cases
  .claude/skills/{skill-name}/results/benchmark.tsv → historial (si existe)
```

### Paso 2: Ejecutar benchmark baseline

Para cada eval en `evals/`:
1. Leer el test case (input + expected behavior)
2. Simular mentalmente la ejecucion del skill con ese input
3. Evaluar contra los criterios definidos
4. Calcular metricas:
   - `pass_rate`: % de criterios que pasarian
   - `token_estimate`: tokens estimados que usaria
   - `tool_calls_estimate`: cantidad de tool calls
   - `quality`: 0-1 basado en formato y completitud esperada

### Paso 3: Identificar areas de mejora

Analizar los evals que tienen menor score y determinar POR QUE:
- Instrucciones ambiguas en SKILL.md?
- Pasos innecesarios que agregan tokens/tiempo?
- Falta de ejemplos concretos?
- Orden suboptimo de operaciones?
- Description del skill no triggerea correctamente?

### Paso 4: Proponer modificacion

Aplicar UNA sola modificacion al SKILL.md por iteracion.
Estrategias en orden de prioridad:
1. Corregir instrucciones que causan fallos en evals
2. Agregar ejemplos para criterios que fallan
3. Eliminar pasos redundantes (reduce tokens)
4. Reordenar para eficiencia
5. Mejorar description/name para triggering
6. Simplificar sin perder precision

### Paso 5: Re-evaluar

Repetir Paso 2 con el SKILL.md modificado.
Comparar scores.

### Paso 6: Decidir

```
SI nuevo_score > score_anterior:
  → Mantener cambio
  → Agregar linea a benchmark.tsv
  → Continuar con siguiente iteracion

SI nuevo_score <= score_anterior:
  → Revertir SKILL.md al estado anterior
  → Anotar en benchmark.tsv que se intento y fallo
  → Intentar estrategia diferente
```

### Paso 7: Reporte final

Al terminar las iteraciones, mostrar:

```
=== Skill Optimization Report: {skill-name} ===

Iteraciones: {N}
Score inicial: {score_i}
Score final: {score_f}
Mejora: {delta} ({porcentaje}%)

Cambios aplicados:
  1. {descripcion del cambio} → score: {x} → {y}
  2. ...

Cambios descartados:
  1. {descripcion} → no mejoro (score: {x})

Metricas finales:
  Pass rate: {%}
  Token efficiency: {%}
  Quality: {%}

Proximos pasos sugeridos:
  - {sugerencia 1}
  - {sugerencia 2}
```

## Reglas Criticas

- NUNCA modificar archivos en `evals/` — son el ground truth
- SOLO modificar SKILL.md del skill objetivo
- UNA modificacion por iteracion (para aislar el efecto)
- Si despues de 3 intentos fallidos seguidos, PARAR e informar
- Cada cambio exitoso debe ser explicable (no "magia")
