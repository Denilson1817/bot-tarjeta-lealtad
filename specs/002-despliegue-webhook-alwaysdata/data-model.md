# Data Model: Publicación en alwaysdata (plan Free) con webhook

**Feature**: `002-despliegue-webhook-alwaysdata` | **Fecha**: 2026-11-16

## Base de datos

**Sin cambios.** Las tablas `clientes` y `citas` y las vistas derivadas siguen exactamente como en
[la feature 001](../001-registro-citas-tarjeta/data-model.md).

En producción, la base vive en el servidor, en la ruta absoluta de `DB_PATH`
(p. ej. `/home/CUENTA/bot-tarjeta-lealtad/data/lealtad.db`):
- está fuera del control de versiones (`data/` está en `.gitignore`);
- `git pull`, `uv sync` y los reinicios del sitio no la tocan (FR-016);
- empieza vacía (FR-017).

## Estado en memoria (no persistente)

| Estado | Contenido | Límite | Al dormirse o reiniciarse |
|--------|-----------|--------|---------------------------|
| Acciones pendientes (de la 001) | `token → Accion` detrás de cada botón | 500, se descarta la más antigua | Se pierden: el botón responde "ya se aplicó o caducó" |
| `update_id` procesados (nuevo, FR-009) | IDs de los últimos updates procesados, en orden de llegada | 1 000, se descarta el más antiguo | Se pierden; los duplicados tras un reinicio los frenan las confirmaciones de la 001 ([research §5](research.md#5-procesamiento-en-serie-y-una-sola-vez-fr-009-fr-010)) |

Ninguno de los dos afecta la corrección de los datos (principio VI): solo evitan efectos repetidos.

## Configuración de producción

Valores que viven en el `.env` del servidor y nunca se versionan. Las reglas de validación y el
modo resultante están en [contracts/configuracion.md](contracts/configuracion.md).

## Datos del botón

El formato cambia (la lógica no): `"a:<token>:<opción>"`, con un máximo de 64 bytes.
- `token`: 11 caracteres de `secrets.token_urlsafe(8)`.
- `opción`: un ID de cliente, `nuevo`, `si` o `no`.
