# Bot Tarjeta de Lealtad — Contexto del proyecto

> Estado: **publicado en alwaysdata con webhook** (feature 002, 2026-11-16) y validado en
> producción con la computadora apagada. El `README.md` explica cómo publicar, actualizar y volver
> a una versión anterior.

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

- [x] **Imagen de la tarjeta:** recibida → `docs/referencia/tarjeta-ejemplo.jpeg` (ver 5.2).
- [x] **Número de casillas:** 9 (cuadrícula 3×3).
- [x] **Qué pasa al completarla:** el ciclo llega hasta la cita 10 (9 flores + la cita 10 de
  premio); la siguiente cita empieza una tarjeta nueva. El número de citas por tarjeta debe ser
  configurable y se guarda el historial de tarjetas completadas (2026-11-16).
- [x] **Assets de producción:** plantilla vacía, flor con transparencia y fuente del nombre (ver 5.2).
- [x] **Canal de envío:** WhatsApp. El bot devuelve la imagen al dueño y este la reenvía desde el iPhone.
- [x] **Dónde se ejecutará:** alwaysdata (igual que el bot de finanzas).
- [x] **Zona horaria del negocio:** `America/Mexico_City` (2026-11-16).

## 5.1 Decisiones de stack (2026-10-25)

Lenguaje: **Python**, pero con herramientas modernas para practicar desarrollo guiado por IA con Spec Kit.

| Área | Elección | Motivo |
|------|----------|--------|
| Gestión de proyecto / deps | `uv` + `pyproject.toml` | Rápido, lockfile reproducible (`uv.lock`) |
| Python | 3.12+ | Compatible con alwaysdata |
| Bot de Telegram | ~~`aiogram` 3~~ → `python-telegram-bot` 22 (async) | Ver los cambios de la feature 002, abajo |
| Imagen | `Pillow` | Superponer las marcas (flor) y el nombre sobre la plantilla |
| Persistencia | SQLite + `SQLAlchemy` 2.0 (tipado) | Un archivo, sin servidor; historial de citas para `/deshacer` |
| Configuración | `pydantic-settings` + `.env` | Token y ID del dueño fuera del código |
| Calidad | `ruff` (lint + format), `mypy` | Estilo y tipos consistentes |
| Pruebas | `pytest` + `pytest-asyncio` | TDD de la lógica de conteo y render |
| Despliegue | ~~alwaysdata **Service** con long polling~~ → sitio *User program* con webhook | Ver los cambios de la feature 002, abajo |


**Cambios de la feature 002 (2026-11-16, publicación):**
- **Webhook en lugar de polling**: el plan Free de alwaysdata no admite *Services*, así que el bot
  corre como sitio *User program* en `CUENTA.alwaysdata.net/tarjeta` y recibe los mensajes por
  webhook (Starlette + uvicorn, como el bot de finanzas). Se duerme tras 30 minutos sin mensajes y
  despierta con el siguiente. En la computadora sigue usando polling con el bot de pruebas.
- **`python-telegram-bot` en lugar de `aiogram`**: por memoria. Con `aiogram` el bot ocupaba
  ~186 MB, que junto a los ~77 MB del bot de finanzas superaba los 256 MB del plan Free; con
  `python-telegram-bot`, ~96 MB.
- **Repositorio público en GitHub**: sin tokens, IDs ni el nombre de la cuenta de alwaysdata.

## 5.2 Análisis de la tarjeta real (2026-10-25)

Referencia: `docs/referencia/tarjeta-ejemplo.jpeg` (ejemplo con 6 de 9 casillas marcadas).

- **Formato:** JPEG, 1050 × 600 px.
- **Casillas:** 9 círculos blancos (RGB 255,255,255) en cuadrícula 3×3, Ø ≈ 118 px.
  - Centros medidos — columnas x = 584.0, 769.5, 954.5; filas y = 119.0, 301.0, 483.0.
  - Orden de llenado observado: por filas, de izquierda a derecha y de arriba abajo.
- **La marca no es una "X":** cada cita se marca con una **flor de lirio rosa** dentro del círculo.
- **La tarjeta es personalizada:** lleva el **nombre del cliente** en fuente manuscrita sobre la
  línea de la izquierda (en el ejemplo, "Carmen"). El bot debe renderizar también el nombre.
  - En el ejemplo, nombre + ✨ ocupan x 167–341, y 282–368; la línea va de x 50 a 440, y 378–381.
- Texto fijo: "Tarjeta de lealtad de:" y "Bienvenida a tu espacio! muchas gracias por tu confianza".

**Assets necesarios para generar tarjetas** (el ejemplo no sirve como plantilla porque ya trae
nombre y flores):

1. Plantilla **vacía**: fondo con los 9 círculos blancos y sin nombre.
   ✅ `assets/plantilla-vacia.png` (2026-11-16): generada a partir del ejemplo, rellenando las
   casillas con blanco y reconstruyendo el degradado bajo el nombre. Conserva el ✨ en su
   posición original (x 316–348, y 280–317): es parte fija del diseño. Si se consigue el original
   de Canva, conviene reemplazarla por una exportación directa.
2. La **flor** como PNG con fondo transparente (o el círculo con flor completo).
   ✅ `assets/flor.png` (2026-11-16): 115 × 115 RGBA, extraída de la casilla 1 del ejemplo; el
   blanco se convirtió en transparencia, así que sobre una casilla blanca reproduce el original.
   El centro del PNG va en el centro de la casilla; en los centros con .5 (x = 769.5, 954.5) se
   redondea hacia abajo, que es como está en el diseño.
3. La **fuente** del nombre (archivo `.ttf`/`.otf`) y la usada en el diseño, si es de Canva.
   ✅ `assets/fuentes/Sacramento-Regular.ttf` (Google Fonts, licencia OFL en `OFL.txt`). El dueño
   indicó que la fuente exacta no es relevante; tiene todas las letras del español. Tamaño de
   fuente del nombre: máximo 117 (con él "Carmen" mide 86 px de alto, como en el ejemplo), mínimo
   36. Los nombres de 19–20 caracteres probados caben con tamaños 37–50.

## 5.3 Personas autorizadas (2026-11-16)

El dueño decidió que otra persona use el bot con **todos los permisos** (todos los comandos y
botones, sobre los mismos clientes), también dentro de un grupo de Telegram donde las tarjetas y
la lista de clientes quedan visibles para todos sus miembros (constitución v4.0.0).

- Se configura con `AUTORIZADOS` en el `.env` (IDs separados por comas); el dueño siempre está
  autorizado. El README explica cómo obtener el ID de una persona.
- En un grupo, el bot solo responde a sus comandos y botones.
- El log anota quién registró, dio de alta o deshizo cada cita, y todo lo que envían las cuentas
  no autorizadas.
- Estado: feature `003-usuarios-autorizados` implementada, con las pruebas en verde. Falta
  publicarla después de integrar la feature 002 y validarla en producción
  (`specs/003-usuarios-autorizados/quickstart.md`).

## 6. Próximos pasos

1. ✅ Responder las preguntas de la sección 5.
2. ✅ Conseguir los assets de producción y mapear las casillas (ver 5.2).
3. ✅ Construir el MVP: `/cita`, `/alta`, `/deshacer`, `/tarjeta`, `/clientes` y `/ayuda`.
4. ✅ Desplegar en alwaysdata y validarlo en producción (feature 002).
5. (Opcional) Fase 2: tarjeta digital con link por cliente.
