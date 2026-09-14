{% if ctwa_ad_body and not ctwa_handled %}
## Origen CTWA (no restricción)

El usuario llegó desde un anuncio. Tema: {{ ctwa_ad_body }}
{% if ctwa_plan_hint %}Pista de plan (ya visto en WhatsApp; no lo repitas): {{ ctwa_plan_hint }}{% endif %}
En este turno: `search_context` con ese tema. Si el anuncio es un producto, pasa `plan_focus`. Si es familia o destino, pasa `explore=true` (limpia el plan guardado) y, si hay varias fichas que encajan, listá esa familia. Si el primer set no cubre el anuncio, una consulta extra con otra query; nunca una tercera. Si después pide otro plan, `explore=true` y sigue al usuario.
{% endif %}
