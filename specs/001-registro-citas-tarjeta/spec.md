# Feature Specification: Registro de citas y tarjeta de lealtad

**Feature Branch**: `001-registro-citas-tarjeta`

**Created**: 2026-11-16

**Status**: Draft

**Input**: User description: "MVP del bot de tarjeta de lealtad (Telegram, un solo usuario: el dueño del negocio). Registrar citas de clientes y devolver su tarjeta de lealtad generada (plantilla vacía + nombre del cliente + una flor por cita en las 9 casillas, llenadas por filas de izquierda a derecha) para reenviarla por WhatsApp desde el iPhone. Comandos del MVP: registrar cita, listar clientes con su conteo y deshacer la última cita. (1) Cada tarjeta dura hasta la cita 10: las citas 1 a 9 ponen una flor cada una y la cita 10 es la del premio; la siguiente cita empieza una tarjeta nueva desde cero. El número de citas por tarjeta debe ser configurable (por defecto 10) sin cambiar código. Se guarda el historial de tarjetas completadas. (2) Cada cliente tiene un identificador único; el nombre puede repetirse. Se escribe el nombre (no el ID): la búsqueda no distingue mayúsculas ni acentos; si hay varias coincidencias se pide elegir; si no hay ninguna, se pide confirmación antes de crear un cliente nuevo. (3) Los nombres largos se ajustan para caber sin invadir los elementos fijos. (4) El destello ✨ es parte fija de la plantilla. (5) La tarjeta se envía como foto. Al dar de alta un cliente debe poder indicarse cuántas citas ya lleva en su tarjeta actual. El conteo se deriva de eventos de cita guardados, y deshacer debe funcionar también si la última cita cerró una tarjeta."

## Clarifications

### Session 2026-11-16

- Q: ¿Deshacer anula la última cita del cliente indicado o la última cita registrada en general? → A: La última cita vigente del cliente indicado.
- Q: ¿La cita de premio usa un diseño especial de tarjeta? → A: No; se envía la tarjeta con todas las casillas marcadas.
- Q: ¿Cambiar el nombre de un cliente entra en el MVP? → A: No, queda fuera del MVP.
- Q: ¿Entran en el MVP el alta con citas previas y la consulta de la tarjeta sin registrar cita? → A: Sí, ambas.
- Q: ¿Qué tipografía se usa para el nombre? → A: Cualquiera sirve; se usa Sacramento (licencia OFL), incluida en el proyecto.
- Q: ¿Cómo se mide el tamaño del nombre al ajustarlo? → A: Por el tamaño de la fuente (la altura de la tinta varía según las letras del nombre): máximo, el que reproduce los 86 px de alto de "Carmen" en la tarjeta de ejemplo; mínimo, 36 px. *(Corregido durante el plan: la primera versión usaba la altura de la tinta, con mínimo de 43 px, y rechazaba nombres legibles.)*

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar una cita y recibir la tarjeta actualizada (Priority: P1)

Al terminar de atender a un cliente, el dueño le escribe al bot el comando de cita con el nombre
del cliente. El bot suma la cita y en segundos le devuelve la tarjeta de lealtad del cliente
(plantilla + nombre + una flor por cada cita de su tarjeta en curso) como foto, lista para
reenviarla por WhatsApp. Si el cliente es nuevo, el bot pide confirmación antes de crearlo.

**Why this priority**: es el proceso que hoy toma varios minutos por cliente (~18 por semana) y el
origen de los errores de conteo. Con solo esta historia el bot ya sustituye la edición manual.

**Independent Test**: con el bot vacío, registrar varias citas a un cliente nuevo y a uno
existente, y comprobar que cada foto recibida muestra el nombre correcto y tantas flores como
citas lleva su tarjeta en curso.

**Acceptance Scenarios**:

1. **Dado** que existe el cliente "Carmen" con 5 citas en su tarjeta en curso, **Cuando** el dueño
   registra una cita para "Carmen", **Entonces** el bot guarda la cita con la fecha y hora del comando
   y responde con una foto de la tarjeta con el nombre "Carmen" y 6 flores en las casillas 1 a 6.
2. **Dado** que existe el cliente "Carmen", **Cuando** el dueño registra una cita escribiendo
   "carmen" o "Cármen", **Entonces** el bot la reconoce como el mismo cliente y no crea uno nuevo.
3. **Dado** que no existe ningún cliente con un nombre parecido a "Lucía", **Cuando** el dueño
   registra una cita para "Lucía", **Entonces** el bot pregunta si quiere crear el cliente nuevo
   "Lucía" y solo al confirmar lo crea, registra su primera cita y envía la tarjeta con 1 flor.
4. **Dado** el escenario anterior, **Cuando** el dueño cancela la confirmación, **Entonces** no se
   crea ningún cliente ni se registra ninguna cita.
5. **Dado** que existe "Carmen" y no existe "Carmn", **Cuando** el dueño registra una cita para
   "Carmn", **Entonces** el bot sugiere a "Carmen" como opción además de crear un cliente nuevo
   "Carmn", y registra la cita en el cliente que el dueño elija.
6. **Dado** que se acaba de enviar la tarjeta, **Cuando** el dueño la abre en el iPhone, **Entonces**
   llega como foto (no como archivo) y puede reenviarse a WhatsApp directamente.

---

### User Story 2 - Completar la tarjeta y empezar una nueva (Priority: P2)

Cuando el cliente llega a la última cita del ciclo (por defecto la 10), el bot avisa que esa es la
cita de premio, cierra la tarjeta y la guarda en el historial del cliente. La siguiente cita del
cliente empieza una tarjeta nueva.

**Why this priority**: sin esta regla el conteo se desborda en cuanto un cliente llega a las 9
flores; los clientes frecuentes lo alcanzan en pocas semanas.

**Independent Test**: registrar 11 citas seguidas a un cliente y comprobar los avisos de las citas
9 y 10, que la tarjeta de la cita 10 queda en el historial y que la cita 11 muestra 1 flor.

**Acceptance Scenarios**:

1. **Dado** un cliente con 8 citas en su tarjeta en curso, **Cuando** se registra su cita 9,
   **Entonces** la tarjeta muestra las 9 casillas con flor y el mensaje avisa que la próxima cita
   es la de premio.
2. **Dado** un cliente con 9 citas en su tarjeta en curso, **Cuando** se registra su cita 10,
   **Entonces** el bot indica claramente que es la cita de premio, envía la tarjeta con las 9
   flores, y la tarjeta queda como completada en el historial con su fecha de cierre.
3. **Dado** un cliente que acaba de completar una tarjeta, **Cuando** se registra su siguiente cita,
   **Entonces** empieza una tarjeta nueva y la foto muestra 1 flor.
4. **Dado** que el número de citas por tarjeta se configuró en 8 y la plantilla tiene 7 casillas,
   **Cuando** un cliente llega a su cita 8, **Entonces** esa es la cita de premio y la tarjeta se
   cierra, sin modificar el código.

---

### User Story 3 - Dar de alta un cliente que ya tiene una tarjeta en curso (Priority: P2)

Al empezar a usar el bot hay clientes que ya llevan citas en su tarjeta manual. El dueño da de alta
al cliente indicando cuántas citas ya tiene, y el bot le devuelve la tarjeta para que compruebe que
coincide con la que tenía el cliente. El alta no cuenta como cita del día.

**Why this priority**: sin esto, los clientes actuales perderían su avance al pasar al bot o
habría que mantener el proceso manual en paralelo.

**Independent Test**: dar de alta un cliente con 6 citas previas, comprobar que la foto muestra
6 flores y que la siguiente cita registrada muestra 7.

**Acceptance Scenarios**:

1. **Dado** que no existe "Rosa", **Cuando** el dueño la da de alta con 6 citas previas,
   **Entonces** el bot crea el cliente, envía su tarjeta con 6 flores y no registra ninguna cita
   con la fecha de hoy.
2. **Dado** el escenario anterior, **Cuando** se registra una cita para "Rosa", **Entonces** la
   tarjeta muestra 7 flores.
3. **Dado** cualquier cliente nuevo, **Cuando** el dueño indica un número de citas previas menor
   que 0 o mayor que el número de casillas, **Entonces** el bot rechaza el alta y explica el rango
   válido.
4. **Dado** que ya existe un cliente "Rosa", **Cuando** el dueño da de alta otro "Rosa",
   **Entonces** el bot avisa que ya existe uno con ese nombre y solo crea el segundo si el dueño
   lo confirma; cada uno conserva su identificador propio.

---

### User Story 4 - Elegir entre clientes con el mismo nombre (Priority: P2)

Si hay dos o más clientes cuyo nombre coincide con lo escrito, el bot no adivina: muestra las
opciones con datos que las distinguen y el dueño elige con un toque. El dueño también puede
indicar al cliente directamente por su identificador.

**Why this priority**: registrar la cita al cliente equivocado afecta directamente su promoción;
con ~18 clientes por semana es muy probable que se repitan nombres.

**Independent Test**: crear dos clientes "María", registrar una cita escribiendo "maría" y
comprobar que se pide elegir y que la cita se suma solo a la elegida.

**Acceptance Scenarios**:

1. **Dado** dos clientes llamados "María" (identificadores distintos), **Cuando** se registra una
   cita para "maria", **Entonces** el bot muestra ambas opciones con su identificador, las citas
   de su tarjeta en curso y la fecha de su última cita, y no registra nada hasta que se elige una.
2. **Dado** el escenario anterior, **Cuando** el dueño elige una de las opciones, **Entonces** la
   cita se registra solo en ese cliente y se envía su tarjeta.
3. **Dado** un cliente con identificador conocido, **Cuando** el dueño registra la cita indicando
   ese identificador, **Entonces** la cita se registra en ese cliente sin preguntar.

---

### User Story 5 - Deshacer la última cita de un cliente (Priority: P3)

Si el dueño registró una cita por error (cliente equivocado o cita duplicada), puede deshacer la
última cita de ese cliente. El bot muestra qué cita se va a anular, pide confirmación y devuelve la
tarjeta corregida. La cita anulada deja de contar, pero queda constancia de la anulación.

**Why this priority**: los errores son raros, pero sin esta opción no habría forma de corregirlos
desde el bot.

**Independent Test**: registrar dos citas a un cliente, deshacer una y comprobar que la tarjeta
vuelve a mostrar las flores anteriores y que la anulación queda registrada.

**Acceptance Scenarios**:

1. **Dado** un cliente con 4 citas en su tarjeta en curso, **Cuando** el dueño deshace la última
   cita y confirma, **Entonces** la tarjeta vuelve a 3 flores, el bot envía la tarjeta corregida y
   la cita anulada queda registrada como anulada con su fecha de anulación.
2. **Dado** un cliente cuya última cita fue la de premio, **Cuando** el dueño la deshace,
   **Entonces** la tarjeta vuelve a estar en curso con 9 flores y deja de aparecer en el historial
   de tarjetas completadas.
3. **Dado** un cliente sin citas vigentes, **Cuando** el dueño intenta deshacer, **Entonces** el bot
   informa que no hay nada que deshacer y nada cambia.
4. **Dado** que el bot pidió confirmación para deshacer, **Cuando** el dueño cancela, **Entonces**
   nada cambia.

---

### User Story 6 - Consultar clientes y tarjetas (Priority: P3)

El dueño puede ver la lista de clientes con su avance y pedir la tarjeta actual de un cliente sin
registrar una cita (por ejemplo, para reenviarla si el cliente la perdió).

**Why this priority**: es consulta; no cambia datos, pero evita tener que llevar la cuenta aparte
y permite recuperar una tarjeta si falló un envío.

**Independent Test**: con varios clientes registrados, pedir la lista y una tarjeta y comprobar que
coinciden con las citas registradas y que no se agregó ninguna cita.

**Acceptance Scenarios**:

1. **Dado** varios clientes registrados, **Cuando** el dueño pide la lista, **Entonces** el bot
   muestra, en orden alfabético, el identificador, el nombre, las citas de la tarjeta en curso y
   el número de tarjetas completadas de cada cliente, marcando a quienes su próxima cita es la de
   premio.
2. **Dado** un cliente con 5 citas en su tarjeta en curso, **Cuando** el dueño pide su tarjeta,
   **Entonces** el bot envía la foto con 5 flores y el conteo del cliente no cambia.

---

### Edge Cases

- **Comando sin nombre o mal escrito**: el bot explica cómo usarlo, con un ejemplo, y no cambia
  nada.
- **Dos citas el mismo día al mismo cliente**: el bot pide confirmación antes de registrar la
  segunda (probable duplicado).
- **Botón pulsado dos veces** (confirmar, elegir cliente, deshacer): la acción se aplica una sola
  vez.
- **Nombre que no cabe** en el área del nombre ni con el tamaño mínimo legible: el bot rechaza el
  alta y pide un nombre más corto (por ejemplo, solo el nombre de pila).
- **Nombre con caracteres que la tipografía no puede dibujar** (por ejemplo, emojis): el bot
  rechaza el alta e indica qué caracteres no se admiten. Las letras del español (á, é, í, ó, ú, ü,
  ñ, mayúsculas incluidas) siempre se admiten.
- **Mensaje de otra cuenta de Telegram**: no recibe respuesta alguna y el intento queda en el
  registro de eventos del sistema.
- **Lista de clientes demasiado larga para un mensaje**: se divide en varios mensajes sin perder
  clientes.
- **Cambio del número de citas por tarjeta con tarjetas en curso**: las tarjetas completadas no
  cambian; si una tarjeta en curso ya tiene tantas o más citas que el nuevo número de casillas, su
  siguiente cita es la de premio.
- **Número de citas por tarjeta incoherente con las casillas de la plantilla** (casillas distinto
  de citas por tarjeta − 1): el bot no arranca e indica el motivo en su registro.
- **Comandos enviados mientras el bot estaba detenido**: se procesan al reanudarse y las citas toman
  la fecha y hora en que el dueño envió el comando, no la del procesamiento.
- **Fallo al generar o enviar la foto**: la cita ya registrada se conserva, el bot informa del
  error y el dueño puede pedir la tarjeta de nuevo con la consulta de tarjeta (Historia 6).
- **Deshacer citas previas al alta**: se permite (corrige un número inicial mal indicado) y siguen
  las mismas reglas que cualquier otra cita.

## Requirements *(mandatory)*

### Functional Requirements

**Acceso**

- **FR-001**: El sistema MUST responder únicamente a la cuenta de Telegram del dueño configurada;
  los mensajes de cualquier otra cuenta se ignoran sin respuesta y se anotan en el registro de
  eventos.
- **FR-002**: Las credenciales del bot y la identidad del dueño MUST configurarse fuera del código
  y no versionarse.

**Identificación de clientes**

- **FR-003**: Cada cliente MUST tener un identificador único asignado automáticamente al crearlo,
  que no cambia ni se reutiliza.
- **FR-004**: El nombre de un cliente MAY repetirse entre clientes distintos.
- **FR-005**: El dueño MUST poder indicar al cliente por su nombre o por su identificador. La
  búsqueda por nombre MUST ignorar mayúsculas, acentos y espacios sobrantes.
- **FR-006**: Si el nombre coincide exactamente (tras ignorar mayúsculas, acentos y espacios) con
  un solo cliente, el sistema MUST actuar sobre él sin preguntar. Si coincide con varios, MUST
  mostrar las opciones con identificador, citas de la tarjeta en curso y fecha de la última cita,
  y esperar a que el dueño elija.
- **FR-007**: Si no hay coincidencia exacta, el sistema MUST ofrecer los clientes con nombre
  parecido junto con la opción de crear un cliente nuevo; si no hay ninguno parecido, MUST pedir
  confirmación para crearlo. El sistema NUNCA crea un cliente sin confirmación del dueño. Un
  nombre es "parecido" si, ignorando mayúsculas y acentos, difiere del escrito en como máximo 2
  letras (falta, sobra, cambia o se intercambia una letra), o si lo escrito coincide con el inicio
  de alguna palabra del nombre (por ejemplo, "Carmn" → "Carmen"; "Mar" → "María López").

**Registro de citas**

- **FR-008**: Registrar una cita MUST sumar una cita vigente a la tarjeta en curso del cliente con
  la fecha y hora en que el dueño envió el comando, en la zona horaria del negocio.
- **FR-009**: Tras registrar una cita, el sistema MUST enviar la tarjeta del cliente como foto,
  acompañada de un texto con el nombre, las citas de la tarjeta en curso y cuántas faltan para la
  cita de premio.
- **FR-010**: Si el cliente ya tiene una cita registrada ese mismo día, el sistema MUST pedir
  confirmación antes de registrar otra.
- **FR-011**: Cada confirmación o selección MUST producir su efecto una sola vez aunque se pulse
  repetidamente.

**Ciclo de la tarjeta**

- **FR-012**: El número de citas por tarjeta (N) MUST ser configurable sin modificar el código, con
  valor por defecto 10. Las citas 1 a N−1 ocupan una casilla cada una; la cita N es la de premio.
- **FR-013**: Al registrar la cita N−1, el texto MUST avisar que la próxima cita es la de premio.
- **FR-014**: Al registrar la cita N, el sistema MUST marcar la tarjeta como completada con su fecha,
  guardarla en el historial del cliente, avisar claramente que es la cita de premio y enviar la
  tarjeta con todas las casillas marcadas, sin un diseño especial.
- **FR-015**: La primera cita después de completar una tarjeta MUST iniciar una tarjeta nueva con
  una flor.
- **FR-016**: Cambiar N MUST no alterar las tarjetas ya completadas. Si una tarjeta en curso ya
  tiene N−1 citas o más con el nuevo valor, su siguiente cita es la de premio.
- **FR-017**: Si el número de casillas de la plantilla no es igual a N−1, el sistema MUST negarse a
  arrancar e indicar el motivo en el registro de eventos.

**Alta de clientes**

- **FR-018**: El dueño MUST poder dar de alta un cliente indicando su nombre y, opcionalmente, las
  citas que ya lleva en su tarjeta actual (de 0 a N−1; 0 si no se indica). El alta no registra una
  cita del día; las citas previas quedan registradas como anteriores al bot, sin fecha real.
- **FR-019**: Tras el alta, el sistema MUST enviar la tarjeta del cliente para que el dueño la
  compare con la que tenía.
- **FR-020**: Si ya existe un cliente con el mismo nombre, el sistema MUST avisarlo y crear el nuevo
  solo si el dueño lo confirma.
- **FR-021**: El nombre se guarda tal como lo escribió el dueño (mayúsculas y acentos incluidos) y
  es el que aparece en la tarjeta.

**Deshacer**

- **FR-022**: El dueño MUST poder deshacer la cita vigente más reciente del cliente que indique (no
  la última cita registrada en general), incluidas las citas previas al alta. Antes de aplicarlo, el sistema MUST mostrar qué cita se anulará y pedir
  confirmación.
- **FR-023**: Una cita deshecha MUST dejar de contar, pero conservarse marcada como anulada con su
  fecha de anulación.
- **FR-024**: Si la cita deshecha era la de premio, la tarjeta MUST volver a estar en curso y salir
  del historial de tarjetas completadas.
- **FR-025**: Tras deshacer, el sistema MUST enviar la tarjeta actualizada. Si el cliente no tiene
  citas vigentes, MUST informarlo sin cambiar nada.

**Generación de la tarjeta**

- **FR-026**: La tarjeta MUST generarse siempre a partir de los datos registrados: plantilla vacía,
  nombre del cliente y una flor por cada cita de la tarjeta en curso, hasta llenar todas las
  casillas. Las casillas se llenan por
  filas, de izquierda a derecha y de arriba abajo. Nunca se modifica una tarjeta generada antes.
- **FR-027**: El nombre MUST dibujarse con la tipografía manuscrita del proyecto, centrado sobre la
  línea de la plantilla. Su tamaño de fuente es como máximo el que reproduce la altura del nombre
  en la tarjeta de referencia (`docs/referencia/tarjeta-ejemplo.jpeg`, "Carmen" con 86 px de alto).
  Se reduce lo necesario para no superponerse al título, la línea ni el destello ✨, y nunca baja
  de 36 px.
- **FR-028**: Si un nombre no cabe con el tamaño mínimo o contiene caracteres que la tipografía no
  puede dibujar, el sistema MUST rechazarlo al dar de alta y pedir otro.
- **FR-029**: Con los mismos datos, la tarjeta generada MUST ser idéntica en cada generación.
- **FR-030**: Los elementos fijos de la plantilla (título, destello ✨, línea, texto de bienvenida,
  fondo y casillas) MUST quedar intactos en la tarjeta generada.

**Consultas**

- **FR-031**: El dueño MUST poder ver la lista de clientes en orden alfabético con identificador,
  nombre, citas de la tarjeta en curso y número de tarjetas completadas, marcando a quienes su
  próxima cita es la de premio. Si no cabe en un mensaje, se divide en varios.
- **FR-032**: El dueño MUST poder pedir la tarjeta actual de un cliente sin registrar una cita.
- **FR-033**: El bot MUST ofrecer una ayuda breve con los comandos disponibles y un ejemplo de uso
  de cada uno.

**Persistencia**

- **FR-034**: Clientes, citas (incluidas las anuladas) y tarjetas completadas MUST conservarse entre
  reinicios del sistema.

### Key Entities

- **Cliente**: persona que acumula citas. Tiene un identificador único, el nombre que aparece en su
  tarjeta (puede repetirse entre clientes) y su fecha de alta.
- **Cita**: un evento de visita de un cliente. Tiene fecha y hora (o la marca "anterior al bot" si
  se cargó en el alta), estado (vigente o anulada, con fecha de anulación) y la tarjeta a la que
  pertenece. El avance de una tarjeta se calcula contando sus citas vigentes.
- **Tarjeta**: un ciclo de N citas de un cliente. Está en curso o completada; si está completada,
  tiene la fecha de su cita de premio. Cada cliente tiene como máximo una tarjeta en curso.
- **Configuración del programa**: número de citas por tarjeta (N), zona horaria del negocio, y la
  plantilla con la posición de sus casillas y del área del nombre.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Registrar la cita de un cliente existente y tener su tarjeta lista para reenviar toma
  al dueño menos de 15 segundos, frente a varios minutos con la edición manual.
- **SC-002**: En el 95 % de los casos la foto de la tarjeta llega en menos de 5 segundos después de
  enviar el comando.
- **SC-003**: En el 100 % de los casos probados (de 0 a N citas, con y sin citas anuladas) el número
  de flores de la tarjeta coincide con las citas vigentes de la tarjeta en curso.
- **SC-004**: El tiempo total que el dueño dedica a las tarjetas en una semana típica (~18 citas)
  baja a menos de 5 minutos.
- **SC-005**: Escribir el nombre de un cliente existente con otras mayúsculas o sin acentos nunca
  crea un cliente duplicado.
- **SC-006**: Nombres de hasta 20 caracteres (por ejemplo, "María Fernanda Ruiz") se muestran
  completos, legibles y sin superponerse a ningún elemento fijo de la plantilla.
- **SC-007**: Deshacer una cita deja la tarjeta y el historial exactamente como estaban antes de
  registrarla, incluso cuando esa cita había completado la tarjeta.
- **SC-008**: Ningún mensaje de una cuenta distinta a la del dueño recibe respuesta.

## Assumptions

- **Usuario único**: solo el dueño usa el bot, desde una cuenta de Telegram en su iPhone. Los
  clientes no interactúan con el bot; el dueño reenvía la foto por WhatsApp.
- **Volumen**: ~18 citas por semana y menos de 200 clientes en total.
- **Premio**: la cita N (10 por defecto) es "la cita de premio". El bot solo la identifica y la
  anuncia; qué premio se entrega lo decide el negocio fuera del bot.
- **Tarjeta nueva**: tras la cita de premio, la tarjeta nueva empieza vacía (0 flores) y la
  siguiente cita pone la primera flor.
- **Fecha de las citas**: se registran con la fecha del comando; no se pueden registrar citas con
  fecha pasada (salvo las citas previas indicadas al dar de alta).
- **Datos para distinguir clientes con el mismo nombre**: identificador, citas de la tarjeta en curso
  y fecha de la última cita. No se piden datos adicionales (apellido, teléfono) en el MVP.
- **Fuera de alcance del MVP**: cambiar el nombre de un cliente, eliminar o fusionar clientes, ver
  el detalle del historial de tarjetas, cambiar N desde el bot (se cambia en la configuración),
  enviar la tarjeta directamente al cliente, copias de seguridad automáticas, varios usuarios
  operadores y la tarjeta web por cliente (fase 2).
- **Dependencias de assets**:
  - Plantilla vacía disponible en `assets/plantilla-vacia.png` (1050 × 600, 9 casillas, incluye el
    ✨). Se generó a partir de la tarjeta de ejemplo; puede reemplazarse por una exportación
    directa del diseño original sin cambiar el comportamiento.
  - Flor con fondo transparente en `assets/flor.png`, extraída de la tarjeta de ejemplo.
  - Tipografía del nombre en `assets/fuentes/Sacramento-Regular.ttf` (licencia OFL, con todas las
    letras del español). La fuente exacta no es relevante para el negocio y puede cambiarse.
- **Zona horaria**: se configura la del negocio; el servidor puede estar en otra zona.
