# Contrato: configuración y modos de ejecución

Variables de entorno, leídas también del `.env` del directorio de trabajo con pydantic-settings
(nombres sin distinguir mayúsculas). Se validan **todas** antes de conectarse a Telegram. Si algo
falla, el proceso registra el motivo y termina con código 1.

## Variables

| Variable | Obligatoria | Regla | Origen en producción |
|----------|-------------|-------|----------------------|
| `BOT_TOKEN` | sí | (sin cambios desde la 001) | `.env` del servidor: token del bot de **producción** |
| `OWNER_ID` | sí | entero | `.env` del servidor |
| `ZONA_HORARIA` | sí | nombre IANA válido | `.env` (`America/Mexico_City`) |
| `CITAS_POR_TARJETA` | no (10) | ≥ 2 y coherente con la plantilla | `.env` |
| `DB_PATH` | no (`data/lealtad.db`) | ruta; en producción, **absoluta** | `.env` del servidor |
| `LOG_LEVEL` | no (`INFO`) | nivel de `logging` | `.env` |
| `WEBHOOK_URL` | no | si existe: debe empezar con `https://` | `.env` del servidor |
| `WEBHOOK_SECRET` | solo con `WEBHOOK_URL` | `^[A-Za-z0-9_-]{16,256}$` | `.env` del servidor (generado con `secrets.token_urlsafe(32)`) |
| `IP` | no (`127.0.0.1`) | dirección donde escuchar | **alwaysdata** (variable del sitio) |
| `PORT` | no (`8000`) | entero | **alwaysdata** (variable del sitio) |

## Selección de modo

| `WEBHOOK_URL` | Modo | Comportamiento al arrancar |
|---------------|------|----------------------------|
| sin valor | **polling** | `getWebhookInfo`: si el bot ya tiene un webhook, se registra "este bot ya corre en el servidor…" y sale con 1 **sin tocar el webhook** (FR-013). Si no, polling como en la 001. |
| con valor | **webhook** | Valida `WEBHOOK_URL` y `WEBHOOK_SECRET`; arranca el servidor en `IP:PORT`, registra el webhook y los comandos ([webhook-http.md](webhook-http.md)). |

## Mensajes de error al arrancar (ejemplos)

- `WEBHOOK_URL debe empezar con https:// (Telegram lo exige).`
- `WEBHOOK_SECRET es obligatorio en modo webhook: de 16 a 256 caracteres, solo letras, dígitos, "_" y "-". Genera uno con: python -c "import secrets; print(secrets.token_urlsafe(32))"`
- `Este bot ya tiene un webhook activo (https://…): ya corre en el servidor. No lo arranco aquí para no quitárselo. Usa el bot de pruebas en tu computadora.`
