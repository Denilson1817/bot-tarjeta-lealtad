# Contrato: comandos del bot

Interfaz que usa el dueño desde Telegram. Solo responde a `OWNER_ID`; cualquier otra cuenta se
ignora sin respuesta y queda en el log (FR-001).

**Convenciones**
- `<cliente>` = un nombre (sin importar mayúsculas ni acentos) o un identificador `#12` o `12`.
- `N` = citas por tarjeta (10) y `C` = casillas (9).
- Los textos son ejemplos: el contenido es obligatorio, la redacción exacta vive en `bot/textos.py`.
- Cada respuesta que incluye tarjeta es una **foto** (PNG 1050 × 600) con el texto como pie.

## Menú de comandos

Se registra al arrancar para que aparezca al escribir "/" en el iPhone.

| Comando | Argumentos | Ejemplo | Requisitos |
|---------|------------|---------|------------|
| `/cita` | `<cliente>` | `/cita Carmen` · `/cita #3` | FR-005 – FR-015 |
| `/alta` | `<nombre> [citas previas]` | `/alta Rosa 6` | FR-018 – FR-021, FR-028 |
| `/deshacer` | `<cliente>` | `/deshacer Carmen` | FR-022 – FR-025 |
| `/tarjeta` | `<cliente>` | `/tarjeta Carmen` | FR-032 |
| `/clientes` | — | `/clientes` | FR-031 |
| `/ayuda` (y `/start`) | — | `/ayuda` | FR-033 |

Si falta el argumento obligatorio, el bot responde con el uso y un ejemplo, sin cambiar nada.
Cualquier texto que no sea un comando recibe: "Usa /ayuda para ver los comandos."

## Resolución de `<cliente>` (común a `/cita`, `/deshacer` y `/tarjeta`)

| Resultado de la búsqueda | `/cita` | `/deshacer`, `/tarjeta` |
|--------------------------|---------|-------------------------|
| ID existente o una sola coincidencia exacta | Continúa sin preguntar | Continúa sin preguntar |
| ID inexistente | "No existe el cliente #99." | Igual |
| Varias coincidencias exactas | Botones, uno por cliente, + `Cancelar` | Igual |
| Solo parecidos | Botones de parecidos + `Crear "Carmn"` + `Cancelar` | Botones de parecidos + `Cancelar` |
| Nada | "¿Crear el cliente nuevo «Lucía»?" `Crear` · `Cancelar` | "No encontré a «Lucía»." |

Etiqueta de cada botón de cliente: `Carmen #3 · 4/9 · 10 nov`, con el nombre, el ID, las flores de
la tarjeta en curso y la fecha de la última cita, o `sin citas` si no tiene.

Antes de ofrecer `Crear`, el nombre se valida (caracteres y que quepa). Si no es válido, no se
ofrece la opción y se explica el motivo.

## `/cita <cliente>`

1. Resuelve el cliente (tabla anterior). Crear un cliente desde aquí equivale a un alta con 0
   citas previas, seguida de la cita.
2. Si el cliente ya tiene una cita ese día (en `ZONA_HORARIA`):
   "Carmen (#3) ya tiene una cita hoy a las 10:32. ¿Registrar otra?" `Sí, registrar` · `Cancelar`.
3. Registra la cita con la fecha del **comando original**, aunque se confirme después, y envía la
   foto:

| Situación tras registrar | Flores en la foto | Pie de foto (ejemplo) |
|--------------------------|-------------------|-----------------------|
| `k` < C | `k` | 🌸 Carmen (#3): 6 de 9 flores. Faltan 4 citas para la de premio (la 10.ª). |
| `k` = C | 9 | 🌸 Carmen (#3): 9 de 9 flores. 🎁 ¡La próxima cita es la de premio! |
| Cita de premio | 9 | 🎁 Carmen (#3): ¡cita de premio! Tarjeta n.º 2 completada. La próxima cita empieza una tarjeta nueva. |

## `/alta <nombre> [citas previas]`

- Si el último elemento es un entero, son las citas previas (0 si no se indica). Los nombres no
  admiten dígitos, así que no hay ambigüedad.
- Las citas previas deben cumplir 0 ≤ k ≤ C; si no: "Las citas previas deben estar entre 0 y 9."
- Si el nombre no es válido: "No puedo usar ese nombre: <motivo>." Motivos posibles:
  - "contiene caracteres no admitidos: 😀 7";
  - "es demasiado largo para la tarjeta; prueba con una versión más corta (por ejemplo, solo el
    nombre de pila)".
- Si ya existe un cliente con el mismo nombre normalizado: "Ya existe Rosa (#8). ¿Crear otro
  cliente con el mismo nombre?" `Crear otro` · `Cancelar`.
- Al crear, envía la foto con `k` flores: "✅ Cliente nuevo: Rosa (#15) con 6 citas previas.
  Revisa que la tarjeta coincida con la que tenía." No registra ninguna cita con fecha de hoy.

## `/deshacer <cliente>`

1. Resuelve el cliente (sin opción de crear).
2. Si no tiene citas vigentes: "Rosa (#15) no tiene citas que deshacer." Nada cambia.
3. Muestra la cita a anular y pide confirmación:
   "¿Anular la última cita de Carmen (#3)? 12 nov 2026, 10:32 · cita de premio"
   `Sí, deshacer` · `Cancelar`. Para una cita previa al alta dice "cita previa al bot".
4. Al confirmar, la anula y envía la foto actualizada: "↩️ Cita anulada. Carmen (#3): 8 de 9
   flores." Si era la de premio, agrega: "La tarjeta n.º 2 vuelve a estar en curso."

## `/tarjeta <cliente>`

Envía la foto con las flores de la tarjeta en curso. No cambia nada.
Pie: "🌸 Carmen (#3): 6 de 9 flores · 1 tarjeta completada."

## `/clientes`

Lista en orden alfabético (por nombre normalizado y luego por ID), una línea por cliente:

```text
Clientes (3):
#8 Carmen: 9/9 🎁
#3 Carmen: 4/9 · 1 completada
#15 Rosa: 6/9
```

🎁 marca a quien su próxima cita es la de premio. Si el texto pasa de 4 000 caracteres, se envía en
varios mensajes partiendo entre líneas. Sin clientes: "Todavía no hay clientes. Empieza con /cita
o /alta."

## Botones y acciones pendientes

- Cada mensaje con botones corresponde a una acción pendiente identificada por un token. Al pulsar
  un botón:
  1. se responde al toque (deja de girar el indicador);
  2. se quitan los botones del mensaje y se anota la elección ("✔️ Carmen #3" o "Cancelado");
  3. se ejecuta la acción una sola vez (FR-011).
- Pulsar de nuevo, o pulsar un botón de antes de un reinicio, responde: "Esta acción ya se aplicó
  o caducó. Repite el comando."
- `Cancelar` no cambia nada (FR-007, US1-4, US5-4).

## Errores

| Situación | Respuesta |
|-----------|-----------|
| La cita se registró, pero la foto no se pudo generar o enviar | "La cita quedó registrada, pero no pude enviar la tarjeta. Pídela con /tarjeta #3." |
| Error inesperado | "Algo salió mal; no se cambió nada." (si la transacción se revirtió). Se registra la traza en el log. |
| Mensaje de otra cuenta | Sin respuesta. Log `WARNING` con el ID y el usuario del remitente. |
