---

description: "Lista de tareas para publicar el bot en alwaysdata (plan Free) con webhook"
---

# Tasks: Publicación en alwaysdata (plan Free) con webhook

**Input**: Design documents from `specs/002-despliegue-webhook-alwaysdata/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: OBLIGATORIOS (constitución, principio III).
- **Dominio** (`conteo`, `busqueda`, `render`, `db`, `servicio`, `diseno`): no cambia, y sus
  pruebas deben seguir en verde sin tocarlas.
- **Lo nuevo** (configuración, servidor web, registro de updates, resguardo de polling): se escribe
  con prueba primero.
- **Capa de Telegram**: sus pruebas se reescriben para python-telegram-bot antes de reescribir el
  código.

**Organization**:
- la Fase 2 cambia la librería de Telegram (lo necesitan ambos modos);
- luego, una fase por historia: US1 (modo webhook), US2 (resguardo de polling), US3 (guía y
  publicación).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: puede ejecutarse en paralelo (archivo distinto, sin depender de tareas incompletas).
- **[Story]**: historia de usuario de la tarea (US1…US3).

## Convenciones para todas las tareas

- **Comportamiento**: los textos, botones y flujos de la feature 001 no cambian
  ([contrato de comandos](../001-registro-citas-tarjeta/contracts/comandos-bot.md)); solo cambia la
  librería.
- **HTTP y configuración**: [contracts/webhook-http.md](contracts/webhook-http.md) y
  [contracts/configuracion.md](contracts/configuracion.md).
- **Nada de `telegram`, `starlette`, `uvicorn` ni `aiogram`** en los módulos de dominio
  (principio II).
- **Repositorio público**: ningún archivo versionado lleva tokens, el ID del dueño ni el nombre real
  de la cuenta de alwaysdata (se usa `CUENTA`).
- **Ejecución**: siempre con `uv run …`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: cambiar las dependencias y separar las fixtures del dominio de las de Telegram.

- [X] T001 En `pyproject.toml`:
  - quitar `aiogram` de `dependencies`;
  - agregar `"python-telegram-bot>=22.8,<23"`, `"starlette>=1.10,<2"` y `"uvicorn>=0.54,<1"`.

  Después, ejecutar `uv lock` y `uv sync` y comprobar que `uv pip list` ya no muestra `aiogram` ni
  `aiohttp`. A partir de aquí, mypy y las pruebas de `tests/bot/` quedan en rojo hasta terminar la
  Fase 2. Las del dominio (`tests/unit`, salvo `test_arquitectura`, y `tests/integration`) deben
  seguir en verde.
- [X] T002 [P] Agregar a `.env.example`, comentadas y con una línea de explicación:
  - `WEBHOOK_URL` (solo en el servidor; ejemplo `https://CUENTA.alwaysdata.net/tarjeta/telegram`);
  - `WEBHOOK_SECRET` (solo en el servidor; cómo generarlo);
  - una nota de que alwaysdata entrega `IP` y `PORT`.

  Según [contracts/configuracion.md](contracts/configuracion.md).
- [X] T003 Mover de `tests/conftest.py` a un nuevo `tests/bot/conftest.py` las fixtures de Telegram
  (`acciones`, `mensaje_falso`, `callback_falso`, `botones`). En `tests/conftest.py` quedan solo
  las del dominio (`zona`, `utc`, `sesiones`, `servicio`). Las fixtures movidas se reescriben en
  T004.

**Checkpoint**: `uv run pytest tests/integration tests/unit/test_conteo.py tests/unit/test_busqueda.py tests/unit/test_render.py tests/unit/test_config.py` en verde.

---

## Phase 2: Foundational (capa de Telegram sobre python-telegram-bot)

**Purpose**: el bot funciona en polling exactamente como en la feature 001, pero sobre
python-telegram-bot. Ambos modos dependen de esto.

**⚠️ CRITICAL**: ninguna historia empieza hasta terminar esta fase.

### Pruebas (escribir/reescribir primero; deben FALLAR)

- [X] T004 Reescribir `tests/bot/conftest.py` para python-telegram-bot ([research §9](research.md#9-adaptación-de-la-capa-de-telegram)). Fixtures:
  - `mensaje_falso(texto, fecha, user_id=1)`: `MagicMock(spec=telegram.Message)` con `text`,
    `date`, `chat_id`, `from_user` y `AsyncMock` en `reply_text`, `reply_photo` y `edit_text`;
  - `update_falso(mensaje)`: `MagicMock` con `update_id`, `message`, `effective_message`,
    `effective_user` (id y username) y `callback_query=None`;
  - `callback_falso(data, mensaje)`: un update cuyo `callback_query` tiene `data`,
    `message=mensaje` y `answer` (`AsyncMock`);
  - `contexto_falso(servicio, acciones, args=None)`: `MagicMock` con `args` (lista) y
    `bot_data={"servicio": ..., "acciones": ...}`;
  - `botones(llamada)`: lista de `(texto, callback_data)` del `reply_markup` de la última
    llamada;
  - `FakeTelegramAPI(BaseRequest)`, con el patrón del bot de finanzas:
    - registra `(método, parámetros)`;
    - responde `getMe`, `sendMessage`, `sendPhoto` y `editMessageText` con JSON válido;
    - `getWebhookInfo` devuelve `{"url": self.webhook_url}` (configurable, `""` por defecto);
    - cualquier otro método devuelve `true`.
- [X] T005 [P] Reescribir `tests/bot/test_acciones.py`:
  - `empaquetar("tok", "nuevo") == "a:tok:nuevo"`;
  - `desempaquetar` hace el viaje de ida y vuelta, y devuelve `None` para `"x"`, `"a:solo"` y
    `"b:t:o"`;
  - el texto empaquetado mide ≤ 64 bytes con un token real y un ID de 6 dígitos;
  - `tomar` devuelve la acción una sola vez;
  - los tokens no se repiten en 1 000 registros;
  - se descarta la acción más antigua al pasar de `MAXIMO_PENDIENTES`.
- [X] T006 [P] Reescribir `tests/bot/test_seguridad.py` para el filtro del dueño que devuelve
  `crear_filtro_dueno(owner_id)`:
  - con el dueño no lanza nada;
  - con otra cuenta lanza `ApplicationHandlerStop` y registra un `WARNING` con el ID y el usuario;
  - un update sin `effective_user` también lanza `ApplicationHandlerStop`.
- [X] T007 [P] Portar `tests/bot/test_handlers_cita.py` a las fixtures nuevas con los **mismos
  escenarios** de la 001:
  - sin argumento → `uso("cita")`;
  - cliente existente → `reply_photo` con el pie exacto;
  - cliente nuevo → `Crear` y `Cancelar`; al confirmar, la cita lleva la fecha del comando
    original;
  - cancelar; doble toque; mismo día;
  - parecidos con `Crear «Carmn»`; nombre inválido sin `Crear`;
  - fallo de envío; premio con 9 flores; homónimos; `#id`; `#999`.

  Los handlers se llaman como `await handlers.cmd_cita(update, contexto)` y
  `await handlers.al_pulsar(update, contexto)`.
- [X] T008 [P] Portar `tests/bot/test_handlers_alta.py` con los mismos escenarios, incluido
  `separar_alta`.
- [X] T009 [P] Portar `tests/bot/test_handlers_deshacer.py` con los mismos escenarios, incluido "la
  última cita cambió".
- [X] T010 [P] Portar `tests/bot/test_handlers_consultas.py` con los mismos escenarios, incluida la
  lista dividida en varios mensajes.
- [X] T011 [P] Crear `tests/bot/test_integracion_app.py` y borrar
  `tests/bot/test_integracion_dispatcher.py`. Con
  `crear_aplicacion(servicio, owner_id=5221, token="42:PRUEBA", request=FakeTelegramAPI(), con_updater=False)`
  y `async with aplicacion:`, alimentar `Update.de_json(...)` por `process_update` y comprobar:
  - un intruso no provoca ninguna llamada `send*`;
  - `/ayuda` y un texto libre responden;
  - `/cita Lucía` → botón `Crear` → update de callback → `sendPhoto` con el pie esperado; un
    segundo toque → "ya se aplicó o caducó";
  - `/alta Rosa 6`, `/tarjeta #1`, `/clientes` y `/deshacer rosa` reciben sus argumentos.
- [X] T012 [P] Ampliar `tests/unit/test_arquitectura.py`: ningún módulo fuera de `bot/` importa
  `aiogram`, `telegram`, `starlette` ni `uvicorn`.

### Implementación

- [X] T013 [P] Reescribir `src/tarjeta_lealtad/bot/acciones.py` sin aiogram:
  - quitar `AccionCB`;
  - agregar `PREFIJO = "a"`, `empaquetar(token, opcion) -> str` y
    `desempaquetar(data) -> tuple[str, str] | None` (formato `"a:<token>:<opción>"`, ≤ 64 bytes,
    [data-model](data-model.md#datos-del-botón));
  - conservar `Accion`, `AccionesPendientes` y sus tipos.
- [X] T014 [P] Reescribir `src/tarjeta_lealtad/bot/seguridad.py`: `crear_filtro_dueno(owner_id)`
  devuelve un callback asíncrono `(update, context)` que, si el remitente no es el dueño, registra
  un `WARNING` (ID y usuario) y lanza `ApplicationHandlerStop`. Se registra como
  `TypeHandler(Update, ...)` en el grupo `-1`.
- [X] T015 Portar `src/tarjeta_lealtad/bot/handlers.py` a python-telegram-bot, después de T013 y
  T014, conservando los mismos flujos y textos:
  - **Firma y datos**: los callbacks son `(update, context)`. `servicio` y `acciones` salen de
    `context.bot_data`; el mensaje, de `update.effective_message`; el texto del comando, de
    `" ".join(context.args or [])`.
  - **Respuestas**: `reply_text` y `reply_photo(photo=png, caption=pie)`; teclados con
    `InlineKeyboardMarkup` y `callback_data=empaquetar(...)`.
  - **Toques de botón**: `al_pulsar` hace `query.answer()`, usa `query.message` (si no es un
    `Message`, termina), `desempaquetar(query.data)` y `acciones.tomar`.
  - **Anotar la elección**: `_anotar` edita el mensaje con `edit_text` e ignora
    `telegram.error.BadRequest`.
  - **Errores**: `al_fallar(update, context)` registra `context.error` y responde
    `ERROR_INESPERADO` si hay mensaje.
  - **Registro**: `registrar_handlers(application)` agrega, en este orden:
    1. `CommandHandler` para `start`/`ayuda`, `cita`, `alta`, `deshacer`, `tarjeta` y `clientes`;
    2. `CallbackQueryHandler(al_pulsar, pattern=r"^a:")`;
    3. `MessageHandler(filters.ALL, sin_comando)`, el último;
    4. el error handler.
  - Actualizar el docstring de `src/tarjeta_lealtad/bot/__init__.py`.
- [X] T016 Reescribir `src/tarjeta_lealtad/bot/app.py`, después de T015:
  - `crear_aplicacion(servicio, owner_id, token, *, request=None, con_updater=True) -> Application`:
    - `ApplicationBuilder` con `request`/`get_updates_request`, si se pasan, y `.updater(None)` si
      `con_updater` es falso;
    - `bot_data["servicio"]` y `bot_data["acciones"] = AccionesPendientes()`;
    - `TypeHandler` del dueño en el grupo -1;
    - `registrar_handlers`.
  - `COMANDOS` (lista de `BotCommand` a partir de `textos.COMANDOS`).
  - `main()` conserva configuración, `verificar_diseno`, assets y base, y por ahora siempre usa
    polling: `run_polling(drop_pending_updates=False, allowed_updates=["message", "callback_query"])`,
    con un `post_init` que registra los comandos y anota "modo polling".
- [X] T017 Correr los gates de `pyproject.toml` (`uv run ruff check`, `uv run ruff format --check`,
  `uv run mypy`, `uv run pytest`) y dejarlos en verde. Probar a mano el bot de pruebas con
  `uv run python -m tarjeta_lealtad` (código en `src/tarjeta_lealtad/bot/`): `/ayuda`, `/cita` con
  su botón y `/deshacer` se comportan como en la 001.

**Checkpoint**: el bot funciona igual que en la 001 sobre python-telegram-bot.

---

## Phase 3: User Story 1 - Usar el bot en producción con la computadora apagada (Priority: P1) 🎯 MVP

**Goal**: modo webhook listo para alwaysdata:
- configuración validada;
- servidor Starlette en `$IP:$PORT`;
- token secreto;
- procesamiento en serie y una sola vez;
- "ok" en GET;
- registro del webhook al arrancar.

**Independent Test**: las pruebas de `test_web.py` y `test_config.py` en verde. Tras publicar
(Fase 5), la tabla de producción de [quickstart §3](quickstart.md#3-validación-en-producción) con
la computadora apagada.

### Tests for User Story 1 ⚠️ (escribir primero; deben FALLAR)

- [X] T018 [P] [US1] Ampliar `tests/unit/test_config.py`:
  - sin `WEBHOOK_URL` → `modo == "polling"`;
  - con `WEBHOOK_URL=https://…` y un `WEBHOOK_SECRET` válido → `modo == "webhook"`;
  - `WEBHOOK_URL=http://…` → `ValidationError` con "https://";
  - con URL pero sin secreto, o con un secreto de 15 caracteres o con caracteres fuera de
    `[A-Za-z0-9_-]` → `ValidationError` que menciona `secrets.token_urlsafe`;
  - `IP`/`PORT` por defecto `127.0.0.1`/`8000`, y se leen de las variables `IP` y `PORT`.
- [X] T019 [P] [US1] Crear `tests/bot/test_web.py`:
  - **Registro de updates** (`RegistroDeUpdates`): `registrar(5)` es verdadero la primera vez y
    falso la segunda; al pasar de la capacidad, el más antiguo se olvida.
  - **Arranque** (`TestClient` como contexto, con `crear_app_web(aplicacion, webhook_url,
    webhook_secret)` y `FakeTelegramAPI`): el *lifespan* llama `setWebhook` con `url`,
    `secret_token`, `max_connections=1`, `allowed_updates=["message","callback_query"]` y
    `drop_pending_updates=False`, y luego `setMyCommands`.
  - **Token secreto**: un POST sin encabezado o con otro valor → 403, sin llamadas `send*` y con
    un `WARNING` que no contiene el valor.
  - **Cuerpo**: inválido → 400; un update `/ayuda` válido del dueño → 200 y `sendMessage`.
  - **Duplicados**: el mismo `update_id` dos veces → una sola respuesta del bot.
  - **Rutas y métodos**: GET a `/`, `/tarjeta` y `/tarjeta/telegram` → 200 `ok`; un PUT → 405;
    un POST válido a `/telegram` y a `/tarjeta/telegram` se procesa (cualquier ruta).
  - **Dueño**: un update de otra cuenta → 200 sin respuesta del bot.
  - **Serie**: con `httpx.AsyncClient(transport=ASGITransport(app))` dentro de
    `app.router.lifespan_context(app)` y un `process_update` lento simulado, dos POST simultáneos
    no se solapan.

### Implementation for User Story 1

- [X] T020 [US1] En `src/tarjeta_lealtad/config.py`:
  - agregar `webhook_url: str | None = None`, `webhook_secret: SecretStr | None = None`,
    `ip: str = "127.0.0.1"` y `port: int = 8000`;
  - un validador que, con URL, exija `https://` y un secreto con `^[A-Za-z0-9_-]{16,256}$`, con los
    mensajes de [contracts/configuracion.md](contracts/configuracion.md);
  - la propiedad `modo` (`"polling"` o `"webhook"`).
- [X] T021 [US1] Crear `src/tarjeta_lealtad/bot/web.py`, después de T020, según
  [contracts/webhook-http.md](contracts/webhook-http.md):
  - `RegistroDeUpdates(capacidad=1000)` con `registrar(update_id) -> bool`;
  - `crear_app_web(application, webhook_url, webhook_secret) -> Starlette`:
    - **lifespan**: `async with application`, luego `set_webhook(...)` con los parámetros del
      contrato y `set_my_commands(COMANDOS)`, y anota "webhook registrado";
    - **POST `/{ruta:path}`**:
      - el token se compara con `hmac.compare_digest`: si falla, 403 y `WARNING`;
      - el cuerpo pasa por `Update.de_json`: si no es válido, 400;
      - si el `update_id` ya se procesó, responde 200 sin procesar;
      - si no, `async with lock: await application.process_update(update)` y responde 200.
    - **GET `/{ruta:path}`**: `PlainTextResponse("ok")`.
- [X] T022 [US1] En `src/tarjeta_lealtad/bot/app.py`, `main()` elige el modo con `ajustes.modo`:
  - **webhook**: `crear_aplicacion(..., con_updater=False)`, `crear_app_web(...)` y
    `uvicorn.run(app_web, host=ajustes.ip, port=ajustes.port, access_log=False)`;
  - en el log: "modo webhook en IP:PORT".
- [X] T023 [US1] Medir la memoria (FR-015) de `src/tarjeta_lealtad/bot/web.py` con el procedimiento
  de `quickstart.md` §1: un script temporal en el scratchpad con `FakeTelegramAPI`; **nunca** se
  arranca el modo webhook en local. Debe quedar < 120 MB. Anotar la cifra en
  `specs/002-despliegue-webhook-alwaysdata/research.md` §2.
- [X] T024 [US1] Correr los gates de `pyproject.toml` y dejarlos en verde.

**Checkpoint**: el modo webhook está listo y probado sin red.

---

## Phase 4: User Story 2 - Seguir probando en la computadora sin tocar producción (Priority: P2)

**Goal**: en polling, si el bot ya tiene un webhook, no arranca y no lo borra (FR-013).

**Independent Test**: `test_app.py` en verde. Tras publicar, la fila 8 de
[quickstart §3](quickstart.md#3-validación-en-producción).

### Tests for User Story 2 ⚠️

- [X] T025 [P] [US2] Crear `tests/bot/test_app.py`:
  - `verificar_sin_webhook(aplicacion)` con `FakeTelegramAPI(webhook_url="https://x")` → `SystemExit(1)`,
    un `ERROR` con "ya corre en el servidor" y **ninguna** llamada `deleteWebhook`;
  - con `webhook_url=""` → no lanza;
  - selección de modo en `main()` (entorno con `monkeypatch`, `DB_PATH` en `tmp_path`, y
    `Application.run_polling` y `uvicorn.run` sustituidos por registros):
    - sin `WEBHOOK_URL` → `run_polling` con `drop_pending_updates=False`;
    - con `WEBHOOK_URL` → `uvicorn.run` con `host`/`port` de la configuración.

### Implementation for User Story 2

- [X] T026 [US2] En `src/tarjeta_lealtad/bot/app.py`:
  - agregar `async def verificar_sin_webhook(application)`, que usa `get_webhook_info()`; si hay URL,
    registra el mensaje de [contracts/configuracion.md](contracts/configuracion.md) y hace
    `sys.exit(1)`;
  - encadenarla en el `post_init` de polling **antes** de registrar los comandos, para que corra
    antes de que python-telegram-bot llame `delete_webhook`.
- [X] T027 [US2] Comprobar, con el resguardo de `src/tarjeta_lealtad/bot/app.py`, que el polling con
  el bot de pruebas sigue funcionando, y correr los gates.

**Checkpoint**: en la computadora es imposible quitarle el webhook al bot de producción por error.

---

## Phase 5: User Story 3 - Publicar y actualizar siguiendo una guía (Priority: P2)

**Goal**: guía en el README, repositorio público en GitHub y primera publicación en alwaysdata.

**Independent Test**: seguir el README en la cuenta de alwaysdata y obtener `ok` y `/ayuda`
([quickstart §2.4](quickstart.md#24-comprobación)).

- [X] T028 [US3] Crear `README.md` a partir de `quickstart.md`, para el dueño, sin tokens, ID ni el
  nombre real de la cuenta. Secciones:
  1. qué hace el bot;
  2. uso en la computadora: instalación, `.env`, ejecución y gates;
  3. publicación en alwaysdata, paso a paso (§2.2 y §2.3);
  4. comprobación (§2.4);
  5. actualizar, volver a la versión anterior, ver los logs, cambiar el token o el secreto y dejar
     alwaysdata (§4).

  Cubre FR-018 – FR-020.
- [X] T029 [US3] Marcar las tareas hechas en `specs/002-despliegue-webhook-alwaysdata/tasks.md`,
  correr los gates y hacer commit en la rama `002-…`. La integración a `main` es T035, después de
  validar en producción (constitución: "integrada a `main` al terminar").
- [X] T030 [US3] Crear el repositorio público en GitHub con el contenido versionado (`README.md`,
  `src/`, `specs/`…) y subir `main` y la rama, según `quickstart.md` §2.1:
  `gh repo create Denilson1817/bot-tarjeta-lealtad --public --source . --remote origin`, luego
  `git push -u origin main` y `git push -u origin 002-despliegue-webhook-alwaysdata`.
  Antes de subir, comprobar que `git ls-files | grep -E '(^|/)\.env$|\.db$|^data/'` no devuelve
  nada (lo cubre `.gitignore`); después, que `gh repo view --json visibility` dice `PUBLIC`.
- [X] T031 [US3] Primera publicación, siguiendo `README.md` §3 pero clonando **la rama de la
  feature** (`git clone -b 002-despliegue-webhook-alwaysdata …`, `quickstart.md` §2.2): uv, clon,
  entorno con el Python 3.12 de alwaysdata, `.env` de producción y sitio *User program* en
  `CUENTA.alwaysdata.net/tarjeta`.
  **Manual**: la hace el dueño con su acceso SSH y al panel.
- [X] T032 [US3] Comprobación de [quickstart.md](quickstart.md) §2.4, filas 1–5: `ok` en el
  navegador, 403 sin token, `/ayuda` del bot de producción, `/saldo` del bot de finanzas, logs y
  disco < 300 MB.
  **Manual** (dueño).

**Checkpoint**: el bot de producción responde desde alwaysdata y el bot de finanzas sigue intacto.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T033 Validación en producción de `quickstart.md` §3 con la computadora apagada (SC-001,
  SC-003): la tabla de la 001 y las filas 6–8. La fila 6 mide además el arranque (< 10 s en el
  log, FR-012) y vuelve a revisar `/saldo` del bot de finanzas (SC-006). **Manual** (dueño).
- [X] T034 [P] Actualizar `bot-tarjeta-lealtad-contexto.md`:
  - estado "publicado en alwaysdata (webhook)";
  - decisiones: plan Free sin Services, sitio en `/tarjeta`, cambio a python-telegram-bot por
    memoria;
  - marcar el paso 4 de "Próximos pasos".
- [ ] T035 Integrar a `main` según `quickstart.md` §3.1, después de T033:
  - gates en verde, `git merge --no-ff` y `git push`;
  - en el servidor, pasar a `main` con el procedimiento de actualización y reiniciar el sitio
    (fila 9: < 5 min y `/clientes` idéntico).

  La parte del servidor es **manual** (dueño).
- [ ] T036 Ensayo de mantenimiento de `quickstart.md` §3.1, filas 10–11 (SC-007, SC-008, US3-3,
  US3-4): el agente prepara y sube un cambio mínimo; el dueño lo publica con «Actualizar»,
  vuelve al commit anterior y regresa a `main`. Se mide el tiempo y se compara `/clientes`.
  **Manual** (dueño).
- [ ] T037 Cerrar la feature en `specs/002-despliegue-webhook-alwaysdata/tasks.md`:
  - **revisión de cumplimiento** de la constitución: gates en verde y principios II–V respetados;
  - si T033 o T036 encontraron problemas, corregirlos en una rama nueva con pruebas;
  - si no, marcar la feature como cerrada, hacer commit y `git push`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (fase 1)** → **Foundational (fase 2)**: la librería nueva y la capa de Telegram portada
  bloquean todo lo demás.
- **US1 (fase 3)** depende de la fase 2.
- **US2 (fase 4)** depende de la fase 2. Toca `app.py` igual que T022, así que va después de US1.
- **US3 (fase 5)** depende de US1 y US2: se publica desde la rama de la feature, y se integra a
  `main` después de validar en producción (T035).
- **Polish (fase 6)** depende de la publicación (T031–T032).

### User Story Dependencies

| Historia | Depende de | Notas |
|----------|------------|-------|
| US1 (P1) | Foundational | Modo webhook |
| US2 (P2) | Foundational; tras US1 por `app.py` | Resguardo de polling |
| US3 (P2) | US1 + US2 | Guía, repositorio público, publicación |

### Within Each Phase

- Pruebas primero; deben fallar (principio III).
- Configuración → servidor web → `app.py`.
- Gates en verde antes de pasar de fase.

### Parallel Opportunities

- **Fase 2**: las pruebas T005–T012 entre sí (archivos distintos); T013 y T014 entre sí.
- **US1**: T018 y T019.
- **Fases 1 y 6**: T002, y T034.

---

## Parallel Example: Foundational

```bash
# Pruebas de la capa de Telegram (tras T004), en paralelo; deben fallar:
Task: "T005 tests/bot/test_acciones.py"
Task: "T006 tests/bot/test_seguridad.py"
Task: "T007 tests/bot/test_handlers_cita.py"
Task: "T008 tests/bot/test_handlers_alta.py"
Task: "T009 tests/bot/test_handlers_deshacer.py"
Task: "T010 tests/bot/test_handlers_consultas.py"
Task: "T011 tests/bot/test_integracion_app.py"
Task: "T012 tests/unit/test_arquitectura.py"

# Cuando estén en rojo:
Task: "T013 src/tarjeta_lealtad/bot/acciones.py"
Task: "T014 src/tarjeta_lealtad/bot/seguridad.py"
```

---

## Implementation Strategy

### MVP (US1)

1. Fases 1 y 2: el bot sobre python-telegram-bot, idéntico en polling.
2. Fase 3: modo webhook probado sin red.
3. US2 (resguardo) y US3 (README, repositorio y publicación).
4. **Validar en producción** (T033).
5. Integrar a `main` y ensayar el mantenimiento (T035–T036); cerrar la feature (T037).

### Riesgos a vigilar

- **Arranque en frío con ¼ de CPU** (FR-012, < 10 s): se mide en T033. Si se excede, la primera
  opción es poner *Idle time* = 0, siempre que la memoria de la cuenta lo permita.
- **Python 3.12 en alwaysdata**: si `PYTHON_VERSION=3.12` no existe, uv descarga Python (≈ +100 MB
  de disco; sigue dentro de FR-015).

---

## Notes

- Las tareas marcadas [P] usan archivos distintos y no tienen dependencias pendientes.
- Se recomienda un commit por fase (mensajes en español, como el historial).
- T031–T033, T036 y la parte del servidor de T035 son **manuales** y las hace el dueño: requieren
  el token de producción y el acceso a la cuenta.
