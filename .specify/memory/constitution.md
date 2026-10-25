# Bot Tarjeta de Lealtad Constitution

Bot de Telegram de un solo usuario (el dueño del negocio) que registra las citas de cada
cliente y genera su tarjeta de lealtad (plantilla + nombre + N marcas) para reenviarla por WhatsApp.

## Core Principles

### I. Simplicidad primero (YAGNI)

- El sistema es un único proceso Python que atiende a un único usuario.
- NO se introducen microservicios, colas, caches, APIs propias ni capas de abstracción
  sin una necesidad presente y documentada en el plan.
- Toda complejidad añadida DEBE justificarse en la tabla "Complexity Tracking" del plan.

**Razón:** el problema es pequeño (~18 clientes/semana); cada capa extra cuesta
mantenimiento sin aportar valor.

### II. Lógica de dominio separada de Telegram

- El conteo de citas, el render de la tarjeta y la persistencia viven en módulos Python
  puros que NO importan `aiogram`.
- Los handlers de `aiogram` son una capa delgada de entrada/salida: interpretan el
  comando, llaman al dominio y devuelven la respuesta.
- Todo el dominio DEBE poder ejercitarse desde pytest sin red ni token de Telegram.

**Razón:** permite probar y reutilizar la lógica (p. ej. en la fase 2 web) sin depender
del bot.

### III. TDD en el dominio (NO NEGOCIABLE)

- Para conteo, deshacer y render de la tarjeta (marcas y nombre), las pruebas se escriben primero, se ven fallar y
  solo después se implementa (Red → Green → Refactor).
- Las pruebas de render verifican la salida de forma determinista (dimensiones, píxeles en
  las posiciones esperadas o comparación con imágenes de referencia).
- Los handlers de Telegram PUEDEN cubrirse con pruebas más ligeras, pero el dominio no.

**Razón:** un error en el conteo afecta directamente la promoción del cliente.

### IV. Los datos son la fuente de verdad

- La imagen de la tarjeta se regenera SIEMPRE desde la base de datos: plantilla vacía
  + nombre del cliente + N marcas en posiciones fijas. Nunca se edita una imagen generada
  previamente.
- Cada cita se registra como un evento (cliente, fecha/hora); el conteo se deriva de
  los eventos, lo que permite `/deshacer` de forma confiable y auditable.
- Las coordenadas de las casillas y del nombre se definen en configuración/código versionado, no a mano.

**Razón:** elimina el error de "perder la cuenta" que hoy vive dentro de las imágenes.

### V. Seguridad básica

- El bot DEBE responder únicamente al ID de Telegram del dueño; cualquier otro usuario se
  ignora (y se registra en el log).
- Los secretos (token del bot, ID del dueño) se cargan desde `.env` mediante
  `pydantic-settings` y NUNCA se versionan en el repositorio.
- La base de datos y las imágenes generadas no se suben al repositorio.

**Razón:** contiene datos de clientes y un token con control total del bot.

### VI. Compatible con alwaysdata

- La aplicación DEBE ejecutarse como un *Service* de alwaysdata usando long polling (sin
  webhook ni dominio propio).
- El despliegue se reduce a `uv sync` + reinicio del servicio; no requiere Docker.
- Consumo de recursos mínimo: SQLite en un archivo, sin dependencias de sistema más allá
  de las que Pillow ya resuelve con wheels.

**Razón:** mantener el hosting gratuito/barato y un despliegue repetible.

## Restricciones técnicas (stack)

| Área | Herramienta |
|------|-------------|
| Lenguaje | Python 3.12+ |
| Proyecto y dependencias | `uv`, `pyproject.toml`, `uv.lock` versionado |
| Bot de Telegram | `aiogram` 3 (async) |
| Imagen | `Pillow` |
| Persistencia | SQLite + `SQLAlchemy` 2.0 con tipado (`Mapped[...]`) |
| Configuración | `pydantic-settings` + `.env` |
| Calidad | `ruff` (lint + format), `mypy` |
| Pruebas | `pytest` + `pytest-asyncio` |

Añadir una dependencia nueva DEBE justificarse en el plan de la feature correspondiente.

## Flujo de desarrollo

- Cada feature sigue el ciclo de Spec Kit: `specify` → `clarify` → `plan` → `tasks` →
  `analyze` → `implement`.
- Una rama por feature (`NNN-nombre-corto`), integrada a `main` al terminar.
- Gates de calidad antes de integrar a `main`: `ruff check`, `ruff format --check`, `mypy`
  y `pytest` DEBEN pasar en verde.
- El "Constitution Check" del plan DEBE pasar antes de generar tareas; las desviaciones se
  documentan en "Complexity Tracking".

## Governance

- Esta constitución prevalece sobre cualquier otra práctica del proyecto. Todo plan y
  revisión DEBE verificar el cumplimiento de sus principios.
- Enmiendas: se proponen mediante `/speckit-constitution`, se documentan en el Sync Impact
  Report y se registran en un commit dedicado.
- Versionado semántico de la constitución:
  - MAJOR: eliminación o redefinición incompatible de un principio.
  - MINOR: principio o sección nueva, o guía ampliada de forma material.
  - PATCH: aclaraciones y correcciones de redacción.
- Revisión de cumplimiento: al cerrar cada feature se confirma que los gates de calidad y
  los principios II–V se respetaron.

**Version**: 1.0.0 | **Ratified**: 2026-10-25 | **Last Amended**: 2026-10-25
