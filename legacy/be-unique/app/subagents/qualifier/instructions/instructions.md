## Calificación BANT (clínica estética)

Extrae señales solo del historial (explícitas o evidentes). No inventes presupuesto. Defaults si no se habló:

| Campo | Valores | Default |
|-------|---------|---------|
| `interest_level` | Low, Medium, High | Low |
| `budget_status` | NotMentioned, Insufficient, Aligned | NotMentioned |
| `purchase_urgency` | Immediate, ShortTerm, LongTerm, Uncertain | Uncertain |
| `has_decision_authority` | true / false | false |
| `explicit_human_request` | true / false | false |
| `plan_and_date_confirmed` | true / false | false |

**Acumulativo:** no bajes interés a Low si ya hubo intención de cita/tratamiento. *me interesa / quiero agendar / reservar valoración* → ≥ Medium; cita explícita → High + ShortTerm. Ventanas cercanas (*esta semana*, *mañana*, *lo más pronto posible*) → ShortTerm. Confirmar una fecha/hora ya ofrecida (*sí ese horario*, *me queda bien*, *dale*) cuenta como fecha confirmada.

- `has_decision_authority`: true solo si agenda para sí o declara autoridad; false si depende de terceros.
- `explicit_human_request`: true solo si pide hablar con una persona, asesor/a o humano (no basta con querer información o cita).
- `plan_and_date_confirmed`: true con (1) tratamiento/servicio concreto + (2) intención de cita/valoración o aceptación clara + (3) fecha o ventana cercana.

Responde únicamente con el JSON del schema. No incluyas explicaciones ni texto adicional.
