# Research: Personas autorizadas para usar el bot

**Feature**: `003-usuarios-autorizados` | **Fecha**: 2026-11-16

Parte del código de la feature 002: python-telegram-bot 22, el filtro del dueño en
`bot/seguridad.py` y `Ajustes` en `config.py`. No hay incógnitas abiertas en el contexto técnico.
Estas son las decisiones.

## 1. Configuración de las personas autorizadas

- **Decision**:
  - se mantiene `OWNER_ID` y se agrega `AUTORIZADOS`, opcional: IDs separados por comas
    (`AUTORIZADOS=111111111,222222222`), con espacios permitidos;
  - en `Ajustes`, el campo es `autorizados: Annotated[frozenset[int], NoDecode]` con un
    `field_validator(mode="before")` que separa por comas;
  - un valor que no es un entero produce `ValidationError` con el valor inválido y el formato
    esperado (FR-006); los elementos vacíos (por ejemplo, una coma al final) se ignoran;
  - la propiedad `ids_autorizados = {owner_id} | autorizados`: el dueño siempre está incluido
    (FR-002) y los duplicados se colapsan;
  - al arrancar, el log dice `Personas autorizadas: N` (cuántas, nunca sus IDs), para confirmar
    después de un reinicio que se leyó la configuración.
- **Rationale**:
  - un `.env` con solo `OWNER_ID` sigue funcionando sin cambios (FR-002, SC-005);
  - la coma es lo natural de escribir a mano en el servidor;
  - verificado con pydantic-settings 2.16.3: `NoDecode` evita que intente leer la variable como
    JSON;
  - `""` → vacío; `"111, 222,111"` → `{111, 222}`; `"111,abc"` → `ValidationError`.
- **Alternatives considered**: JSON (`[111,222]`), propenso a errores al editar a mano; renombrar
  `OWNER_ID` a una lista, que rompería la configuración existente; una tabla en la base de datos,
  descartada por la spec (cambios solo por configuración).

## 2. Filtro de acceso

- **Decision**: `crear_filtro_dueno(owner_id)` pasa a `crear_filtro(autorizados: frozenset[int])`.
  Sigue registrado como `TypeHandler(Update, …)` en el grupo -1 y lanza `ApplicationHandlerStop`
  para las cuentas no autorizadas. `crear_aplicacion` recibe `autorizados` en lugar de `owner_id`,
  y `main()` le pasa `ajustes.ids_autorizados`.
- **Rationale**: un único punto de control, igual que en las features 001 y 002.
- **Registro** (FR-004, principio V): todo lo que llega de una cuenta no autorizada se anota con
  nivel `WARNING`, con el ID, el usuario y el tipo de chat (`chat=privado` o `chat=grupo`):
  mensajes, comandos, avisos y toques de botón, en privado o en grupos.
- **Alternatives considered**:
  - `filters.User(user_id=...)` en cada handler (tantos puntos de control como handlers);
  - anotar con `WARNING` solo los *intentos* de uso (comandos, botones, mensajes privados) y la
    conversación de un grupo con `DEBUG`: descartado porque con `LOG_LEVEL=INFO` esas cuentas no
    quedarían en el log, y el principio V exige registrarlas. El ruido es acotado: el principio V
    pide agregar el bot solo a grupos de confianza, donde casi todos estarán autorizados.
- **Administradores anónimos**: un administrador que escribe como anónimo llega con la cuenta
  compartida `GroupAnonymousBot` (no con la suya), así que el filtro lo ignora. Esa cuenta nunca se
  autoriza: autorizaría a cualquier administrador anónimo de cualquier grupo donde esté el bot. Por
  eso la guía pide que la persona escriba **en privado** al bot para obtener su ID, y advierte
  sobre `GroupAnonymousBot`.

## 3. Grupos: solo comandos y botones

- **Decision**:
  - el handler de texto que no es comando (`sin_comando`) pasa a
    `MessageHandler(filters.ChatType.PRIVATE, sin_comando)`;
  - en grupos no hay handler para la conversación normal ni para los avisos del grupo, que se
    ignoran (FR-008, SC-003);
  - el resto de handlers no cambia: `CommandHandler` ya acepta `/cita@NombreDelBot` y descarta
    `/cita@OtroBot`; las respuestas van al chat de origen con `reply_text`/`reply_photo`
    (FR-007).
- **Rationale**: es un cambio de una línea con un efecto grande: un bot administrador del grupo
  recibe todos los mensajes, y hoy contestaría "Usa /ayuda…" a cada uno.
- **Nota**: con el modo de privacidad activo, que es lo predeterminado, Telegram solo entrega al
  bot los comandos y las respuestas a sus mensajes. Si es administrador, recibe todo. El diseño
  funciona igual en ambos casos.

## 4. Botones compartidos

- **Decision**: sin cambios en el registro de acciones pendientes. Cualquier persona autorizada
  puede pulsar un botón, aunque lo haya pedido otra, y el `pop` del registro garantiza un solo
  efecto (FR-005). Un toque de una cuenta no autorizada lo frena el filtro del grupo -1 antes de
  llegar a `al_pulsar`, así que la acción sigue disponible.
- **Rationale**: todas las personas autorizadas tienen los mismos permisos (FR-003).

## 5. Quién hizo cada acción (FR-010)

- **Decision**: las funciones internas que cambian datos reciben un parámetro explícito
  `autor: int`: `_registrar`, `_crear_y_registrar`, `_crear_alta` y `_deshacer`, y en la cadena
  `_resolver` → `_continuar`. Los handlers lo toman de `update.effective_user.id`. Las líneas de
  log quedan:
  - `Cita registrada: cliente=… premio=… usuario=…`;
  - `Alta: cliente=… previas=… usuario=…`;
  - `Cita anulada: cliente=… premio=… usuario=…`.
- **Rationale**: en un toque de botón, el `Message` que llega es el mensaje del bot; el autor real
  es `update.effective_user`. Pasarlo explícitamente es claro y fácil de probar.
- **Alternatives considered**: un `contextvar` que fije el filtro (implícito; las pruebas
  unitarias que llaman handlers sin el filtro registrarían `None`); guardar el autor en la tabla
  `citas` (fuera de alcance según la spec).

## 6. Despliegue

- **Decision**: sin cambios en el modo webhook. Publicar la 003 equivale a una actualización
  (README, «Actualizar»), más agregar `AUTORIZADOS=…` al `.env` del servidor y reiniciar el sitio.
- **Dependencia**: la rama 003 sale de la 002, todavía sin integrar. Orden de integración: 002 →
  `main` (cuando termine su T033), luego 003 → `main`. El servidor, que hoy sigue la rama 002,
  pasa a `main`.

## 7. Pruebas

- **Configuración**: `AUTORIZADOS` vacío, uno, varios con espacios y duplicados, inválido; el
  dueño siempre incluido.
- **Filtro**: una segunda cuenta autorizada pasa; una no autorizada que escribe en privado, que
  envía un comando o conversa en un grupo, o que pulsa un botón → `ApplicationHandlerStop` y
  `WARNING` con el tipo de chat correspondiente.
- **Integración** (aplicación real y `FakeTelegramAPI`):
  - la segunda persona registra una cita y confirma un botón que pidió el dueño;
  - en grupo, el texto normal no recibe respuesta y `/ayuda@tarjeta_bot` sí;
  - un aviso de miembro nuevo no recibe respuesta;
  - un no autorizado que pulsa un botón no tiene efecto y el botón sigue funcionando para el
    dueño.
- **Log**: las acciones registran `usuario=<id>` de quien las hizo.
