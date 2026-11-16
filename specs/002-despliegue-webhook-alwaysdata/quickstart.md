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

**Memoria** (FR-015): **no** arranques el modo webhook en la computadora. Al arrancar registraría
un webhook falso en el bot de pruebas y lo dejaría sin polling. En su lugar, un script temporal
(fuera del repositorio):
1. importa `tarjeta_lealtad.bot.app` y `tarjeta_lealtad.bot.web`;
2. construye la aplicación y el servidor web con el `FakeTelegramAPI` de las pruebas;
3. genera una tarjeta;
4. imprime el RSS de `/proc/self/status`.

Debe quedar **< 120 MB** (medido en el research: ~96 MB).

## 2. Primera publicación

### 2.1 Código en GitHub (una vez)

El agente crea el repositorio público con la cuenta autenticada y sube `main` y la rama de la
feature. La publicación se valida desde la rama; se integra a `main` después (§3.1):

```bash
gh repo create Denilson1817/bot-tarjeta-lealtad --public --source . --remote origin
git push -u origin main
git push -u origin 002-despliegue-webhook-alwaysdata
```

### 2.2 En el servidor, por SSH

```bash
ssh CUENTA@ssh-CUENTA.alwaysdata.net
curl -LsSf https://astral.sh/uv/install.sh | sh            # uv en ~/.local/bin
git clone -b 002-despliegue-webhook-alwaysdata https://github.com/Denilson1817/bot-tarjeta-lealtad.git  # tras integrar: main (§3.1)
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
| 5 | En el servidor: revisar el log del sitio (`ls ~/admin/logs/sites/`) y el disco (`du -sh ~/bot-tarjeta-lealtad ~/.local/bin/uv`) | "modo webhook", "webhook registrado", sin errores; el disco suma < 300 MB | FR-019, FR-015 |

## 3. Validación en producción

Con la **computadora apagada**, recorrer contra el bot de producción la tabla de
[quickstart §5 de la feature 001](../001-registro-citas-tarjeta/quickstart.md#5-validación-manual-de-punta-a-punta)
(SC-001). La base empieza vacía (FR-017). Además:

| # | Acción | Esperado | Cubre |
|---|--------|----------|-------|
| 6 | No escribirle al bot durante más de 30 minutos y luego enviar `/clientes` | Responde en < 15 s. En el log del sitio, de "modo webhook" a "webhook registrado" pasan < 10 s. Después, `/saldo` del bot de finanzas responde. | US1-2, SC-003, FR-012, SC-006 |
| 7 | Pulsar un botón que se envió antes de esa pausa | "Esta acción ya se aplicó o caducó…" | US1-4 |
| 8 | En la computadora, poner temporalmente en `.env` el token de **producción** (sin `WEBHOOK_URL`) y arrancar | Se niega a arrancar: "ya corre en el servidor"; el bot de producción sigue respondiendo. Volver al token de pruebas. | US2-2, FR-013 |

### 3.1 Integrar a `main` y ensayar el mantenimiento

Tras las filas 6–8:
1. **En la computadora**: gates en verde, `git merge --no-ff` de la rama a `main` y `git push`.
2. **En el servidor**: pasar a `main` con el procedimiento de actualización (§4), usando
   `git checkout main && git pull` en lugar de solo `git pull`, y reiniciar el sitio.

| # | Acción | Esperado | Cubre |
|---|--------|----------|-------|
| 9 | Antes del paso 2, anotar la salida de `/clientes`; medir cuánto toma el paso 2 | < 5 min; `/clientes` idéntico; `/ayuda` responde | SC-007, SC-008, US3-3 |
| 10 | Publicar un cambio mínimo (p. ej., una corrección en el README) con «Actualizar» (§4) | < 5 min; `/clientes` idéntico | SC-007, SC-008, FR-019 |
| 11 | Volver al commit anterior con «Volver a la versión anterior» (§4) y luego regresar a `main` | El bot responde en ambos casos; `/clientes` idéntico | US3-4, FR-019 |

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
