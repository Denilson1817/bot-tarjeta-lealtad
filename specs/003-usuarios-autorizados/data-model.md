# Data Model: Personas autorizadas para usar el bot

**Feature**: `003-usuarios-autorizados` | **Fecha**: 2026-11-16

## Base de datos

**Sin cambios.** Todas las personas autorizadas comparten las tablas `clientes` y `citas` de la
[feature 001](../001-registro-citas-tarjeta/data-model.md). No se guarda quién hizo cada acción:
queda en el registro de eventos (FR-010).

## Persona autorizada (configuración, no base de datos)

| Campo | Origen | Reglas |
|-------|--------|--------|
| ID de Telegram del dueño | `OWNER_ID` | Obligatorio, entero. Siempre autorizado (FR-002). |
| IDs adicionales | `AUTORIZADOS` | Opcional; enteros separados por comas, con espacios permitidos; los elementos vacíos se ignoran. Si un valor no es entero, el bot no arranca (FR-006). |
| Conjunto efectivo | `ids_autorizados` (calculado) | `{OWNER_ID} ∪ AUTORIZADOS`, sin duplicados. |

Cambiar el conjunto efectivo requiere editar el `.env` y reiniciar el bot (US3).

## Estado en memoria

Sin cambios: el registro de acciones pendientes y el de `update_id` (feature 002) son compartidos
por todas las personas autorizadas.
