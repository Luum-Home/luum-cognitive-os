<!-- SCOPE: both -->
<!-- TIER: 2 -->
# License Policy

For commercial/closed-source projects, ALL dependencies must comply with this policy. Adjust based on your project's licensing model.

## Regla General

Antes de integrar CUALQUIER herramienta open-source, verificar su licencia.

## Licencias Permitidas

| Licencia | Veredicto | Condiciones |
|----------|-----------|-------------|
| MIT | ✅ SAFE | Solo mantener copyright notice |
| BSD-2, BSD-3 | ✅ SAFE | Solo mantener copyright notice |
| Apache 2.0 | ✅ SAFE | Mantener NOTICE + indicar cambios |
| ISC | ✅ SAFE | Sin restricciones |
| CC0 / Public Domain | ✅ SAFE | Sin restricciones |

## Licencias con Precaucion

| Licencia | Veredicto | Condiciones |
|----------|-----------|-------------|
| LGPL v2.1/v3 | ⚠️ CAUTION | Solo como library dinamica. NO modificar el codigo LGPL. NO linkear estaticamente |
| MPL 2.0 | ⚠️ CAUTION | Cambios al codigo MPL deben ser open-source, pero TU codigo puede ser cerrado |
| Artistic 2.0 | ⚠️ CAUTION | Similar a MPL — cambios al original deben publicarse |

## Licencias BLOQUEADAS para SaaS

| Licencia | Veredicto | Por que |
|----------|-----------|---------|
| AGPL v3 | 🚫 BLOCKER | Si usuarios interactuan via red, DEBES open-sourcear TODO tu codigo |
| SSPL | 🚫 BLOCKER | Bloquea SaaS completamente (estilo MongoDB) |
| BSL (Business Source) | 🚫 BLOCKER | No podes competir con el vendor. Se abre despues de X anios pero con restricciones |
| ELv2 (Elastic License) | 🚫 BLOCKER | No podes ofrecer el software como servicio managed |
| Commons Clause | 🚫 BLOCKER | No podes vender el software como servicio |
| FSL (Functional Source) | 🚫 BLOCKER | Similar a BSL — restricciones de uso comercial |
| Server Side Public License | 🚫 BLOCKER | Variante de SSPL, mismas restricciones |

## Procedimiento Obligatorio

1. **Antes de agregar cualquier dependencia**: verificar licencia en GitHub/npm/Maven
2. **Dependencias transitivas tambien cuentan**: si A (MIT) depende de B (AGPL), B contamina
3. **Dual licensing**: si una herramienta ofrece Community (AGPL) + Commercial, evaluar costo de licencia comercial
4. **Ante la duda**: NO integrar. Buscar alternativa con licencia permisiva.
5. **Documentar**: toda decision de licencia en `docs/03-PoCs/research/license-analysis.md`

## Excepciones

Una herramienta con licencia AGPL/SSPL PUEDE usarse si:
- Corre como servicio COMPLETAMENTE SEPARADO (container propio, sin modificaciones)
- NO se modifica su codigo fuente
- Se comunica SOLO via API publica documentada
- Se documenta la justificacion y el riesgo
- Se aprueba explicitamente

Aun asi, la recomendacion es buscar alternativa con licencia permisiva.
