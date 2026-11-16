# Implementation Plan: Registro de citas y tarjeta de lealtad

**Branch**: `001-registro-citas-tarjeta` | **Date**: 2026-11-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-registro-citas-tarjeta/spec.md`

## Summary

Bot de Telegram de un solo usuario que registra citas como eventos en SQLite y devuelve, como foto,
la tarjeta de lealtad del cliente generada desde cero. La tarjeta combina la plantilla vacía, el
nombre en Sacramento ajustado para no tocar el ✨ y una flor por cita.

El ciclo de tarjeta (9 flores + cita de premio, N configurable) **se deriva** de las citas
vigentes: cada cita guarda si cerró una tarjeta y deshacer solo la anula. Así, deshacer un premio
reabre la tarjeta sin lógica adicional ([research §6](research.md#6-modelo-de-ciclo-de-tarjeta-derivado-de-eventos)).

El dominio (conteo, búsqueda, render, servicio) es Python puro probado con TDD. `bot/` es una capa
delgada de aiogram que procesa los mensajes en serie y resuelve confirmaciones con acciones
pendientes en memoria.

## Technical Context

**Language/Version**: Python 3.12 (`.python-version`; intérprete gestionado por uv)

**Primary Dependencies**: aiogram ≥ 3.32, Pillow ≥ 13, SQLAlchemy ≥ 2.0 (resuelve a 2.1.x, API
tipada estilo 2.0), pydantic-settings ≥ 2.16. Desarrollo: pytest ≥ 9, pytest-asyncio ≥ 1.5,
ruff ≥ 0.17, mypy ≥ 2.4. Build backend: `uv_build`.

**Storage**: SQLite en `data/lealtad.db` (tablas `clientes` y `citas`, ver [data-model.md](data-model.md))

**Testing**: pytest + pytest-asyncio (`asyncio_mode = "auto"`); render verificado por píxeles

**Target Platform**: Linux; *Service* de alwaysdata con long polling

**Project Type**: proceso único (bot de Telegram) con paquete Python en `src/`

**Performance Goals**: foto de la tarjeta en < 5 s en el 95 % de los casos (SC-002); render < 1 s

**Constraints**: un usuario; procesamiento en serie (`handle_as_tasks=False`); sin Docker, webhook
ni dependencias de sistema; imágenes solo en memoria

**Scale/Scope**: < 200 clientes, ~18 citas por semana (~1 000 por año); 6 comandos

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Verificación | Antes de Fase 0 | Después de Fase 1 |
|-----------|--------------|-----------------|-------------------|
| I. Simplicidad (YAGNI) | Un proceso y un usuario. Sin colas, caché, API propia ni capa de repositorio: `servicio.py` usa la sesión directamente. Sin `aiosqlite` ni Alembic. El registro de acciones pendientes tiene una necesidad documentada (callback ≤ 64 bytes y FR-011, [research §5](research.md#5-acciones-pendientes-confirmaciones-y-selección)). | ✅ | ✅ |
| II. Dominio separado de Telegram | `conteo`, `busqueda`, `diseno`, `render`, `db` y `servicio` no importan `aiogram`. Una prueba de arquitectura (AST) lo verifica. `bot/` solo traduce entre Telegram y el [contrato del servicio](contracts/servicio-dominio.md). | ✅ | ✅ |
| III. TDD en el dominio | Pruebas primero para conteo y ciclo, deshacer (en conteo y servicio) y render (flores por casilla, nombre, ✨ intacto, determinismo). El orden en `tasks.md` debe ser prueba → implementación. | ✅ | ✅ |
| IV. Los datos son la fuente de verdad | La tarjeta se regenera siempre desde la base de datos. Las citas son eventos que se anulan sin borrarse. Las tarjetas se derivan, sin contadores guardados. Las coordenadas viven en `diseno.py`, versionado. | ✅ | ✅ |
| V. Seguridad básica | El middleware de solo dueño descarta y registra lo demás. Los secretos van en `.env` (ignorado). La base no se versiona: se agregó `data/` a `.gitignore` para cubrir también los archivos `-journal`/`-wal` de SQLite. Las imágenes no se escriben a disco. | ✅ | ✅ |
| VI. Compatible con alwaysdata | *Service* con long polling. Despliegue = `uv sync --frozen --no-dev` + reinicio. SQLite en un archivo. Pillow desde wheels. | ✅ | ✅ |
| Restricciones de stack | Solo herramientas de la constitución. `uv_build` es el backend de empaquetado de uv, no una dependencia de ejecución. SQLAlchemy 2.1 conserva la API tipada 2.0. | ✅ | ✅ |
| Flujo de desarrollo | Rama `001-registro-citas-tarjeta`. Gates: `ruff check`, `ruff format --check`, `mypy`, `pytest` ([quickstart §3](quickstart.md#3-gates-de-calidad-constitución-obligatorios-antes-de-integrar-a-main)). | ✅ | ✅ |

**Resultado**: sin violaciones. El registro de acciones pendientes queda justificado en Complexity
Tracking (principio I).

## Project Structure

### Documentation (this feature)

```text
specs/001-registro-citas-tarjeta/
├── plan.md                    # Este archivo
├── research.md                # Fase 0: versiones, API verificada y decisiones
├── data-model.md              # Fase 1: tablas, vistas derivadas y transiciones
├── quickstart.md              # Fase 1: entorno, gates, validación y despliegue
├── contracts/
│   ├── comandos-bot.md        # Interfaz del dueño (comandos, botones, mensajes)
│   └── servicio-dominio.md    # Frontera dominio ↔ bot (principio II)
├── checklists/
│   └── requirements.md        # Calidad de la spec
└── tasks.md                   # Fase 2 (/speckit-tasks; no lo crea este comando)
```

### Source Code (repository root)

```text
pyproject.toml                 # dependencias, ruff, mypy (strict), pytest
uv.lock                        # versionado
.python-version                # 3.12
.env.example                   # variables sin valores reales
assets/                        # ya existe
├── plantilla-vacia.png
├── flor.png
└── fuentes/
    ├── Sacramento-Regular.ttf
    └── OFL.txt
src/tarjeta_lealtad/
├── __init__.py
├── __main__.py                # python -m tarjeta_lealtad → bot.app.main()
├── config.py                  # Ajustes (pydantic-settings) + verificar_diseno
├── diseno.py                  # coordenadas, tamaños y rutas de assets
├── conteo.py                  # ciclo de tarjeta derivado (puro)
├── busqueda.py                # normalización, ID, parecidos y validación de caracteres (puro)
├── render.py                  # ajustar_nombre, generar_tarjeta (Pillow)
├── db.py                      # modelos SQLAlchemy, UTCDateTime, motor y sesiones
├── servicio.py                # casos de uso (contrato servicio-dominio)
└── bot/
    ├── __init__.py
    ├── app.py                 # arranque: ajustes, verificación, BD, comandos, polling
    ├── seguridad.py           # middleware de solo dueño
    ├── acciones.py            # registro de acciones pendientes (token → acción)
    ├── handlers.py            # comandos y callbacks
    └── textos.py              # mensajes, etiquetas de botones y división de listas
tests/
├── conftest.py                # servicio sobre SQLite en tmp_path, relojes fijos
├── unit/
│   ├── test_conteo.py
│   ├── test_busqueda.py
│   ├── test_render.py         # píxeles, ✨, determinismo, lista de nombres de SC-006
│   ├── test_config.py
│   └── test_arquitectura.py   # el dominio no importa aiogram
├── integration/
│   └── test_servicio.py       # ciclo completo, alta, homónimos, deshacer premio, cambio de N
└── bot/
    ├── test_seguridad.py
    ├── test_acciones.py       # un solo efecto por token
    └── test_handlers.py       # flujos con AsyncMock
```

**Structure Decision**: un solo proyecto con *src layout* y el paquete `tarjeta_lealtad`. Los
módulos de dominio quedan planos en la raíz del paquete (son seis y pequeños). Todo lo que depende
de aiogram está en `bot/`, la frontera del principio II. `assets/` se queda en la raíz del repo y
`diseno.py` resuelve las rutas respecto al paquete; uv instala el proyecto en modo editable, así
que funciona igual en local y en alwaysdata.

## Cambios a la spec durante el plan

- **FR-027 y la aclaración sobre el tamaño del nombre**: la medida pasó de "alto de la tinta, mínimo
  43 px" a "tamaño de fuente, máximo el que reproduce el nombre del ejemplo (117), mínimo 36". La
  altura de la tinta depende de las letras y habría rechazado nombres legibles
  ([research §9](research.md#9-render-de-la-tarjeta-pillow)).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Registro de acciones pendientes en memoria (`bot/acciones.py`) | Los datos de un botón de Telegram admiten como máximo 64 bytes (un nombre largo no cabe) y FR-011 exige un solo efecto por toque. | Una tabla en SQLite agrega una entidad sin necesidad (los botones solo caducan tras un reinicio); poner todos los datos en el botón no cabe. |
