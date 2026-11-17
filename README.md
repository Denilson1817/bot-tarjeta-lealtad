# Bot de tarjeta de lealtad

Bot de Telegram para el dueño del negocio y las personas que el dueño autorice, que registra las
citas de cada cliente y devuelve su **tarjeta de lealtad** como foto, lista para reenviarla por
WhatsApp. La tarjeta se
genera desde los datos guardados: la plantilla, el nombre del cliente y una flor por cita.
Al llegar a la cita 10, que es la de premio, empieza una tarjeta nueva.

## Comandos

| Comando | Para qué | Ejemplo |
|---------|----------|---------|
| `/cita <nombre o #id>` | Registra una cita y envía la tarjeta | `/cita Carmen` |
| `/alta <nombre> [citas previas]` | Da de alta un cliente, con las citas que ya traía | `/alta Rosa 6` |
| `/deshacer <nombre o #id>` | Anula la última cita (pide confirmación) | `/deshacer Carmen` |
| `/tarjeta <nombre o #id>` | Envía la tarjeta sin registrar cita | `/tarjeta Carmen` |
| `/clientes` | Lista de clientes con su avance | `/clientes` |
| `/ayuda` | Muestra la ayuda | `/ayuda` |

El bot solo responde a las personas autorizadas; cualquier otra cuenta se ignora.

## Personas autorizadas

El dueño (`OWNER_ID`) siempre puede usar el bot. Para que otra persona lo use, con los mismos
permisos y sobre los mismos clientes, agrega su ID de Telegram en `AUTORIZADOS`.

1. **Obtén su ID.** Pídele que escriba `/ayuda` al bot **en privado** (no en un grupo). No
   recibirá respuesta, pero el log anota su ID:

   ```text
   Mensaje ignorado de una cuenta no autorizada: id=222222222 usuario=nombre chat=privado
   ```

   En tu computadora, la línea aparece en la terminal. En alwaysdata:

   ```bash
   grep -rh "cuenta no autorizada" ~/admin/logs/sites/ | tail -3
   ```

2. **Autorízala.** Agrega su ID en el `.env` (si son varias personas, sepáralas con comas):

   ```bash
   AUTORIZADOS=222222222
   ```

   Reinicia el bot: en tu computadora, Ctrl+C y vuelve a arrancarlo; en alwaysdata, reinicia el
   sitio en **Web > Sites**. Al arrancar, el log dice `Personas autorizadas: 2` (cuenta al
   dueño). Si un ID está mal escrito, el bot no arranca y el log dice cuál es.
3. **Para quitarla**, borra su ID de `AUTORIZADOS` y reinicia.

**En un grupo.** Agrega el bot al grupo. Los comandos se escriben igual que en privado o con el
nombre del bot (`/cita@NombreDelBot Carmen`), y el bot responde en el grupo. No responde a la
conversación normal ni a los miembros no autorizados (sus mensajes quedan en el log).

- Las tarjetas y la lista de clientes quedan **visibles para todos los miembros**: agrega el bot
  solo a grupos cuyos miembros puedan verlas.
- Si un administrador tiene activado **«Permanecer anónimo»**, Telegram oculta su cuenta y el bot
  no lo reconoce (en el log aparece `usuario=GroupAnonymousBot`): desactívalo en sus permisos de
  administrador. **Nunca** agregues a `AUTORIZADOS` el ID de `GroupAnonymousBot`: es una cuenta
  compartida y daría acceso a cualquier administrador anónimo.

## Uso en tu computadora

Aquí el bot funciona en **modo polling** con un **bot de pruebas**. Nunca uses el bot de
producción en tu computadora.

1. **Requisitos**:
   - [uv](https://docs.astral.sh/uv/) y Python 3.12 (`uv python install 3.12`);
   - un bot de pruebas creado con @BotFather y tu ID numérico de Telegram.
2. **Instalación**:

   ```bash
   uv sync
   cp .env.example .env      # pon BOT_TOKEN (bot de pruebas), OWNER_ID y ZONA_HORARIA
   ```

3. **Ejecutar**: `uv run python -m tarjeta_lealtad`. En el log aparece "Modo polling".
4. **Gates de calidad**: los cuatro deben estar en verde antes de integrar a `main`.

   ```bash
   uv run ruff check && uv run ruff format --check && uv run mypy && uv run pytest
   ```

**Resguardo:** si por error arrancas en tu computadora un bot que ya corre en el servidor, el
bot se niega a arrancar ("ya corre en el servidor") para no quitarle el webhook al de producción.

**Modo webhook:** no lo arranques en tu computadora. Registraría un webhook falso en el bot de
pruebas y lo dejaría sin polling.

## Publicar en alwaysdata (plan Free)

En producción, el bot corre como **sitio** de alwaysdata y recibe los mensajes de Telegram por
webhook. El plan Free no admite *Services*, así que no hay un proceso permanente: el sitio se
duerme tras 30 minutos sin mensajes y despierta con el siguiente.

El bot vive en `CUENTA.alwaysdata.net/tarjeta`, sin tocar otros sitios de la cuenta. En los
comandos de abajo, cambia `CUENTA` por el nombre de tu cuenta de alwaysdata.

### 1. En el servidor, por SSH

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

En `.env`:
- `BOT_TOKEN`: el token del bot de **producción**;
- `OWNER_ID` y `ZONA_HORARIA=America/Mexico_City`;
- `AUTORIZADOS`, si otras personas usarán el bot (ver «Personas autorizadas»);
- `DB_PATH=/home/CUENTA/bot-tarjeta-lealtad/data/lealtad.db`;
- `WEBHOOK_URL=https://CUENTA.alwaysdata.net/tarjeta/telegram`;
- el `WEBHOOK_SECRET` que generó el comando `echo`.

Si el servidor no tiene Python 3.12 (`PYTHON_VERSION=3.12 python` falla), quita
`UV_PYTHON_DOWNLOADS=never` y deja que uv descargue Python 3.12 (unos 100 MB más de disco).

### 2. En el panel de alwaysdata

En **Web > Sites > Add a site**:
- **Name**: Tarjeta de lealtad.
- **Addresses**: `CUENTA.alwaysdata.net/tarjeta`.
- **Type**: User program.
- **Command**: `/home/CUENTA/bot-tarjeta-lealtad/.venv/bin/python -m tarjeta_lealtad`.
- **Working directory**: `/home/CUENTA/bot-tarjeta-lealtad`.
- **Idle time**: déjalo con el valor por defecto.

### 3. Comprobar

| Qué hacer | Qué esperar |
|-----------|-------------|
| Abrir `https://CUENTA.alwaysdata.net/tarjeta` en el navegador | `ok` (la primera vez tarda unos segundos: despierta el sitio) |
| `curl -s -o /dev/null -w '%{http_code}\n' -X POST https://CUENTA.alwaysdata.net/tarjeta/telegram` | `403`: sin el token secreto no entra nada |
| `/ayuda` al bot de producción desde el iPhone | Responde la ayuda |
| Si tienes otros bots en la cuenta, escribirles | Responden como siempre |
| En el servidor: `ls ~/admin/logs/sites/` y revisar el log del sitio | "Personas autorizadas: N", "Modo webhook", "Webhook registrado", sin errores |

## Mantenimiento

**Actualizar.** En tu computadora, `git push`. En el servidor:

```bash
cd ~/bot-tarjeta-lealtad && git pull && UV_PYTHON_DOWNLOADS=never ~/.local/bin/uv sync --frozen --no-dev
```

Luego reinicia el sitio en **Web > Sites** (botón de reinicio) y comprueba `ok` y `/ayuda`. Los
datos viven en `data/lealtad.db` y no se tocan al actualizar.

**Volver a la versión anterior.**

```bash
cd ~/bot-tarjeta-lealtad && git log --oneline -5
git checkout <commit-anterior> && UV_PYTHON_DOWNLOADS=never ~/.local/bin/uv sync --frozen --no-dev
```

Reinicia el sitio. Para retomar las actualizaciones normales: `git checkout main`.

**Ver los logs.** Están en `~/admin/logs/sites/`, en el servidor.

**Cambiar el token del bot o el secreto.** Edita `.env` en el servidor y reinicia el sitio: al
arrancar, el bot vuelve a registrar el webhook con los valores nuevos.

**Dejar alwaysdata.**
1. Borra el sitio.
2. Quita el webhook: `curl "https://api.telegram.org/bot<TOKEN>/deleteWebhook"`.
3. Arranca el bot en polling donde corresponda.

## Cómo está hecho

- Python 3.12 con [uv](https://docs.astral.sh/uv/), [python-telegram-bot](https://python-telegram-bot.org/),
  Pillow, SQLAlchemy (SQLite), pydantic-settings, Starlette + uvicorn (solo en modo webhook).
- El dominio (conteo de citas, búsqueda, render de la tarjeta y base de datos) no depende de
  Telegram y está cubierto por pruebas.
- Se desarrolla con [Spec Kit](https://github.com/github/spec-kit). Los principios del proyecto
  están en `.specify/memory/constitution.md` y cada feature tiene su especificación, plan y tareas
  en `specs/`.
- La fuente del nombre es [Sacramento](https://fonts.google.com/specimen/Sacramento), con licencia
  OFL (`assets/fuentes/OFL.txt`).
