# Quickstart: Personas autorizadas para usar el bot

Pasos para validar la feature y publicarla. Comportamiento esperado:
[contracts/acceso-y-grupos.md](contracts/acceso-y-grupos.md). El repositorio es público: aquí no
van IDs reales.

## 1. En la computadora

```bash
uv run ruff check && uv run ruff format --check && uv run mypy && uv run pytest
```

Esperado: los 4 gates en verde. Las pruebas cubren configuración, filtro, grupos, botones
compartidos y el registro de quién hizo cada acción, sin red.

Validación con el **bot de pruebas** (opcional, si la otra persona puede usarlo):
1. Arranca el bot en polling. Pídele a la otra persona que le escriba `/ayuda` **en privado**: no
   recibe respuesta, y en el log aparece
   `Mensaje ignorado de una cuenta no autorizada: id=… chat=privado`.
2. Agrega ese ID en `.env` (`AUTORIZADOS=<id>`) y reinicia. El log dice
   `Personas autorizadas: 2` y ahora `/ayuda` le responde.

## 2. Publicar

Requiere que la feature 002 ya esté integrada a `main` y que el servidor siga `main`.

1. **En la computadora**: integra la rama 003 a `main` (con los gates en verde) y haz `git push`.
2. **En el servidor**: actualiza como dice el README («Actualizar»).
3. **Obtén el ID de la otra persona**. Pídele que escriba `/ayuda` al bot de producción **en
   privado** (no en el grupo) y busca la línea con `chat=privado` en el log del sitio:

   ```bash
   grep -rh "cuenta no autorizada" ~/admin/logs/sites/ | tail -3
   ```

   Nunca autorices una línea con `usuario=GroupAnonymousBot`: es la cuenta compartida de los
   administradores anónimos de un grupo.
4. **Agrega el ID** al `.env` del servidor: `AUTORIZADOS=<id>`. Si son varias personas, sepáralas
   con comas.
5. **Reinicia el sitio** en Web > Sites y comprueba que el log dice `Personas autorizadas: 2`.
   Desde que tienes el ID hasta este punto: menos de 5 minutos (SC-004).

## 3. Validación en producción

| # | Acción | Esperado | Cubre |
|---|--------|----------|-------|
| 1 | La otra persona envía `/ayuda`, `/clientes` y `/cita <alguien>` en privado | Respuestas como las del dueño; la cita se suma a la misma base | US1, SC-001 |
| 2 | Lo mismo en el grupo | El bot responde en el grupo | US1-3 |
| 3 | El dueño pide `/cita Lucía` (cliente nuevo) en el grupo y la otra persona pulsa `Crear` | Se crea y registra una sola vez; un segundo toque dice "ya se aplicó o caducó" | FR-005 |
| 4 | Ambos conversan en el grupo sin comandos | El bot no responde | US4, SC-003 |
| 5 | Una tercera cuenta del grupo (no autorizada) envía `/clientes` o pulsa un botón | Sin respuesta ni efecto; `WARNING` con `chat=grupo` en el log | US2, SC-002 |
| 6 | Revisar el log del sitio después de las filas 1 y 3 | `Cita registrada: … usuario=<id de quien la registró>` | FR-010 |
| 7 | Quitar el ID de `AUTORIZADOS`, reiniciar y escribir de nuevo desde esa cuenta, midiendo el tiempo | Sin respuesta; el log dice `Personas autorizadas: 1`; menos de 5 minutos | US3-3, SC-004 |
