# Contrato: acceso y comportamiento por tipo de chat

Complementa el [contrato de comandos](../../001-registro-citas-tarjeta/contracts/comandos-bot.md),
cuyos textos y flujos no cambian, y la
[configuración de la 002](../../002-despliegue-webhook-alwaysdata/contracts/configuracion.md).

## Configuración nueva

| Variable | Obligatoria | Regla | Ejemplo |
|----------|-------------|-------|---------|
| `AUTORIZADOS` | no | IDs de Telegram (enteros) separados por comas; espacios permitidos | `AUTORIZADOS=111111111,222222222` |

- Personas autorizadas = `OWNER_ID` + `AUTORIZADOS`.
- Con un valor inválido, el bot no arranca:
  `AUTORIZADOS debe ser una lista de IDs numéricos separados por comas; valor inválido: 'abc'`.

## Qué hace el bot según quién escribe y dónde

| Quién | Dónde | Qué envía | Respuesta | Log |
|-------|-------|-----------|-----------|-----|
| Autorizado | Privado | Comando | Como en la 001 | Acciones con `usuario=<id>` |
| Autorizado | Privado | Texto que no es comando | "Usa /ayuda para ver los comandos." | — |
| Autorizado | Grupo | Comando (`/cita …` o `/cita@NombreDelBot …`) | Como en la 001, en el grupo | Acciones con `usuario=<id>` |
| Autorizado | Grupo | Texto que no es comando o aviso del grupo | **Ninguna** | — |
| Autorizado | Cualquiera | Toque de botón (aunque lo pidiera otra persona autorizada) | Como en la 001; un solo efecto | Acciones con `usuario=<id>` |
| No autorizado | Privado | Cualquier mensaje | **Ninguna** | `WARNING` con id, usuario y "privado" |
| No autorizado | Grupo | Comando | **Ninguna** | `WARNING` con id, usuario y "grupo" |
| No autorizado | Cualquiera | Toque de botón | **Ninguna**; la acción sigue disponible | `WARNING` con id, usuario y tipo de chat |
| No autorizado | Grupo | Texto que no es comando o aviso del grupo | **Ninguna** | `DEBUG` (no ensucia el log) |

Formato de la línea `WARNING`, que es de donde el dueño copia el ID:

```text
Mensaje ignorado de una cuenta no autorizada: id=222222222 usuario=nombre chat=grupo
```
