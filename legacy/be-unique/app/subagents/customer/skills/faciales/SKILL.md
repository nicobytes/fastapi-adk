---
name: faciales
description: >
  Tratamientos faciales de Be Unique: catálogo, disponibilidad por sede,
  combinaciones, seguridad, tarifas y reserva con anticipo de 100 Bs en Sucre
  y Cochabamba. Usar cuando mencione limpieza facial, Hidrafacial, Dermapen,
  HIFU, peeling, Cosmelan, Plasmapén o precios faciales.
metadata:
  author: be-unique
  version: "1.0"
---

# Faciales Be Unique

## Overview

Esta skill cubre tratamientos faciales: catálogo, reglas de combinación,
seguridad, tarifas y política de reserva específica de Faciales.

## Instructions

1. Llama `load_skill` antes de responder sobre faciales.
2. Carga recursos L3 según la consulta:
   - **Catálogo y disponibilidad por sede:** `references/catalogo.md`
   - **Dependencias y combinaciones:** `references/combinaciones.md`
   - **Seguridad y cuidados:** `references/seguridad-cuidados.md`
   - **FAQs faciales:** `references/faqs-faciales.md`
   - **Tarifas:** `references/tarifas.md`
   - **Reserva y anticipo:** `references/politicas-reserva.md`
3. **Política específica de Faciales:** la reserva de la primera valoración
   requiere **100 Bs en Sucre y en Cochabamba**. Esta excepción prevalece sobre
   la regla general de Cochabamba (valoración sin anticipo para otros servicios).
4. **Disponibilidad:** verifica en el catálogo si el servicio es solo Sucre,
   solo Cochabamba o ambas sedes (p. ej. Hidrafacial y Radiofrecuencia solo Sucre).
5. **HIFU:** rostro completo = HIFU Full Face; no sumes tercios para cubrir
   rostro completo.
6. Herramientas auxiliares no tienen tarifa independiente.
7. No garantices resultados específicos de PDRN, exosomas u otros activos.
8. Plasmapén sí utiliza crema anestésica; láser no (consulta FAQ si confunden).
9. **Duración para agenda:** pasa `duration_minutes` del tarifario facial si
   existe; si falta, omite (fallback del schedule). Valoración inicial ≈ 30 min.
10. Si el cliente quiere agendar, usa las tools de agenda de producción.
    No prometas que el equipo reservará el cupo.
11. Deriva decisiones clínicas o excepciones a `derivacion-equipo`.
