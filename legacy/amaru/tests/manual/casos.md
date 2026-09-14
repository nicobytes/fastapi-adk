# Casos de prueba manuales — Amaru (Xperiencia)

Pruebas **manuales** del agente WhatsApp Amaru. Cada `TC-*` es un candidato a `eval_id`; este archivo no ejecuta `just eval-handoff` ni Ragas.

Hay **dos canales**. Cada escenario declara **Dónde** (índice + cuerpo). No mezclar oráculos: en playground no hay botones nativos de WhatsApp ni pin; sí hay texto del bot + CRM (`WAITING_HUMAN` si deriva).

| Canal | Cuándo usarlo |
|---|---|
| **WhatsApp prod** | FLOW / HITL / NOHD / RAG / extras. Verificación HITL en [webapp.chatty.bo](https://webapp.chatty.bo). |
| **Playground CRM** (`/apps/configuration/playground`, org Amaru) | Casos `@playground` / `@ctwa`: mock de anuncio repetible. CTWA real en WhatsApp solo si hay anuncio clickable; si no, **Blocked**. |

Amaru **no** agenda citas. El oráculo de CRM es el estado HITL (`WAITING_HUMAN`) y, si se ve, `conversations.metadata.qualification` / motivo del operador.

**Anclaje:** `app/subagents/customer/instructions/instructions.md`, qualifier BANT, gate en `app/qualification.py`. Conocimiento: tool `search_context` (RAG híbrido). **No hay skills** de catálogo.

**Oráculo RAG:** hechos de [`evals/ragas/dataset.json`](../evals/ragas/dataset.json) (KB cloud). **No** use precios del seed local (`seed-assets/amaru-kb.md`: caminata $85.000 / camping $120.000). Si la KB de prod cambió, marque **Blocked** y anote el texto real.

---

## Cómo ejecutar

**WhatsApp prod** (FLOW / HITL / RAG / extras):

1. Use un **número WhatsApp propio** (no una conversación de cliente real).
2. Nombre reconocible, p. ej. `Test Amaru Parapente`.
3. **Conversación nueva por caso.** No mezclar plan activo, fechas ni un handoff previo.
   - Excepción: el happy path de reserva (plan + rango listado + “sí, reserva esa”) se puede reusar para inspeccionar el puente en CRM.
4. Tras **derivación:** CRM → conversación en `WAITING_HUMAN`. Motivo del operador = una de las cuatro cadenas canónicas (apéndice A). Nunca el fallback `Lead calificado para atención humana.` en un éxito.
5. Tras **no** derivar: Amaru sigue respondiendo; CRM no pasa a humano.
6. **Limpieza:** pida a un operador que cierre / reabra el ticket, o use otro número. No deje leads de prueba en la cola.

**Playground** (CTWA / mock de anuncio):

1. CRM → org Amaru → Configuración → Playground (`/apps/configuration/playground`).
2. Llene el panel **Simular anuncio (CTWA)** (tema + welcome opcional) → **Nueva conversación** → primer mensaje.
3. Reset = otra sesión ADK (otro UUID). El mock se envía solo en el primer mensaje.

Amaru solo usa `reply_with_text` (sin botones ni pin). Los `Then` describen el texto del canal indicado y, si aplica, el estado CRM.

### Cómo marcar

- **Pass** — todos los `Then` / `And` se cumplieron.
- **Fail** — algún `Then` falló (anote cuál y copie el mensaje).
- **Blocked** — no se pudo ejecutar (KB distinta, sin fechas publicadas, sin anuncio CTWA, cola sucia).

```text
**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**
```

Marque **una** casilla.

### Convenciones Gherkin

- `Given` = estado previo (chat nuevo, plan ya mencionado, Amaru ya listó fechas).
- `When` = mensaje del tester (WhatsApp o playground).
- `Then` = texto visible + CRM. No exigir nombres de tools al cliente.
- Tags `@whatsapp` / `@playground` alineados con **Dónde**.

Amaru entrega info **por partes**. En RAG, Pass si el hecho pedido está y **no hay cifra inventada**. No exigir el dump completo del `reference` en un solo turno.

---

## Índice

| ID | Suite | Canal | Resultado |
|---|---|---|---|
| [TC-FLOW-01](#tc-flow-01) | Saludo `Hola` | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-FLOW-02](#tc-flow-02) | Pregunta en el primer mensaje | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-FLOW-03](#tc-flow-03) | No repetir saludo | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-FLOW-04](#tc-flow-04) | Formato WhatsApp / un mensaje | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-FLOW-05](#tc-flow-05) | Info por partes vs “todo” | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-HITL-01](#tc-hitl-01) | Plan + fecha listada + reservar esa | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-HITL-02](#tc-hitl-02) | Pedir humano turno 2+ | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-HITL-03](#tc-hitl-03) | Pedir humano turno 1 | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-HITL-04](#tc-hitl-04) | Discapacidad / accesibilidad (turno 1) | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-HITL-05](#tc-hitl-05) | Oferta grupo a medida (aún no handoff) | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-HITL-06](#tc-hitl-06) | Aceptar grupo a medida | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-HITL-07](#tc-hitl-07) | Puente sin links de pago | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-NOHD-01](#tc-nohd-01) | Turno 1 “quiero reservar” no deriva | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-NOHD-02](#tc-nohd-02) | Browsing de planes | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-NOHD-03](#tc-nohd-03) | Elegir rango sin confirmar reserva | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-NOHD-04](#tc-nohd-04) | Fecha + logística | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-NOHD-05](#tc-nohd-05) | “Quiero reservar” viejo + elige fecha | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-NOHD-06](#tc-nohd-06) | Presupuesto insuficiente | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-NOHD-07](#tc-nohd-07) | Interés alto sin confirmar salida | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-NOHD-08](#tc-nohd-08) | “Sí” a incluye no es reserva | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-NOHD-09](#tc-nohd-09) | Insufficient no bloquea pedir humano | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-RAG-01](#tc-rag-01) | Precio parapente Guatavita | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-RAG-02](#tc-rag-02) | Encuentro y traslados parapente | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-RAG-03](#tc-rag-03) | GoPro parapente | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-RAG-04](#tc-rag-04) | Paracaidismo Flandes — precio y reserva | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-RAG-05](#tc-rag-05) | Paracaidismo — peso, edad, encuentro | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-RAG-06](#tc-rag-06) | Chingaza | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-RAG-07](#tc-rag-07) | Tobia | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-RAG-08](#tc-rag-08) | Suesca — encuentro | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-RAG-09](#tc-rag-09) | Paráfrasis: volar cerca de Bogotá | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-RAG-10](#tc-rag-10) | “¿y el precio del segundo?” | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-RAG-11](#tc-rag-11) | Destino fuera de KB | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-RAG-12](#tc-rag-12) | Recargo BOLD 6.5% | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-RAG-13](#tc-rag-13) | Dificultad parapente 1/5 | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-RAG-14](#tc-rag-14) | Destino con varios tours (lista) | WhatsApp prod / playground prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-RAG-15](#tc-rag-15) | Lugar sin ficha + tour de paso | WhatsApp prod / playground prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-XTRA-01](#tc-xtra-01) | No arma vuelos / logística personal | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-XTRA-02](#tc-xtra-02) | “¿Eres una IA?” | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-XTRA-03](#tc-xtra-03) | CTWA (opcional; ver playground) | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-XTRA-04](#tc-xtra-04) | Sin JSON BANT visible | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-CTWA-01](#tc-ctwa-01) | CTWA — primer mensaje + body ballenas | Playground | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-CTWA-02](#tc-ctwa-02) | CTWA — segundo turno otro plan | Playground | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-CTWA-03](#tc-ctwa-03) | CTWA — sin mock, saludo normal | Playground | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-CTWA-01-WA](#tc-ctwa-01-wa) | CTWA — mismo Then si hay anuncio Meta | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |

---

## 1. Saludo y forma

Feature: Primer contacto y formato WhatsApp
  Amaru se presenta una vez, no inventa planes en el saludo, un mensaje por turno.

### TC-FLOW-01

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @flujo
Scenario: Saludo "Hola" sin handoff ni planes inventados
  Given una conversación nueva en WhatsApp de Xperiencia
  When el tester envía "Hola"
  Then Amaru se presenta como guía digital del equipo Xperiencia
  And el tono encaja con: "¡Hola! Soy Amaru tu guía digital del equipo Xperiencia"
  And no deriva a un humano
  And no muestra JSON BANT ni la palabra handoff
  And no inventa precios ni nombres de planes que el tester no pidió
  And en CRM la conversación no está en WAITING_HUMAN
```

Eval espejo: `es_greeting_no_handoff`

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-FLOW-02

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @flujo @rag
Scenario: Pregunta en el primer mensaje — saluda y responde
  Given una conversación nueva
  When el tester envía "Hola, qué planes hay cerca de Bogotá?"
  Then el mismo turno incluye presentación de Amaru
  And responde con planes de la KB (p. ej. Chingaza, Tobia, Suesca, parapente Guatavita)
  And no pregunta solo “¿qué te interesa?” sin datos
  And no hace handoff
```

Eval espejo: `es_browsing_plans`

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-FLOW-03

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @flujo
Scenario: No se vuelve a presentar a mitad de conversación
  Given TC-FLOW-01 ya respondió el saludo
  When el tester envía "cuéntame del parapente en Guatavita"
  Then ningún mensaje posterior repite el saludo completo "Soy Amaru tu guía digital…"
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-FLOW-04

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @flujo
Scenario: Un mensaje por turno y formato nativo
  Given cualquier turno del camino principal
  Then llega un solo mensaje de bot (no racha de 3–4 burbujas del mismo turno)
  And el énfasis usa *asteriscos* de WhatsApp, no **markdown** ni # títulos
  And no escribe fechas tipo 2026-07-29
  And cierra con una pregunta corta (una sola), salvo que sea el puente de handoff
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-FLOW-05

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @flujo @rag
Scenario: Info por partes; dump solo si piden todo
  Given conversación nueva y el tester ya saludó
  When envía "parapente en Guatavita"
  Then Amaru da ~2–3 datos (p. ej. duración/dificultad/precio) y una pregunta corta
  And no vuelca itinerario + incluye + no incluye + fechas + extras en el mismo turno
  When el tester envía "cuéntame todo lo que incluye y el itinerario"
  Then un mensaje más largo con lo pedido
  And igual cierra con una pregunta corta
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

---

## 2. Derivación — las 4 rutas (HITL)

Feature: Solo cuatro caminos abren handoff
  (1) plan publicado + salida listada + aceptar reservar esa
  (2) pedido explícito de humano
  (3) aceptar grupo/fecha a medida después de la oferta de Amaru
  (4) pregunta de discapacidad/accesibilidad
  Score ≥ 70 no califica. Turno 1 bloquea salvo (2) o (4).

**Setup HITL-01:** use un plan de la KB que **liste salidas/rangos**. Si el RAG no devuelve fechas, marque Blocked y pruebe otro plan (o use “ninguna fecha” → HITL-05/06).

### TC-HITL-01

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @hitl @crm
Scenario: Plan + salida listada + "sí, reserva esa"
  Given conversación nueva, turno 2+
  And Amaru ya listó salidas concretas de un plan publicado
  When el tester elige un rango de esa lista (p. ej. "el del 18 al 21")
  Then Amaru pregunta una vez si quieren reservar ESA salida
  And CRM aún no está en WAITING_HUMAN
  When el tester envía "sí, reserva esa" o "quiero reservar el del 18 al 21"
  Then llega un mensaje puente breve (cierre, no más preguntas de planes)
  And no muestra JSON BANT
  And en CRM la conversación pasa a WAITING_HUMAN
  And el motivo del operador es "Plan y fecha confirmados para reserva."
```

Eval espejo: `es_handoff_plan_and_date`, `es_yes_after_reserve_ask`

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-HITL-02

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @hitl @crm
Scenario: Pedir humano en turno 2+
  Given al menos un turno previo (saludo ya respondido)
  When el tester envía "quiero hablar con una persona" / "pásame con un asesor"
  Then mensaje puente breve
  And no muestra JSON ni la palabra handoff
  And CRM WAITING_HUMAN
  And motivo "Cliente solicitó atención humana."
```

Eval espejo: `es_explicit_human`

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-HITL-03

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @hitl @crm
Scenario: Pedir humano en el primer mensaje SÍ deriva
  Given conversación nueva
  When el primer mensaje es "quiero hablar con un asesor del equipo"
  Then hay puente (turno 1 bypass por pedido humano)
  And CRM WAITING_HUMAN
  And motivo "Cliente solicitó atención humana."
  And no continúa el saludo largo pidiendo destino
```

A diferencia de “quiero reservar” en turno 1 (TC-NOHD-01), el pedido de **persona** sí abre handoff.

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-HITL-04

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @hitl @crm
Scenario: Discapacidad / silla de ruedas en turno 1
  Given conversación nueva
  When el tester envía "Hola, ¿puedo ir en silla de ruedas al Cocuy? Voy con alguien con discapacidad"
  Then Amaru no afirma ni niega que el plan sea apto
  And no inventa una ficha médica desde la KB
  And hay puente breve
  And CRM WAITING_HUMAN
  And motivo "Consulta por discapacidad o accesibilidad."
```

Eval espejo: `es_disability_access_handoff`

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-HITL-05

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @hitl
Scenario: Ninguna fecha listada → ofrece grupo; aún no deriva
  Given Amaru listó salidas de un plan y el tester sigue interesado en ESE plan
  When envía "ninguna de esas fechas me sirve"
  Then Amaru ofrece armar un grupo o fecha a medida
  And no dice que ya pasó el caso a un asesor
  And CRM no está en WAITING_HUMAN
```

Eval espejo: `es_no_published_date_offer_custom`

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-HITL-06

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @hitl @crm
Scenario: Aceptar grupo a medida → puente
  Given TC-HITL-05 (Amaru ya ofreció armar grupo)
  When el tester envía "sí, ármenlo" / "dale"
  Then mensaje puente
  And CRM WAITING_HUMAN
  And motivo "Quiere armar grupo o fecha a medida."
```

Eval espejo: `es_accept_custom_group_handoff`

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-HITL-07

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @hitl
Scenario: El puente no vende ni manda links de pago
  Given un handoff exitoso (HITL-01, 02, 03, 04 o 06)
  Then el mensaje de cierre no incluye URLs de checkout / reserva / pago
  And no pide anticipo ni “completa tu reserva en la página”
  And puede mencionar plan o fecha ya hablados
  And no hace más preguntas de itinerario
```

Eval espejo: `es_no_payment_links`

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

---

## 3. No derivar (negativos HITL)

Feature: Score alto, fecha suelta o "quiero reservar" temprano no abren handoff
  Amaru suele fallar por derivar de más.

### TC-NOHD-01

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @hitl
Scenario: Turno 1 con intención fuerte de reserva no deriva
  Given conversación nueva
  When el tester envía "Hola, quiero reservar mi cupo para el Tour de Ballenas para mañana, yo pago y decido"
  Then Amaru continúa (saludo + info / pregunta)
  And no hay puente de asesor
  And CRM no está en WAITING_HUMAN
```

Eval espejo: `es_no_handoff_turn1_booking`

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-NOHD-02

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @hitl @rag
Scenario: Solo browsing de planes
  Given saludo ya respondido
  When el tester envía "qué planes tienes para Bogotá?" o "parapente"
  Then responde con info de la KB
  And no deriva
```

Eval espejo: `es_browsing_plans`, `es_whale_watching_short_reply`

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-NOHD-03

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @hitl
Scenario: Elegir un rango de la lista no es reservar
  Given Amaru listó salidas concretas
  When el tester responde solo con el rango ("Del 9 al 12")
  Then Amaru pregunta una vez si reservan ESA salida
  And ese turno no hay handoff
  And CRM no está en WAITING_HUMAN
```

Eval espejo: `es_pick_date_from_list_no_handoff`

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-NOHD-04

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @hitl @rag
Scenario: Mencionar fecha + pregunta de logística
  Given hay un plan activo
  When el tester envía "el 18 de agosto, ¿incluye traslado?"
  Then Amaru responde con el hecho de la KB (incluye / no incluye)
  And no deriva solo por nombrar el día
```

Eval espejo: `es_date_plus_logistics_no_handoff`, `es_cocuy_date_triggers`

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-NOHD-05

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @hitl
Scenario: "Quiero reservar" al inicio no se reutiliza al elegir fecha
  Given el tester dijo "quiero reservar" en un turno temprano
  And Amaru luego listó salidas
  When el tester solo elige un rango de la lista
  Then no hay handoff en ese turno
  And Amaru vuelve a preguntar si reservan ESA salida
```

Eval espejo: `es_want_reserve_then_pick_date_no_handoff`

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-NOHD-06

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @hitl
Scenario: Presupuesto insuficiente bloquea plan+fecha y grupo
  Given el tester dijo "solo tengo 50 mil" / "eso me queda muy caro, no me alcanza"
  When intenta confirmar una salida listada o aceptar grupo a medida
  Then no hay handoff por esas rutas
  And Amaru puede seguir conversando o reencuadrar (sin inventar descuentos)
  And CRM no está en WAITING_HUMAN
```

Eval espejo: `es_insufficient_budget`

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-NOHD-07

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @hitl
Scenario: Interés alto sin confirmar salida listada
  Given plan en contexto
  When el tester envía "me encanta, yo decido y pago, quiero ir sí o sí"
  Then no hay handoff (score alto no califica)
  And Amaru sigue (fechas, incluye, o pregunta corta)
```

Eval espejo: `es_high_score_no_confirm_no_handoff`

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-NOHD-08

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @hitl
Scenario: "Sí" a "¿te muestro qué incluye?" no es reserva
  Given Amaru preguntó si quiere ver incluye / itinerario
  When el tester envía "sí"
  Then Amaru da el dato de la KB
  And no deriva
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-NOHD-09

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @hitl @crm
Scenario: Presupuesto corto no bloquea pedir humano
  Given el tester ya dijo que no le alcanza el presupuesto
  When envía "igual quiero hablar con un asesor"
  Then sí hay puente
  And motivo "Cliente solicitó atención humana."
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

---

## 4. RAG — información correcta

Feature: Responder solo con hechos de search_context
  Gold: evals/ragas/dataset.json (KB cloud).
  Pass = el hecho pedido aparece y no hay cifra inventada.

Si un precio no coincide con el gold, compruebe la KB en CRM (rag-debug) antes de Fail: puede ser drift → Blocked.

### TC-RAG-01

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @rag
Scenario: Precio parapente Guatavita
  Given saludo ya respondido
  When el tester pregunta "¿Cuánto cuesta el parapente en Guatavita?"
  Then menciona Meditación ~$250.000 (15 min)
  And Intermedio ~$310.000 (20–25 min)
  And Adrenalina ~$370.000 (25 min)
  And puede mencionar reserva 30% y/o BOLD +6.5%
  And no inventa otros montos (p. ej. $85.000 del seed local)
```

Ragas: `precio-parapente-guatavita`, `cuanto-sale-parapente-guatavita`

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-RAG-02

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @rag
Scenario: Encuentro parapente y traslados
  Given plan parapente Guatavita en contexto (o pregunta directa)
  When pregunta el punto de encuentro
  Then Zona de vuelo Laguna de Guatavita
  When pregunta si incluye traslados al voladero
  Then no incluye traslados desde/hacia el voladero
  And sí puede mencionar seguro, piloto certificado, derecho de despegue
```

Ragas: `encuentro-parapente-guatavita`, `parapente-incluye-traslados`

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-RAG-03

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @rag
Scenario: Fotos GoPro del parapente
  When pregunta "¿Cuánto cuestan las fotos GoPro del parapente en Guatavita?"
  Then Fotos/Video GoPro $45.000
  And Video 360 $100.000
  And no vienen incluidas en el vuelo
```

Ragas: `gopro-parapente`

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-RAG-04

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @rag
Scenario: Paracaidismo Flandes — precio y reserva
  When pregunta precio del paracaidismo en Flandes / Xielo
  Then desde 800.000
  And se reserva con el 30%
  And puede mencionar recargo BOLD 6.5%
```

Ragas: `precio-paracaidismo-flandes`, `reserva-30-flandes`

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-RAG-05

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @rag
Scenario: Paracaidismo — peso, edad, encuentro
  Given paracaidismo Flandes en contexto
  When pregunta peso máximo
  Then 100 kilos; más de 85 kg consultar
  When pregunta edad mínima
  Then mínimo 12 años; sin tope máximo de edad
  When pregunta punto de encuentro
  Then Aeropuerto Santiago Vila en Flandes (Tolima), ~10 min de Girardot
  And el plan no incluye transporte hasta el encuentro
```

Ragas: `peso-maximo-paracaidismo`, `edad-minima-paracaidismo`, `encuentro-paracaidismo-flandes`

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-RAG-06

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @rag
Scenario: Chingaza — altura, ubicación, fauna
  When pregunta por Chingaza / trekking de páramo cerca de Bogotá
  Then Parque Nacional Natural Chingaza, La Calera, ~1.5 h de Bogotá
  And 4000 MSNM
  And puede mencionar oso de anteojos / lagunas
  And dificultad 2/5 si habla de exigencia
  And no inventa otro páramo con esas cifras
```

Ragas: `altura-chingaza`, `trekking-paramo-bogota`, `oso-anteojos-plan`, `chingaza-tiempo-bogota`, `dificultad-chingaza`

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-RAG-07

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @rag
Scenario: Tobia — rafting y clima cálido
  When pregunta "¿Dónde puedo hacer rafting cerca de Bogotá?" o "planes pa tierra caliente"
  Then Pasadía en Tobia: rafting en el río Negro
  And ~2 horas de Bogotá / clima cálido
  And puede mencionar torrentismo, canopy, puentes colgantes
  And no atribuye el rafting a Chingaza o Guatavita
```

Ragas: `rafting-cerca-bogota`, `actividades-tobia`, `planes-pa-tierra-caliente`

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-RAG-08

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @rag
Scenario: Suesca — hora y punto de encuentro
  When pregunta hora y lugar de la caminata/escalada en Suesca
  Then 9:00 am en la entrada de las Rocas de Suesca
  And no inventa otro punto (p. ej. Portal El Dorado del seed)
```

Ragas: `suesca-encuentro-hora`, `escalada-cundinamarca`

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-RAG-09

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @rag
Scenario: Paráfrasis — volar cerca de Bogotá
  When envía "¿Hay algún plan para volar al aire libre cerca de Bogotá?"
  Then parapente en Guatavita (biplaza, Embalse de Tominé / sabana)
  And no inventa un vuelo en globo u otro producto que no esté en la KB
```

Ragas: `volar-cerca-bogota`, `vuelo-biplaza-embalse`

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-RAG-10

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @rag
Scenario: Referencia "el segundo" / "¿y el precio?"
  Given Amaru listó 2+ planes (p. ej. cerca de Bogotá)
  When el tester envía "¿y el precio del segundo?"
  Then el precio corresponde al segundo plan de ESA lista
  And no inventa un monto
  And no pregunta de nuevo “¿cuál plan?” si la referencia es clara
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-RAG-11

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @rag
Scenario: Destino que no está en la KB
  When el tester pregunta "¿cuánto sale el tour a la Luna?" o un destino claramente fuera de catálogo
  Then Amaru pide aclaración o dice que no tiene ese plan
  And no inventa precio, fechas ni itinerario
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-RAG-12

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @rag
Scenario: Recargo BOLD
  When pregunta "¿Cuánto es el recargo BOLD?"
  Then 6.5% en pagos con tarjeta BOLD
```

Ragas: `recargo-bold`

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-RAG-13

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @rag
Scenario: Dificultad parapente Guatavita
  When pregunta qué tan difícil es el parapente en Guatavita
  Then 1/5 principiante / apto para principiantes
```

Ragas: `dificultad-parapente-guatavita`

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-RAG-14

**Dónde:** WhatsApp prod o playground `just serve-prod` (seed local no trae este destino)

```gherkin
@whatsapp @rag @list-plans
Scenario: Destino con varios tours — listar, no vender uno
  Given conversación nueva, sin plan activo
  When el tester pregunta por la experiencia al Nevado del Tolima (incluye / itinerario / precio)
  Then nombra cada tour distinto que trajo el conocimiento (ficha corta, una vez cada uno)
  And no presenta el precio o la duración de un solo tour como “el” del destino
  And no duplica la misma ficha
  And cierra con una pregunta
  And no muestra “Result 1”, thought tags ni URLs crudas
```

Gold: hilo de aceptación Caso A. No es ancla de prompt.

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-RAG-15

**Dónde:** WhatsApp prod o playground `just serve-prod`

```gherkin
@whatsapp @rag @list-plans
Scenario: Lugar sin ficha + tour que solo pasa cerca
  Given conversación nueva, sin plan activo
  When el tester pide planes de un lugar sin ficha publicada (p. ej. Nuquí)
  And el conocimiento solo trae un tour de otra zona que pasa cerca
  Then dice que no hay planes publicados ahí
  And ofrece ese tour como otro destino/plan
  And no lo vende como catálogo de ese lugar
```

Gold: hilo de aceptación. El nombre del lugar vive aquí, no en `instructions.md`.

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

---

## 5. Extra

Feature: Alcance, identidad, CTWA
  Activate / [CHATTY_ACTIVATE] queda fuera de esta corrida (scheduler de Nest), salvo una prueba ops.

### TC-XTRA-01

**Dónde:** WhatsApp prod

```gherkin
@whatsapp
Scenario: No arma vuelos ni logística personal
  Given un plan activo
  When el tester pide "ármame los vuelos desde Medellín y un hotel"
  Then Amaru no cotiza vuelos ni reserva hotel
  And reencuadra a planes / experiencias de Xperiencia
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-XTRA-02

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @flujo
Scenario: "¿Eres una IA?"
  When el tester pregunta si es una inteligencia artificial
  Then responde que es el guía digital de Xperiencia y está para ayudar
  And no dice "asesor digital"
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-XTRA-03

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @ctwa
Scenario: Click-to-WhatsApp desde anuncio (opcional)
  Given el tester entra por un anuncio CTWA (welcome de Meta ya visible)
  When envía el primer mensaje ("¡Hola! Quiero más información")
  Then Amaru habla del plan del anuncio (search_context de ese tema)
  And no pregunta genérico “¿qué te interesa?”
  And no repite el texto del welcome de Meta
  And no hace handoff solo por el anuncio
```

Eval espejo: `evals/ctwa` / `generic_icebreaker_with_ad_state`. Camino oficial repetible: **Playground** (`TC-CTWA-01`). Si no hay anuncio Meta clickable: **Blocked**. Opcional WhatsApp si hay anuncio; si no, Blocked.

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-XTRA-04

**Dónde:** WhatsApp prod

```gherkin
@whatsapp
Scenario: Nunca se ve JSON BANT en WhatsApp
  Given cualquier caso FLOW, HITL o RAG de esta corrida
  Then el cliente no ve bloques JSON (interest_level, budget_status, etc.)
  And no ve [CHATTY_ACTIVATE], "handoff" ni "BANT"
```

Eval espejo: `es_whale_watching_bant_polluted_history` + métrica `forbidden_output`

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

**Fuera de alcance manual (salvo ops):** nudge de inactividad (`activate_pending`). No hay caso WhatsApp aquí.

---

## 6. Campañas CTWA (playground)

Feature: Click-to-WhatsApp con mock en playground
  El contexto de campaña no vive en el contacto. Meta lo manda una vez; el playground lo inyecta en el primer mensaje.

### TC-CTWA-01

**Dónde:** Playground CRM (`/apps/configuration/playground`, org Amaru)

```gherkin
@playground @ctwa
Scenario: Primer mensaje genérico + body de ballenas
  Given playground org Amaru, panel CTWA con tema "Tour de avistamiento de ballenas en Nuquí" y welcome opcional
  And una conversación nueva (Nueva conversación)
  When el tester envía "Quiero más info"
  Then Amaru habla de ese plan (avistamiento de ballenas / Nuquí)
  And no pregunta genérico “¿qué te interesa?”
  And no repite el texto del welcome
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-CTWA-02

**Dónde:** Playground CRM (`/apps/configuration/playground`, org Amaru)

```gherkin
@playground @ctwa
Scenario: Segundo turno pide otro plan
  Given el hilo de TC-CTWA-01 (mismo conversation UUID, mock ya enviado)
  When el tester pide otro plan (p. ej. parapente en Guatavita)
  Then Amaru sigue al usuario y habla del plan pedido
  And no insiste en ballenas como único destino
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-CTWA-03

**Dónde:** Playground CRM (`/apps/configuration/playground`, org Amaru)

```gherkin
@playground @ctwa
Scenario: Sin mock — saludo normal
  Given playground org Amaru, panel CTWA vacío
  And una conversación nueva
  When el tester envía "Hola"
  Then el Then es el mismo que TC-FLOW-01 (presentación Xperiencia, sin plan inventado)
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-CTWA-01-WA

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @ctwa
Scenario: Mismo Then que CTWA-01 si se entra por anuncio Meta
  Given el tester entra por un anuncio CTWA de ballenas (welcome de Meta ya visible)
  When envía el primer mensaje ("¡Hola! Quiero más información")
  Then los Then de TC-CTWA-01
```

Si no hay anuncio clickable: **Blocked**. Camino oficial: playground `TC-CTWA-01`.

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

---

## Apéndice A — Motivos canónicos de handoff

Prioridad en Python: humano → discapacidad → grupo → plan+fecha.

| Ruta | Motivo (exacto) |
|---|---|
| Pedido de persona | `Cliente solicitó atención humana.` |
| Accesibilidad | `Consulta por discapacidad o accesibilidad.` |
| Grupo / fecha a medida aceptada | `Quiere armar grupo o fecha a medida.` |
| Plan + salida listada + reservar esa | `Plan y fecha confirmados para reserva.` |

Éxito **nunca** debe guardar `Lead calificado para atención humana.`

Presupuesto `Insufficient` bloquea plan+fecha y grupo; **no** bloquea humano ni discapacidad.

Turno 1: handoff solo si humano o discapacidad.

---

## Apéndice B — Mapa a evals existentes

Corridas automáticas (no sustituyen este MD):

```bash
cd projects/agents/amaru
just eval-handoff && just eval-handoff-grade
just eval-ragas -- --modes hybrid --limit 10
```

| TC | Eval / Ragas |
|---|---|
| TC-FLOW-01 | `es_greeting_no_handoff` |
| TC-FLOW-02, TC-NOHD-02 | `es_browsing_plans` |
| TC-HITL-01 | `es_handoff_plan_and_date`, `es_yes_after_reserve_ask` |
| TC-HITL-02 | `es_explicit_human` |
| TC-HITL-04 | `es_disability_access_handoff` |
| TC-HITL-05 | `es_no_published_date_offer_custom` |
| TC-HITL-06 | `es_accept_custom_group_handoff` |
| TC-HITL-07 | `es_no_payment_links` |
| TC-NOHD-01 | `es_no_handoff_turn1_booking` |
| TC-NOHD-03 | `es_pick_date_from_list_no_handoff` |
| TC-NOHD-04 | `es_date_plus_logistics_no_handoff`, `es_cocuy_date_triggers` |
| TC-NOHD-05 | `es_want_reserve_then_pick_date_no_handoff` |
| TC-NOHD-06 | `es_insufficient_budget` |
| TC-NOHD-07 | `es_high_score_no_confirm_no_handoff` |
| TC-XTRA-03 | `evals/ctwa` |
| TC-XTRA-04 | `es_whale_watching_bant_polluted_history` |
| TC-RAG-01 | `precio-parapente-guatavita` |
| TC-RAG-02 | `encuentro-parapente-guatavita`, `parapente-incluye-traslados` |
| TC-RAG-03 | `gopro-parapente` |
| TC-RAG-04 | `precio-paracaidismo-flandes` |
| TC-RAG-05 | `peso-maximo-paracaidismo`, `edad-minima-paracaidismo`, `encuentro-paracaidismo-flandes` |
| TC-RAG-06 | `altura-chingaza`, `trekking-paramo-bogota` |
| TC-RAG-07 | `rafting-cerca-bogota`, `actividades-tobia` |
| TC-RAG-08 | `suesca-encuentro-hora` |
| TC-RAG-09 | `volar-cerca-bogota` |
| TC-RAG-12 | `recargo-bold` |
| TC-RAG-13 | `dificultad-parapente-guatavita` |

---

## Apéndice C — Hechos gold (subset)

Fuente: `evals/ragas/dataset.json`. No usar seed local.

| Tema | Hecho |
|---|---|
| Parapente Guatavita precios | Meditación 15 min $250.000; Intermedio 20–25 min $310.000; Adrenalina 25 min $370.000 |
| Parapente reserva / BOLD | 30% de reserva; BOLD +6.5% |
| Parapente encuentro | Zona de vuelo Laguna de Guatavita |
| Parapente traslados | No incluye traslados al voladero |
| GoPro | $45.000 fotos/video; $100.000 video 360; no incluidas |
| Parapente dificultad / msnm | 1/5 principiante; 2.700 MSNM |
| Paracaidismo Flandes | Desde 800.000; 30%; Xielo; tándem >10.000 pies |
| Peso / edad | Máx. 100 kg; >85 consultar; min. 12 años |
| Encuentro Flandes | Aeropuerto Santiago Vila; no incluye transporte |
| Chingaza | 4000 MSNM; La Calera; ~1.5 h Bogotá; oso de anteojos; 2/5 |
| Tobia | Rafting río Negro; ~2 h Bogotá; clima cálido |
| Suesca | 9:00 am entrada Rocas de Suesca |

---

## Apéndice D — Hacia evals

Cuando se automaticen más casos:

1. HITL ya tiene dataset (`just eval-handoff`); este MD valida el mismo gate en prod.
2. RAG agente (tool + WhatsApp) no es Ragas: Ragas mide retrieve/generate naive. Un eval ADK futuro puede reusar los `id` de `dataset.json`.
3. No bajar umbrales de eval para “hacer pasar” un Fail de este MD.

---

## Apéndice E — Humo local (seed)

`just serve` + fila `https://local.seed/amaru/planes-bogota`: prueba **fetch por URL** (una página; varios planes en el mismo markdown). No sirve para listar fichas hermanas. Hermanos reales: `just serve-prod`.
