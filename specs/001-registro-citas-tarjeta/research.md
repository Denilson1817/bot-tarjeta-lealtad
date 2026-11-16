# Research: Registro de citas y tarjeta de lealtad

**Feature**: `001-registro-citas-tarjeta` | **Fecha**: 2026-11-16

El stack lo fija la constitución; no hubo `NEEDS CLARIFICATION` en el contexto técnico. Esta fase
verifica versiones y API reales y fija las decisiones de diseño que la spec deja abiertas.

## 1. Versiones de dependencias (verificadas en PyPI, 2026-11-16)

| Paquete | Versión actual | Restricción en `pyproject.toml` |
|---------|----------------|---------------------------------|
| aiogram | 3.32.0 | `aiogram>=3.32,<4` |
| Pillow | 13.0.0 | `pillow>=13,<14` |
| SQLAlchemy | 2.1.8 | `sqlalchemy>=2.0,<3` |
| pydantic-settings | 2.16.3 | `pydantic-settings>=2.16,<3` |
| pytest (dev) | 9.2.0 | `pytest>=9` |
| pytest-asyncio (dev) | 1.5.0 | `pytest-asyncio>=1.5` |
| ruff (dev) | 0.17.5 | `ruff>=0.17` |
| mypy (dev) | 2.4.1 | `mypy>=2.4` |

- **Decision**: esas restricciones, con `uv.lock` versionado como fuente de verdad.
- **Rationale**: todas soportan Python 3.12. SQLAlchemy 2.1 conserva la API tipada estilo 2.0
  (`Mapped[...]`, `mapped_column`) que exige la constitución, así que cumple el principio.
- **Alternatives considered**: fijar versiones exactas en `pyproject.toml` (redundante con el
  lockfile).

## 2. Versión de Python y entorno

- **Decision**: `requires-python = ">=3.12"` y `.python-version` = `3.12`. uv gestiona el
  intérprete tanto en local como en alwaysdata.
- **Rationale**: la constitución pide 3.12+. Fijar 3.12 en desarrollo evita usar algo de 3.13/3.14
  que falle en el servidor. `ruff` (`target-version = "py312"`) y `mypy` (`python_version = "3.12"`)
  lo refuerzan.
- **Hallazgo**: en la máquina de desarrollo `/etc/uv/uv.toml` define `python-downloads = "manual"`,
  así que hay que ejecutar `uv python install 3.12` una vez (ver quickstart).
- **Alternatives considered**: usar el 3.14 del sistema en local (riesgo de divergencia con
  producción).

## 3. Procesamiento de mensajes en aiogram 3

- **Decision**: long polling con `dp.start_polling(bot, handle_as_tasks=False)`, sin descartar los
  mensajes pendientes al arrancar.
- **Rationale**:
  - Con `handle_as_tasks=False` (por defecto es `True`, verificado en aiogram 3.32) los mensajes se
    procesan uno a uno. Con un solo usuario no se pierde nada y desaparecen las condiciones de
    carrera: un doble toque en un botón se procesa en serie, lo que hace trivial cumplir FR-011.
  - No descartar pendientes cumple el caso borde de "comandos enviados mientras el bot estaba
    detenido". Telegram los guarda hasta 24 h.
- **Alternatives considered**: concurrencia con locks (complejidad sin beneficio); webhook
  (prohibido por el principio VI).

## 4. Fecha de las citas

- **Decision**: la cita toma `message.date` del comando original, en UTC. Si pasa por una
  confirmación, se usa la fecha del comando que la originó, no la del toque al botón. Se guarda en
  UTC y se convierte a la zona del negocio (`ZONA_HORARIA`) para mostrarla y para la regla de
  "mismo día" (FR-010).
- **Rationale**: FR-008 y el caso borde de mensajes atrasados.
- **Alternatives considered**: hora de procesamiento (falla con mensajes atrasados).

## 5. Acciones pendientes (confirmaciones y selección)

- **Decision**: guardar en memoria del proceso un registro `token → acción` (tipo, comando
  que la originó, cliente(s), nombre, fecha del comando original). El botón solo lleva el token corto. Al pulsarlo, la acción
  se *extrae* del registro (pop) y se ejecuta; un segundo toque ya no la encuentra y el bot responde
  "Esta acción ya se aplicó o caducó".
- **Rationale**:
  - Los datos del botón de Telegram tienen como máximo 64 bytes y un nombre largo no cabe.
  - El pop, junto con el procesamiento en serie (§3), garantiza un solo efecto (FR-011).
  - Si el bot se reinicia, los botones antiguos solo caducan: el dueño repite el comando.
- **Alternatives considered**: tabla en SQLite de acciones (sobrevive reinicios, pero agrega una
  entidad sin necesidad real); datos completos en el botón (no caben).
- **Constitución**: es estado de interacción de la capa de Telegram, no una caché ni una capa
  nueva; vive en `bot/` y el dominio no lo conoce.

## 6. Modelo de ciclo de tarjeta: derivado de eventos

- **Decision**: no hay tabla de tarjetas. Cada `Cita` guarda `es_premio`, que se marca al registrar
  la cita que cierra una tarjeta, y `anulada_en`. Las tarjetas se derivan recorriendo las citas
  vigentes en orden de `id`:
  - cada cita vigente con `es_premio` cierra una tarjeta, cuya fecha de cierre es la de esa cita;
  - la tarjeta en curso son las citas vigentes posteriores al último premio vigente.
- **Rationale**:
  - Principio IV: el conteo se deriva de eventos y no hay contadores que mantener en sincronía.
  - Deshacer el premio basta para reabrir la tarjeta (FR-024): al anularse, la tarjeta se une con
    sus 9 citas. Como deshacer siempre anula la cita más reciente, nunca se mezclan tarjetas.
  - Cambiar N no altera tarjetas completadas (FR-016), porque el cierre quedó marcado en la cita y
    no se recalcula con N.
- **Regla de premio**: al registrar, si `citas_en_curso >= N − 1`, la nueva cita es la de premio.
  Esto cubre el caso de bajar N con tarjetas en curso.
- **Orden**: por `id` autoincremental. El procesamiento es en serie, así que el orden de inserción
  es el orden real; las citas previas al alta no tienen fecha y van primero porque se insertan al
  crear al cliente.
- **Alternatives considered**: tabla `tarjetas` con estado (dos fuentes de verdad; reabrir exige
  más lógica); conteo total módulo N (cambiar N reescribiría el historial).

## 7. Búsqueda de clientes

- **Decision** (módulo puro `busqueda.py`, sin dependencias nuevas):
  - **Normalización**: NFKD, quitar marcas diacríticas, `casefold()` y colapsar espacios. Así
    "Cármen" = "carmen" y, por quitar diacríticos, también "Peña" = "Pena" (aceptable: solo hace
    la búsqueda más tolerante).
  - **Identificador**: si el argumento es `#12` o `12`, se busca por ID.
  - **Exacta**: nombre normalizado igual al texto normalizado. Una coincidencia → actuar; varias →
    elegir.
  - **Parecida** (solo si no hubo exacta):
    1. distancia de Damerau-Levenshtein (variante OSA: falta, sobra, cambia o se intercambia una
       letra) ≤ 2 contra el nombre completo o contra cualquiera de sus palabras; o
    2. el texto es prefijo del nombre completo o de alguna de sus palabras.
  - **Orden de sugerencias**: por distancia y luego por nombre; máximo 6 botones más "Crear nuevo"
    y "Cancelar".
- **Rationale**: implementa FR-005 a FR-007 tal como los definió la spec, en unas 30 líneas
  probadas por TDD.
- **Alternatives considered**: `rapidfuzz` (dependencia nueva sin necesidad para menos de 200
  nombres).

## 8. Validación de nombres

- **Decision**:
  - Caracteres permitidos: letras ASCII, letras Latin-1 (`À`–`ÿ`, sin `×` ni `÷`), espacio,
    apóstrofo, guion y punto. Debe haber al menos una letra.
  - No se admiten dígitos, para que `/alta Rosa 6` sea inequívoco.
  - Espacios colapsados y recortados.
  - Debe caber en la tarjeta según §9.
- **Rationale**: se verificó con fontTools que Sacramento contiene todas las letras Latin-1. Una
  prueba con Pillow compara cada carácter permitido contra el glifo "no definido" de la fuente
  (sin agregar fontTools al proyecto).
- **Alternatives considered**: leer el `cmap` de la fuente en tiempo de ejecución (requiere
  fontTools); admitir cualquier carácter (dibujaría cuadros vacíos).

## 9. Render de la tarjeta (Pillow)

- **Decision**: geometría versionada en `diseno.py`, medida sobre la tarjeta de referencia:

  | Elemento | Valor |
  |----------|-------|
  | Lienzo | 1050 × 600, `assets/plantilla-vacia.png` |
  | Centros de casillas | x = 584.0, 769.5, 954.5; y = 119.0, 301.0, 483.0; orden por filas |
  | Flor | `assets/flor.png`, 115 × 115 RGBA; esquina = (⌊cx⌋ − 57, ⌊cy⌋ − 57) |
  | Nombre: centro horizontal | x = 245 (centro de la línea) |
  | Nombre: borde inferior de la tinta | y = 370 (la línea empieza en y = 378) |
  | Nombre: ancho máximo de tinta | 390 px (x 50–440, largo de la línea) |
  | Nombre: borde superior de la tinta | y ≥ 246 (el título termina en y = 234) |
  | Nombre: tamaño de fuente | máximo 117 px (con él "Carmen" mide 86 px de alto, como en el ejemplo); mínimo 36 px |
  | Zona prohibida del ✨ | x 310–354, y 274–323 (destello x 316–348, y 280–317 + 6 px) |
  | Fuente | `assets/fuentes/Sacramento-Regular.ttf`, color blanco |

- **Ajuste del nombre**: se busca el mayor tamaño de fuente ≤ 117 cuya tinta cumpla ancho ≤ 390,
  borde superior en y ≥ 246 (para no tocar el título) y ningún píxel dentro de la zona del ✨. La comprobación se hace sobre la máscara real del
  texto, no sobre su caja, porque las minúsculas pueden pasar por debajo del destello. Si el tamaño
  resultante es menor de 36, el nombre se rechaza con `NombreNoCabe`.
- **Por qué tamaño de fuente y no alto de tinta**: el alto de la tinta depende de las letras. Por
  ejemplo, "Marisol Del Castillo" con tamaño 50 mide solo 40 px de alto por no tener letras que
  bajan de la línea (g, j, p, q, y), aunque se ve más grande que "María Fernanda Ruiz" con tamaño
  39. Un umbral por alto de tinta rechazaría nombres legibles.
- **Validación previa (2026-11-16)**, con borde inferior en y = 370:
  - "Carmen": tamaño 117.
  - "Isabel": tamaño 67; su "l" final chocaría con el ✨ a mayor tamaño.
  - Nombres de 19–20 caracteres probados ("María Fernanda Ruiz", "Maximiliana Montoya",
    "Wilhelmina Whitfield", "Itzel Bethel Ballard", "Marisol Del Castillo"…): tamaños 37–50.
  - Con 36 un nombre largo sigue siendo legible a escala de teléfono; con 32 ya cuesta.
  - Sin el tope superior, "Ángela" e "Íñigo" con tamaño 117 empezarían en y ≈ 202–206 y tocarían
    el título. Con todas las restricciones quedan en tamaños 60 y 68 (el ✨ es el límite que
    manda); el tope no cambia ninguno de los tamaños anteriores.
- **Determinismo**: mismos datos producen los mismos bytes PNG (FR-029). La versión de Pillow
  (que trae FreeType incluido) queda fijada por `uv.lock`.
- **Salida**: PNG en memoria → `BufferedInputFile(bytes, "tarjeta.png")` → `answer_photo`. Telegram
  la recomprime como foto, igual que WhatsApp después.
- **Alternatives considered**:
  - Alinear el nombre por la línea base (los descendentes podrían tocar la línea).
  - Usar la caja del texto contra el ✨ (rechazaría "Carmen" sin necesidad).
  - Comparar contra imágenes de referencia (frágil ante cambios de FreeType). Las pruebas verifican
    píxeles en posiciones conocidas.

## 10. Persistencia

- **Decision**:
  - SQLAlchemy 2.x **síncrono** sobre SQLite en `data/lealtad.db` (ruta configurable).
  - Tablas creadas con `metadata.create_all()` al arrancar.
  - `AUTOINCREMENT` en las claves para que los IDs nunca se reutilicen (FR-003).
  - Fechas guardadas como UTC con un `TypeDecorator` que devuelve `datetime` con zona UTC.
- **Rationale**:
  - Con un usuario y consultas de milisegundos, bloquear el event loop es irrelevante. Async
    exigiría `aiosqlite`, una dependencia que no se justifica.
  - Alembic tampoco se justifica para un esquema nuevo de dos tablas; se agregará cuando haya la
    primera migración real.
- **Alternatives considered**: `sqlalchemy[asyncio]` + `aiosqlite`; Alembic desde el día uno.

## 11. Configuración y arranque

- **Decision**: `pydantic-settings` lee `.env`:
  - `BOT_TOKEN` (SecretStr) y `OWNER_ID` (int), obligatorios;
  - `CITAS_POR_TARJETA` (int ≥ 2, por defecto 10);
  - `ZONA_HORARIA` (nombre IANA, obligatorio, validado con `zoneinfo`);
  - `DB_PATH` (por defecto `data/lealtad.db`);
  - `LOG_LEVEL` (por defecto `INFO`).

  Al arrancar se comprueba que el número de casillas de `diseno.py` sea igual a N − 1. Si no, se
  registra el error y el proceso sale con código 1 (FR-017). También se comprueba que los assets
  carguen y se registran los comandos en el menú de Telegram (`set_my_commands`).
- **Rationale**: principios V y VI; fallar pronto si algo está mal configurado.
- **Nota**: `zoneinfo` usa la base de zonas del sistema (presente en alwaysdata). Si faltara, se
  agregaría `tzdata`.

## 12. Seguridad

- **Decision**: un *outer middleware* sobre los updates descarta todo lo que no venga de
  `OWNER_ID` antes de llegar a cualquier handler. Registra con nivel `WARNING` el ID y el usuario
  del remitente y no responde.
- **Rationale**: FR-001, SC-008, principio V; un único punto de control en lugar de un filtro por
  handler.

## 13. Despliegue en alwaysdata

- **Decision**:
  - Instalar uv en la cuenta, clonar el repo, `uv python install 3.12` si hace falta,
    `uv sync --frozen --no-dev` y crear el `.env`.
  - Crear un *Service* con el comando `.venv/bin/python -m tarjeta_lealtad`, cuyo directorio de
    trabajo es el repo.
  - Actualizar: `git pull && uv sync --frozen --no-dev` y reiniciar el servicio.
- **Rationale**: principio VI (sin Docker, sin dominio, despliegue repetible).

## 14. Estrategia de pruebas

- **Decision**:
  - **Dominio, por TDD obligatorio** (`tests/unit`): conteo y ciclo, búsqueda, validación de
    nombres, render y configuración.
  - **Integración** (`tests/integration`): servicio sobre SQLite en `tmp_path`.
  - **Bot, pruebas ligeras** (`tests/bot`): handlers con mensajes simulados (`AsyncMock`), el
    middleware y la idempotencia de acciones.
  - `asyncio_mode = "auto"` en pytest-asyncio 1.x.
- **Rationale**: principio III; ninguna prueba necesita red ni token.
