# Quickstart: Registro de citas y tarjeta de lealtad

Guía para preparar el entorno, pasar los gates de calidad y validar la feature de punta a punta.
Los detalles de comandos y respuestas están en [contracts/comandos-bot.md](contracts/comandos-bot.md).

## 1. Requisitos previos

- **uv** instalado (`uv --version`).
- **Python 3.12 gestionado por uv**. En esta máquina las descargas automáticas de Python están
  desactivadas (`/etc/uv/uv.toml`), así que se instala una vez con:
  ```bash
  uv python install 3.12
  ```
- **Dos bots de Telegram** creados con @BotFather: uno de **pruebas** (local) y otro de
  **producción** (alwaysdata). Telegram no permite que dos procesos hagan polling con el mismo
  token: el segundo recibe `409 Conflict`.
- **El ID numérico de Telegram del dueño**, que se obtiene escribiéndole a @userinfobot.

## 2. Preparar el proyecto

```bash
uv sync                      # crea .venv con Python 3.12 e instala dependencias y herramientas de desarrollo
cp .env.example .env         # luego editar .env con los valores reales
```

Variables de `.env` (ver [contracts/servicio-dominio.md § config.py](contracts/servicio-dominio.md#configpy)):

```dotenv
BOT_TOKEN=123456:ABC...        # token del bot de pruebas en local
OWNER_ID=111111111
ZONA_HORARIA=America/Mexico_City   # zona IANA del negocio
CITAS_POR_TARJETA=10
# DB_PATH=data/lealtad.db
# LOG_LEVEL=INFO
```

## 3. Gates de calidad (constitución: obligatorios antes de integrar a `main`)

```bash
uv run ruff check
uv run ruff format --check
uv run mypy
uv run pytest
```

Resultado esperado: los cuatro en verde. `pytest` no necesita red ni token.

## 4. Ejecutar el bot en local

```bash
uv run python -m tarjeta_lealtad
```

Esperado en el log:
- configuración cargada;
- diseño verificado (9 casillas para 10 citas por tarjeta);
- base de datos lista en `data/lealtad.db`;
- comandos registrados;
- polling iniciado.

Con `CITAS_POR_TARJETA=8`, el proceso debe **negarse a arrancar** e indicar que la plantilla tiene
9 casillas y se esperaban 7 (FR-017).

## 5. Validación manual de punta a punta

Con el bot de pruebas y una base vacía, desde el iPhone:

| # | Acción | Resultado esperado | Cubre |
|---|--------|--------------------|-------|
| 1 | `/cita Lucía` → `Crear` | Foto con "Lucía" y 1 flor en la casilla 1 | US1, FR-007 |
| 2 | `/cita lucia` | Pregunta si registrar otra cita hoy → `Sí, registrar` → 2 flores | FR-005, FR-010 |
| 3 | `/cita Lucía` → `Cancelar` | Nada cambia | FR-011 |
| 4 | `/cita Lcia` | Sugiere "Lucía #1" y ofrece `Crear "Lcia"` | FR-007 |
| 5 | `/alta Rosa 6` | Foto con 6 flores; `/clientes` muestra "#2 Rosa: 6/9" | US3 |
| 6 | `/alta Rosa` → `Crear otro` | Nace "#3 Rosa"; `/cita rosa` muestra dos botones con ID, flores y última cita | US4 |
| 7 | `/cita #2` tres veces (confirmando las repeticiones del día) | La 3.ª muestra 9/9 y avisa que la próxima es la de premio | US2, FR-013 |
| 8 | `/cita #2` | "¡Cita de premio! Tarjeta n.º 1 completada", con 9 flores | FR-014 |
| 9 | `/tarjeta #2` | Tarjeta nueva con 0 flores; "1 tarjeta completada" | FR-015, FR-032 |
| 10 | `/deshacer #2` → `Sí, deshacer` | Vuelve a 9/9 y la tarjeta n.º 1 sigue en curso | US5, FR-024 |
| 11 | Tocar dos veces el mismo `Sí, deshacer` | El segundo toque responde "ya se aplicó o caducó" | FR-011 |
| 12 | `/alta María Fernanda Ruiz` | Nombre completo, legible y sin tocar el ✨ ni la línea | SC-006, FR-027 |
| 13 | `/alta Ana 😀` | Rechazado: carácter no admitido | FR-028 |
| 14 | Escribirle al bot desde otra cuenta | Sin respuesta; `WARNING` en el log | FR-001, SC-008 |
| 15 | Detener el bot, enviar `/cita Lucía`, esperar un minuto y arrancarlo | Se procesa al arrancar; la cita queda con la hora del envío | Caso borde |
| 16 | Reenviar una foto de tarjeta a WhatsApp desde el iPhone | Se reenvía como imagen en dos toques | US1-6 |

Tiempo de respuesta (SC-002): las fotos de los pasos anteriores deben llegar en menos de 5 s.

## 6. Despliegue en alwaysdata

Una sola vez, por SSH:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone <repo> ~/bot-tarjeta-lealtad && cd ~/bot-tarjeta-lealtad
uv python install 3.12
uv sync --frozen --no-dev
cp .env.example .env    # token y OWNER_ID de producción, ZONA_HORARIA del negocio
```

En el panel de alwaysdata, en **Advanced → Services → Add**:
- **Command**: `/home/<cuenta>/bot-tarjeta-lealtad/.venv/bin/python -m tarjeta_lealtad`
- **Working directory**: `/home/<cuenta>/bot-tarjeta-lealtad`

Para actualizar:

```bash
cd ~/bot-tarjeta-lealtad && git pull && uv sync --frozen --no-dev
```

y después reiniciar el servicio desde el panel.

Verificación: el log del servicio muestra "polling iniciado" y `/ayuda` responde desde el iPhone.
La base de datos queda en `data/lealtad.db`, fuera del repositorio.
