# holaOS Adoptions Registry

Append-only audit trail para todas las adopciones clean-room desde holaOS.
Cada fila es REQUERIDA cuando se acepta una adopción (per ADR-259).

## Rules

- **Append-only** — no editar entries históricas, solo agregar nuevas al final de la tabla.
- Cada entry corresponde a un ADR aceptado bajo el paraguas de ADR-259.
- **"grep clean"** significa que el checklist F§5 fue ejecutado y pasado (ningún token
  del staged diff matchea `/tmp/holaOS-investigation`).
- **Status values**:
  - `accepted` — decisión tomada, sin implementación de código (meta/architecture)
  - `implemented` — código en `main`, tests pasando
  - `spike` — implementación boxeada para observación time-boxed
  - `deprecated` — ADR superseded, código removido o desactivado
  - `reverted` — rollback ejecutado (ver ADR correspondiente)

## Schema

| Date | Feature | ADR | Source-pattern | Implementer Agent | Compliance verified | Status |
|------|---------|-----|----------------|-------------------|---------------------|--------|

## Adoptions

| 2026-05-11 | holaOS adoption posture (umbrella) | ADR-259 | n/a (meta) | orchestrator (Opus 4.7) | n/a (decisional) | accepted |
| 2026-05-11 | Grant-signed cosd API (HMAC + nonce + TTL + scope) | ADR-260 | docs/research/holaos-annex-d-security-plan.md §P0 | Opus 4.7 impl agent | grep clean ✓ tests 14/14 ✓ | implemented |
| 2026-05-11 | Memory governance v2 (typed policies) | ADR-261 | docs/research/holaos-annex-a-memory.md §1 | Sonnet impl agent | grep clean ✓ tests 47/47 ✓ | implemented |
| 2026-05-11 | Evolve loop spike (LLM proposals + queue) | ADR-262 | docs/research/holaos-annex-c-evolution.md §1 | Sonnet impl agent | grep clean ✓ tests 65/65 ✓ | spike — observation 7 días |
| 2026-05-11 | Tool-replay budget ledger | ADR-263 | docs/research/holaos-annex-b-cost-budget.md §B1 | Sonnet impl agent | grep clean ✓ tests 22/22 ✓ | implemented |
| 2026-05-11 | Tool result envelope (28KB threshold) | ADR-264 | docs/research/holaos-annex-g-surprise-findings.md §G1 | Sonnet impl agent | grep clean ✓ tests 19/19 ✓ | implemented |
| 2026-05-11 | holaOS cleanroom gate + registry infrastructure | ADR-259 §impl | hooks/holaos-cleanroom-gate.sh + docs/compliance/holaos-adoptions.md | Sonnet impl agent | n/a (infra, no source adoption) | implemented |
