# Contrato: interfaz HTTP del bot (modo webhook)

Lo que expone el sitio de alwaysdata. Los comandos y respuestas en Telegram no cambian:
[contrato de comandos de la 001](../../001-registro-citas-tarjeta/contracts/comandos-bot.md).

El servidor escucha en `$IP:$PORT`. alwaysdata termina el HTTPS y reenvía la petición, con la ruta
de la dirección recortada o no según `path_trim`; por eso las rutas aceptan **cualquier valor**
([research §4](../research.md#4-dirección-y-rutas)).

## `POST /{cualquier ruta}`: update de Telegram

| Condición | Respuesta | Efecto |
|-----------|-----------|--------|
| Encabezado `X-Telegram-Bot-Api-Secret-Token` ausente o distinto de `WEBHOOK_SECRET` | `403` (sin cuerpo) | Nada se procesa. `WARNING` en el log con la ruta, nunca con el valor recibido. |
| Token correcto, cuerpo que no es un update válido | `400` | Nada se procesa. `WARNING` en el log. |
| Token correcto, `update_id` ya procesado | `200` | No se vuelve a procesar (FR-009). `INFO` "update repetido". |
| Token correcto, update nuevo | `200` cuando **termina** el procesamiento | Se procesa en serie (uno a la vez, en orden de llegada) con los mismos handlers que en polling. |
| Un handler falla al procesar | `200` | El error handler registra la traza y avisa al dueño ("Algo salió mal…"); no se fuerza un reintento de Telegram. |

## `GET /{cualquier ruta}`: comprobación de salud

- `200`, `text/plain`, cuerpo `ok` (FR-011).
- No revela datos de clientes, versión ni configuración.

## Otros métodos

- `405`.

## Registro ante Telegram (al arrancar)

`setWebhook` con:

| Parámetro | Valor |
|-----------|-------|
| `url` | `WEBHOOK_URL` |
| `secret_token` | `WEBHOOK_SECRET` |
| `max_connections` | `1` (serie, FR-010) |
| `allowed_updates` | `["message", "callback_query"]` |
| `drop_pending_updates` | `false` (los mensajes pendientes se procesan, FR-008) |

Al apagarse no se llama `deleteWebhook`.
