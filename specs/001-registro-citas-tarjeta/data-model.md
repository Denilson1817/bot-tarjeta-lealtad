# Data Model: Registro de citas y tarjeta de lealtad

**Feature**: `001-registro-citas-tarjeta` | **Fecha**: 2026-11-16

Se guardan dos tablas: `clientes` y `citas`. La **tarjeta** no se guarda; se deriva de las citas
(principio IV, ver [research.md §6](research.md#6-modelo-de-ciclo-de-tarjeta-derivado-de-eventos)).
Todas las fechas se guardan en UTC y se muestran en `ZONA_HORARIA`.

## Tablas

### `clientes`

| Campo | Tipo | Reglas |
|-------|------|--------|
| `id` | entero, PK, `AUTOINCREMENT` | Asignado al crear; nunca cambia ni se reutiliza (FR-003). Es el "#12" que ve el dueño. |
| `nombre` | texto, no nulo, ≤ 60 | Tal como lo escribió el dueño, con espacios recortados y colapsados (FR-021). Es lo que aparece en la tarjeta. |
| `nombre_normalizado` | texto, no nulo, indexado | Sin mayúsculas, acentos ni espacios extra ([research §7](research.md#7-búsqueda-de-clientes)). No es único: los nombres pueden repetirse (FR-004). |
| `creado_en` | fecha UTC, no nulo | Momento del alta. |

Validación al crear ([research §8](research.md#8-validación-de-nombres)):
- solo letras ASCII o Latin-1, espacio, apóstrofo, guion y punto;
- al menos una letra y ningún dígito;
- tiene que caber en la tarjeta con tamaño de fuente ≥ 36 (FR-028).

### `citas`

| Campo | Tipo | Reglas |
|-------|------|--------|
| `id` | entero, PK, `AUTOINCREMENT` | Define el orden de los eventos. |
| `cliente_id` | entero, FK → `clientes.id`, indexado, no nulo | |
| `origen` | texto: `bot` \| `previa` | `previa` = cargada al dar de alta (FR-018). |
| `registrada_en` | fecha UTC, nula | Fecha del comando (`message.date`). Nula si y solo si `origen = previa` (restricción CHECK). |
| `es_premio` | booleano, no nulo, por defecto falso | Verdadero si esta cita cerró una tarjeta (FR-014). Se fija al insertar y no cambia. |
| `anulada_en` | fecha UTC, nula | Fecha en que se deshizo (FR-023). Nula = vigente. |
| `creada_en` | fecha UTC, no nulo | Momento de inserción, para auditoría. |

Las citas nunca se borran: deshacer solo rellena `anulada_en`.

## Vistas derivadas (en el dominio, sin tabla)

Se calculan a partir de las citas **vigentes** de un cliente (`anulada_en` nula), ordenadas por
`id`:

| Vista | Definición |
|-------|------------|
| **Tarjeta completada** | Cada cita vigente con `es_premio`. Número = posición del premio (1.ª, 2.ª…); `completada_en` = su `registrada_en`. |
| **Tarjeta en curso** | Las citas vigentes posteriores al último premio vigente. `citas_en_curso` = cuántas son. |
| **Flores a dibujar** | `min(citas_en_curso, casillas)`. En la respuesta a la cita de premio se dibujan todas las casillas (FR-014). |
| **Próxima es premio** | `citas_en_curso ≥ N − 1`. |
| **Faltan para el premio** | `max(N − 1 − citas_en_curso, 0)` flores, y luego la cita de premio. |
| **Última cita** | Máxima `registrada_en` entre las citas vigentes con `origen = bot` (para distinguir clientes, FR-006). |
| **Resumen del cliente** | `id`, `nombre`, `citas_en_curso`, `tarjetas_completadas`, `ultima_cita`, `proxima_es_premio` (FR-031). |

## Transiciones

**Cita**

```text
(insertada) ──► vigente ──deshacer──► anulada      (irreversible)
```

**Tarjeta** (derivada). Con N = 10 y 9 casillas:

```text
en curso (0..8 flores) ──cita──► en curso (k+1)
en curso (9 flores)    ──cita──► completada (la cita se guarda con es_premio = true)
completada             ──cita──► nueva tarjeta en curso con 1 flor
completada             ──deshacer premio──► en curso con 9 flores   (FR-024)
```

**Regla al registrar una cita** (FR-012, FR-016): `es_premio = (citas_en_curso >= N − 1)`.

**Regla al deshacer** (FR-022): se anula la cita vigente de mayor `id` del cliente; puede ser una
`previa`.

## Reglas de configuración relacionadas

| Regla | Origen |
|-------|--------|
| `CITAS_POR_TARJETA` (N) ≥ 2, por defecto 10 | FR-012 |
| Número de casillas de `diseno.py` = N − 1; si no, el bot no arranca | FR-017 |
| Citas previas al alta: 0 ≤ k ≤ N − 1 | FR-018 |
| "Mismo día" se evalúa en `ZONA_HORARIA` entre citas vigentes `origen = bot` | FR-010 |

## Volumen esperado

Menos de 200 clientes y unas 1 000 citas por año. Con un índice por `cliente_id`, cada consulta
lee solo las citas de un cliente (decenas de filas).
