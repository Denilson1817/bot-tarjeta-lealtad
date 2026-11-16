# Implementation Plan: Publicación en alwaysdata (plan Free) con webhook

**Branch**: `002-despliegue-webhook-alwaysdata` | **Date**: 2026-11-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-despliegue-webhook-alwaysdata/spec.md`

## Summary

El bot pasa a tener dos modos, elegidos solo por configuración, que comparten handlers, dominio y
base de datos:
- **polling** (como hoy) en la computadora del dueño;
- **webhook** en un sitio *User program* de alwaysdata Free, en `CUENTA.alwaysdata.net/tarjeta`,
  sin tocar el bot de finanzas.

La memoria medida obliga a cambiar la librería de Telegram. Con aiogram el bot ocupa ~186 MB y no
cabe junto al bot de finanzas en los 256 MB de la cuenta; con **python-telegram-bot** ocupa ~96 MB
(decisión del dueño, constitución v3.0.0). Por eso esta feature:
1. reescribe la capa `bot/` sobre python-telegram-bot, sin tocar el dominio;
2. agrega un servidor Starlette + uvicorn, con el mismo patrón que el bot de finanzas, que:
   - valida el token secreto;
   - procesa en serie y una sola vez;
   - responde "ok" a un GET;
3. agrega a la configuración el modo webhook y el resguardo de polling;
4. publica el código en un repositorio público de GitHub y deja la guía de despliegue,
   actualización y vuelta atrás en el README.

## Technical Context

**Language/Version**: Python 3.12 (sin cambios; en el servidor, el 3.12 de alwaysdata vía `PYTHON_VERSION`)

**Primary Dependencies**:
- **Entran**: `python-telegram-bot` ≥ 22.8,<23, `starlette` ≥ 1.10,<2 y `uvicorn` ≥ 0.54,<1.
- **Sale**: `aiogram`.
- **Siguen**: Pillow, SQLAlchemy 2.x y pydantic-settings.
- **Desarrollo**: sin cambios (pytest, pytest-asyncio, ruff, mypy). `httpx`, que llega con
  python-telegram-bot, permite usar el `TestClient` de Starlette.

**Storage**: SQLite sin cambios de esquema; en producción, la ruta absoluta de `DB_PATH` en el servidor

**Testing**: pytest + pytest-asyncio
- dominio: las pruebas de la 001, sin cambios;
- capa de Telegram: con `MagicMock(spec=Message)` y `FakeTelegramAPI(BaseRequest)`;
- servidor web: con `TestClient`.

**Target Platform**:
- alwaysdata Free: sitio *User program*, ¼ de CPU, 256 MB de RAM para la cuenta;
- local: Linux en polling.

**Project Type**: proceso único (bot de Telegram) con un servidor web opcional en el mismo proceso

**Performance Goals**: foto en < 5 s con el bot despierto (SC-002); listo en < 10 s al despertar (FR-012); primera respuesta tras una pausa en < 15 s (SC-003)

**Constraints**:
- **memoria** < 120 MB (medido: ~96 MB; la cuenta queda por debajo de 200 MB con el bot de
  finanzas);
- **disco** < 300 MB (medido: ~100 MB);
- **procesamiento**: en serie y una vez por `update_id`.

**Scale/Scope**: un usuario; ~18 citas por semana; 2 modos; 1 sitio nuevo en alwaysdata

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* Constitución **v3.0.0**.

| Principio | Verificación | Antes de Fase 0 | Después de Fase 1 |
|-----------|--------------|-----------------|-------------------|
| I. Simplicidad | **Un proceso, un usuario.** El servidor web vive en el mismo proceso que el bot. **Sin colas ni base nueva.** El registro de `update_id` es un conjunto en memoria acotado a 1 000, con necesidad documentada (FR-009, ver Complexity Tracking). **Sin capa de abstracción** sobre la librería de Telegram. | ✅ | ✅ |
| II. Dominio separado | `conteo`, `busqueda`, `render`, `db`, `servicio` y `diseno` no cambian; `config` solo suma campos. La prueba de arquitectura pasa a vigilar `telegram`, `starlette` y `uvicorn`, además de `aiogram`. | ✅ | ✅ |
| III. TDD en el dominio | El dominio no cambia y sus pruebas siguen en verde. Lo nuevo de configuración y servidor web también se escribe con prueba primero (validaciones, 403, duplicados, serie). | ✅ | ✅ |
| IV. Datos como fuente de verdad | Sin cambios en el modelo. El estado en memoria (acciones, `update_id`) no afecta la corrección de los datos ([data-model](data-model.md)). | ✅ | ✅ |
| V. Seguridad | Filtro del dueño en ambos modos (`TypeHandler` en el grupo -1). Token secreto con `compare_digest`. Secretos solo en el `.env` del servidor (`chmod 600`). El repositorio es público, pero sin `.env`, base de datos, ID ni token ([quickstart](quickstart.md)). | ✅ | ✅ |
| VI. alwaysdata Free | Sitio *User program* en `$IP:$PORT`, webhook HTTPS en `*.alwaysdata.net`, Starlette + uvicorn. Modo por configuración (`WEBHOOK_URL`). Despliegue = `uv sync` + reinicio. Memoria ~96 MB con el bot de finanzas al lado. Arranque estimado < 10 s. | ✅ | ✅ |
| Stack | Coincide con la tabla v3.0.0 (python-telegram-bot 22, Starlette + uvicorn). aiogram se elimina. | ✅ | ✅ |
| Flujo | Rama `002-despliegue-webhook-alwaysdata`; la primera publicación se hace desde la rama y la integración a `main` ocurre al terminar, después de validar en producción, con los gates en verde. La enmienda v3.0.0 va en su propio commit. | ✅ | ✅ |

**Resultado**: pasa. Las justificaciones de complejidad están en Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/002-despliegue-webhook-alwaysdata/
├── plan.md
├── research.md                  # Fase 0: alwaysdata, memoria medida y decisiones
├── data-model.md                # sin cambios de esquema; estado en memoria
├── quickstart.md                # validación, publicación y mantenimiento
├── contracts/
│   ├── webhook-http.md          # POST/GET del sitio, códigos, setWebhook
│   └── configuracion.md         # variables, validaciones y selección de modo
├── checklists/requirements.md
└── tasks.md                     # /speckit-tasks
```

### Source Code (repository root)

```text
pyproject.toml                   # − aiogram; + python-telegram-bot, starlette, uvicorn
uv.lock
.env.example                     # + WEBHOOK_URL, WEBHOOK_SECRET (comentadas)
README.md                        # NUEVO: uso local, publicación, actualización, vuelta atrás, logs, secretos
src/tarjeta_lealtad/
├── config.py                    # + webhook_url, webhook_secret, ip, port y sus validaciones; modo
├── (conteo, busqueda, render, db, servicio, diseno)   # sin cambios
└── bot/
    ├── acciones.py              # sin aiogram: Accion, AccionesPendientes, empaquetar/desempaquetar "a:<token>:<opción>"
    ├── seguridad.py             # solo_dueno(): TypeHandler del grupo -1 → ApplicationHandlerStop
    ├── textos.py                # sin cambios
    ├── handlers.py              # mismos flujos sobre python-telegram-bot; registrar_handlers(app)
    ├── web.py                   # NUEVO: app Starlette (lifespan, POST con token y duplicados, GET "ok")
    └── app.py                   # crear_aplicacion(); main(): elige el modo, resguardo de polling, uvicorn
tests/
├── unit/                        # sin cambios + test_config (modos y webhook) + arquitectura ampliada
├── integration/                 # sin cambios (dominio)
└── bot/                         # reescritas para python-telegram-bot
    ├── conftest.py              # fakes de Message/CallbackQuery/context y FakeTelegramAPI(BaseRequest)
    ├── test_acciones.py, test_seguridad.py, test_textos.py
    ├── test_handlers_cita.py, _alta, _deshacer, _consultas
    ├── test_integracion_app.py  # Application real + FakeTelegramAPI (sustituye test_integracion_dispatcher)
    ├── test_web.py              # NUEVO: 403, 400, duplicados, serie, "ok", setWebhook
    └── test_app.py              # NUEVO: selección de modo y resguardo de polling
```

**Structure Decision**: se mantiene la estructura de la 001. Solo cambia la capa `bot/`, que la
constitución ya aislaba (principio II); se agregan `bot/web.py` y el `README.md`. Las fixtures de
la capa de Telegram pasan a `tests/bot/conftest.py`, para no mezclarlas con las del dominio.

## Cambios a la spec durante el plan

- **FR-015**: el presupuesto de memoria pasó de "< 100 MB" a "< 120 MB, con la cuenta por debajo
  de 200 MB junto al bot de finanzas". Con aiogram se midieron ~186 MB; con python-telegram-bot,
  ~96 MB ([research §2](research.md#2-librería-de-telegram-python-telegram-bot)).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Registro de acciones pendientes en memoria (de la 001, se conserva) | Los datos de un botón de Telegram admiten como máximo 64 bytes, y FR-011 de la 001 exige un solo efecto por toque. | Tabla en SQLite: agrega una entidad sin necesidad. |
| Registro en memoria de los últimos 1 000 `update_id` (nuevo) | Telegram reenvía un update si no recibe respuesta a tiempo (por ejemplo, al despertar); FR-009 exige procesarlo una sola vez. | Tabla en SQLite: más esquema para un caso que, tras un reinicio, ya frenan las confirmaciones de la 001. Sin registro: se procesaría dos veces un update reenviado. |
| Reescritura de la capa `bot/` (cambio de librería) | Con aiogram el bot no cabe en la memoria de la cuenta Free junto al bot de finanzas (~260 MB de 256). | Plan Small, parche de aiogram o asumir el riesgo: el dueño eligió el cambio de librería (2026-11-16). |
