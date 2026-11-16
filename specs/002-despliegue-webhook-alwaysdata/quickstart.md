# Quickstart: Publicación en alwaysdata (plan Free) con webhook

Pasos para validar la feature y publicar el bot. La guía definitiva para el dueño quedará en el
`README.md` del proyecto (FR-018 – FR-020) a partir de esta. El repositorio es **público**: aquí no
van tokens, IDs ni el nombre real de la cuenta; `CUENTA` es el nombre de la cuenta de alwaysdata.

## 1. En la computadora (sin cambios para el dueño)

```bash
uv sync
uv run ruff check && uv run ruff format --check && uv run mypy && uv run pytest
uv run python -m tarjeta_lealtad      # sin WEBHOOK_URL en .env → polling con el bot de pruebas
```

Esperado:
- los 4 gates en verde;
- el bot de pruebas responde igual que en la feature 001 (US2-1);
- en el log aparece "modo polling".

**Memoria** (FR-015): con el bot arrancado en modo webhook en local (`IP=127.0.0.1`, `PORT=8000`
y valores de prueba en `WEBHOOK_URL`/`WEBHOOK_SECRET`; las llamadas a Telegram se simulan en las
pruebas), el RSS del proceso debe quedar **< 120 MB**:

```bash
ps -o rss=,cmd= -C python | grep tarjeta_lealtad   # RSS en KB
```

## 2. Primera publicación

### 2.1 Código en GitHub (una vez)

El agente crea el repositorio público con la cuenta autenticada:
`gh repo create Denilson1817/bot-tarjeta-lealtad --public --source . --remote origin --push`.

### 2.2 En el servidor, por SSH

```bash
ssh CUENTA@ssh-CUENTA.alwaysdata.net
curl -LsSf https://astral.sh/uv/install.sh | sh            # uv en ~/.local/bin
git clone https://github.com/Denilson1817/bot-tarjeta-lealtad.git
cd bot-tarjeta-lealtad
PY312="$(PYTHON_VERSION=3.12 python -c 'import sys; print(sys.executable)')"
~/.local/bin/uv venv --python "$PY312"
UV_PYTHON_DOWNLOADS=never ~/.local/bin/uv sync --frozen --no-dev
cp .env.example .env && chmod 600 .env && mkdir -p data
echo "WEBHOOK_SECRET=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')" >> .env
nano .env
```

En `.env` (ver [contracts/configuracion.md](contracts/configuracion.md)):
- `BOT_TOKEN`: el token del bot de **producción**;
- `OWNER_ID` y `ZONA_HORARIA=America/Mexico_City`;
- `DB_PATH=/home/CUENTA/bot-tarjeta-lealtad/data/lealtad.db`;
- `WEBHOOK_URL=https://CUENTA.alwaysdata.net/tarjeta/telegram`;
- el `WEBHOOK_SECRET` que generó el comando `echo`.

Si `PYTHON_VERSION=3.12 python` no existe en el servidor, quita `UV_PYTHON_DOWNLOADS=never` y deja
que uv descargue Python 3.12 (≈ +100 MB de disco; sigue dentro de FR-015).

### 2.3 En el panel de alwaysdata

**Web > Sites > Add a site**:
- **Name**: Tarjeta de lealtad.
- **Addresses**: `CUENTA.alwaysdata.net/tarjeta` (el sitio del bot de finanzas sigue en
  `CUENTA.alwaysdata.net` y no se toca).
- **Type**: User program.
- **Command**: `/home/CUENTA/bot-tarjeta-lealtad/.venv/bin/python -m tarjeta_lealtad`.
- **Working directory**: `/home/CUENTA/bot-tarjeta-lealtad`.
- **Idle time**: dejar el valor por defecto.

### 2.4 Comprobación

| # | Acción | Esperado | Cubre |
|---|--------|----------|-------|
| 1 | Abrir `https://CUENTA.alwaysdata.net/tarjeta` en el navegador | `ok` (la primera vez puede tardar unos segundos: despierta el sitio) | FR-011, US3-2 |
| 2 | `curl -s -o /dev/null -w '%{http_code}\n' -X POST https://CUENTA.alwaysdata.net/tarjeta/telegram` | `403` | FR-006, SC-005 |
| 3 | `/ayuda` al bot de producción desde el iPhone | Responde la ayuda | US3-1 |
| 4 | `/saldo` al bot de finanzas | Responde como siempre | FR-014, SC-006 |
| 5 | En el servidor: `ls ~/admin/logs/sites/` y revisar el log del sitio | "modo webhook", "webhook registrado", sin errores | FR-019 |

## 3. Validación en producción

Con la **computadora apagada**, recorrer contra el bot de producción la tabla de
[quickstart §5 de la feature 001](../001-registro-citas-tarjeta/quickstart.md#5-validación-manual-de-punta-a-punta)
(SC-001). La base empieza vacía (FR-017). Además:

| # | Acción | Esperado | Cubre |
|---|--------|----------|-------|
| 6 | No escribirle al bot durante más de 30 minutos y luego enviar `/clientes` | Responde en < 15 s | US1-2, SC-003 |
| 7 | Pulsar un botón que se envió antes de esa pausa | "Esta acción ya se aplicó o caducó…" | US1-4 |
| 8 | En la computadora, poner temporalmente en `.env` el token de **producción** (sin `WEBHOOK_URL`) y arrancar | Se niega a arrancar: "ya corre en el servidor"; el bot de producción sigue respondiendo. Volver al token de pruebas. | US2-2, FR-013 |

## 4. Mantenimiento

**Actualizar** (< 5 min, FR-019). En la computadora, `git push`. En el servidor:

```bash
cd ~/bot-tarjeta-lealtad && git pull && UV_PYTHON_DOWNLOADS=never ~/.local/bin/uv sync --frozen --no-dev
```

Después, reiniciar el sitio en **Web > Sites** (botón de reinicio) y comprobar `ok` y `/ayuda`.

**Volver a la versión anterior**:
1. `git log --oneline -5`;
2. `git checkout <commit-anterior>` y `uv sync --frozen --no-dev`;
3. reiniciar el sitio;
4. para retomar las actualizaciones: `git checkout main`.

**Logs**: `~/admin/logs/sites/` en el servidor.

**Cambiar el token del bot o el secreto**: editar `.env` y reiniciar el sitio. Al arrancar, el
webhook se registra con los valores nuevos.

**Dejar alwaysdata**:
1. borrar el sitio;
2. `curl "https://api.telegram.org/bot<TOKEN>/deleteWebhook"`;
3. arrancar el bot en polling donde corresponda.
