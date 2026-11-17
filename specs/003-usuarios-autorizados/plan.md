# Implementation Plan: Personas autorizadas para usar el bot

**Branch**: `003-usuarios-autorizados` | **Date**: 2026-11-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-usuarios-autorizados/spec.md`

## Summary

El bot pasa de atender a un solo `OWNER_ID` a atender a un **conjunto de personas autorizadas**:
el dueño más los IDs de una variable nueva, `AUTORIZADOS`, separados por comas. Todas tienen los
mismos permisos y comparten la base de clientes. Los cambios son pequeños y quedan en la capa de
Telegram y la configuración; el dominio no se toca:

1. **`config.py`**: el campo `autorizados` (`NoDecode` + validador por comas) y la propiedad
   `ids_autorizados`.
2. **`bot/seguridad.py`**: el filtro recibe el conjunto, y solo anota como `WARNING` los
   *intentos* de uso (comandos, botones, mensajes privados), no la conversación de un grupo.
3. **`bot/handlers.py`**:
   - `sin_comando` solo responde en chats privados, así que en grupos no hay ruido;
   - las acciones que cambian datos registran `usuario=<id>` con un parámetro `autor` explícito.
4. **`bot/app.py`**: `crear_aplicacion(…, autorizados, …)`.
5. **README y `.env.example`**: cómo autorizar, cómo hallar el ID en el log y la visibilidad en
   grupos.

## Technical Context

**Language/Version**: Python 3.12 (sin cambios)

**Primary Dependencies**: las de la feature 002 (python-telegram-bot 22, Starlette, uvicorn, Pillow, SQLAlchemy, pydantic-settings 2.16). **Ninguna nueva**.

**Storage**: SQLite sin cambios de esquema

**Testing**: pytest + pytest-asyncio
- **Configuración y filtro**: pruebas unitarias.
- **Handlers**: pruebas con los fakes de `tests/bot/conftest.py`.
- **Integración**: aplicación real con `FakeTelegramAPI`, que se amplía para simular grupos.

**Target Platform**: igual que la 002 (alwaysdata Free con webhook; polling en local)

**Project Type**: proceso único (bot de Telegram)

**Performance Goals**: sin cambios (SC-002 de la 001 y SC-002/SC-003 de la 002)

**Constraints**:
- sin dependencias nuevas;
- compatible con los `.env` existentes (solo `OWNER_ID`);
- en grupos, cero respuestas a mensajes que no son comandos.

**Scale/Scope**: de 1 a 5 personas autorizadas además del dueño; 1 grupo

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* Constitución **v4.0.0**.

| Principio | Verificación | Antes de Fase 0 | Después de Fase 1 |
|-----------|--------------|-----------------|-------------------|
| I. Simplicidad | **Personas**: atiende a un grupo pequeño de usuarios autorizados (principio I v4.0.0). **Sin complejidad nueva**: no hay roles, tablas ni comandos de administración; la lista vive en la configuración. | ✅ | ✅ |
| II. Dominio separado | El dominio no cambia. `config.py` suma un campo sin importar `telegram` (lo vigila la prueba de arquitectura). | ✅ | ✅ |
| III. TDD en el dominio | No se toca el dominio. La configuración y el filtro, que son lo nuevo, se escriben con prueba primero. | ✅ | ✅ |
| IV. Datos como fuente de verdad | Sin cambios en el modelo ni en las reglas de conteo. | ✅ | ✅ |
| V. Seguridad | **Acceso**: responde solo a las cuentas autorizadas, también en grupos, con un único filtro en el grupo -1. **Intentos**: los no autorizados quedan con `WARNING`. **Secretos**: los IDs van en `.env`, nunca en el repositorio. **Grupos**: la regla de visibilidad queda en el README. | ✅ | ✅ |
| VI. alwaysdata Free | **Despliegue**: sin cambios; publicar es «Actualizar», agregar `AUTORIZADOS` y reiniciar. **Memoria**: sin impacto medible. | ✅ | ✅ |
| Stack | Sin dependencias nuevas. `NoDecode` ya viene en pydantic-settings 2.16. | ✅ | ✅ |
| Flujo | La rama `003-usuarios-autorizados` sale de la 002. Se integra a `main` después de la 002 y con los gates en verde. Enmienda v4.0.0 en su propio commit (`b85a7e3`). | ✅ | ✅ |

**Resultado**: pasa sin violaciones.

## Project Structure

### Documentation (this feature)

```text
specs/003-usuarios-autorizados/
├── plan.md
├── research.md                 # decisiones (formato de AUTORIZADOS, filtro, grupos, autor)
├── data-model.md               # sin cambios en la base; personas autorizadas en configuración
├── quickstart.md               # gates, validación local, publicación y validación en producción
├── contracts/
│   └── acceso-y-grupos.md      # AUTORIZADOS y matriz quién/dónde/qué → respuesta y log
├── checklists/requirements.md
└── tasks.md                    # /speckit-tasks
```

### Source Code (repository root)

```text
.env.example                    # + AUTORIZADOS (comentada, con explicación)
README.md                       # + sección "Personas autorizadas" y nota de visibilidad en grupos
src/tarjeta_lealtad/
├── config.py                   # + autorizados (NoDecode, validador por comas), ids_autorizados
└── bot/
    ├── seguridad.py            # crear_filtro(autorizados); WARNING solo para intentos de uso
    ├── handlers.py             # sin_comando solo en privado; parámetro autor en las acciones
    └── app.py                  # crear_aplicacion(…, autorizados, …); main() usa ids_autorizados
tests/
├── unit/test_config.py         # + AUTORIZADOS
└── bot/
    ├── conftest.py             # FakeTelegramAPI/update_de: tipo de chat (privado/grupo) y avisos
    ├── test_seguridad.py       # conjunto de autorizados; WARNING solo para intentos
    ├── test_handlers_*.py      # + autor en el log
    ├── test_integracion_app.py # + segunda persona, grupo, botón compartido, no autorizado
    └── (test_web.py, test_app.py: ajustar la firma de crear_aplicacion)
```

**Structure Decision**: sin archivos nuevos de código. Los cambios se concentran en
configuración, filtro y handlers, que es lo que el principio II deja fuera del dominio.

## Complexity Tracking

Sin violaciones de la constitución.
