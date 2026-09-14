# Casos de prueba manuales — Sofía (Be Unique)

Pruebas **manuales** del agente WhatsApp Sofía. Cada `TC-*` es un candidato a `eval_id` cuando se conviertan en evals ADK; este archivo no ejecuta `agents-cli eval`.

Hay **dos canales**. Cada escenario declara **Dónde** (índice + cuerpo). No mezclar oráculos: en playground no hay botones nativos de WhatsApp ni pin; los “botones” se ven como texto/opciones del emulador.

| Canal | Cuándo usarlo |
|---|---|
| **WhatsApp prod** | FLOW / BOOK / CANCEL / RESCH / SKILL / PROMO / INFO / DUR / HITL. Verificación en [webapp.chatty.bo](https://webapp.chatty.bo) (Agenda). |
| **Playground CRM** (`/apps/configuration/playground`, org Be Unique) | Casos `@playground` / `@ctwa`: mock de anuncio repetible. CTWA real en WhatsApp solo si hay anuncio clickable; si no, **Blocked**. |

**Anclaje:** camino principal en `app/subagents/customer/instructions/instructions.md`. Skills: `info-institucional`, `depilacion-laser`, `faciales`, `promociones`, `derivacion-equipo`.

---

## Cómo ejecutar

**WhatsApp prod** (FLOW / agenda / skills / HITL):

1. Use un **número WhatsApp propio** (no una conversación de cliente real).
2. Nombre ficticio reconocible, p. ej. `Test Sofía Axilas`. Facilita filtrar en CRM.
3. **Conversación nueva por caso** (o reset claro: otro número / borrar chat y escribir como si fuera el primer mensaje). No mezclar `active_sede`, nombre ni citas previas.
   - Excepción: suites **Cancelar** y **Reprogramar** reusan la cita creada en el caso de booking indicado.
4. Tras cada reserva: CRM → Agenda de la sede → comprobar bloque (inicio, **fin = inicio + duración**, servicio, nombre).
5. **Limpieza:** cancele las citas de prueba al terminar (por WhatsApp o CRM) para no ocupar cupos reales.
6. Fallback de schedule: Sucre y Cochabamba tienen `duration_minutes = 60` si Sofía **no** pasa duración del skill. Si un slot de **valoración** o **axilas** sale de 60 min, el caso de duración **falla**.

**Playground** (CTWA / mock de anuncio):

1. CRM → org Be Unique → Configuración → Playground (`/apps/configuration/playground`).
2. Llene el panel **Simular anuncio (CTWA)** (tema + welcome opcional) → **Nueva conversación** → primer mensaje.
3. En playground los “botones” se ven como texto/opciones del emulador, no chips nativos de WhatsApp. No hay pin.
4. Reset = otra sesión ADK (otro UUID). El mock se envía solo en el primer mensaje.

### Cómo marcar

En cada escenario y en la tabla índice:

- **Pass** — todos los `Then` / `And` se cumplieron.
- **Fail** — algún `Then` falló (anote cuál).
- **Blocked** — no se pudo ejecutar (cupo, CRM, conversación sucia, etc.).

```text
**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**
```

Marque **una** casilla. Si falla, copie el mensaje de Sofía en notas.

### Convenciones Gherkin

- `Given` = estado previo (chat nuevo, sede ya elegida, cita existente).
- `When` = mensaje o tap de botón/lista (WhatsApp) o texto en el emulador (playground).
- `Then` = lo que debe verse en el canal indicado y, si aplica, en CRM.
- No se listan nombres de tools al cliente; los `Then` describen el **efecto** (botones nativos o texto/opciones del emulador, pin, bloque en agenda).
- Tags `@whatsapp` / `@playground` alineados con **Dónde**.

---

## Índice

Marque al completar. Detalle en cada escenario más abajo.

| ID | Suite | Canal | Resultado |
|---|---|---|---|
| [TC-FLOW-01](#tc-flow-01) | Camino principal — saludo `Hola` + sede | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-FLOW-02](#tc-flow-02) | Camino principal — `Buenos días` | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-FLOW-03](#tc-flow-03) | Camino principal — pregunta sin saludo | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-FLOW-04](#tc-flow-04) | Camino principal — orden sede → nombre → tratamiento → zona | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-FLOW-05](#tc-flow-05) | Camino principal — ciudad en el primer mensaje | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-FLOW-06](#tc-flow-06) | Camino principal — no re-preguntar datos ya dados | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-FLOW-07](#tc-flow-07) | Camino principal — precio solo si lo pide | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-BOOK-01](#tc-book-01) | Crear cita — happy path valoración | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-BOOK-02](#tc-book-02) | Crear cita — fecha nombrada (`mañana`) | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-BOOK-03](#tc-book-03) | Crear cita — no YYYY-MM-DD ni slot_id | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-BOOK-04](#tc-book-04) | Crear cita — sin handoff tras reservar | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-BOOK-05](#tc-book-05) | Crear cita — día sin cupos / más allá del horizonte | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-CANC-01](#tc-canc-01) | Cancelar — con confirmación | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-CANC-02](#tc-canc-02) | Cancelar — sin confirmar no cancela | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-CANC-03](#tc-canc-03) | Cancelar — 0 citas | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-RESCH-01](#tc-resch-01) | Reprogramar — happy path | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-RESCH-02](#tc-resch-02) | Reprogramar — no cancelar y crear | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-SKILL-01](#tc-skill-01) | Skills — tecnología Sucre | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-SKILL-02](#tc-skill-02) | Skills — tecnología Cochabamba | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-SKILL-03](#tc-skill-03) | Skills — precio axilas / bozo / piernas | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-SKILL-04](#tc-skill-04) | Skills — ¿duele? / crema anestésica láser | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-SKILL-05](#tc-skill-05) | Skills — Hidrafacial solo Sucre | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-SKILL-06](#tc-skill-06) | Skills — precios faciales | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-SKILL-07](#tc-skill-07) | Skills — anticipo Sucre vs CBBA vs Faciales | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-SKILL-08](#tc-skill-08) | Skills — zona íntima masculina | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-SKILL-09](#tc-skill-09) | Skills — embarazo | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-SKILL-10](#tc-skill-10) | Skills — bronceado | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-PROMO-01](#tc-promo-01) | Promos — no ofrecer en el saludo | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-PROMO-02](#tc-promo-02) | Promos — Primavera INACTIVA → tarifa regular | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-INFO-01](#tc-info-01) | Info — horarios | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-INFO-02](#tc-info-02) | Info — WhatsApp / redes | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-INFO-03](#tc-info-03) | Info — pagos (sin tarjetas) | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-INFO-04](#tc-info-04) | Info — pin de ubicación | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-INFO-05](#tc-info-05) | Info — puntualidad y 2 reprogramaciones | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-DUR-01](#tc-dur-01) | Duración — valoración 30 min | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-DUR-02](#tc-dur-02) | Duración — axilas 30 min | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-DUR-03](#tc-dur-03) | Duración — bozo 20 min | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-DUR-04](#tc-dur-04) | Duración — piernas completas 65 min | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-DUR-05](#tc-dur-05) | Duración — radiofrecuencia 60 min (Sucre) | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-DUR-06](#tc-dur-06) | Duración — limpieza facial 90 min | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-DUR-07](#tc-dur-07) | Duración — Hidrafacial 120 min (Sucre) | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-DUR-08](#tc-dur-08) | Duración — reagendar conserva 30 min | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-HITL-01](#tc-hitl-01) | HITL — pedir humano turno 2+ | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-HITL-02](#tc-hitl-02) | HITL — turno 1 no corta el saludo | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-HITL-03](#tc-hitl-03) | HITL — cita confirmada sin pedir humano | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-MISC-01](#tc-misc-01) | Extra — formato WhatsApp / un mensaje | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-MISC-02](#tc-misc-02) | Extra — no repetir “Soy Sofía” | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-MISC-03](#tc-misc-03) | Extra — domingo / feriado | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-MISC-04](#tc-misc-04) | Extra — no inventar horarios | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-CTWA-01](#tc-ctwa-01) | CTWA — mock Hidrafacial + Hola → sede | Playground | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-CTWA-02](#tc-ctwa-02) | CTWA — elige Sucre, habla de Hidrafacial | Playground | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-CTWA-03](#tc-ctwa-03) | CTWA — láser axilas + Cochabamba | Playground | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-CTWA-04](#tc-ctwa-04) | CTWA — sin mock, mismo Then que FLOW-01 | Playground | [ ] Pass [ ] Fail [ ] Blocked |
| [TC-CTWA-01-WA](#tc-ctwa-01-wa) | CTWA — opcional si hay anuncio Meta | WhatsApp prod | [ ] Pass [ ] Fail [ ] Blocked |

---

## 1. Camino principal (orden del prompt)

Feature: Camino principal de atención a cliente nuevo
  Sofía pide una cosa por turno: sede → nombre → tratamiento → zona (si láser)
  → valor/tecnología → invitación a valoración. Precio solo si el cliente lo pide.

### TC-FLOW-01

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @flujo
Scenario: Saludo "Hola" ofrece sedes con botones nativos
  Given una conversación nueva en WhatsApp de Be Unique
  When el cliente envía "Hola"
  Then Sofía responde con botones nativos "Sucre" y "Cochabamba" (no solo prosa)
  And el body incluye presentación: "Soy Sofía, asistente de Be Unique Clínica Estética"
  And el saludo empieza por "Hola." y luego "Soy Sofía" en el mismo párrafo
  And la pregunta de sede va en un segundo párrafo
  And no envía pin de ubicación
  And no menciona precios, zonas ni promociones
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-FLOW-02

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @flujo
Scenario: Saludo "Buenos días" adapta el copy
  Given una conversación nueva
  When el cliente envía "Buenos días"
  Then el body empieza por "Hola, buenos días. Soy Sofía"
  And ofrece botones Sucre y Cochabamba
  And no inventa "buenas tardes" ni "buenas noches"
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-FLOW-03

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @flujo
Scenario: Pregunta directa sin saludo usa "Hola" neutro y pide sede
  Given una conversación nueva
  When el cliente envía "Quiero información de depilación láser"
  Then Sofía saluda con "Hola" (neutro, sin momento del día)
  And se presenta como Sofía
  And pide sede con botones Sucre / Cochabamba
  And aún no pregunta zona ni da precios
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-FLOW-04

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @flujo @skill-laser
Scenario: Orden obligatorio sede → nombre → tratamiento → zona (Cochabamba, axilas)
  Given una conversación nueva
  When el cliente envía "Hola" y elige el botón "Cochabamba"
  Then Sofía pide el nombre (no zona, no tratamiento, no precio)
  When el cliente envía "Test Sofía Axilas"
  Then Sofía pregunta qué tratamiento le interesa (no menciona axilas/piernas/rostro como menú)
  When el cliente envía "Depilación láser"
  Then Sofía pregunta qué zona desea tratar
  And no pregunta aún si es sesión o paquete
  And no da precios
  When el cliente envía "axilas"
  Then explica tecnología Vega de Ibramed (Cochabamba), no Crystal Láser 3D de Sucre
  And describe resultados progresivos (vello más fino / menor frecuencia) sin "elimina el 100%" ni "no duele nada"
  And invita a revisar disponibilidad para la valoración
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-FLOW-05

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @flujo
Scenario: Ciudad en el primer mensaje omite la pregunta de sede
  Given una conversación nueva
  When el cliente envía "Hola, quiero atenderme en Sucre"
  Then Sofía se presenta
  And no vuelve a preguntar Sucre vs Cochabamba
  And continúa con el nombre (siguiente dato faltante)
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-FLOW-06

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @flujo
Scenario: No re-pregunta datos ya dados
  Given una conversación nueva
  When el cliente envía "Soy Andrea, quiero depilación láser de axilas en Cochabamba"
  Then Sofía no pregunta de nuevo sede, nombre, tratamiento ni zona
  And continúa con valor/tecnología de Cochabamba e invitación a valoración
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-FLOW-07

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @flujo @skill-laser
Scenario: Precio de axilas solo si el cliente lo pide
  Given el flujo de TC-FLOW-04 hasta zona axilas en Cochabamba (sin haber pedido precio)
  Then el mensaje de valor/tecnología no incluye "160 Bs" ni otra cifra de tarifa
  When el cliente envía "¿Cuánto cuesta?"
  Then Sofía responde 160 Bs para axilas (misma tarifa Sucre y Cochabamba)
  And vuelve a orientar a la valoración
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

---

## 2. Crear cita

Feature: Reserva de valoración o sesión
  Días primero si no hay fecha; horas después; confirmación con pin de sede.
  Verificar bloque en CRM.

**Setup sugerido:** completar sede + nombre + tratamiento (p. ej. láser axilas) y aceptar valoración. Use un nombre `Test Sofía Book`.

### TC-BOOK-01

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @agenda @crm
Scenario: Happy path — días → hora → reserva con pin
  Given el cliente aceptó revisar disponibilidad y no nombró fecha
  When Sofía ofrece días
  Then muestra días/fechas (botones si 2–3, lista "Elegir día" si 4+)
  And el body no lista horas HH:MM
  When el cliente elige un día
  Then ofrece horarios de ese día (botones 2–3 o lista "Elegir hora" si 4+)
  And si hay demasiados slots, primero pide franja mañana/tarde/noche
  When el cliente elige una hora
  Then confirma la cita (sede, nombre, servicio/zona, fecha y hora en español natural)
  And envía un pin de ubicación de esa sede (el texto va antes del pin)
  And incluye indicaciones previas del tratamiento y horario de sede (L-V 09:00–12:00 y 14:00–20:00; sáb 09:00–16:00)
  And no deriva a un humano
  And en CRM la cita aparece en Agenda de esa sede, status booked, con el nombre de prueba
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-BOOK-02

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @agenda
Scenario: Fecha nombrada — "mañana" va a horas de ese día
  Given sede y nombre ya dados, el cliente acepta valoración
  When el cliente envía "quiero para mañana"
  Then Sofía ofrece horarios de mañana (no re-lista solo la lista corta de días ignorando "mañana")
  And no dice "no es día hábil" solo porque mañana no estaba en los botones anteriores
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-BOOK-03

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @agenda
Scenario: No expone YYYY-MM-DD ni slot_id al cliente
  Given una reserva en curso (días u horas en pantalla)
  Then ningún mensaje al cliente contiene fecha tipo 2026-09-15
  And ningún mensaje muestra ids técnicos (slot_..., booking uuid, day_2026-...)
  And las fechas se dicen en español (*miércoles 16 de septiembre*) o DD/MM/YYYY
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-BOOK-04

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @agenda @crm @hitl
Scenario: Tras booked no hay handoff automático
  Given TC-BOOK-01 completado (cita confirmada)
  Then el chat sigue con Sofía (no mensaje de "lo paso con un asesor" salvo que el cliente lo pida)
  And en CRM la conversación no pasa a WAITING_HUMAN solo por haber agendado
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-BOOK-05

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @agenda
Scenario: Día sin cupos o fuera de horizonte
  Given el cliente nombra una fecha lejana (p. ej. "en 2 meses") o un día que la clínica no atiende
  Then Sofía no inventa horarios
  And si no hay cupos ese día, lo dice y ofrece otros días (no "no es hábil" genérico sin consultar)
  And si está más allá del horizonte de reserva (~30 días), explica que aún no se puede reservar tan adelante y ofrece días reservables
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

---

## 3. Cancelar cita

Feature: Cancelación con confirmación explícita
  Siempre lista citas reales; pide sí/no; texto sin pin.

**Setup:** reutilizar la cita de TC-BOOK-01 (o crear otra con el mismo número).

### TC-CANC-01

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @agenda @crm
Scenario: Cancelar una cita tras confirmación
  Given el cliente tiene 1 cita futura confirmada
  When envía "quiero cancelar mi cita"
  Then Sofía recapitula servicio, fecha y hora en español
  And pregunta confirmación explícita (sí/no)
  When el cliente envía "sí"
  Then confirma la cancelación por texto
  And no envía pin de ubicación
  And no ofrece reagendar en el mismo turno salvo que el cliente lo pida
  And en CRM el bloque desaparece o queda cancelado
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-CANC-02

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @agenda @crm
Scenario: Pedir cancelar sin confirmar no cancela
  Given el cliente tiene 1 cita futura
  When envía "quiero cancelar"
  Then Sofía pide confirmación
  When el cliente envía "no" o no responde "sí"
  Then la cita sigue activa en CRM
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-CANC-03

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @agenda
Scenario: Cancelar sin citas no inventa reservas
  Given una conversación nueva (sin citas en este número)
  When el cliente envía "cancelen mi cita"
  Then Sofía indica que no hay citas confirmadas futuras
  And no menciona una cita del historial inventada
  And puede ofrecer agendar si el cliente quiere
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

---

## 4. Reprogramar cita

Feature: Reagendar con listado real + nuevo slot
  Nunca cancelar y volver a crear a mano.

**Setup:** tener 1 cita futura (TC-BOOK-01 u otra). Nombre `Test Sofía Resch`.

### TC-RESCH-01

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @agenda @crm
Scenario: Reprogramar happy path
  Given el cliente tiene 1 cita futura
  When envía "quiero cambiar mi cita" o "reagendar"
  Then Sofía confirma cuál (sede, servicio, fecha y hora)
  When el cliente pide un día nuevo (o elige de la lista de días)
  Then ofrece horas de ese día
  When elige una hora
  Then confirma el nuevo horario
  And envía pin de la sede con el nuevo horario en el texto (antes del pin)
  And en CRM el mismo bloque (o la misma reserva) aparece en el nuevo start/end
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-RESCH-02

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @agenda @crm
Scenario: Reprogramar no es cancelar + crear
  Given TC-RESCH-01 en curso o recién completado
  Then en CRM no quedan dos citas (una cancelada y una nueva) para el mismo pedido
  And no aparece un mensaje de "cita cancelada" seguido de una reserva distinta en el mismo flujo
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

---

## 5. Skills de producto

Feature: Hechos autorizados por skills
  Cargar conocimiento; no inventar cifras ni mezclar sedes.

Complete sede + nombre antes de preguntar (salvo que el caso diga lo contrario).

### TC-SKILL-01

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @skill-laser
Scenario: Tecnología Sucre — Crystal Láser 3D
  Given sede Sucre y tratamiento depilación láser (zona cualquiera, p. ej. axilas)
  When el cliente pregunta "¿con qué láser trabajan?"
  Then menciona Crystal Láser 3D de Body Health
  And tres ondas: Alexandrita, Diodo y Nd:YAG
  And no atribuye Vega de Ibramed a Sucre
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-SKILL-02

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @skill-laser
Scenario: Tecnología Cochabamba — Vega Ibramed
  Given sede Cochabamba y depilación láser
  When el cliente pregunta por la tecnología
  Then menciona Vega de Ibramed (Triple Wave)
  And no atribuye Crystal Láser 3D a Cochabamba
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-SKILL-03

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @skill-laser
Scenario: Precios láser — axilas, bozo, piernas completas
  Given sede confirmada (Sucre o Cochabamba; precios iguales)
  When el cliente pide precio de axilas
  Then 160 Bs sesión individual
  When pide precio de bozo
  Then 100 Bs
  When pide precio de piernas completas
  Then 480 Bs
  And no inventa otros montos ni mezcla paquetes si no los pidió
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-SKILL-04

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @skill-laser
Scenario: FAQ — dolor y crema anestésica en láser
  Given sede y láser en contexto
  When el cliente envía "¿duele?"
  Then describe sensación tolerable (toque eléctrico / pinchazo / calor) y enfriamiento
  And no dice "no duele nada"
  When envía "¿ponen crema anestésica?"
  Then indica que en depilación láser no se usa crema anestésica como protocolo habitual
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-SKILL-05

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @skill-faciales
Scenario: Hidrafacial solo en Sucre
  Given sede Cochabamba (o sin asumir Sucre)
  When el cliente pregunta "¿hacen Hidrafacial?"
  Then indica que Hidrafacial está disponible solo en Sucre
  And no cotiza Hidrafacial como si existiera en Cochabamba
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-SKILL-06

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @skill-faciales
Scenario: Precios faciales — limpieza e HIFU Full Face
  Given sede donde el servicio existe (limpieza: ambas; HIFU: verificar catálogo)
  When el cliente pregunta precio de Limpieza Facial Profunda
  Then 250 Bs
  When pregunta precio de HIFU Full Face
  Then 850 Bs
  And no garantiza resultados de PDRN/exosomas
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-SKILL-07

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @skill-laser @skill-faciales
Scenario: Anticipo — Sucre láser vs Cochabamba láser vs Faciales
  Given conversación en Sucre hablando de valoración láser
  When el cliente pregunta si hay que pagar anticipo
  Then 100 Bs en Sucre (se abona al tratamiento si continúa)
  Given otra conversación en Cochabamba, láser
  When pregunta por anticipo / costo de valoración
  Then valoración sin costo (no decir 100 Bs para láser en Cochabamba)
  Given conversación de Faciales (Sucre o Cochabamba)
  When pregunta por reserva / anticipo
  Then 100 Bs en ambas sedes para la primera valoración de Faciales
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-SKILL-08

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @skill-laser
Scenario: No cotiza ni agenda zona íntima masculina
  Given un cliente que se identifica como hombre (o pide zona íntima masculina)
  When pide depilación láser en zona íntima
  Then Sofía no cotiza ni ofrece agendar esa zona
  And puede orientar a otras zonas disponibles o a valoración / equipo si insiste
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-SKILL-09

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @skill-laser
Scenario: Embarazo — no se realiza láser
  Given sede y láser en contexto
  When el cliente dice "estoy embarazada, ¿puedo hacerme láser?"
  Then indica que no se realiza durante el embarazo (se posterga)
  And no autoriza la sesión
  And orienta a valoración posterior o a una persona si la pide
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-SKILL-10

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @skill-laser
Scenario: Bronceado reciente — se posterga
  Given sede y láser en contexto
  When el cliente dice "me bronceé hace unos días, ¿puedo ir igual?"
  Then indica que con piel bronceada la sesión se posterga hasta recuperar el color basal
  And no confirma la sesión como segura "igual"
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

---

## 6. Promociones

Feature: Campañas temporales
  Estado actual del skill `promociones` (sep 2026): **Inicio de Primavera 2026 = INACTIVA**
  (40 % sobre sesión individual, vigencia 1–30 sep 2026, Publicable = Sí).
  No ofrecer. Cotizar tarifa regular.

Si el negocio activa la campaña, actualizar TC-PROMO-02: tarifa promocional = regular × 0,60, redondeo al múltiplo de 10 Bs (axilas 160 → 100 Bs).

### TC-PROMO-01

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @promociones
Scenario: No ofrece promo en el saludo
  Given una conversación nueva
  When el cliente envía "Hola"
  Then el mensaje de sede no menciona descuentos, 2x1, primavera ni "promo"
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-PROMO-02

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @promociones @skill-laser
Scenario: Pregunta por promo / primavera → tarifa regular (campaña INACTIVA)
  Given sede Cochabamba, nombre y zona axilas ya dados
  When el cliente envía "¿hay promoción?" o "vi lo de primavera / 2x1"
  Then no ofrece 40 % de descuento ni una campaña inventada
  And cotiza tarifa regular de axilas (160 Bs) si habla de precio
  And no acumula descuentos imaginarios con paquetes
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

---

## 7. Información general

Feature: Horarios, canales, pagos, ubicación, políticas
  Horario / WhatsApp / pagos / puntualidad: personalidad (SSOT).
  Dirección: pin nativo, no URL de Maps en texto.

### TC-INFO-01

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @info
Scenario: Horarios de atención
  Given sede identificada o pregunta general
  When el cliente envía "¿cuál es el horario?"
  Then L-V 09:00–12:00 y 14:00–20:00; sábado 09:00–16:00
  And domingos y feriados: generalmente no se atiende
  And no envía pin si solo preguntó horario
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-INFO-02

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @info
Scenario: WhatsApp y redes
  When el cliente pregunta el número o las redes
  Then WhatsApp 71701973 / +591 71701973
  And puede citar Facebook / Instagram / TikTok oficiales (beunique)
  And no inventa otros números
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-INFO-03

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @info
Scenario: Métodos de pago
  When el cliente pregunta "¿cómo puedo pagar?"
  Then acepta efectivo, QR (preferido), transferencia, Meru, Binance
  And indica que no se aceptan tarjetas de débito ni crédito
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-INFO-04

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @info
Scenario: Pin de ubicación (una sede y ambas)
  Given sede Cochabamba ya elegida
  When el cliente envía "¿dónde quedan?" o "mándenme la ubicación"
  Then llega un pin nativo de WhatsApp (no solo un link maps.app.goo.gl en texto)
  When (otra conversación o mismo hilo) pide "las dos sedes" / "ambas ubicaciones"
  Then envía pines de Sucre y Cochabamba
  Given conversación nueva sin sede
  When pide dirección
  Then primero botones Sucre/Cochabamba, sin pin todavía
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-INFO-05

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @info
Scenario: Puntualidad y reprogramaciones
  When el cliente pregunta "¿si llego tarde?" o "¿cuántas veces puedo cambiar la cita?"
  Then tolerancia de hasta 15 minutos; no hace falta llegar antes
  And hasta 2 reprogramaciones por reserva
  And no autoriza excepciones (tercer cambio, domingo, etc.) por su cuenta
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

---

## 8. Duración de slots (CRM)

Feature: duration_minutes del skill = largo del bloque en Agenda
  Valoración inicial ≈ 30 min.
  Sesión = **Tiempo total** del tarifario (no solo tiempo de procedimiento).
  Fallback del schedule = 60 min → **Fail** si aparece en valoración/axilas/bozo/piernas/limpieza/Hidrafacial.

Cómo medir: CRM → Agenda → abrir el evento → `fin − inicio`.

Para DUR-02 a DUR-07 el cliente debe pedir **sesión / tratamiento** (no solo valoración) o confirmar que agenda el servicio con esa duración. Si Sofía insiste en valoración 30 min, anote Blocked y fuerce el servicio en el mensaje (“quiero agendar la sesión de …, no solo la valoración”).

### TC-DUR-01

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @agenda @crm @duracion
Scenario: Valoración ocupa 30 minutos
  Given reserva de valoración (láser o facial) vía WhatsApp
  Then en CRM el bloque dura 30 minutos
  And no dura 60 (fallback del schedule)
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-DUR-02

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @agenda @crm @duracion @skill-laser
Scenario: Depilación axilas — Tiempo total 30 min
  Given el cliente agenda sesión de depilación láser de axilas (no solo valoración)
  Then en CRM el bloque dura 30 minutos
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-DUR-03

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @agenda @crm @duracion @skill-laser
Scenario: Depilación bozo — Tiempo total 20 min
  Given sesión de bozo (mujeres) agendada
  Then en CRM el bloque dura 20 minutos
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-DUR-04

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @agenda @crm @duracion @skill-laser
Scenario: Piernas completas — Tiempo total 65 min
  Given sesión de piernas completas agendada
  Then en CRM el bloque dura 65 minutos (no 50 de procedimiento ni 60 de fallback)
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-DUR-05

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @agenda @crm @duracion @skill-faciales
Scenario: Radiofrecuencia facial — 1 h (solo Sucre)
  Given sede Sucre y Radiofrecuencia facial agendada
  Then en CRM el bloque dura 60 minutos
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-DUR-06

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @agenda @crm @duracion @skill-faciales
Scenario: Limpieza Facial Profunda — 1 h 30 min
  Given Limpieza Facial Profunda agendada
  Then en CRM el bloque dura 90 minutos
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-DUR-07

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @agenda @crm @duracion @skill-faciales
Scenario: Hidrafacial — 2 h (solo Sucre)
  Given sede Sucre y Hidrafacial agendado
  Then en CRM el bloque dura 120 minutos
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-DUR-08

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @agenda @crm @duracion
Scenario: Reagendar valoración conserva 30 min
  Given una valoración de 30 min ya booked (TC-DUR-01)
  When el cliente reprograma a otro horario
  Then el nuevo bloque en CRM sigue durando 30 minutos
  And no cae a 60 min de fallback
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

---

## 9. HITL y extras

Feature: Handoff solo con pedido explícito de persona
  Score alto o cita confirmada no derivan. Formato WhatsApp nativo.

### TC-HITL-01

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @hitl @crm
Scenario: Pedir humano en turno 2+ cierra con puente
  Given una conversación con al menos un turno previo (sede o saludo ya respondido)
  When el cliente envía "quiero hablar con una persona" / "pásame con un asesor"
  Then Sofía confirma con calidez que lo conectará (mensaje puente, no JSON)
  And no muestra bloques BANT ni texto tipo "handoff"
  And en CRM la conversación pasa a WAITING_HUMAN (o equivalente HITL)
  And Sofía no sigue ofreciendo botones de agenda en ese mismo cierre
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-HITL-02

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @hitl @flujo
Scenario: Turno 1 pidiendo humano no salta el saludo/sede
  Given conversación nueva
  When el primer mensaje es "quiero hablar con alguien"
  Then Sofía aún hace el saludo + botones de sede (no corta el flujo de turno 1)
  And no aparece JSON interno
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-HITL-03

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @hitl @agenda
Scenario: Cita confirmada sin pedir humano — Sofía continúa
  Given TC-BOOK-01 (cita booked) y el cliente no pidió asesor
  Then no hay derivación automática
  And si el cliente escribe después (p. ej. "gracias"), Sofía puede responder sin puente de handoff
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-MISC-01

**Dónde:** WhatsApp prod

```gherkin
@whatsapp
Scenario: Un mensaje por turno y formato WhatsApp
  Given cualquier turno del camino principal
  Then llega un solo mensaje de bot al cliente (no racha de 3–4 burbujas del mismo turno)
  And el énfasis usa *asteriscos* de WhatsApp, no **markdown** ni # títulos
  And 1–2 emojis por bloque como máximo
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-MISC-02

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @flujo
Scenario: No se vuelve a presentar a mitad de conversación
  Given TC-FLOW-04 ya pasó el saludo inicial
  When el cliente sigue el flujo (nombre, tratamiento, zona)
  Then ningún mensaje posterior vuelve a decir "Soy Sofía, asistente de Be Unique…" como presentación completa
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-MISC-03

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @info
Scenario: Domingo o feriado — Sofía no autoriza
  When el cliente pide cita "el domingo" o "un feriado"
  Then no confirma ese horario por su cuenta
  And no inventa que la clínica atiende
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-MISC-04

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @agenda
Scenario: No inventa días ni horas
  Given el cliente pide "el martes a las 22:00" (fuera de horario) o un día sin oferta previa
  Then Sofía no confirma un cupo que no haya consultado
  And no ofrece 22:00 si el horario de sede cierra a las 20:00
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

---

## 10. Campañas CTWA (playground)

Feature: Click-to-WhatsApp con mock en playground
  El contexto de campaña no vive en el contacto. Meta lo manda una vez; el playground lo inyecta en el primer mensaje.

### TC-CTWA-01

**Dónde:** Playground CRM (`/apps/configuration/playground`, org Be Unique)

```gherkin
@playground @ctwa
Scenario: Mock Hidrafacial + "Hola" pide sede
  Given playground org Be Unique, panel CTWA con tema "Hidrafacial"
  And una conversación nueva (Nueva conversación)
  When el tester envía "Hola"
  Then Sofía ofrece opciones de sede Sucre y Cochabamba (texto/opciones del emulador, no chips nativos de WhatsApp)
  And se presenta como Sofía
  And no envía pin ni llama skills
  And no habla aún del Hidrafacial
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-CTWA-02

**Dónde:** Playground CRM (`/apps/configuration/playground`, org Be Unique)

```gherkin
@playground @ctwa
Scenario: Elige Sucre y habla de Hidrafacial
  Given el hilo de TC-CTWA-01 (mismo conversation UUID, mock ya enviado)
  When el tester elige "Sucre"
  Then Sofía no pregunta “qué tratamiento”
  And habla de Hidrafacial
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-CTWA-03

**Dónde:** Playground CRM (`/apps/configuration/playground`, org Be Unique)

```gherkin
@playground @ctwa
Scenario: Mock láser axilas + sede Cochabamba
  Given playground org Be Unique, panel CTWA con tema "depilación láser axilas"
  And una conversación nueva
  When el tester envía "Hola" y luego elige "Cochabamba"
  Then Sofía sigue el flujo láser (Vega) para axilas
  And no re-pregunta el tratamiento como si no hubiera anuncio
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-CTWA-04

**Dónde:** Playground CRM (`/apps/configuration/playground`, org Be Unique)

```gherkin
@playground @ctwa
Scenario: Sin mock — mismo Then que FLOW-01
  Given playground org Be Unique, panel CTWA vacío
  And una conversación nueva
  When el tester envía "Hola"
  Then el Then es el mismo que TC-FLOW-01 (sede Sucre/Cochabamba como texto/opciones del emulador; sin pin ni skills)
```

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

### TC-CTWA-01-WA

**Dónde:** WhatsApp prod

```gherkin
@whatsapp @ctwa
Scenario: Opcional si hay anuncio Meta
  Given el tester entra por un anuncio CTWA (welcome de Meta ya visible)
  When envía el primer mensaje
  Then los Then de TC-CTWA-01 (botones nativos de sede; no pin ni skills)
```

Si no hay anuncio clickable: **Blocked**. Camino oficial: playground `TC-CTWA-01`.

**Resultado:** [ ] Pass  [ ] Fail  [ ] Blocked
**Fecha / tester / notas:**

---

## Apéndice A — Skills y archivos de referencia

| Skill | Cuándo | Recursos |
|---|---|---|
| `info-institucional` | Horario, sedes, pagos, políticas generales | `sedes-horarios-canales.md`, `politicas-reserva.md`, `pagos.md` |
| `depilacion-laser` | Láser, zonas, precios, FAQ, tech | `tecnologia.md`, `zonas.md`, `tarifario.md`, `faqs-laser.md`, `preparacion-cuidados.md` |
| `faciales` | Catálogo, tarifas, anticipo 100 Bs ambas sedes | `catalogo.md`, `tarifas.md`, `politicas-reserva.md` |
| `promociones` | Promo / descuento / primavera | `promociones.md` (Primavera 2026 **INACTIVA**) |
| `derivacion-equipo` | Excepción, domingo, reductores detallados, clínica dudosa | `SKILL.md` (el orquestador solo hace HITL si piden persona) |

Personalidad gana si hay conflicto de política (horarios, pagos, reserva general). `info-institucional` es lookup, no SSOT.

---

## Apéndice B — Duraciones y tarifas ancla

### Láser — Tiempo total (agenda) y sesión individual

Precios iguales en Sucre y Cochabamba. Valoración inicial ≈ **30 min** (aparte).

| Zona | Tiempo total | Sesión individual |
|---|---:|---:|
| Bozo (mujeres) | 20 min | 100 Bs |
| Axilas | 30 min | 160 Bs |
| Piernas completas | 65 min | 480 Bs |
| Rostro completo | 45 min | 320 Bs |
| Espalda completa | 50 min | 400 Bs |

### Faciales — tiempo de agenda

| Servicio | Duración | Tarifa | Sede |
|---|---:|---:|---|
| Limpieza Facial Profunda | 90 min | 250 Bs | ambas |
| Radiofrecuencia facial | 60 min | 250 Bs | solo Sucre |
| Hidrafacial | 120 min | 250 Bs | solo Sucre |
| HIFU Full Face | 105 min (1 h 45) | 850 Bs | ver catálogo |

### Anticipos

| Caso | Regla |
|---|---|
| Valoración láser Sucre | 100 Bs (se abona al tratamiento si inicia) |
| Valoración láser Cochabamba | sin costo |
| Primera valoración Faciales (ambas sedes) | 100 Bs |

### Schedule fallback

Si Sofía omite `duration_minutes`, Nest usa **60 min**. Cualquier caso DUR de valoración/axilas/bozo/piernas/limpieza/Hidrafacial que mida 60 min es **Fail**.

---

## Apéndice C — Hacia evals

Cuando se conviertan estos casos:

1. Un `eval_id` = un `TC-*`.
2. Empezar por FLOW + SKILL (multi-turno, rubrics de hechos).
3. BOOK/CANC/RESCH/DUR necesitan tools de agenda + aserción de `duration_minutes` / `end - start` (hoy el CRM es el oráculo).
4. No bajar umbrales para “hacer pasar” un Fail de este MD.
