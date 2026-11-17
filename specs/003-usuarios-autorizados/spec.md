# Feature Specification: Personas autorizadas para usar el bot

**Feature Branch**: `003-usuarios-autorizados`

**Created**: 2026-11-16

**Status**: Draft

**Input**: User description: "Permitir que otras personas autorizadas por el dueño usen el bot de tarjeta de lealtad (hoy solo responde a un único OWNER_ID; constitución v4.0.0). La otra persona tiene TODOS los permisos (todos los comandos y botones) y comparte la misma base de clientes; el bot se usará también dentro de un grupo de Telegram donde están el dueño y esa persona (ambos administradores), y las tarjetas y listas quedan visibles para todos los miembros, lo cual está aceptado. Cualquier cuenta no autorizada, en privado o en el grupo, se ignora y queda en el log con su ID y usuario. Agregar o quitar personas autorizadas debe hacerse por configuración, sin cambiar código, y la configuración actual con un solo OWNER_ID debe seguir funcionando. En un grupo, hoy el bot respondería "Usa /ayuda…" a cualquier texto que no sea un comando, lo que sería ruido. Los botones deben poder pulsarlos las personas autorizadas, nunca las no autorizadas, y seguir teniendo un solo efecto. Conviene que el log anote qué cuenta autorizada hizo cada acción. La guía (README) debe explicar cómo autorizar a alguien y cómo encontrar su ID."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Otra persona autorizada usa el bot con todos los permisos (Priority: P1)

El dueño autoriza a otra persona. Desde entonces, esa persona usa el bot igual que el dueño: puede
registrar citas, dar de alta clientes, deshacer, pedir tarjetas y ver la lista de clientes, sobre
la misma base de clientes. Puede hacerlo en un chat privado con el bot o en un grupo donde también
esté el bot.

**Why this priority**: es el objetivo de la feature: que el negocio pueda atender a sus clientes
aunque el dueño no sea quien tenga el teléfono en la mano.

**Independent Test**: autorizar una segunda cuenta y recorrer con ella, en un chat privado y en un
grupo, los comandos principales de la feature 001.

**Acceptance Scenarios**:

1. **Dado** que una segunda persona está autorizada, **Cuando** envía `/cita Carmen` al bot,
   **Entonces** la cita se registra en la misma base que usa el dueño y recibe la tarjeta.
2. **Dado** el mismo escenario, **Cuando** usa `/alta`, `/deshacer`, `/tarjeta`, `/clientes` y
   `/ayuda`, **Entonces** obtiene los mismos resultados que obtendría el dueño.
3. **Dado** un grupo donde están el bot, el dueño y la persona autorizada, **Cuando** la persona
   autorizada envía un comando al bot en el grupo, **Entonces** el bot responde en el grupo.
4. **Dado** que el dueño registró una cita para "Carmen" hoy, **Cuando** la persona autorizada
   registra otra cita para "Carmen" el mismo día, **Entonces** el bot pide confirmación (la regla
   de "mismo día" de la feature 001 aplica sin importar quién registró la primera).

---

### User Story 2 - Las cuentas no autorizadas no pueden usar el bot (Priority: P1)

Cualquier cuenta que no esté autorizada, sea en un chat privado o dentro de un grupo, no obtiene
ninguna respuesta ni efecto del bot. Su intento queda en el registro de eventos con su ID y su
nombre de usuario; así el dueño puede obtener el ID de alguien que quiere autorizar.

**Why this priority**: con más de una persona y con el bot dentro de un grupo, el riesgo de que
alguien no autorizado registre o borre citas crece; la protección no puede debilitarse.

**Independent Test**: desde una cuenta no autorizada, enviar comandos y pulsar botones, en privado
y en un grupo, y comprobar que nada cambia y que el intento quedó en el registro.

**Acceptance Scenarios**:

1. **Dado** un miembro del grupo que no está autorizado, **Cuando** envía `/cita Carmen` en el
   grupo, **Entonces** el bot no responde, no se registra nada y el intento queda en el registro
   con su ID y usuario.
2. **Dado** un mensaje del bot con botones en el grupo, **Cuando** un miembro no autorizado pulsa
   un botón, **Entonces** no hay ningún efecto y la acción sigue disponible para las personas
   autorizadas.
3. **Dado** una cuenta no autorizada, **Cuando** escribe al bot en privado, **Entonces** no recibe
   respuesta.

---

### User Story 3 - El dueño administra quién está autorizado (Priority: P2)

El dueño agrega o quita personas autorizadas cambiando la configuración del bot y reiniciándolo,
sin tocar el código. La configuración que ya existe (solo el dueño) sigue funcionando sin cambios.
La guía explica cómo encontrar el ID de una persona y cómo autorizarla.

**Why this priority**: sin esto, cada cambio de personal requeriría un desarrollo; pero el uso
diario (US1, US2) es más importante.

**Independent Test**: siguiendo la guía, autorizar una cuenta nueva y luego quitarla; comprobar
que después de cada reinicio el bot la atiende o la ignora según corresponda.

**Acceptance Scenarios**:

1. **Dado** la configuración actual con solo el dueño, **Cuando** el bot arranca con la versión
   nueva, **Entonces** funciona igual que antes: solo atiende al dueño.
2. **Dado** el ID de una persona (obtenido del registro de eventos), **Cuando** el dueño lo agrega
   a la configuración y reinicia el bot, **Entonces** esa persona puede usar el bot.
3. **Dado** una persona autorizada, **Cuando** el dueño la quita de la configuración y reinicia,
   **Entonces** el bot la ignora desde ese momento.
4. **Dado** una configuración con un ID mal escrito (por ejemplo, con letras), **Cuando** el bot
   arranca, **Entonces** se niega a arrancar y explica qué valor es inválido.

---

### User Story 4 - Uso en grupo sin ruido (Priority: P2)

Dentro de un grupo, el bot solo reacciona a sus comandos y a sus botones. La conversación normal
entre los miembros no recibe respuestas del bot.

**Why this priority**: sin esto, en un grupo donde el bot recibe todos los mensajes, cada
conversación normal recibiría "Usa /ayuda para ver los comandos", y el grupo sería inutilizable.

**Independent Test**: en un grupo con el bot, conversar con mensajes normales y comprobar que el
bot no responde; luego enviar un comando y comprobar que sí responde.

**Acceptance Scenarios**:

1. **Dado** un grupo con el bot, **Cuando** el dueño o la persona autorizada envía un mensaje que
   no es un comando, **Entonces** el bot no responde.
2. **Dado** un grupo con el bot, **Cuando** alguien autorizado envía un comando dirigido a este bot
   (por ejemplo, con su nombre de usuario al final, como hace Telegram en grupos), **Entonces** el
   bot lo atiende igual que sin el nombre.
3. **Dado** un chat privado con el bot, **Cuando** una persona autorizada envía un texto que no es
   un comando, **Entonces** el bot sigue respondiendo con la indicación de usar `/ayuda` (como en
   la feature 001).

---

### Edge Cases

- **Dos personas autorizadas responden al mismo mensaje con botones**: el primer toque surte efecto
  y el segundo responde que la acción ya se aplicó (la regla de "un toque, un efecto" de la
  feature 001 se mantiene entre personas distintas).
- **La persona autorizada confirma un botón que pidió el dueño (o al revés)**: se permite; ambos
  tienen todos los permisos.
- **El bot se agrega a un grupo sin ninguna persona autorizada**: ignora todo lo que llega de ese
  grupo.
- **El mismo ID aparece repetido en la configuración**: se trata como una sola persona.
- **La configuración autoriza a alguien pero no incluye al dueño**: no se permite; el dueño siempre
  está autorizado.
- **Mensajes del propio sistema de Telegram en el grupo** (alguien entra o sale, cambios del grupo):
  el bot no responde.
- **Administrador anónimo en el grupo**: si una persona autorizada escribe como administradora
  anónima, Telegram oculta su cuenta y la muestra como una cuenta compartida del sistema; el bot no
  la reconoce y la ignora. Esa cuenta compartida no se autoriza nunca, porque autorizaría a
  cualquier administrador anónimo; el ID de una persona se obtiene de un mensaje que envía en
  privado al bot.

## Requirements *(mandatory)*

### Functional Requirements

**Autorización**

- **FR-001**: El sistema MUST permitir configurar, sin cambiar el código, una lista de cuentas de
  Telegram autorizadas además del dueño.
- **FR-002**: La configuración existente con solo el ID del dueño MUST seguir funcionando sin
  cambios, y el dueño MUST estar siempre autorizado.
- **FR-003**: Todas las personas autorizadas MUST tener los mismos permisos: todos los comandos y
  todos los botones, sobre la misma base de clientes.
- **FR-004**: Cualquier cuenta no autorizada MUST ignorarse, en chats privados y en grupos: sin
  respuesta y sin efecto. El intento MUST anotarse en el registro de eventos con su ID y su nombre
  de usuario.
- **FR-005**: Los botones del bot MUST surtir efecto solo cuando los pulsa una persona autorizada,
  una sola vez aunque los pulsen varias personas (FR-011 de la feature 001).
- **FR-006**: Si la configuración de personas autorizadas tiene un valor inválido, el sistema MUST
  negarse a arrancar y explicar cuál es.

**Grupos**

- **FR-007**: El bot MUST funcionar en chats privados y en grupos, respondiendo en el chat donde
  se envió el comando.
- **FR-008**: En un grupo, el bot MUST responder solo a sus comandos (también cuando llevan su
  nombre de usuario) y a sus botones; los mensajes que no son comandos y los avisos del propio
  grupo MUST NOT recibir respuesta.
- **FR-009**: En un chat privado, la respuesta a un texto que no es comando se mantiene como en la
  feature 001.

**Registro**

- **FR-010**: El registro de eventos MUST anotar qué cuenta autorizada hizo cada acción que cambia
  datos (registrar cita, dar de alta, deshacer), usando solo IDs.

**Guía**

- **FR-011**: La guía del proyecto MUST explicar cómo encontrar el ID de una persona (a partir del
  registro de eventos), cómo autorizarla, cómo quitarla y que en un grupo las tarjetas quedan
  visibles para todos sus miembros.

### Key Entities

- **Persona autorizada**: una cuenta de Telegram, identificada por su ID numérico, que puede usar
  el bot con todos los permisos. El dueño es siempre una de ellas. La lista vive en la
  configuración, no en la base de datos.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Una segunda persona autorizada completa los pasos principales de la tabla de
  validación de la feature 001 (cita, alta, deshacer, tarjeta, clientes) con los mismos resultados
  que el dueño, en privado y en un grupo.
- **SC-002**: El 100 % de los mensajes y toques de botón de cuentas no autorizadas, en privado y en
  grupos, no producen respuesta ni efecto.
- **SC-003**: En un grupo, 0 respuestas del bot a mensajes que no son comandos.
- **SC-004**: Autorizar o quitar a una persona siguiendo la guía toma menos de 5 minutos, incluido
  el reinicio del bot.
- **SC-005**: Con la configuración anterior (solo el dueño), el bot se comporta exactamente igual
  que antes de esta feature.

## Assumptions

- **Pocas personas**: se autorizarán entre 1 y 5 personas además del dueño.
- **Permisos únicos**: no hay roles ni permisos por persona; todas pueden hacer todo (decisión del
  dueño, 2026-11-16).
- **Visibilidad en grupos aceptada**: en un grupo, las tarjetas y listas (nombres de clientes y su
  avance) quedan visibles para todos los miembros, y el dueño lo aceptó (2026-11-16; principio V
  de la constitución v4.0.0).
- **Cambios por configuración**: autorizar o quitar personas requiere editar la configuración y
  reiniciar el bot; no hay comandos de Telegram para administrar personas.
- **Datos compartidos**: no se guarda en la base de datos quién hizo cada acción; queda solo en el
  registro de eventos (FR-010).
- **Dependencia**: esta feature parte de la feature 002 (bot en producción con webhook), que debe
  estar integrada antes de publicar la 003.
- **Fuera de alcance**: roles o permisos distintos por persona; administrar personas desde
  Telegram; restringir el bot a un grupo concreto; historial de acciones por persona en la base de
  datos.
