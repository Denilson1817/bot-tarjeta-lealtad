# Research: Publicación en alwaysdata (plan Free) con webhook

**Feature**: `002-despliegue-webhook-alwaysdata` | **Fecha**: 2026-11-16

Todas las cifras de este documento se midieron en la máquina de desarrollo el 2026-11-16, salvo
las que se citan de la documentación de alwaysdata.

## 1. Restricciones de alwaysdata (documentación oficial)

| Hecho | Fuente |
|-------|--------|
| *Services* solo en planes de pago ("available on all our paid plans") | `web-hosting/services/index.md` |
| Plan Free: 1 GB de disco, **256 MB de RAM**, ¼ de CPU; plan Small: 1 GB de RAM, 5–6 €/mes | `admin-billing/billing/public-cloud-prices.md` |
| *User program*: comando, directorio de trabajo, variables de entorno; logs en `/home/CUENTA/admin/logs/sites/` | `web-hosting/sites/http-servers/user-program/index.md` |
| El sitio arranca con la primera petición, se detiene tras el *idle time* (30 min, configurable; `0` = nunca) y **nunca corre en varias instancias a la vez**, ni siquiera durante un reinicio | `web-hosting/sites/misc.md` |
| `SIGTERM` → `SIGKILL` tras 30 s | `technical-specifications/limits` |
| Las direcciones de un sitio pueden **contener una ruta**; `path_trim` decide si se recorta antes de llegar a la aplicación | API `v1/site` (campo `path_trim`) |
| La versión de Python se elige con la variable `PYTHON_VERSION` | `web-hosting/languages/python/configuration/index.md` |

## 2. Librería de Telegram: python-telegram-bot

- **Decision**: reemplazar `aiogram` 3.32 por `python-telegram-bot` 22.8 (decisión del dueño;
  constitución v3.0.0).
- **Rationale** (medido):

  | Proceso | Memoria (RSS) |
  |---------|---------------|
  | Bot de tarjetas con aiogram (imports + servidor web + tarjeta generada) | ~186–194 MB |
  | Bot de tarjetas con python-telegram-bot + Starlette + uvicorn (misma prueba) | **~96 MB** |
  | Bot de finanzas del dueño (python-telegram-bot + Starlette + uvicorn) | ~77 MB |

  Con aiogram, los dos bots juntos (~260 MB) superan los 256 MB de la cuenta. El costo de aiogram
  viene de su `aiogram/types/__init__.py`, que llama `model_rebuild()` en todos los tipos de la API
  al importar y obliga a pydantic a construir sus validadores (~100 MB nativos; `defer_build` y
  `malloc_trim` no lo reducen). Con python-telegram-bot los dos bots suman ~173 MB.
- **Alternatives considered**:
  - plan Small (5–6 €/mes): descartado por el dueño, que quiere seguir en el plan gratuito;
  - parchear `model_rebuild` (61 MB): depende de detalles internos de aiogram y pydantic, con
    riesgo de fallos en producción;
  - mantener aiogram y asumir el riesgo de que alwaysdata detenga procesos.

## 3. Servidor web del webhook: Starlette + uvicorn

- **Decision**: una aplicación Starlette, servida por uvicorn en `$IP:$PORT`. Es el mismo patrón
  que el bot de finanzas (`app/web.py`):
  - un *lifespan* con `async with application` y el registro del webhook;
  - validación del token con `hmac.compare_digest`;
  - `process_update` antes de responder;
  - "ok" en un GET.
- **Rationale**: el dueño ya lo opera en su cuenta y está probado en el plan Free. Además permite
  la ruta de salud que exige FR-011.
- **Alternatives considered**: `Application.run_webhook` de python-telegram-bot (usa tornado; no
  permite rutas propias, así que no hay "ok" en GET); aiohttp (ya no llega con ninguna
  dependencia y sería un patrón distinto al del bot de finanzas).

## 4. Dirección y rutas

- **Decision**:
  - el sitio usa la dirección `CUENTA.alwaysdata.net/tarjeta`; el bot de finanzas conserva
    `CUENTA.alwaysdata.net`;
  - `WEBHOOK_URL=https://CUENTA.alwaysdata.net/tarjeta/telegram`;
  - la aplicación acepta el **POST del webhook en cualquier ruta** y responde "ok" a **cualquier
    GET**.
- **Rationale**: funciona igual tenga o no activado `path_trim` el sitio, así que no hace falta
  saber cómo lo configura el panel. La seguridad no depende de la ruta, sino del token secreto
  (§6).
- **Alternatives considered**: ruta fija, que depende de `path_trim` y obliga a coordinar dos
  valores; subdominio, que la documentación no confirma para cuentas Free.

## 5. Procesamiento en serie y una sola vez (FR-009, FR-010)

- **Decision**:
  - **Llegada de mensajes**:
    - `set_webhook(max_connections=1)`: Telegram envía un update a la vez y espera la respuesta;
    - cada petición se procesa **antes** de responder 200, con `await application.process_update`
      y protegida con un `asyncio.Lock`, por si llegaran peticiones simultáneas;
    - python-telegram-bot conserva su valor por defecto `concurrent_updates=False`.
  - **Mensajes repetidos**:
    - un registro en memoria de los últimos 1 000 `update_id` procesados; un update repetido se
      responde 200 sin procesar.
  - **Errores**:
    - se responde 200 aunque un handler falle;
    - el error handler ya avisó al dueño, y devolver 500 haría que Telegram reintentara en bucle.
- **Rationale**: es la misma garantía de "un toque, un efecto" que en polling. Si el proceso muere
  a mitad de un update, Telegram lo reenvía. El registro en memoria se pierde con el reinicio, pero
  los flujos de la feature 001 ya piden confirmación ante un duplicado: cita del mismo día,
  homónimo, deshacer. Los botones viejos caducan.
- **Alternatives considered**: responder 200 de inmediato y procesar en segundo plano (Telegram no
  reintenta, pero un reinicio pierde el update); guardar los `update_id` en SQLite (una tabla más
  sin necesidad real; principio I).

## 6. Seguridad del webhook (FR-006, FR-007)

- **Decision**:
  - `WEBHOOK_SECRET` (`SecretStr`), validado al arrancar con `^[A-Za-z0-9_-]{16,256}$`;
  - comparación del encabezado `X-Telegram-Bot-Api-Secret-Token` con `hmac.compare_digest`;
  - si no coincide: respuesta 403 sin procesar y un `WARNING` en el log (sin el valor recibido).
  - El filtro del dueño (principio V) sigue activo dentro de la aplicación.
  - `WEBHOOK_URL` debe empezar con `https://`.
- **Rationale**: es el mecanismo que Telegram documenta para autenticar sus llamadas al webhook.

## 7. Arranque y apagado

- **Decision**:
  - **Webhook**: el *lifespan* de Starlette:
    1. `async with application` (`initialize`, que hace un `getMe`);
    2. `set_webhook(url, secret_token, max_connections=1, allowed_updates=["message",
       "callback_query"], drop_pending_updates=False)`;
    3. `set_my_commands`;
    4. recién entonces uvicorn acepta peticiones.

    Al apagarse **no** se borra el webhook: Telegram retiene los mensajes y despierta el sitio.
  - **Polling**: `run_polling(drop_pending_updates=False, allowed_updates=[...])` con un `post_init`
    que consulta `get_webhook_info()`. Si hay URL, registra el error y termina con código 1 antes
    de que python-telegram-bot llame `delete_webhook` (FR-013). Es el mismo resguardo que el bot
    de finanzas.
- **Rationale**: registrar el webhook en cada arranque es idempotente y aplica los cambios de token
  o secreto con solo reiniciar.
- **Tiempo de arranque** (medido): imports + primera tarjeta en 0,85 s con CPU completa (3 s en frío,
  con el disco sin caché). Con ¼ de CPU se estiman ~3,5 s en caliente, más ~1 s de llamadas a
  Telegram: dentro de FR-012 (< 10 s), salvo un arranque con disco frío, que lo valida el
  quickstart.

## 8. Configuración (FR-001, FR-004 – FR-007)

- **Decision**: se amplía `Ajustes` (pydantic-settings) con:
  - `webhook_url: str | None`: sin valor, modo polling;
  - `webhook_secret: SecretStr | None`: obligatorio y con formato válido si hay URL;
  - `ip: str = "127.0.0.1"` y `port: int = 8000`: alwaysdata los entrega en `IP` y `PORT`.

  Ver [contracts/configuracion.md](contracts/configuracion.md).
- **Rationale**: un solo lugar valida todo antes de conectarse a Telegram, y el modo se elige solo
  por configuración.

## 9. Adaptación de la capa de Telegram

| Hoy (aiogram) | Con python-telegram-bot |
|---------------|-------------------------|
| `Router` + filtros `Command` | `Application.add_handler(CommandHandler(...))` en `registrar_handlers(app)` |
| `CommandObject.args` | `" ".join(context.args)` (los nombres ya se limpian en el dominio) |
| `message.answer` / `answer_photo` | `message.reply_text` / `reply_photo(photo=bytes, caption=...)` |
| `callback.answer()` / `message.edit_text` | `query.answer()` / `query.message.edit_text` |
| `CallbackData` (`AccionCB`) | formato propio `"a:<token>:<opción>"` con `pack`/`unpack` y `pattern=r"^a:"` (≤ 64 bytes) |
| *Outer middleware* `SoloDueno` | `TypeHandler(Update, solo_dueno)` en el grupo -1 que lanza `ApplicationHandlerStop` |
| Inyección por `workflow_data` | `application.bot_data["servicio"]` y `["acciones"]` |
| `@router.errors()` | `application.add_error_handler(...)` |
| `message.date` (UTC) | `message.date` (UTC con zona en python-telegram-bot ≥ 20) |

El dominio (`conteo`, `busqueda`, `render`, `db`, `servicio`, `diseno`, `config`) **no cambia**,
salvo `config.py` (§8). `textos.py` y la lógica de los flujos se conservan.

## 10. Python y disco en el servidor (FR-015)

- **Decision**:
  - se usa el Python 3.12 de alwaysdata:
    `uv venv --python "$(PYTHON_VERSION=3.12 python -c 'import sys; print(sys.executable)')"` y
    luego `UV_PYTHON_DOWNLOADS=never uv sync --frozen --no-dev`;
  - el sitio arranca con la ruta absoluta `.venv/bin/python`, sin depender de `PYTHON_VERSION`.
  - Si 3.12 no existiera, se permite que uv descargue su propio Python (≈ +100 MB).
- **Disco** (medido):

  | Componente | Tamaño |
  |------------|--------|
  | Entorno de producción | 54 MB |
  | Binario de uv | 41 MB |
  | Repositorio (código, assets, `.git`) | ~4 MB |
  | **Total** | **~100 MB** (~200 MB si uv descarga Python) |

  Ambas cifras están por debajo de 300 MB.

## 11. Pruebas

- **Decision**:
  - las pruebas del dominio no cambian;
  - las de la capa de Telegram se reescriben:
    - **unitarias de handlers**: `MagicMock(spec=Message)` y `context` con `args`/`bot_data`;
    - **integración**: un `FakeTelegramAPI(BaseRequest)`, como en el bot de finanzas, alimentado
      por `Application.process_update`;
    - **servidor web**: `starlette.testclient.TestClient`, que ejecuta el *lifespan*.
  - Se agregan pruebas de configuración (modos, validaciones), del servidor web (403, duplicados,
    "ok", serie), del resguardo de polling y de arquitectura: el dominio no importa `telegram`.
- **Rationale**: principio III para el dominio; el resto, con pruebas ligeras pero de punta a
  punta.

## 12. Repositorio público y despliegue

- **Decision**:
  - crear `Denilson1817/bot-tarjeta-lealtad` público con `gh repo create --public --source .
    --push` (lo ejecuta el agente con la cuenta ya autenticada, al llegar a esa tarea);
  - en el servidor, `git clone` por HTTPS y luego `git pull`.
- **Rationale**: decisión del dueño (spec, FR-018); es el mismo flujo que el bot de finanzas. Los
  commits usan el correo que ya es público en ese repositorio.
