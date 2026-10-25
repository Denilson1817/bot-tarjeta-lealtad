# Bot Tarjeta de Lealtad — Contexto del proyecto

> Estado: **idea / definición**. Aún no hay código.

## 1. El problema

En el negocio se usa una **tarjeta de lealtad en imagen PNG** para la promoción de cada cliente. Por cada cita del cliente se marca una **"X"** adicional en la tarjeta.

Proceso actual (manual):

1. Abrir el PNG del cliente.
2. Editarlo a mano para agregar una X más.
3. Guardar y enviar la imagen al cliente.

Problemas:

- **Volumen:** ~18 clientes por semana → 18 ediciones de imagen una por una.
- **Tiempo:** cada edición + envío toma varios minutos.
- **Errores:** el "registro" de cuántas citas lleva cada cliente vive solo en las imágenes; es fácil equivocarse o perder la cuenta.
- **Dispositivo:** todo se hace desde un **iPhone**; no se quiere desarrollar una app nativa desde cero.

## 2. Qué hay que automatizar

| Paso | Descripción | ¿Automatizable? |
|------|-------------|-----------------|
| 1. Llevar la cuenta | Cuántas citas lleva cada cliente | Sí, 100% |
| 2. Generar la imagen | Plantilla base + N X en posiciones fijas | Sí, 100% |
| 3. Enviar al cliente | Hacer llegar la imagen | Depende del canal (WhatsApp / Telegram) |

## 3. Opciones evaluadas

### Opción A — Bot de Telegram ✅ (recomendada)

**Cómo funciona:**

- Se escribe `/cita Juan` al bot.
- El bot suma +1 a Juan en una base de datos, superpone las X sobre el PNG plantilla y devuelve la imagen lista en segundos.
- Desde el iPhone se comparte la imagen al cliente (WhatsApp, Telegram, etc.) en 2 toques.

**Funciones extra posibles:**

- `/clientes` — lista de clientes con su conteo actual.
- `/deshacer Juan` — revertir la última cita registrada.
- Aviso automático cuando un cliente completa la tarjeta + reinicio a 0.

**Ventajas:**

- Ya se tiene experiencia con bots de Telegram (ver `bot-finanzas-telegram`).
- No requiere crear una app.
- Pasa de minutos por cliente a ~5 segundos.
- Deja un registro confiable de citas.

**Consideraciones:**

- Necesita estar corriendo en algún lado (servidor gratuito/barato o la PC encendida).
- Un bot de Telegram **solo puede escribirle a usuarios que le hayan dado "Iniciar"**. Si los clientes están en WhatsApp, lo práctico es que el bot genere la imagen para el dueño y este la reenvíe.

**Stack técnico propuesto:**

- Python
- `python-telegram-bot` — interacción con Telegram
- `Pillow` — superponer las X sobre la plantilla PNG
- `SQLite` — guardar clientes y conteos

### Opción B — Atajos de iPhone (sin servidor, sin código)

- La app **Atajos** tiene la acción **"Superponer imagen"** para colocar una X sobre la plantilla.

**Ventajas:** no requiere servidor ni programación.

**Desventajas:** llevar el conteo por cliente y posicionar cada X exactamente se vuelve torpe y frágil. Para ~18 clientes rotando cada semana **no se recomienda**.

### Opción C — Tarjeta digital con link por cliente

- Cada cliente tiene un link (página web) donde ve su tarjeta siempre actualizada.
- El dueño solo marca la cita; ni siquiera hay que enviar la imagen.

**Ventajas:** la mejor experiencia para el cliente.

**Desventajas:** más trabajo de montar. Candidata para una **fase 2**, posiblemente reutilizando la misma base de datos del bot.

## 4. Recomendación

**Opción A: Bot de Telegram.** Es el mejor balance entre esfuerzo, experiencia previa y ahorro de tiempo, y además resuelve el problema del registro de citas.

## 5. Información pendiente para construirlo

- [ ] **Imagen PNG** de la tarjeta (colocarla en la carpeta del proyecto) para mapear las coordenadas de cada X. *(El dueño la compartirá.)*
- [ ] **Número de casillas** de la tarjeta y qué pasa al completarla (¿premio?, ¿se reinicia a 0?). *(Se deduce de la imagen / `/speckit-clarify`.)*
- [x] **Canal de envío:** WhatsApp. El bot devuelve la imagen al dueño y este la reenvía desde el iPhone.
- [x] **Dónde se ejecutará:** alwaysdata (igual que el bot de finanzas).

## 5.1 Decisiones de stack (2026-10-25)

Lenguaje: **Python**, pero con herramientas modernas para practicar desarrollo guiado por IA con Spec Kit.

| Área | Elección | Motivo |
|------|----------|--------|
| Gestión de proyecto / deps | `uv` + `pyproject.toml` | Rápido, lockfile reproducible (`uv.lock`) |
| Python | 3.12+ | Compatible con alwaysdata |
| Bot de Telegram | `aiogram` 3 (async) | Router/filtros modernos, distinto a `python-telegram-bot` usado antes |
| Imagen | `Pillow` | Superponer X sobre la plantilla PNG |
| Persistencia | SQLite + `SQLAlchemy` 2.0 (tipado) | Un archivo, sin servidor; historial de citas para `/deshacer` |
| Configuración | `pydantic-settings` + `.env` | Token y ID del dueño fuera del código |
| Calidad | `ruff` (lint + format), `mypy` | Estilo y tipos consistentes |
| Pruebas | `pytest` + `pytest-asyncio` | TDD de la lógica de conteo y render |
| Despliegue | alwaysdata **Service** con long polling | Sin dominio/webhook; proceso persistente |


## 6. Próximos pasos

1. Responder las preguntas de la sección 5.
2. Mapear las posiciones de las X en la plantilla.
3. Construir el MVP: `/cita`, `/clientes`, `/deshacer`.
4. Desplegar y probar con clientes reales.
5. (Opcional) Fase 2: tarjeta digital con link por cliente.
