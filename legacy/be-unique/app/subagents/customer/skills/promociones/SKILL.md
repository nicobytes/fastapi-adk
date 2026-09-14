---
name: promociones
description: >
  Aplica promociones temporales de Be Unique. Usar cuando el usuario mencione
  promo, descuento, oferta, primavera o precio especial en depilación láser.
  Verificar Estado ACTIVA/INACTIVA, Publicable y vigencia con current_date
  de la sesión antes de cotizar. No modifica tarifas regulares permanentes.
metadata:
  author: be-unique
  version: "1.0"
---

# Promociones Be Unique

## Overview

Esta skill define beneficios comerciales temporales. Las tarifas regulares
permanecen en las skills de servicio; aquí solo se decide si hay un beneficio
aplicable y bajo qué condiciones.

## Instructions

1. Llama `load_skill` y luego `load_skill_resource` con `references/promociones.md`.
2. Usa `current_date` de la sesión (America/La_Paz) para comprobar vigencia.
   No inventes la fecha.
3. **Reglas de oro:** ofrece una campaña solo si **Estado = ACTIVA**,
   **Publicable = Sí**, `current_date` está dentro de la vigencia, y sede/zona
   del cliente coinciden. Si falta Publicable o cualquier check falla, cotiza
   tarifa regular. **INACTIVA**, Borrador o Pausada: no ofrecer.
4. Si está ACTIVA y Publicable, verifica también las condiciones específicas
   de esa promoción.
5. Las promociones **no reescriben** la tarifa regular del servicio.
6. Si la promoción no dice que es acumulable, **no acumules** con paquetes,
   combos, planes combinados ni otras promociones.
7. Para cotizar láser con promoción, coordina con la skill `depilacion-laser`:
   primero identifica zonas y tarifa regular; luego aplica el beneficio promocional
   solo si esta skill confirma una promoción aplicable.
8. Si el usuario pregunta por una promoción que no pasa los checks, explica que
   no está disponible actualmente y ofrece tarifa regular si corresponde.
