---

description: "Lista de tareas para que las personas autorizadas por el dueño usen el bot, también en grupos"
---

# Tasks: Personas autorizadas para usar el bot

**Input**: Design documents from `specs/003-usuarios-autorizados/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/acceso-y-grupos.md](contracts/acceso-y-grupos.md),
[quickstart.md](quickstart.md)

**Tests**: OBLIGATORIOS (constitución, principio III).
- **Dominio** (`conteo`, `busqueda`, `render`, `db`, `servicio`, `diseno`): no cambia, y sus
  pruebas deben seguir en verde sin tocarlas.
- **Lo nuevo** (configuración, filtro, comportamiento en grupos, autor en el log): se escribe con
  prueba primero.

**Organization**:
- la Fase 2 hace que el bot acepte un *conjunto* de personas autorizadas (lo necesitan todas las
  historias);
- luego, una fase por historia: US1 (otra persona con todos los permisos), US2 (no autorizados),
  US4 (grupo sin ruido) y US3 (guía para administrar personas). US4 va antes que US3 porque la guía
  describe el comportamiento en grupos.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: puede ejecutarse en paralelo (archivo distinto, sin depender de tareas incompletas).
- **[Story]**: historia de usuario de la tarea (US1…US4).

## Convenciones para todas las tareas

- **Comportamiento**: los textos, botones y flujos de la feature 001 no cambian
  ([contrato de comandos](../001-registro-citas-tarjeta/contracts/comandos-bot.md)). Qué responde
  el bot según quién escribe y dónde: [contracts/acceso-y-grupos.md](contracts/acceso-y-grupos.md).
- **Nada de `telegram`, `starlette` ni `uvicorn`** fuera de `bot/` (principio II; lo vigila
  `tests/unit/test_arquitectura.py`).
- **Repositorio público**: ningún archivo versionado lleva tokens, IDs reales de Telegram ni el
  nombre real de la cuenta de alwaysdata (se usa `CUENTA`). En pruebas y documentos, IDs de
  ejemplo (`111111111`, `222222222`) o constantes de prueba.
- **IDs autorizados**: son secretos de configuración (principio V). El log de arranque solo dice
  cuántas personas hay, nunca sus IDs.
- **Ejecución**: siempre con `uv run …`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: que las pruebas puedan simular grupos, avisos del grupo y toques de botón de otra
cuenta.

- [ ] T001 Ampliar `tests/bot/conftest.py` sin cambiar el comportamiento de las pruebas actuales:
  - `update_json(update_id, texto=None, *, de=1, data=None, chat=None, aviso=False)`:
    - con `chat=None`, el chat es privado con id `de` (como hoy);
    - con `chat=<id negativo>`, el chat es `{"id": chat, "type": "group", "title": "Grupo"}`,
      también en el mensaje que lleva un toque de botón;
    - con `aviso=True`, el mensaje no tiene `text` y lleva `new_chat_members` con el usuario
      (aviso de miembro nuevo);
  - `FakeTelegramAPI._mensaje`: el chat de las respuestas es `"group"` si `chat_id` es negativo;
  - `Telegram.pulsar(prompt, data, de=None)`: con `de`, el toque lo hace otra cuenta
    (`update.effective_user = MagicMock(id=de, username=f"u{de}")`).

**Checkpoint**: `uv run pytest` en verde, con las mismas pruebas que antes.

---

## Phase 2: Foundational (conjunto de personas autorizadas)

**Purpose**: la configuración, el filtro y `crear_aplicacion` trabajan con un conjunto de IDs
autorizados. Con `AUTORIZADOS` vacío, el bot se comporta exactamente igual que antes (SC-005).

**⚠️ CRITICAL**: ninguna historia empieza hasta terminar esta fase.

### Pruebas (escribir primero; deben FALLAR)

- [ ] T002 [P] Ampliar `tests/unit/test_config.py` ([research §1](research.md#1-configuración-de-las-personas-autorizadas)):
  - agregar `"AUTORIZADOS"` a `VARIABLES`;
  - sin `AUTORIZADOS` → `autorizados == frozenset()` e `ids_autorizados == {42}` (FR-002,
    US3-1);
  - `AUTORIZADOS=""` → vacío;
  - `AUTORIZADOS="111"` → `ids_autorizados == {42, 111}`;
  - `AUTORIZADOS=" 111, 222,111 "` → `autorizados == {111, 222}` (espacios permitidos, duplicados
    colapsados);
  - `AUTORIZADOS="111,"` → `{111}` (los elementos vacíos, como una coma al final, se ignoran);
  - `AUTORIZADOS="42,111"` (el dueño repetido) → `ids_autorizados == {42, 111}`;
  - `AUTORIZADOS="111,abc"` → `ValidationError` cuyo texto contiene `'abc'` y "separados por
    comas" (FR-006, US3-4).
- [ ] T003 [P] Reescribir `tests/bot/test_seguridad.py` para `crear_filtro(autorizados)`:
  - con `crear_filtro(frozenset({DUENO, OTRA}))`, ninguna de las dos lanza nada;
  - una tercera cuenta que escribe en privado → `ApplicationHandlerStop` y un `WARNING` con su ID y
    su usuario;
  - un update sin `effective_user` → `ApplicationHandlerStop`.

  Los casos por tipo de chat (grupo, botón, conversación) son de US2 (T015).
- [ ] T004 [P] Ampliar `tests/bot/test_app.py`: con `OWNER_ID=42` y `AUTORIZADOS=7` en el entorno,
  `main()` llama `crear_aplicacion` con `frozenset({42, 7})` (sustituirla con `monkeypatch` por un
  registro que delega en la original), en polling y en webhook, y el log de arranque dice
  "Personas autorizadas: 2" sin mostrar los IDs.

### Implementación

- [ ] T005 [P] En `src/tarjeta_lealtad/config.py`, según
  [contracts/acceso-y-grupos.md](contracts/acceso-y-grupos.md):
  - `autorizados: Annotated[frozenset[int], NoDecode] = frozenset()` (`NoDecode` de
    `pydantic_settings`, para que no intente leerla como JSON);
  - un `field_validator("autorizados", mode="before")` que, si recibe texto, lo separa por comas,
    quita espacios, ignora los elementos vacíos y convierte cada uno a entero; con un valor que no
    es entero lanza `ValueError` con el mensaje del contrato:
    `AUTORIZADOS debe ser una lista de IDs numéricos separados por comas; valor inválido: 'abc'`;
  - la propiedad `ids_autorizados -> frozenset[int]`: `{owner_id} | autorizados`.
- [ ] T006 [P] En `src/tarjeta_lealtad/bot/seguridad.py`, cambiar `crear_filtro_dueno(owner_id)` por
  `crear_filtro(autorizados: frozenset[int])`: corta con `ApplicationHandlerStop` todo update sin
  usuario o de una cuenta fuera del conjunto, con el `WARNING` actual. Actualizar el docstring del
  módulo (personas autorizadas; FR-004 de la 003, principio V).
- [ ] T007 En `src/tarjeta_lealtad/bot/app.py`, después de T005 y T006:
  - `crear_aplicacion(servicio, autorizados: frozenset[int], token, *, request=None, con_updater=True, al_iniciar=None)`
    registra `TypeHandler(Update, crear_filtro(autorizados))` en el grupo -1;
  - `main()` pasa `ajustes.ids_autorizados` en ambos modos y anota
    `log.info("Personas autorizadas: %s", len(...))`;
  - actualizar las llamadas existentes en `tests/bot/test_integracion_app.py`
    (`autorizados=frozenset({DUENO})`), `tests/bot/test_web.py` y `tests/bot/test_app.py`.
- [ ] T008 Correr los gates de `pyproject.toml` (`uv run ruff check`, `uv run ruff format --check`,
  `uv run mypy`, `uv run pytest`) y dejarlos en verde.

**Checkpoint**: con `AUTORIZADOS` vacío, todas las pruebas anteriores siguen en verde (SC-005); con
un ID más, esa cuenta pasa el filtro.

---

## Phase 3: User Story 1 - Otra persona autorizada usa el bot con todos los permisos (Priority: P1) 🎯 MVP

**Goal**: una segunda persona registra citas, da de alta, deshace, consulta y confirma botones
(también los que pidió el dueño), en privado y en un grupo, sobre la misma base. El log anota quién
hizo cada acción que cambia datos (FR-010).

**Independent Test**: las pruebas de T009–T012 en verde. En producción, las filas 1–3 y 6 de
[quickstart §3](quickstart.md#3-validación-en-producción).

### Tests for User Story 1 ⚠️ (escribir primero; deben FALLAR)

- [ ] T009 [P] [US1] Ampliar `tests/bot/test_handlers_cita.py` (con `caplog`):
  - `/cita` de un cliente existente desde `user_id=7` → el log contiene
    `Cita registrada: cliente=<id> premio=False usuario=7`;
  - cliente nuevo pedido por la cuenta 1 y `Crear` pulsado con `de=7` → `Alta: … usuario=7` y
    `Cita registrada: … usuario=7` (cuenta quien pulsa, no quien pidió);
  - "mismo día" confirmado con `de=7` → `Cita registrada: … usuario=7`.
- [ ] T010 [P] [US1] Ampliar `tests/bot/test_handlers_alta.py`: `/alta Rosa 6` desde `user_id=7` →
  `Alta: cliente=<id> previas=6 usuario=7`; un homónimo confirmado con `de=7` → `Alta: … usuario=7`.
- [ ] T011 [P] [US1] Ampliar `tests/bot/test_handlers_deshacer.py`: deshacer confirmado con `de=7`
  → `Cita anulada: cliente=<id> premio=False usuario=7`.
- [ ] T012 [P] [US1] Ampliar `tests/bot/test_integracion_app.py` con constantes `OTRA` (segunda
  persona autorizada) y `GRUPO` (ID negativo); la aplicación se crea con
  `autorizados=frozenset({DUENO, OTRA})`:
  - **base compartida**: `OTRA` envía `/alta Rosa 6` en privado y el `/clientes` del dueño muestra
    a Rosa (US1-1, FR-003);
  - **todos los comandos**: parametrizar `test_los_comandos_reciben_sus_argumentos` con `DUENO` y
    `OTRA` (US1-2);
  - **en grupo**: `OTRA` envía `/cita@tarjeta_bot Lucía` con `chat=GRUPO`; el dueño pulsa `Crear` →
    `sendPhoto` con `chat_id == GRUPO`; un segundo toque de `OTRA` → "ya se aplicó o caducó"
    (US1-3, FR-005, FR-007);
  - **mismo día entre personas**: el dueño registra `/cita Rosa` y `OTRA` envía `/cita Rosa` →
    pide confirmación con los botones de "mismo día" (US1-4).

### Implementation for User Story 1

- [ ] T013 [US1] En `src/tarjeta_lealtad/bot/handlers.py` ([research §5](research.md#5-quién-hizo-cada-acción-fr-010)):
  - `_autor(update) -> int`: el ID de `update.effective_user` (el filtro del grupo -1 garantiza que
    existe);
  - parámetro explícito `autor: int` en `_resolver`, `_continuar`, `_registrar`, `_crear_alta`,
    `_crear_y_registrar` y `_deshacer`. En los comandos sale de `_autor(update)`; en `al_pulsar`,
    también, porque el autor es quien pulsa;
  - líneas de log: `Cita registrada: cliente=%s premio=%s usuario=%s`,
    `Alta: cliente=%s previas=%s usuario=%s` y `Cita anulada: cliente=%s premio=%s usuario=%s`;
  - el docstring de `_ofrecer_opciones` dice "para que se elija" en lugar de "para que el dueño
    elija".
- [ ] T014 [US1] Correr los gates de `pyproject.toml` y dejarlos en verde.

**Checkpoint**: una segunda persona usa todo el bot en privado y en grupo (en pruebas), y el log
identifica quién hizo cada acción.

---

## Phase 4: User Story 2 - Las cuentas no autorizadas no pueden usar el bot (Priority: P1)

**Goal**: ninguna cuenta no autorizada obtiene respuesta ni efecto, en privado o en grupos. Sus
*intentos* quedan en el log con `WARNING` (de ahí se copia su ID); la conversación normal de un
grupo, solo con `DEBUG` ([research §2](research.md#2-filtro-de-acceso)).

**Independent Test**: las pruebas de T015–T016 en verde. En producción, la fila 5 de
[quickstart §3](quickstart.md#3-validación-en-producción).

### Tests for User Story 2 ⚠️ (escribir primero)

- [ ] T015 [P] [US2] Ampliar `tests/bot/test_seguridad.py` según la tabla del
  [contrato](contracts/acceso-y-grupos.md#qué-hace-el-bot-según-quién-escribe-y-dónde), con updates
  construidos a partir de `update_json` (por ejemplo, `Update.de_json(...)`):
  - una cuenta no autorizada:
    - en privado, con un texto cualquiera → `ApplicationHandlerStop` y
      `WARNING` `Mensaje ignorado de una cuenta no autorizada: id=… usuario=… chat=privado`;
    - en grupo, con `/cita Carmen` → `ApplicationHandlerStop` y `WARNING` con `chat=grupo`;
    - un toque de botón en un grupo → `ApplicationHandlerStop` y `WARNING` con `chat=grupo`;
    - en grupo, con un texto normal o con un aviso del grupo → `ApplicationHandlerStop` **sin**
      `WARNING` (registro `DEBUG`);
  - una cuenta autorizada, en cualquier caso, no deja ningún `WARNING`.

  Deben fallar los casos de `chat=` y del registro `DEBUG`.
- [ ] T016 [P] [US2] Ampliar `tests/bot/test_integracion_app.py` con una constante `INTRUSO` (no
  autorizada):
  - `INTRUSO` envía `/cita@tarjeta_bot Rosa` con `chat=GRUPO` → ninguna llamada `send*` y la base
    no cambia (US2-1);
  - el dueño envía `/cita Lucía` en el grupo; `INTRUSO` pulsa `Crear` → ninguna llamada nueva y
    Lucía no existe; después el dueño pulsa el mismo botón → `sendPhoto` (la acción seguía
    disponible, US2-2);
  - `test_el_intruso_no_recibe_nada` ya cubre el chat privado (US2-3).

  Estas pruebas protegen contra regresiones; pueden pasar desde la Fase 2.

### Implementation for User Story 2

- [ ] T017 [US2] En `src/tarjeta_lealtad/bot/seguridad.py`, para una cuenta no autorizada:
  - tipo de chat: `privado` si `update.effective_chat` es privado; si no, `grupo`;
  - es un **intento** si es un toque de botón, si el chat es privado o si el texto del mensaje
    empieza con `/`: `log.warning("Mensaje ignorado de una cuenta no autorizada: id=%s usuario=%s chat=%s", …)`;
  - en otro caso, el mismo texto con `log.debug`;
  - en ambos casos, `ApplicationHandlerStop`.
- [ ] T018 [US2] Correr los gates de `pyproject.toml` y dejarlos en verde.

**Checkpoint**: el 100 % de lo que envía una cuenta no autorizada queda sin respuesta ni efecto
(SC-002), y el log solo anota sus intentos.

---

## Phase 5: User Story 4 - Uso en grupo sin ruido (Priority: P2)

**Goal**: en un grupo, el bot solo reacciona a sus comandos y botones; en privado, el texto libre
sigue recibiendo "Usa /ayuda…" ([research §3](research.md#3-grupos-solo-comandos-y-botones)).

**Independent Test**: las pruebas de T019 en verde. En producción, la fila 4 de
[quickstart §3](quickstart.md#3-validación-en-producción).

### Tests for User Story 4 ⚠️ (escribir primero; deben FALLAR)

- [ ] T019 [US4] Ampliar `tests/bot/test_integracion_app.py`:
  - en el grupo, `hola` del dueño y de `OTRA` → ninguna llamada `send*` (US4-1, SC-003);
  - un aviso de miembro nuevo (`aviso=True`, `chat=GRUPO`) → ninguna llamada `send*` (FR-008);
  - `/ayuda@tarjeta_bot` en el grupo → `sendMessage` con `chat_id == GRUPO` (US4-2);
  - `/ayuda@otro_bot` en el grupo → ninguna llamada `send*`;
  - en privado, `hola` sigue respondiendo "Usa /ayuda…" (US4-3, FR-009; comprobar que
    `test_ayuda_y_texto_libre` lo cubre).

### Implementation for User Story 4

- [ ] T020 [US4] En `registrar_handlers` de `src/tarjeta_lealtad/bot/handlers.py`, cambiar el último
  handler por `MessageHandler(filters.ChatType.PRIVATE, sin_comando)`, con un comentario: en grupos,
  la conversación y los avisos no reciben respuesta.
- [ ] T021 [US4] Correr los gates de `pyproject.toml` y dejarlos en verde.

**Checkpoint**: en un grupo, 0 respuestas a mensajes que no son comandos (SC-003).

---

## Phase 6: User Story 3 - El dueño administra quién está autorizado (Priority: P2)

**Goal**: la guía explica cómo hallar el ID de una persona, autorizarla y quitarla, y que en un
grupo las tarjetas son visibles para todos (FR-011). La validación de la configuración ya quedó en
la Fase 2 (US3-1, US3-4).

**Independent Test**: seguir el README para autorizar una cuenta y quitarla, en menos de 5 minutos
cada vez (SC-004). En producción, la fila 7 de
[quickstart §3](quickstart.md#3-validación-en-producción).

- [ ] T022 [P] [US3] En `.env.example`, después de `OWNER_ID`, agregar comentada
  `# AUTORIZADOS=111111111,222222222`, con la explicación: IDs de otras personas autorizadas,
  separados por comas, opcional; el dueño siempre está autorizado; cómo obtener un ID, en el README
  («Personas autorizadas»).
- [ ] T023 [P] [US3] Actualizar `README.md`, sin IDs reales:
  - **Descripción** (línea 3): "para el dueño del negocio y las personas que el dueño autorice".
  - **Comandos** (línea 19): "El bot solo responde a las personas autorizadas; cualquier otra
    cuenta se ignora".
  - **Publicar en alwaysdata §1**: mencionar `AUTORIZADOS` (opcional) junto a `OWNER_ID`.
  - **Sección nueva «Personas autorizadas»**:
    1. **Hallar el ID**: pedirle a la persona que escriba `/ayuda` al bot y buscar la línea
       "cuenta no autorizada" en el log (en la computadora, la terminal; en alwaysdata,
       `grep -rh "cuenta no autorizada" ~/admin/logs/sites/ | tail -3`).
    2. **Autorizar**: `AUTORIZADOS=<id>` en `.env` (varias personas, separadas por comas) y
       reiniciar (en la computadora, Ctrl+C y volver a arrancar; en alwaysdata, reiniciar el sitio
       en Web > Sites). Al arrancar, el log dice "Personas autorizadas: N".
    3. **Quitar**: borrar el ID de `AUTORIZADOS` y reiniciar.
    4. **Grupos**: agregar el bot al grupo; los comandos se escriben como en privado o con el
       nombre del bot (`/cita@NombreDelBot Carmen`). Las tarjetas y la lista de clientes quedan
       visibles para todos los miembros: agregar el bot solo a grupos cuyos miembros puedan verlas.
       El bot ignora la conversación normal y a los miembros no autorizados.
    5. **Administradores anónimos**: si alguien tiene activado «Permanecer anónimo» como
       administrador del grupo, Telegram oculta su cuenta y el bot no lo reconoce (en el log
       aparece `usuario=GroupAnonymousBot`); hay que desactivarlo.

  Cubre FR-011 y SC-004.
- [ ] T024 [US3] (Opcional) Validación local de [quickstart §1](quickstart.md#1-en-la-computadora)
  con el bot de pruebas, si la otra persona puede usarlo: sin autorizar no recibe respuesta y su ID
  aparece en el log; con `AUTORIZADOS=<id>` y reinicio, `/ayuda` le responde.
  **Manual** (dueño).

**Checkpoint**: la guía permite autorizar y quitar personas sin tocar el código.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T025 [P] Actualizar `bot-tarjeta-lealtad-contexto.md`:
  - decisión del 2026-11-16: otra persona con todos los permisos, también en un grupo donde las
    tarjetas son visibles (constitución v4.0.0);
  - estado de la feature 003.
- [ ] T026 Cierre en la rama `003-usuarios-autorizados`:
  - gates de `pyproject.toml` en verde;
  - `git grep -nE '[0-9]{9,}' -- README.md .env.example src tests specs/003-usuarios-autorizados`
    solo devuelve los ejemplos `111111111` y `222222222`;
  - marcar las tareas hechas en `specs/003-usuarios-autorizados/tasks.md`, hacer commit y
    `git push -u origin 003-usuarios-autorizados`.
- [ ] T027 Integrar a `main` según [quickstart §2](quickstart.md#2-publicar), **después** de que la
  feature 002 esté integrada (T035 de `specs/002-despliegue-webhook-alwaysdata/tasks.md`):
  - gates en verde, `git merge --no-ff 003-usuarios-autorizados` en `main` y `git push`;
  - en el servidor, «Actualizar» según el README y reiniciar el sitio.

  La parte del servidor es **manual** (dueño).
- [ ] T028 Autorizar a la otra persona en producción, [quickstart §2](quickstart.md#2-publicar)
  pasos 3–5: que escriba `/ayuda` al bot, copiar su ID del log del sitio, agregarlo a
  `AUTORIZADOS` en el `.env` del servidor y reiniciar el sitio. **Manual** (dueño).
- [ ] T029 Validación en producción de [quickstart §3](quickstart.md#3-validación-en-producción),
  filas 1–7 (SC-001 – SC-005), con la otra persona y el grupo. **Manual** (dueño).
- [ ] T030 Cerrar la feature en `specs/003-usuarios-autorizados/tasks.md`:
  - **revisión de cumplimiento** de la constitución v4.0.0: gates en verde y principios I–VI
    respetados;
  - si T029 encontró problemas, corregirlos en una rama nueva con pruebas;
  - si no, marcar la feature como cerrada, hacer commit y `git push`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (fase 1)** → **Foundational (fase 2)**: las fixtures de grupo y el conjunto de
  autorizados bloquean todo lo demás.
- **US1 (fase 3)** depende de la fase 2.
- **US2 (fase 4)** depende de la fase 2. Toca `test_integracion_app.py` igual que US1, así que va
  después.
- **US4 (fase 5)** depende de la fase 2. Toca `handlers.py` y `test_integracion_app.py`, así que va
  después de US1.
- **US3 (fase 6)** depende de US4: la guía describe el comportamiento final en grupos.
- **Polish (fase 7)** depende de todas las historias. La publicación (T027–T029) depende además de
  que la feature 002 esté validada en producción (su T033) e integrada a `main` (su T035).

### User Story Dependencies

| Historia | Depende de | Notas |
|----------|------------|-------|
| US1 (P1) | Foundational | Segunda persona; autor en el log |
| US2 (P1) | Foundational; tras US1 por `test_integracion_app.py` | Intentos con `WARNING`, conversación con `DEBUG` |
| US4 (P2) | Foundational; tras US1 por `handlers.py` | `sin_comando` solo en privado |
| US3 (P2) | US4 | `.env.example` y README |

### Within Each Phase

- Pruebas primero; deben fallar (principio III), salvo las de regresión de T016.
- Configuración → filtro → `app.py` → handlers.
- Gates en verde antes de pasar de fase.

### Parallel Opportunities

- **Fase 2**: las pruebas T002–T004 entre sí; T005 y T006 entre sí.
- **US1**: T009–T012 (archivos distintos).
- **US2**: T015 y T016.
- **US3**: T022 y T023.
- **Fase 7**: T025.

---

## Parallel Example: User Story 1

```bash
# Pruebas de US1 en paralelo (deben fallar):
Task: "T009 tests/bot/test_handlers_cita.py"
Task: "T010 tests/bot/test_handlers_alta.py"
Task: "T011 tests/bot/test_handlers_deshacer.py"
Task: "T012 tests/bot/test_integracion_app.py"

# Cuando estén en rojo:
Task: "T013 src/tarjeta_lealtad/bot/handlers.py"
```

---

## Implementation Strategy

### MVP (US1 + US2)

1. Fases 1 y 2: el bot acepta un conjunto de personas autorizadas; sin `AUTORIZADOS`, nada cambia.
2. Fase 3 (US1): la segunda persona usa todo, y el log dice quién hizo cada acción.
3. Fase 4 (US2): las cuentas no autorizadas siguen fuera, y el log solo anota sus intentos.
4. Fase 5 (US4): el grupo sin ruido. **Necesaria antes de publicar si el bot va a un grupo**: sin
   ella, si el bot es administrador del grupo, respondería "Usa /ayuda…" a cada mensaje.
5. Fase 6 (US3): la guía.
6. Integrar después de la 002, autorizar a la persona y validar en producción (T027–T029); cerrar
   (T030).

### Riesgos a vigilar

- **Administradores anónimos**: un administrador con «Permanecer anónimo» llega como
  `GroupAnonymousBot` y el bot lo ignora. Queda documentado en el README (T023).
- **Orden de integración**: la rama 003 sale de la 002. Si la 002 necesita correcciones tras su
  T033, se hacen en la 002 y se integran a `main` antes que la 003.

---

## Notes

- Las tareas marcadas [P] usan archivos distintos y no tienen dependencias pendientes.
- Se recomienda un commit por fase (mensajes en español, como el historial).
- T024 y T027–T029 son **manuales** (la parte del servidor y la validación con la otra persona) y
  las hace el dueño.
