---

description: "Lista de tareas para implementar el registro de citas y la tarjeta de lealtad"
---

# Tasks: Registro de citas y tarjeta de lealtad

**Input**: Design documents from `specs/001-registro-citas-tarjeta/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: OBLIGATORIOS. El principio III (TDD, no negociable) exige escribir primero las pruebas
del dominio (conteo, deshacer y render), verlas fallar y solo después implementar. Las pruebas de
handlers de Telegram son ligeras, con objetos simulados.

**Organization**: tareas agrupadas por historia de usuario. Las historias US2–US6 se apoyan en el
flujo básico de US1 (buscar, crear, registrar, enviar la tarjeta).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: puede ejecutarse en paralelo (archivo distinto, sin depender de tareas incompletas).
- **[Story]**: historia de usuario de la tarea (US1…US6).

## Path Conventions

Proyecto único con *src layout*: `src/tarjeta_lealtad/`, `tests/` y `assets/` en la raíz del
repositorio ([plan.md § Project Structure](plan.md#project-structure)).

## Convenciones para todas las tareas

- **Firmas**: las del [contrato dominio ↔ bot](contracts/servicio-dominio.md). Los mensajes y
  botones siguen el [contrato de comandos](contracts/comandos-bot.md).
- **Fechas**: dentro del sistema son `datetime` con zona UTC. Solo se convierten a `ZONA_HORARIA`
  para mostrarlas y para la regla de "mismo día".
- **Nada de `aiogram`** en módulos fuera de `src/tarjeta_lealtad/bot/` (principio II).
- **Ejecución**: siempre con `uv run …`. Cada fase de historia termina con los gates de calidad en
  verde.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: dejar el proyecto instalable, con herramientas y gates funcionando sobre un
esqueleto vacío.

- [X] T001 Crear `pyproject.toml` en la raíz con:
  - `[project]`: `name = "tarjeta-lealtad"`, `version = "0.1.0"`, `requires-python = ">=3.12"`,
    `dependencies = ["aiogram>=3.32,<4", "pillow>=13,<14", "sqlalchemy>=2.0,<3", "pydantic-settings>=2.16,<3"]`.
  - `[dependency-groups] dev = ["pytest>=9", "pytest-asyncio>=1.5", "ruff>=0.17", "mypy>=2.4"]`.
  - `[build-system]`: backend `uv_build`, con la restricción compatible con el uv instalado (uv
    0.12.x → `uv_build>=0.12,<0.13`).
  - `[tool.ruff]`: `target-version = "py312"`, `line-length = 100`, `src = ["src", "tests"]`;
    `[tool.ruff.lint] select = ["E", "F", "W", "I", "UP", "B", "SIM", "RUF"]`. Si RUF001/RUF003
    marcan caracteres tipográficos del español usados en los textos ("·", "—", "«", "»"),
    agregarlos a `allowed-confusables`.
  - `[tool.mypy]`: `python_version = "3.12"`, `strict = true`, `files = ["src"]`,
    `plugins = ["pydantic.mypy"]`.
  - `[tool.pytest.ini_options]`: `testpaths = ["tests"]`, `asyncio_mode = "auto"`,
    `addopts = "--import-mode=importlib"`.
- [X] T002 [P] Crear `.python-version` con el contenido `3.12`.
- [X] T003 [P] Crear `.env.example` con las claves de [quickstart §2](quickstart.md#2-preparar-el-proyecto) y valores
  vacíos o de ejemplo (`BOT_TOKEN=`, `OWNER_ID=`, `ZONA_HORARIA=America/Mexico_City`,
  `CITAS_POR_TARJETA=10`, `DB_PATH` y `LOG_LEVEL` comentados). No copiar valores del `.env` real.
- [X] T004 Crear el esqueleto del paquete en `src/tarjeta_lealtad/` y `tests/`:
  - `src/tarjeta_lealtad/__init__.py` y `src/tarjeta_lealtad/bot/__init__.py`, ambos con un
    docstring de una línea;
  - los directorios `tests/unit/`, `tests/integration/` y `tests/bot/` (sin `__init__.py`; se usa
    `--import-mode=importlib`).
- [X] T005 Ejecutar `uv sync` para generar `.venv` y `uv.lock` (este último se versiona). Comprobar
  que `uv run ruff check`, `uv run ruff format --check` y `uv run mypy` pasan sobre el esqueleto.

**Checkpoint**: `uv sync` funciona y los tres gates estáticos están en verde.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: configuración, diseño, conteo, render, base de datos, esqueleto del servicio y del
bot. Todo lo usan las seis historias.

**⚠️ CRITICAL**: ninguna historia empieza hasta terminar esta fase.

### Pruebas fundacionales (escribir primero; deben FALLAR)

- [X] T006 Crear `tests/conftest.py`. Para que una prueba no rompa a las demás mientras el código no
  existe, cada fixture importa los módulos del paquete **dentro** de su cuerpo. Fixtures:
  - `zona` → `ZoneInfo("America/Mexico_City")`.
  - `utc(texto)` → fábrica de `datetime` con zona UTC a partir de `"2026-11-16 10:32"`.
  - `sesiones(tmp_path)` → `db.crear_motor(tmp_path / "t.db")` + `db.inicializar(...)` + sesiones.
  - `servicio(sesiones, zona)` → `ServicioTarjetas(sesiones, citas_por_tarjeta=10, zona=zona)`.
  - `mensaje_falso(texto, fecha, user_id=1)` → `MagicMock` con `text`, `date`,
    `from_user.id`/`username`, `chat.id` y `AsyncMock` en `answer`, `answer_photo`, `edit_text`
    y `edit_reply_markup`.
  - `callback_falso(data, mensaje)` → `MagicMock` con `data`, `message` y `answer` (`AsyncMock`).
  - `acciones` → `AccionesPendientes()`.

  Los handlers se prueban llamándolos directamente con esos objetos y
  `CommandObject(prefix="/", command="cita", args=...)`.
- [X] T007 [P] Crear `tests/unit/test_config.py`. Usar `monkeypatch.setenv` y `Ajustes(_env_file=None)`.
  Casos:
  - carga correcta;
  - falta `BOT_TOKEN` u `OWNER_ID` → `ValidationError`;
  - `ZONA_HORARIA="America/Mexico_city"` (mal escrita) → `ValidationError`;
  - `CITAS_POR_TARJETA=1` → `ValidationError`;
  - valores por defecto: `citas_por_tarjeta == 10`, `db_path == Path("data/lealtad.db")`,
    `log_level == "INFO"`;
  - `verificar_diseno(10)` no lanza;
  - `verificar_diseno(8)` lanza una excepción cuyo mensaje menciona 9 casillas y 7 esperadas
    (FR-017).
- [X] T008 [P] Crear `tests/unit/test_conteo.py` con `CitaEvento` construidos a mano. Casos:
  - `estado([])` → 0 en curso, sin completadas y `ultima_cita is None`;
  - 6 citas vigentes → 6 en curso;
  - 10 citas con la 10.ª `es_premio=True` + 2 más → 2 en curso y 1 completada, con la fecha de la
    10.ª;
  - las citas `previa` (`registrada_en=None`) no cuentan para `ultima_cita`;
  - `siguiente_es_premio(8, 10)` es falso; `siguiente_es_premio(9, 10)` y
    `siguiente_es_premio(12, 10)` son verdaderos;
  - `flores_a_dibujar(12, 9) == 9`;
  - `faltan_para_premio(6, 10) == 4`, `faltan_para_premio(9, 10) == 1` y
    `faltan_para_premio(12, 10) == 1`.
- [X] T009 [P] Crear `tests/unit/test_render.py` (abrir la salida con `PIL.Image.open(BytesIO(...))`).
  Casos:
  - la salida es un PNG de 1050 × 600;
  - para `flores` de 0 a 9: en las casillas `1..flores`, al menos el 20 % de los píxeles del disco
    de radio 50 alrededor del centro no son blancos; en las demás, todo el disco de radio 56 es
    exactamente `(255, 255, 255)`;
  - los píxeles fuera de los discos de radio 58 y del rectángulo x 40–450 / y 240–376 son
    idénticos a `assets/plantilla-vacia.png`;
  - la tinta del nombre (diferencia con la plantilla dentro del rectángulo) queda en x 50–440 y
    y ≤ 370, sin ningún píxel en la zona del ✨ (x 310–354, y 274–323);
  - `ajustar_nombre("Carmen").tamano == 117` e `ajustar_nombre("Isabel").tamano < 117`;
  - con "Ángela" e "Íñigo", ninguna tinta por encima de y = 246 (no tocan el título);
  - estos nombres de SC-006 caben con `tamano >= 36`: "María Fernanda Ruiz", "Guadalupe
    Hernández", "Wendy Montserrat Paz", "Maximiliana Montoya", "Ximena Guadalupe Mtz", "Marisol Del
    Castillo", "Itzel Bethel Ballard" y "Wilhelmina Whitfield";
  - "Maximiliana Guadalupe Montoya Ruiz" → `NombreNoCabe`;
  - dos llamadas iguales devuelven bytes idénticos (FR-029);
  - `flores=-1` y `flores=10` → `ValueError`;
  - cada carácter permitido por el [research §8](research.md#8-validación-de-nombres) tiene glifo
    en Sacramento: su máscara difiere de la del glifo no definido, obtenido con `""`.
- [X] T010 [P] Crear `tests/unit/test_arquitectura.py`: recorrer con `ast` todos los `.py` de
  `src/tarjeta_lealtad/` excepto `bot/` y fallar si alguno importa `aiogram` (principio II).
- [X] T011 [P] Crear `tests/integration/test_db.py`. Casos:
  - las tablas se crean;
  - un `datetime` UTC hace el viaje de ida y vuelta conservando la zona;
  - guardar un `datetime` sin zona lanza `ValueError`;
  - una cita `origen="bot"` con `registrada_en=None` o una `origen="previa"` con fecha →
    `IntegrityError`;
  - al borrar el último cliente, el siguiente no reutiliza su `id` (`AUTOINCREMENT`);
  - al cerrar el motor y abrir uno nuevo sobre el mismo archivo, siguen los clientes y las citas,
    incluidas las anuladas (FR-034).
- [X] T012 [P] Crear `tests/integration/test_servicio_base.py`, insertando clientes y citas
  directamente con las sesiones. Casos:
  - `resumen()` calcula `citas_en_curso`, `tarjetas_completadas`, `ultima_cita` y
    `proxima_es_premio`, ignorando citas anuladas;
  - `tarjeta_png()` devuelve un PNG;
  - un `id` inexistente → `ClienteInexistente`.
- [X] T013 [P] Crear `tests/bot/test_seguridad.py` para el middleware `SoloDueno(owner_id)`:
  - con `data["event_from_user"].id == owner_id` llama al handler;
  - con otro ID no lo llama, no responde y registra un `WARNING` con ID y usuario (`caplog`);
  - un evento sin usuario no llama al handler.
- [X] T014 [P] Crear `tests/bot/test_acciones.py`:
  - `registrar(accion)` devuelve un token ≤ 16 caracteres;
  - `tomar(token)` devuelve la acción la primera vez y `None` la segunda (FR-011);
  - los tokens no se repiten en 1 000 registros;
  - `AccionCB(token=t, opcion="nuevo").pack()` ocupa ≤ 64 bytes.
- [X] T015 [P] Crear `tests/bot/test_textos.py` (base), siempre en `America/Mexico_City`:
  - `fecha_corta(utc("2026-11-10 18:00"))` → `"10 nov"`;
  - `fecha_hora(utc("2026-11-12 16:32"))` → `"12 nov 2026, 10:32"`;
  - `AYUDA` menciona los seis comandos con un ejemplo cada uno.

### Implementación fundacional

- [X] T016 [P] Implementar `src/tarjeta_lealtad/config.py`:
  - `Ajustes(BaseSettings)` con `env_file=".env"` y los campos del
    [contrato § config.py](contracts/servicio-dominio.md#configpy): `bot_token: SecretStr`,
    `owner_id: int`, `zona_horaria: str` (validada con `ZoneInfo`), `citas_por_tarjeta: int = 10`
    (`>= 2`), `db_path: Path = Path("data/lealtad.db")` y `log_level: str = "INFO"`;
  - `verificar_diseno(citas_por_tarjeta)`, que lanza si `diseno.CASILLAS != citas_por_tarjeta - 1`.
- [X] T017 [P] Implementar `src/tarjeta_lealtad/diseno.py` con las constantes **literales** del
  [research §9](research.md#9-render-de-la-tarjeta-pillow):
  - rutas a `assets/` resueltas con `Path(__file__).resolve().parents[2] / "assets"`;
  - `CENTROS` = las 9 tuplas en orden de llenado `[(584.0, 119.0), (769.5, 119.0), (954.5, 119.0), (584.0, 301.0), …, (954.5, 483.0)]` y `CASILLAS = len(CENTROS)`;
  - `MITAD_FLOR = 57` y la esquina de la flor `(floor(cx) - 57, floor(cy) - 57)`;
  - `CENTRO_NOMBRE_X = 245`, `BORDE_INFERIOR_NOMBRE = 370`, `TOPE_SUPERIOR_NOMBRE = 246`,
    `ANCHO_MAX_NOMBRE = 390`;
  - `TAMANO_MAX = 117`, `TAMANO_MIN = 36`;
  - `ZONA_DESTELLO = (310, 274, 354, 323)` y `COLOR_NOMBRE = (255, 255, 255)`.
- [X] T018 [P] Implementar `src/tarjeta_lealtad/conteo.py` (`CitaEvento`, `EstadoTarjetas`, `estado`,
  `siguiente_es_premio`, `flores_a_dibujar` y `faltan_para_premio`) según el
  [contrato](contracts/servicio-dominio.md#conteopy) y las
  [vistas derivadas](data-model.md#vistas-derivadas-en-el-dominio-sin-tabla). Sin E/S.
- [X] T019 Implementar `src/tarjeta_lealtad/render.py`, después de T017:
  - `ajustar_nombre(nombre)` busca el mayor tamaño ≤ `TAMANO_MAX` cuya **máscara de tinta** tenga
    ancho ≤ 390, borde superior en y ≥ `TOPE_SUPERIOR_NOMBRE` y ningún píxel en `ZONA_DESTELLO`, colocada con centro de tinta en x = 245 y borde
    inferior en y = 370. Si el tamaño quedaría < 36, lanza `NombreNoCabe`. Usar búsqueda binaria
    para el ancho y el alto, y luego bajar de 1 en 1 mientras choque con el ✨;
  - `generar_tarjeta(nombre, flores)` pega la flor (canal alfa como máscara) en las casillas
    `0..flores-1`, dibuja el nombre en blanco y devuelve los bytes PNG, sin escribir a disco;
  - carga la plantilla, la flor y la fuente una sola vez (`functools.cache`).
- [X] T020 [P] Implementar `src/tarjeta_lealtad/db.py` con SQLAlchemy 2 tipado (`Mapped[...]`):
  - `UTCDateTime(TypeDecorator)`: rechaza `datetime` sin zona, guarda UTC sin zona y devuelve UTC
    con zona;
  - `Cliente` (`clientes`): `id` PK con `sqlite_autoincrement=True`, `nombre` "texto, no nulo,
    ≤ 60", `nombre_normalizado` "no nulo, indexado" (no único) y `creado_en` UTC no nulo;
  - `Cita` (`citas`): `id` PK con `sqlite_autoincrement=True`, `cliente_id` FK indexada no nula,
    `origen` `bot`/`previa` (CHECK), `registrada_en` UTC "nula si y solo si `origen = previa`
    (restricción CHECK)", `es_premio` booleano no nulo por defecto falso, `anulada_en` UTC nula y
    `creada_en` UTC no nula;
  - `crear_motor(db_path)`: crea el directorio padre y activa `PRAGMA foreign_keys=ON`;
  - `inicializar(motor)` (`create_all`) y `crear_sesiones(motor)`.
- [X] T021 Implementar en `src/tarjeta_lealtad/servicio.py`, después de T018–T020:
  - las dataclasses y excepciones del [contrato](contracts/servicio-dominio.md#serviciopy);
  - `ServicioTarjetas.__init__`, que expone `zona` y `citas_por_tarjeta` como atributos de solo
    lectura;
  - el helper privado `_eventos(sesion, cliente_id) -> list[CitaEvento]` (solo vigentes, por `id`);
  - `resumen()` y `tarjeta_png()`.

  El resto de métodos se agrega en cada historia.
- [X] T022 [P] Implementar `src/tarjeta_lealtad/bot/seguridad.py`: `SoloDueno(BaseMiddleware)` para
  `dp.update.outer_middleware`, que lee `data["event_from_user"]`, registra un `WARNING` y corta el
  flujo si el remitente no es el dueño (FR-001).
- [X] T023 [P] Implementar `src/tarjeta_lealtad/bot/acciones.py`:
  - `Accion` (dataclass congelada con `tipo`, `comando` (`Literal["cita", "deshacer", "tarjeta"]`),
    `cliente_ids`, `nombre`, `fecha_comando` y `citas_previas`);
  - `AccionesPendientes` (`registrar` → token `secrets.token_urlsafe(8)`; `tomar` con `pop`);
  - `class AccionCB(CallbackData, prefix="a")` con `token: str` y `opcion: str` (un ID, `"nuevo"`,
    `"si"` o `"no"`).
- [X] T024 [P] Implementar `src/tarjeta_lealtad/bot/textos.py` (base):
  - `AYUDA`, `uso(comando)`, `NO_ES_COMANDO`, `ACCION_CADUCADA`, `ERROR_INESPERADO` y
    `CANCELADO`, con la redacción del [contrato](contracts/comandos-bot.md);
  - `fecha_corta(dt, zona)` y `fecha_hora(dt, zona)` con meses abreviados en español escritos en el
    código (sin depender del *locale*).
- [X] T025 Implementar `src/tarjeta_lealtad/bot/handlers.py` (base), después de T021, T023 y T024:
  - `router = Router()`;
  - `/start` y `/ayuda` → `AYUDA`; texto que no es comando → `NO_ES_COMANDO`;
  - `async def enviar_tarjeta(message, servicio, cliente_id, flores, pie)`: envía
    `BufferedInputFile(png, "tarjeta.png")` con `answer_photo`; si falla, responde el error de envío
    del contrato y registra la traza;
  - un manejador de errores del router que registra la traza y responde `ERROR_INESPERADO`.

  Los handlers reciben `servicio` y `acciones` por inyección de `workflow_data`.
- [X] T026 Implementar `src/tarjeta_lealtad/bot/app.py` (`main()`) y `src/tarjeta_lealtad/__main__.py`
  (que llama a `main()`), después de T016, T022 y T025. Pasos de `main()`:
  1. configurar `logging` a stdout con `LOG_LEVEL`;
  2. cargar `Ajustes`; si falla, registrar el error y `sys.exit(1)`;
  3. `verificar_diseno` (FR-017), con `sys.exit(1)` si falla;
  4. comprobar que los assets cargan (`render.ajustar_nombre("Prueba")`);
  5. crear el motor e inicializar la base;
  6. crear `Dispatcher(servicio=..., acciones=AccionesPendientes())`, registrar
     `SoloDueno(owner_id)` como *outer middleware* de `dp.update` e incluir el router;
  7. `bot.set_my_commands` con los 6 comandos y descripciones en español;
  8. registrar "polling iniciado" y llamar a `dp.start_polling(bot, handle_as_tasks=False)`, **sin**
     descartar los mensajes pendientes.
- [ ] T027 Verificar la fundación (`tests/` y `src/tarjeta_lealtad/bot/app.py`):
  - `uv run pytest` muestra en verde todas las pruebas de T007–T015;
  - los gates estáticos pasan;
  - `uv run python -m tarjeta_lealtad` arranca con el `.env` local, `/ayuda` responde desde el iPhone
    y el menú de comandos aparece al escribir "/";
  - con `CITAS_POR_TARJETA=8` el proceso sale con el error de FR-017.

**Checkpoint**: el bot arranca, solo responde al dueño y sabe dibujar una tarjeta.

---

## Phase 3: User Story 1 - Registrar una cita y recibir la tarjeta actualizada (Priority: P1) 🎯 MVP

**Goal**: con `/cita <nombre>`, el bot encuentra o crea (con confirmación) al cliente, registra la
cita con la fecha del comando y devuelve la tarjeta como foto.

**Independent Test**: con la base vacía, registrar citas a un cliente nuevo y a uno existente;
cada foto muestra el nombre y tantas flores como citas lleva
([quickstart §5](quickstart.md#5-validación-manual-de-punta-a-punta), filas 1–4 y 16).

### Tests for User Story 1 ⚠️ (escribir primero; deben FALLAR)

- [X] T028 [P] [US1] Crear `tests/unit/test_busqueda.py`:
  - `normalizar(" Cármen  LÓPEZ ") == "carmen lopez"`;
  - `limpiar_nombre("  María   Fernanda ") == "María Fernanda"`;
  - `caracteres_no_admitidos`: devuelve `["😀"]` para `"Ana 😀"` y `["7"]` para `"Ana7"`, y una
    lista vacía para `"Zoë O'Neil-Peña Jr."`. Regla: "letras ASCII, letras Latin-1 (`À`–`ÿ`, sin
    `×` ni `÷`), espacio, apóstrofo, guion y punto. Debe haber al menos una letra. No se admiten
    dígitos";
  - `distancia("carmen", "carmn") == 1`, `distancia("ab", "ba") == 1` (intercambio) y
    `distancia("ana", "eva") == 2`;
  - `parecido`: devuelve una puntuación para `("carmn", "carmen")` y para `("mar", "maria lopez")`
    (prefijo de palabra), y `None` para `("lucia", "carmen")`.
- [X] T029 [P] [US1] Crear `tests/integration/test_servicio_cita.py`:
  - `buscar("carmen")`, `buscar("Cármen")` y `buscar("  CARMEN ")` → `Encontrado` del mismo
    cliente;
  - `buscar("Lucía")` sin parecidos → `SinCoincidencias`;
  - `buscar("Carmn")` → `Parecidos` que incluye a Carmen, con máximo 6 opciones ordenadas por
    puntuación y luego por nombre;
  - `validar_nombre("  Lucía ")` devuelve `"Lucía"`; con emoji, con dígitos o con un nombre que
    no cabe → `NombreInvalido` con `motivo`;
  - `crear_cliente("Lucía", 0, ahora)` asigna un `id`, guarda el nombre limpio y su forma
    normalizada;
  - `registrar_cita(id, cuando)` guarda `registrada_en == cuando` y `origen == "bot"`, y devuelve
    `ResultadoCita` con `citas_en_curso` +1 y `flores` igual a las citas en curso;
  - `cita_del_dia`: con una cita el 2026-11-16 a las 23:30 hora de Mexico City (05:30 UTC del
    17), consultar el 2026-11-16 a las 20:00 local la encuentra; consultar el 17 a las 09:00 local
    devuelve `None`.
- [X] T030 [P] [US1] Crear `tests/bot/test_handlers_cita.py`:
  - `/cita` sin argumento → `uso("cita")`;
  - cliente existente → `answer_photo` con el pie de foto de la cita;
  - cliente nuevo → mensaje con los botones `Crear` y `Cancelar`; `Crear` crea, registra con la
    `fecha_comando` original y envía la foto; `Cancelar` no cambia nada;
  - repetir el toque en el mismo botón → `ACCION_CADUCADA`;
  - cita el mismo día → botones `Sí, registrar` y `Cancelar`;
  - `Carmn` → botón `Carmen #… · …` y `Crear «Carmn»`;
  - nombre inválido → no ofrece `Crear` y explica el motivo;
  - si `answer_photo` lanza → la cita queda registrada y se responde el error de envío.
- [X] T031 [P] [US1] Ampliar `tests/bot/test_textos.py`:
  - `pie_cita` para un resultado normal (`"🌸 Carmen (#3): 6 de 9 flores. Faltan 4 citas para la de premio (la 10.ª)."`);
  - `etiqueta_cliente` → `"Carmen #3 · 4/9 · 10 nov"`, o `"… · sin citas"` si no tiene;
  - `confirmar_crear("Lucía")` y `confirmar_mismo_dia(...)` con la hora local.

### Implementation for User Story 1

- [X] T032 [US1] Implementar en `src/tarjeta_lealtad/busqueda.py`, después de que T028 falle, `normalizar`,
  `limpiar_nombre`, `caracteres_no_admitidos`, `distancia` (Damerau-Levenshtein OSA) y `parecido`,
  según el [research §7–§8](research.md#7-búsqueda-de-clientes). Sin dependencias nuevas.
- [X] T033 [US1] Agregar a `src/tarjeta_lealtad/servicio.py`:
  - `validar_nombre`: limpia; comprueba caracteres y largo "≤ 60"; llama a `render.ajustar_nombre`
    y traduce `NombreNoCabe` a `NombreInvalido(motivo)`;
  - `crear_cliente(nombre, 0, ahora)`;
  - `buscar`: una coincidencia exacta → `Encontrado`; sin exacta → `Parecidos` (máx. 6) o
    `SinCoincidencias`.
- [X] T034 [US1] Agregar a `src/tarjeta_lealtad/servicio.py`:
  - `cita_del_dia(cliente_id, cuando)`: citas vigentes `origen="bot"` del mismo día local en
    `zona`;
  - `registrar_cita(cliente_id, cuando)`: inserta la cita con `es_premio=False` (la regla de premio
    llega en US2) y devuelve `ResultadoCita`;
  - cada método de escritura en una sola transacción.
- [X] T035 [US1] Agregar a `src/tarjeta_lealtad/bot/textos.py`: `pie_cita(resultado, citas_por_tarjeta)`,
  `etiqueta_cliente(resumen, zona)`, `confirmar_crear(nombre)`,
  `confirmar_mismo_dia(resumen, hora, zona)`, `nombre_invalido(motivo)` y `error_envio(cliente_id)`,
  con la redacción del [contrato § /cita](contracts/comandos-bot.md#cita-cliente).
- [X] T036 [US1] Implementar `/cita` en `src/tarjeta_lealtad/bot/handlers.py`:
  - sin argumento → `uso`;
  - `buscar` → `Encontrado`: si `cita_del_dia` encuentra una, registrar una `Accion` de
    confirmación; si no, `registrar_cita(id, message.date)` + `enviar_tarjeta`;
  - `Parecidos` → teclado con una opción por cliente, `Crear «X»` (solo si `validar_nombre` pasa)
    y `Cancelar`;
  - `SinCoincidencias` → confirmación de alta o `nombre_invalido`.

  Cada teclado se respalda con una `Accion` registrada que guarda `fecha_comando=message.date`.
- [X] T037 [US1] Implementar en `src/tarjeta_lealtad/bot/handlers.py` el callback de `AccionCB`:
  1. `callback.answer()` y `acciones.tomar(token)`; si devuelve `None` → `ACCION_CADUCADA`;
  2. quitar los botones del mensaje y anotar la elección (`edit_text`);
  3. despachar por `tipo`:
     - elegir cliente → según `accion.comando`: `cita` → comprobación de mismo día; `deshacer` →
       confirmación de deshacer (US5); `tarjeta` → enviar la foto sin registrar cita (US6);
     - crear y registrar → `crear_cliente` + `registrar_cita` con `fecha_comando`;
     - confirmar mismo día → `registrar_cita` con `fecha_comando`;
     - cancelar → `CANCELADO`.

  Siempre se pasa el `ResultadoCita` completo a `pie_cita`.
- [ ] T038 [US1] Correr los gates y validar con el bot de pruebas `quickstart.md` §5, filas 1–4 y 16.

**Checkpoint**: US1 funciona sola. El dueño ya puede sustituir la edición manual.

---

## Phase 4: User Story 2 - Completar la tarjeta y empezar una nueva (Priority: P2)

**Goal**: la cita N es la de premio, cierra la tarjeta y la guarda en el historial; la siguiente
empieza otra tarjeta. N es configurable.

**Independent Test**: 11 citas seguidas a un cliente nuevo: avisos en las citas 9 y 10, la tarjeta 1
queda completada y la cita 11 muestra 1 flor. Las filas 7–9 del quickstart, que usan `/alta` y `#id`,
se validan en T057.

### Tests for User Story 2 ⚠️

- [X] T039 [P] [US2] Crear `tests/integration/test_servicio_ciclo.py`:
  - tras la cita 9, `proxima_es_premio` es verdadero;
  - la cita 10 devuelve `es_premio`, `numero_tarjeta == 1`, `flores == 9`, `citas_en_curso == 0` y
    `tarjetas_completadas == 1`;
  - la cita 11 devuelve `flores == 1`;
  - un cliente con 9 citas en curso, con un servicio creado con `citas_por_tarjeta=8`, cierra la
    tarjeta en su siguiente cita (FR-016);
  - completar una tarjeta con N=10 y consultar con un servicio N=5 conserva
    `tarjetas_completadas == 1` (cambiar N no altera tarjetas completadas).
- [X] T040 [P] [US2] Ampliar `tests/bot/test_textos.py`:
  - `pie_cita` con 9 de 9 → "🎁 ¡La próxima cita es la de premio!";
  - `pie_cita` con premio → "¡cita de premio! Tarjeta n.º 1 completada. La próxima cita empieza
    una tarjeta nueva.".
- [X] T041 [P] [US2] Ampliar `tests/bot/test_handlers_cita.py`: la cita de premio envía la foto con
  9 flores y el pie de premio.

### Implementation for User Story 2

- [X] T042 [US2] En `ServicioTarjetas.registrar_cita` (`src/tarjeta_lealtad/servicio.py`):
  - `es_premio = conteo.siguiente_es_premio(citas_en_curso, citas_por_tarjeta)`;
  - con premio, `numero_tarjeta` = número de premios vigentes después de insertar y
    `flores = diseno.CASILLAS`.
- [X] T043 [US2] Completar en `src/tarjeta_lealtad/bot/textos.py` las variantes de `pie_cita` para
  9 de 9 y para premio, según la tabla del [contrato § /cita](contracts/comandos-bot.md#cita-cliente).
- [ ] T044 [US2] Correr los gates y validar con el bot de pruebas (sin usar `quickstart.md` §5, filas 7–9):
  `/cita Prueba` → `Crear` y 10 citas más, confirmando las del mismo día. Deben aparecer los avisos de
  las citas 9 y 10 y la 11.ª debe mostrar 1 flor. Con `CITAS_POR_TARJETA=8` el bot no debe arrancar.

**Checkpoint**: US1 y US2 funcionan; los ciclos de tarjeta son correctos.

---

## Phase 5: User Story 3 - Dar de alta un cliente con tarjeta en curso (Priority: P2)

**Goal**: con `/alta <nombre> [citas previas]` se crea un cliente con k flores, sin registrar una
cita del día, avisando si el nombre ya existe.

**Independent Test**: `/alta Rosa 6` → foto con 6 flores; la siguiente `/cita Rosa` → 7 (quickstart
§5, filas 5, 12 y 13).

### Tests for User Story 3 ⚠️

- [X] T045 [P] [US3] Crear `tests/integration/test_servicio_alta.py`:
  - `crear_cliente("Rosa", 6, ahora)` → `citas_en_curso == 6`, 6 citas con `origen="previa"` y
    `registrada_en is None`, y `cita_del_dia(...)` es `None`;
  - después, `registrar_cita` → 7;
  - con citas previas fuera de "0 ≤ k ≤ N − 1" (`-1` y `10`) → `CitasPreviasFueraDeRango`;
  - `homonimos("rosa")` devuelve el cliente existente;
  - un nombre inválido → `NombreInvalido`.
- [X] T046 [P] [US3] Crear `tests/bot/test_handlers_alta.py`:
  - `separar_alta`: `"Rosa 6"` → `("Rosa", 6)`; `"María Fernanda Ruiz"` → `(…, 0)`; `"Rosa -1"` →
    `("Rosa", -1)` (lo rechaza el rango); `"6"` → sin nombre, así que `uso("alta")`;
  - `/alta Rosa 6` → foto con el pie "✅ Cliente nuevo: Rosa (#…) con 6 citas previas…";
  - homónimo → botones `Crear otro` y `Cancelar`;
  - fuera de rango → "Las citas previas deben estar entre 0 y 9.";
  - nombre inválido → motivo.

### Implementation for User Story 3

- [X] T047 [US3] En `src/tarjeta_lealtad/servicio.py`:
  - extender `crear_cliente` para validar `0 <= citas_previas <= citas_por_tarjeta - 1` e insertar
    `citas_previas` citas `origen="previa"`, en la misma transacción que el cliente;
  - agregar `homonimos(nombre)`.
- [X] T048 [US3] Agregar a `src/tarjeta_lealtad/bot/textos.py`: `pie_alta`, `confirmar_homonimo` y
  `PREVIAS_FUERA_DE_RANGO` (con el máximo calculado a partir de N), según el
  [contrato § /alta](contracts/comandos-bot.md#alta-nombre-citas-previas).
- [X] T049 [US3] Implementar en `src/tarjeta_lealtad/bot/handlers.py`:
  - la función pura `separar_alta(args) -> tuple[str, int]` (el último elemento es entero → citas
    previas);
  - el comando `/alta`: validar, revisar homónimos (`Accion` "crear homónimo"), crear y enviar la
    tarjeta con `enviar_tarjeta`;
  - el caso "crear homónimo" en el despachador del callback.
- [ ] T050 [US3] Correr los gates y validar las filas 5, 12 y 13 de `quickstart.md` §5.

**Checkpoint**: los clientes actuales se pueden migrar con su avance.

---

## Phase 6: User Story 4 - Elegir entre clientes con el mismo nombre (Priority: P2)

**Goal**: si hay varias coincidencias exactas, el bot pide elegir. El dueño también puede usar
`#id`.

**Independent Test**: dos "María"; `/cita maria` pide elegir y la cita se suma solo a la elegida
(quickstart §5, fila 6).

### Tests for User Story 4 ⚠️

- [X] T051 [P] [US4] Ampliar `tests/unit/test_busqueda.py`: `interpretar_id` acepta `"#12"`, `"12"`
  y `" #7 "`; devuelve `None` para `"12a"`, `"#"` y `"Carmen"`.
- [X] T052 [P] [US4] Crear `tests/integration/test_servicio_homonimos.py`:
  - dos "María" → `buscar("maria")` devuelve `Varios` con ambas, ordenadas por `id`;
  - `buscar(f"#{id}")` → `Encontrado`;
  - `buscar("#999")` → `IdInexistente(999)`.
- [X] T053 [P] [US4] Ampliar `tests/bot/test_handlers_cita.py`:
  - `Varios` → un botón por cliente con `etiqueta_cliente` y `Cancelar`, sin registrar nada;
  - elegir uno registra la cita **solo** en ese cliente;
  - `/cita #id` registra sin preguntar;
  - `/cita #999` → "No existe el cliente #999.".

### Implementation for User Story 4

- [X] T054 [US4] Agregar `interpretar_id` a `src/tarjeta_lealtad/busqueda.py`, después de que T051 falle.
- [X] T055 [US4] Extender `ServicioTarjetas.buscar` (`src/tarjeta_lealtad/servicio.py`): primero
  la rama de ID (`Encontrado` o `IdInexistente`); luego, con varias coincidencias exactas,
  `Varios`.
- [X] T056 [US4] En `src/tarjeta_lealtad/bot/handlers.py`, manejar `Varios` (teclado sin `Crear`,
  reutilizando la acción "elegir cliente") e `IdInexistente`. Agregar `ID_INEXISTENTE` a
  `src/tarjeta_lealtad/bot/textos.py`.
- [ ] T057 [US4] Correr los gates y validar las filas 6–9 de `quickstart.md` §5 (las 7–9 necesitan
  `/alta` y `#id`).

**Checkpoint**: ya no se puede registrar una cita a un homónimo equivocado sin que el dueño lo
elija.

---

## Phase 7: User Story 5 - Deshacer la última cita de un cliente (Priority: P3)

**Goal**: con `/deshacer <cliente>` se anula, previa confirmación, la cita vigente más reciente
del cliente; si era la de premio, la tarjeta se reabre.

**Independent Test**: registrar dos citas, deshacer una y ver las flores anteriores y la
anulación registrada (quickstart §5, filas 10–11).

### Tests for User Story 5 ⚠️

- [X] T058 [P] [US5] Crear `tests/integration/test_servicio_deshacer.py`:
  - con 4 citas, `deshacer_ultima` → 3 en curso, y la cita anulada sigue en la tabla con
    `anulada_en` (no se borra);
  - deshacer el premio → `citas_en_curso == 9` y `tarjetas_completadas == 0` (FR-024);
  - deshacer una cita `previa` está permitido;
  - sin citas vigentes → `None`;
  - `ultima_cita_vigente` devuelve la de mayor `id`;
  - dos `deshacer` seguidos anulan dos citas.
- [X] T059 [P] [US5] Crear `tests/bot/test_handlers_deshacer.py`:
  - la confirmación muestra `"12 nov 2026, 10:32 · cita de premio"`, o `"cita previa al bot"`
    para una previa;
  - `Sí, deshacer` → foto con "↩️ Cita anulada…" y, si fue premio, "La tarjeta n.º … vuelve a
    estar en curso.";
  - `Cancelar` no cambia nada; repetir el toque → `ACCION_CADUCADA`;
  - sin citas → "… no tiene citas que deshacer.";
  - con parecidos no se ofrece `Crear`, y elegir uno lleva a la confirmación de deshacer sin
    registrar ninguna cita;
  - `/deshacer` sin argumento → `uso("deshacer")`.

### Implementation for User Story 5

- [X] T060 [US5] Agregar a `src/tarjeta_lealtad/servicio.py` `ultima_cita_vigente` y
  `deshacer_ultima(cliente_id, ahora)`: rellena `anulada_en`, nunca borra.
- [X] T061 [US5] Agregar a `src/tarjeta_lealtad/bot/textos.py` `confirmar_deshacer(cita, resumen, zona)`,
  `pie_deshacer(resumen, era_premio, numero)` y `nada_que_deshacer(resumen)`, según el
  [contrato § /deshacer](contracts/comandos-bot.md#deshacer-cliente).
- [X] T062 [US5] Implementar `/deshacer` en `src/tarjeta_lealtad/bot/handlers.py` (resolución sin
  `Crear`), el caso "elegir cliente" con `comando="deshacer"` y el caso "confirmar deshacer" del
  callback.
- [ ] T063 [US5] Correr los gates y validar las filas 10–11 de `quickstart.md` §5.

**Checkpoint**: los errores de registro se corrigen desde el bot.

---

## Phase 8: User Story 6 - Consultar clientes y tarjetas (Priority: P3)

**Goal**: `/clientes` lista el avance de todos y `/tarjeta <cliente>` reenvía la tarjeta sin
registrar una cita.

**Independent Test**: con varios clientes, la lista y la tarjeta coinciden con lo registrado y el
conteo no cambia (quickstart §5, fila 9).

### Tests for User Story 6 ⚠️

- [X] T064 [P] [US6] Crear `tests/integration/test_servicio_consultas.py`: `listar()` ordena por
  nombre normalizado y luego por `id`; los campos de `ResumenCliente` son correctos (`ultima_cita`
  solo con citas `bot`).
- [X] T065 [P] [US6] Ampliar `tests/bot/test_textos.py`:
  - `lista_clientes` produce `"Clientes (3):"`, `"#8 Carmen: 9/9 🎁"`,
    `"#3 Carmen: 4/9 · 1 completada"` y `"… · 2 completadas"`;
  - `dividir_mensajes(texto, 4000)` parte entre líneas y no pierde ninguna;
  - `SIN_CLIENTES`;
  - `pie_tarjeta` → `"🌸 Carmen (#3): 6 de 9 flores · 1 tarjeta completada."`.
- [X] T066 [P] [US6] Crear `tests/bot/test_handlers_consultas.py`:
  - `/clientes` envía uno o varios mensajes;
  - `/tarjeta Carmen` envía la foto con `pie_tarjeta` y el conteo no cambia;
  - `/tarjeta` con parecidos no ofrece `Crear`; elegir uno envía la foto y el conteo no cambia;
  - `/tarjeta` sin argumento → `uso("tarjeta")`.

### Implementation for User Story 6

- [X] T067 [US6] Agregar `listar()` a `src/tarjeta_lealtad/servicio.py`.
- [X] T068 [US6] Agregar a `src/tarjeta_lealtad/bot/textos.py` `lista_clientes`, `dividir_mensajes`,
  `SIN_CLIENTES` y `pie_tarjeta`, según el
  [contrato § /clientes y /tarjeta](contracts/comandos-bot.md#clientes).
- [X] T069 [US6] Implementar `/clientes` y `/tarjeta` en `src/tarjeta_lealtad/bot/handlers.py`
  (resolución sin `Crear`; el caso "elegir cliente" con `comando="tarjeta"` envía la foto **sin
  registrar cita**).
- [ ] T070 [US6] Correr los gates y validar con el bot de pruebas `quickstart.md` §5, fila 9, y `/clientes`.

**Checkpoint**: las seis historias funcionan.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: observabilidad, rendimiento, validación final y despliegue.

- [X] T071 [P] Registrar con `INFO` en `src/tarjeta_lealtad/bot/handlers.py` los eventos de dominio:
  cita registrada (ID del cliente y si fue premio), alta (ID y citas previas) y deshacer (ID).
  Usar **solo IDs**, no nombres (principio V).
- [X] T072 [P] Agregar a `tests/unit/test_render.py` una prueba de tiempo: `generar_tarjeta` tarda
  < 1 s con cada nombre de la lista de SC-006 (SC-002).
- [X] T073 Correr los cuatro gates de la constitución, configurados en `pyproject.toml` (`uv run ruff check`,
  `uv run ruff format --check`, `uv run mypy`, `uv run pytest`) y dejarlos en verde.
- [ ] T074 Validar completa la tabla de `quickstart.md` §5 con el bot de pruebas, incluidas las filas
  14 (otra cuenta) y 15 (bot detenido). Esta tarea es manual: la ejecuta el dueño desde el iPhone.
- [X] T075 [P] Actualizar `bot-tarjeta-lealtad-contexto.md`: cambiar el estado de "idea /
  definición" a "MVP implementado" y marcar los pasos 2 y 3 de "Próximos pasos".
- [ ] T076 Integrar la rama a `main` y desplegar en alwaysdata según `quickstart.md`
  [§6](quickstart.md#6-despliegue-en-alwaysdata). Es manual y requiere el token de
  producción y acceso a la cuenta.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (fase 1)**: sin dependencias.
- **Foundational (fase 2)**: depende de Setup y **bloquea** todas las historias.
- **US1 (fase 3)**: depende de Foundational. Es el MVP.
- **US2–US6 (fases 4–8)**: dependen de US1, que aporta la búsqueda, el alta por `/cita`,
  `registrar_cita`, `enviar_tarjeta` y el despachador de callbacks.
- **Polish (fase 9)**: depende de las historias que se quieran entregar.

### User Story Dependencies

| Historia | Depende de | Notas |
|----------|------------|-------|
| US1 (P1) | Foundational | MVP |
| US2 (P2) | US1 | Cambia `registrar_cita` y `pie_cita` |
| US3 (P2) | US1 | Extiende `crear_cliente`; primer camino para crear homónimos desde el bot |
| US4 (P2) | US1 (US3 para probarla desde el bot) | En el servicio se prueba creando homónimos directamente |
| US5 (P3) | US1 (US2 para el caso del premio) | |
| US6 (P3) | US1 | Solo lectura |

Tras US1, las historias US2, US3, US5 y US6 tocan los mismos archivos (`servicio.py`,
`handlers.py`, `textos.py`), así que conviene hacerlas **en serie**, en orden de prioridad.

### Within Each User Story

- Pruebas primero; deben fallar (principio III).
- Dominio (`busqueda`/`conteo`/`servicio`) → textos → handlers.
- Gates en verde y validación del quickstart antes de pasar a la siguiente historia.

### Parallel Opportunities

- **Setup**: T002 y T003.
- **Foundational**: las pruebas T007–T015 entre sí. Las implementaciones T016, T017, T018, T020,
  T022, T023 y T024 entre sí; T019 espera a T017, T021 a T018–T020, T025 a T021/T023/T024 y T026 a
  T025.
- **Cada historia**: sus tareas de pruebas [P] entre sí. La implementación empieza cuando sus
  pruebas están escritas y fallan (por ejemplo, T032 después de T028).

---

## Parallel Example: User Story 1

```bash
# Pruebas de US1 en paralelo (deben fallar):
Task: "T028 tests/unit/test_busqueda.py"
Task: "T029 tests/integration/test_servicio_cita.py"
Task: "T030 tests/bot/test_handlers_cita.py"
Task: "T031 tests/bot/test_textos.py (pie_cita, etiqueta_cliente, confirmaciones)"

# Cuando T028 esté en rojo:
Task: "T032 src/tarjeta_lealtad/busqueda.py"
```

## Parallel Example: Foundational

```bash
Task: "T016 src/tarjeta_lealtad/config.py"
Task: "T017 src/tarjeta_lealtad/diseno.py"
Task: "T018 src/tarjeta_lealtad/conteo.py"
Task: "T020 src/tarjeta_lealtad/db.py"
Task: "T022 src/tarjeta_lealtad/bot/seguridad.py"
Task: "T023 src/tarjeta_lealtad/bot/acciones.py"
Task: "T024 src/tarjeta_lealtad/bot/textos.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Fase 1 (Setup) y fase 2 (Foundational).
2. Fase 3 (US1).
3. **PARAR Y VALIDAR**: filas 1–4 y 16 del quickstart con el bot de pruebas.
4. Con esto el dueño ya registra citas y reenvía tarjetas en el bot de pruebas. A producción se
   despliega con todas las historias (T076), porque la ayuda y el mensaje de error ya mencionan
   `/tarjeta` y los demás comandos.

### Incremental Delivery

1. US1, el MVP.
2. US2: los clientes frecuentes llegan a la cita 10 en pocas semanas, así que es lo siguiente.
3. US3: migrar a los clientes con tarjetas en curso antes del uso real.
4. US4 → US5 → US6.
5. Polish y despliegue.

---

## Notes

- Las tareas marcadas [P] usan archivos distintos y no tienen dependencias pendientes.
- La etiqueta de historia permite rastrear cada tarea hasta la spec.
- Se recomienda un commit por tarea o grupo lógico (mensajes en español, como el historial).
- No guardar tarjetas generadas en disco ni versionar `.env` o `data/`.
