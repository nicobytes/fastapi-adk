# Benchmark queries — clasificación ambiguo vs puntual

Queries para comparar **semantic**, **hybrid** y **full text** en el Admin compare dialog o en evals de Amaru.

## Criterio

| Tipo | Definición | Modo esperado |
|------|------------|---------------|
| **Ambiguo** | Exploración por intención, categoría o filtro amplio; no ancla un plan concreto | Semantic gana; FTS puede quedar vacío |
| **Puntual** | Anclado a nombre de plan, variante o detalle específico de un plan identificado | Hybrid gana; FTS aporta ancla léxica |

**Desempate:**

- Destino genérico (Tolima, Cocuy, Colombia) sin nombre de plan → **ambiguo**
- Nombre de plan o variante (p. ej. "Montaña Pura", "Tradicional") → **puntual**
- Nombre propio único fuera de catálogo (Everest) → **puntual (borde)**; control negativo de recall

## Clasificación

| # | Query | Tipo | Razón |
|---|-------|------|-------|
| 1 | planes destinos recomendados | Ambiguo | Descubrimiento genérico; sin destino ni plan |
| 2 | planes de montaña trekking nevados | Ambiguo | Filtro por categoría/tema |
| 3 | itinerario y que incluye Nevado del Tolima Montaña Pura | Puntual | Nombre exacto del plan + atributos |
| 4 | condiciones restricciones requisitos seguridad Nevado del Tolima Montaña Pura | Puntual | Plan identificado + detalle de seguridad |
| 5 | diferencias entre los planes del Nevado del Tolima Montaña Pura, Tradicional, Travesía, Anzoátegui | Puntual | Variantes concretas; comparación puntual |
| 6 | Everest | Puntual (borde) | Nombre propio específico; fuera de catálogo Xperiencia |
| 7 | planes en Colombia salidas este año | Ambiguo | Filtro geográfico + temporal |
| 8 | alta montaña nevados Colombia | Ambiguo | Tema/categoría amplia |
| 9 | nevados Colombia expedicion | Ambiguo | Intención exploratoria con keywords temáticos |
| 10 | curso taller escalada montañismo escuela | Ambiguo | Tipo de producto; sin curso concreto |
| 11 | alta montaña trekking nevado tolima cocuy | Ambiguo | Destinos geográficos; exploración, no plan nombrado |
| 12 | Cumbre Nevado del Tolima | Puntual | Nombre concreto del plan |
| 13 | Nevado del Tolima precio incluye | Puntual | Producto anclado + atributos; puede mezclar variantes |
| 14 | curso de escalada | Ambiguo | Categoría genérica |

## Resumen

- **Ambiguos (8):** 1, 2, 7, 8, 9, 10, 11, 14
- **Puntuales (6):** 3, 4, 5, 12, 13 (+ 6 como control negativo)

## Suites sugeridas

1. **Exploratoria (semantic):** 1, 2, 7, 8, 9, 10, 11, 14
2. **Puntual (hybrid):** 3, 4, 5, 12, 13
3. **Control negativo:** 6

## Casos borde — validación esperada

| Query | Hipótesis en compare dialog |
|-------|----------------------------|
| **#6 Everest** | 0 resultados o ruido irrelevante; no usar para medir calidad retrieval |
| **#11 vs #12–13** | #11 favorece semantic (geo/tema); #12–13 muestran badge `FTS #n` en hybrid |
| **#13 vs #5** | #13 puede traer varias variantes del Tolima; #5 compara variantes ya nombradas |

Validar manualmente en Admin → Files → Compare search dialog cuando la base de conocimiento Xperiencia esté cargada.

## Lista plana (copy-paste)

```
planes destinos recomendados
planes de montaña trekking nevados
itinerario y que incluye Nevado del Tolima Montaña Pura
condiciones restricciones requisitos seguridad Nevado del Tolima Montaña Pura
diferencias entre los planes del Nevado del Tolima Montaña Pura, Tradicional, Travesía, Anzoátegui
Everest
planes en Colombia salidas este año
alta montaña nevados Colombia
nevados Colombia expedicion
curso taller escalada montañismo escuela
alta montaña trekking nevado tolima cocuy
Cumbre Nevado del Tolima
Nevado del Tolima precio incluye
curso de escalada
```
