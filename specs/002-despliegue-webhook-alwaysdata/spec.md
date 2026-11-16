# Feature Specification: Publicación en alwaysdata (plan Free) con webhook

**Feature Branch**: `002-despliegue-webhook-alwaysdata`

**Created**: 2026-11-16

**Status**: Draft

**Input**: User description: "Publicar el bot de tarjeta de lealtad (feature 001, ya integrada y validada en el iPhone) en alwaysdata con el plan Free, que no admite Services. Según la constitución v2.0.0 (principio VI): en producción el bot corre como sitio de tipo "User program" que recibe los mensajes de Telegram por webhook HTTPS en una dirección gratuita *.alwaysdata.net, escuchando en la IP y el puerto que alwaysdata entrega en $IP y $PORT, y valida cada petición con el secret token de Telegram (además de que solo responde al dueño). En la computadora del dueño sigue funcionando igual que hoy (long polling con el bot de pruebas). El modo se elige por configuración: si existe WEBHOOK_URL, modo webhook; si no, polling. Todas las funciones de la feature 001 deben comportarse igual en ambos modos. La cuenta de alwaysdata del dueño ya aloja su bot de finanzas como sitio en la dirección principal de la cuenta (también por webhook), y este bot no debe afectarlo; el plan Free da 256 MB de RAM y 1 GB de disco para toda la cuenta; los sitios se duermen tras un tiempo sin peticiones (30 min por defecto, configurable) y despiertan con la siguiente petición; Telegram reintenta las entregas si el sitio no responde. El bot de finanzas responde "ok" en la raíz para comprobarlo desde el navegador, y al arrancar en polling se niega a hacerlo si el bot ya tiene un webhook activo en el servidor. La base SQLite vive en el servidor y no se versiona. El repositorio todavía no tiene remoto; el bot de finanzas se publicó clonando su repositorio público de GitHub en el servidor. Incluir la guía de despliegue y de actualización paso a paso para alwaysdata."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Usar el bot en producción con la computadora apagada (Priority: P1)

El dueño usa desde el iPhone el bot de producción, que vive en su cuenta de alwaysdata. Todas las
funciones de la feature 001 (registrar citas, altas, deshacer, consultar tarjetas y clientes)
responden igual que en las pruebas, aunque su computadora esté apagada y aunque el bot haya estado
inactivo un rato.

**Why this priority**: es el objetivo de la feature: dejar de depender de la computadora para
atender a los clientes.

**Independent Test**: con el bot publicado y la computadora apagada, recorrer desde el iPhone la
tabla de validación de la feature 001 contra el bot de producción.

**Acceptance Scenarios**:

1. **Dado** el bot publicado y la computadora del dueño apagada, **Cuando** el dueño registra una
   cita, **Entonces** recibe la tarjeta como foto, igual que en las pruebas de la feature 001.
2. **Dado** que el bot no recibió mensajes durante más del tiempo de inactividad del sitio,
   **Cuando** el dueño envía un comando, **Entonces** el bot despierta y responde sin que el dueño
   tenga que repetir el comando.
3. **Dado** que el dueño envió un comando mientras el bot se reiniciaba, **Cuando** el bot vuelve a
   estar disponible, **Entonces** el comando se procesa y la cita queda con la hora en que se envió.
4. **Dado** un botón enviado antes de que el bot se durmiera o reiniciara, **Cuando** el dueño lo
   pulsa, **Entonces** el bot avisa que la acción caducó y no aplica ningún efecto.
5. **Dado** el bot publicado, **Cuando** alguien envía a su dirección una petición que no viene de
   Telegram (sin el token secreto correcto), **Entonces** se rechaza sin procesar nada.
6. **Dado** el bot de finanzas funcionando en la misma cuenta, **Cuando** el bot de tarjetas se
   publica, se reinicia o se duerme, **Entonces** el bot de finanzas sigue respondiendo igual.

---

### User Story 2 - Seguir probando en la computadora sin tocar producción (Priority: P2)

En su computadora, el dueño sigue usando el bot de pruebas exactamente como hoy. El mismo código
funciona en ambos lugares y solo cambia la configuración. Si por error intenta arrancar en su
computadora un bot que ya está publicado en el servidor, el bot se niega y le explica por qué.

**Why this priority**: permite seguir probando cambios antes de publicarlos sin riesgo para el bot
de producción.

**Independent Test**: arrancar el bot en la computadora sin la dirección del webhook configurada y
comprobar que funciona como en la feature 001; luego intentar arrancarlo con el bot de producción y
comprobar que se niega.

**Acceptance Scenarios**:

1. **Dado** que la configuración local no indica una dirección de webhook, **Cuando** el dueño
   arranca el bot en su computadora, **Entonces** funciona como en la feature 001 con el bot de
   pruebas.
2. **Dado** que el bot configurado tiene un webhook activo en el servidor, **Cuando** el dueño lo
   arranca en su computadora, **Entonces** el bot se niega a arrancar, explica que ya corre en el
   servidor y no modifica nada de producción.
3. **Dado** el mismo código, **Cuando** se arranca con la configuración de producción o con la
   local, **Entonces** el comportamiento de los comandos es idéntico; solo cambia cómo llegan los
   mensajes.

---

### User Story 3 - Publicar y actualizar siguiendo una guía (Priority: P2)

El dueño publica el bot por primera vez y, más adelante, publica versiones nuevas siguiendo una guía
paso a paso. La guía incluye cómo comprobar que quedó en marcha y cómo volver a la versión anterior
si algo sale mal. Los datos de clientes y citas nunca se pierden al actualizar.

**Why this priority**: sin una guía repetible, cada publicación depende de recordar pasos sueltos y
es fácil romper producción o perder datos.

**Independent Test**: seguir la guía desde cero en la cuenta de alwaysdata y luego publicar un
cambio menor, comprobando que los clientes registrados siguen igual.

**Acceptance Scenarios**:

1. **Dado** la cuenta de alwaysdata con el bot de finanzas, **Cuando** el dueño sigue la guía de
   primera publicación, **Entonces** el bot de producción responde `/ayuda` desde el iPhone.
2. **Dado** el bot publicado, **Cuando** el dueño abre la dirección del bot en un navegador,
   **Entonces** ve una confirmación simple de que está en marcha, sin ningún dato de clientes.
3. **Dado** clientes y citas registrados en producción, **Cuando** el dueño publica una versión nueva
   siguiendo la guía, **Entonces** el bot corre la versión nueva y los clientes y citas no cambian.
4. **Dado** que una versión nueva falla, **Cuando** el dueño sigue los pasos para volver a la
   versión anterior, **Entonces** el bot vuelve a funcionar sin pérdida de datos.

---

### Edge Cases

- **Telegram entrega el mismo mensaje más de una vez** (por ejemplo, porque el bot tardó en
  despertar): se procesa una sola vez; no se registran citas duplicadas.
- **Llegan varios mensajes casi al mismo tiempo**: se procesan de uno en uno y en orden, así que
  la garantía de "un toque, un efecto" de la feature 001 se mantiene.
- **La dirección del webhook configurada no es HTTPS**: el bot no arranca y explica que Telegram
  exige HTTPS.
- **Falta el token secreto o no cumple el formato que acepta Telegram** (en modo webhook): el bot no
  arranca y explica cómo generar uno válido.
- **El bot de producción se duerme**: las acciones pendientes de los botones se pierden y caducan;
  los datos (clientes y citas) no se ven afectados.
- **El servidor del alojamiento usa otra zona horaria**: las fechas se siguen registrando y mostrando
  en la zona del negocio (ya configurable desde la feature 001).
- **La memoria de la cuenta es limitada y la comparte con el bot de finanzas**: el bot de tarjetas
  debe caber sin provocar que alguno de los dos se detenga.
- **Se cambia el token del bot o el token secreto**: al reiniciar, el bot vuelve a registrar su
  dirección con los valores nuevos.

## Requirements *(mandatory)*

### Functional Requirements

**Modos de ejecución**

- **FR-001**: El sistema MUST elegir el modo por configuración, sin cambios de código: modo webhook
  si está configurada la dirección del webhook; modo polling si no.
- **FR-002**: Todas las funciones de la feature 001 MUST comportarse igual en ambos modos: mismos
  comandos, textos, tarjetas y reglas de datos.
- **FR-003**: El filtro "solo responde al dueño" de la feature 001 MUST aplicarse en ambos modos.

**Modo webhook (producción)**

- **FR-004**: El sistema MUST recibir los mensajes de Telegram únicamente en la dirección HTTPS
  configurada. Si la dirección no empieza con `https://`, MUST negarse a arrancar con un mensaje
  claro.
- **FR-005**: El sistema MUST escuchar en la IP y el puerto que el alojamiento indica mediante
  variables de entorno.
- **FR-006**: Cada petición entrante MUST traer el token secreto configurado. Las que no lo traigan,
  o traigan uno distinto, MUST rechazarse sin procesar nada y anotarse en el registro de eventos.
- **FR-007**: El token secreto MUST configurarse fuera del código y cumplir el formato que acepta
  Telegram (de 16 a 256 caracteres; solo letras, dígitos, "_" y "-"). Si falta o no lo cumple, el
  sistema MUST negarse a arrancar en modo webhook y explicar cómo generar uno.
- **FR-008**: Al arrancar en modo webhook, el sistema MUST registrar (o actualizar) ante Telegram su
  dirección y su token secreto, sin descartar los mensajes pendientes. Esos mensajes se procesan con
  su fecha original, como en la feature 001.
- **FR-009**: Cada mensaje o toque de botón MUST procesarse como máximo una vez, aunque Telegram lo
  entregue varias veces.
- **FR-010**: Los mensajes MUST procesarse de uno en uno y en el orden en que llegan.
- **FR-011**: Al abrir la dirección del bot en un navegador, el sistema MUST responder una
  confirmación simple de que está en marcha (por ejemplo, "ok"), sin datos de clientes ni de
  configuración.
- **FR-012**: Desde que despierta, el sistema MUST estar listo para responder en menos de 10
  segundos.

**Modo polling (computadora del dueño)**

- **FR-013**: Al arrancar en modo polling, si el bot configurado tiene un webhook activo, el sistema
  MUST negarse a arrancar, explicar que ese bot ya corre en el servidor y no modificar el webhook.

**Convivencia y recursos en alwaysdata**

- **FR-014**: El bot MUST publicarse en una dirección propia dentro de la cuenta del dueño, gratuita y
  distinta de la del bot de finanzas, sin modificar el sitio, la configuración ni los datos del bot
  de finanzas.
- **FR-015**: El bot MUST funcionar con los recursos del plan Free compartidos con el bot de
  finanzas: menos de 120 MB de memoria en uso normal, de modo que con el bot de finanzas (~77 MB)
  la cuenta quede por debajo de 200 MB de sus 256 MB, y menos de 300 MB de disco en total
  (programa, dependencias y base de datos de un año de uso).

**Datos**

- **FR-016**: La base de datos de producción MUST vivir en el servidor, fuera del control de
  versiones, en una ubicación configurada en el servidor. Publicar versiones nuevas, reiniciar o
  dormir el sitio MUST NOT alterarla.
- **FR-017**: La base de producción MUST empezar vacía. Los datos de prueba de la computadora del
  dueño no se copian; los clientes reales se registran con `/alta` (feature 001).

**Guía de publicación**

- **FR-018**: El proyecto MUST incluir una guía paso a paso para la primera publicación en
  alwaysdata (plan Free). La guía cubre:
  - requisitos previos;
  - cómo llevar el código al servidor: clonando el repositorio **público** del proyecto en GitHub,
    como el bot de finanzas, y actualizándolo con `git pull`;
  - instalación de dependencias;
  - configuración de producción;
  - creación del sitio en el panel;
  - comprobación final (navegador y `/ayuda` desde el iPhone).
- **FR-019**: La guía MUST incluir cómo publicar una versión nueva en menos de 5 minutos, cómo ver los
  registros del bot en el servidor y cómo volver a la versión anterior.
- **FR-020**: La guía MUST incluir cómo cambiar el token del bot o el token secreto, y cómo volver a
  usar el bot de producción en modo polling si algún día se deja de usar alwaysdata.

### Key Entities

- **Configuración de producción**: valores que viven solo en el servidor, nunca en el repositorio.
  Son el token del bot de producción, el ID del dueño, la zona horaria, las citas por tarjeta, la
  dirección del webhook, el token secreto y la ubicación de la base de datos.
- **Sitio del bot en alwaysdata**: la entrada del panel que arranca el bot. Tiene su dirección,
  el comando de arranque, la carpeta de trabajo y el tiempo de inactividad antes de dormirse.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Con la computadora del dueño apagada, el 100 % de los pasos de la tabla de validación
  de la feature 001 funcionan contra el bot de producción.
- **SC-002**: Con el bot despierto, la foto de la tarjeta llega en menos de 5 segundos en el 95 % de
  los casos (igual que en la feature 001).
- **SC-003**: Tras un periodo de inactividad, la primera respuesta llega en menos de 15 segundos.
- **SC-004**: Ningún mensaje entregado varias veces por Telegram produce citas duplicadas.
- **SC-005**: Ninguna petición sin el token secreto correcto produce un efecto en los datos ni una
  respuesta en Telegram.
- **SC-006**: El bot de finanzas no tiene interrupciones atribuibles a la publicación ni al
  funcionamiento del bot de tarjetas.
- **SC-007**: La primera publicación siguiendo la guía toma menos de 45 minutos y cada actualización
  menos de 5 minutos.
- **SC-008**: Después de cada actualización, los clientes y citas de producción son idénticos a los
  de antes.

## Assumptions

- **Acceso**: el dueño tiene acceso SSH a su cuenta de alwaysdata (ya lo usa para el bot de
  finanzas). La guía usa `CUENTA` en lugar del nombre real de la cuenta.
- **Dos bots en Telegram**: producción usa el bot de producción que el dueño ya creó; la computadora
  sigue usando el bot de pruebas. Nunca comparten token.
- **Tiempo de inactividad**: se deja el valor por defecto del sitio (el bot se duerme tras 30
  minutos sin mensajes). Si la primera respuesta tras una pausa resulta lenta, el dueño puede
  configurar que no se duerma, siempre que la memoria de la cuenta alcance para ambos bots.
- **Botones tras dormir**: los botones de confirmación caducan si el bot se durmió o se reinició
  antes de pulsarlos; el dueño repite el comando (mismo comportamiento que la feature 001 ante un
  reinicio).
- **Repositorio público** (decisión del dueño, 2026-11-16): el código, la documentación y los
  assets del proyecto, incluida la tarjeta de ejemplo, quedan públicos en GitHub. Los secretos
  (`.env`) y las bases de datos nunca se versionan (principio V).
- **Plan Free**: alwaysdata describe el plan Free como "para necesidades personales". El dueño
  decidió usarlo para este bot del negocio conociendo esa descripción (2026-11-16).
- **Dirección**: el bot usa una dirección gratuita `*.alwaysdata.net` propia. Que sea una ruta dentro
  de la dirección principal de la cuenta o un subdominio se decide en el plan, según lo que permita
  el panel de alwaysdata.
- **Fuera de alcance**:
  - copias de seguridad automáticas de la base;
  - monitoreo y alertas;
  - dominio propio;
  - publicación automática (CI/CD);
  - entornos adicionales además de "computadora" y "producción";
  - migrar datos de prueba a producción.
