"""Mensajes y etiquetas del bot (contracts/comandos-bot.md). Texto plano, sin formato."""

from datetime import datetime
from zoneinfo import ZoneInfo

from tarjeta_lealtad import conteo, diseno
from tarjeta_lealtad.servicio import CitaVigente, ResultadoCita, ResumenCliente

_MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")

# comando: (uso, descripción, ejemplo)
COMANDOS: dict[str, tuple[str, str, str]] = {
    "cita": ("/cita <nombre o #id>", "registra una cita y envía la tarjeta", "/cita Carmen"),
    "alta": ("/alta <nombre> [citas previas]", "da de alta un cliente", "/alta Rosa 6"),
    "deshacer": ("/deshacer <nombre o #id>", "anula la última cita", "/deshacer Carmen"),
    "tarjeta": (
        "/tarjeta <nombre o #id>",
        "envía la tarjeta sin registrar cita",
        "/tarjeta Carmen",
    ),
    "clientes": ("/clientes", "lista de clientes con su avance", "/clientes"),
    "ayuda": ("/ayuda", "muestra esta ayuda", "/ayuda"),
}

AYUDA = "Comandos:\n" + "\n".join(
    f"{uso_} — {descripcion}. Ej.: {ejemplo}" for uso_, descripcion, ejemplo in COMANDOS.values()
)
NO_ES_COMANDO = "Usa /ayuda para ver los comandos."
ACCION_CADUCADA = "Esta acción ya se aplicó o caducó. Repite el comando."
ERROR_INESPERADO = "Algo salió mal y no pude terminar. Revisa con /clientes antes de repetir."
CANCELADO = "Cancelado. No se cambió nada."


def error_envio(cliente_id: int) -> str:
    return (
        f"No pude enviar la tarjeta de #{cliente_id}; los datos ya quedaron guardados. "
        f"Pídela con /tarjeta #{cliente_id}."
    )


def uso(comando: str) -> str:
    uso_, _, ejemplo = COMANDOS[comando]
    return f"Uso: {uso_}. Ejemplo: {ejemplo}"


def fecha_corta(momento: datetime, zona: ZoneInfo) -> str:
    local = momento.astimezone(zona)
    return f"{local.day} {_MESES[local.month - 1]}"


def fecha_hora(momento: datetime, zona: ZoneInfo) -> str:
    local = momento.astimezone(zona)
    return f"{local.day} {_MESES[local.month - 1]} {local.year}, {local:%H:%M}"


# --- botones -----------------------------------------------------------------------------------

BOTON_CREAR = "Crear"
BOTON_CANCELAR = "Cancelar"
BOTON_SI_REGISTRAR = "Sí, registrar"


def boton_crear(nombre: str) -> str:
    return f"Crear «{nombre}»"


def elegido(etiqueta: str) -> str:
    return f"✔️ {etiqueta}"


def etiqueta_cliente(cliente: ResumenCliente, zona: ZoneInfo) -> str:
    """Nombre, ID, flores en curso y última cita: "Carmen #3 · 4/9 · 10 nov"."""
    flores = conteo.flores_a_dibujar(cliente.citas_en_curso, diseno.CASILLAS)
    ultima = fecha_corta(cliente.ultima_cita, zona) if cliente.ultima_cita else "sin citas"
    return f"{cliente.nombre} #{cliente.id} · {flores}/{diseno.CASILLAS} · {ultima}"


# --- /cita -------------------------------------------------------------------------------------


def pie_cita(resultado: ResultadoCita, citas_por_tarjeta: int) -> str:
    cliente = resultado.cliente
    quien = f"{cliente.nombre} (#{cliente.id})"
    if resultado.es_premio:
        return (
            f"🎁 {quien}: ¡cita de premio! Tarjeta n.º {resultado.numero_tarjeta} completada. "
            "La próxima cita empieza una tarjeta nueva."
        )
    flores = f"{resultado.flores} de {diseno.CASILLAS} flores"
    if cliente.proxima_es_premio:
        return f"🌸 {quien}: {flores}. 🎁 ¡La próxima cita es la de premio!"
    faltan = conteo.faltan_para_premio(cliente.citas_en_curso, citas_por_tarjeta)
    return (
        f"🌸 {quien}: {flores}. Faltan {faltan} citas para la de premio (la {citas_por_tarjeta}.ª)."
    )


def confirmar_crear(nombre: str) -> str:
    return f"No encontré a «{nombre}». ¿Crear el cliente nuevo «{nombre}»?"


def confirmar_mismo_dia(cliente: ResumenCliente, hora: datetime, zona: ZoneInfo) -> str:
    return (
        f"{cliente.nombre} (#{cliente.id}) ya tiene una cita hoy a las "
        f"{hora.astimezone(zona):%H:%M}. ¿Registrar otra?"
    )


def elegir_parecido(texto: str) -> str:
    return f"No encontré a «{texto}». ¿Te refieres a alguno de estos?"


def elegir_homonimo(texto: str) -> str:
    return f"Hay varios clientes llamados «{texto}». ¿Cuál es?"


def id_inexistente(cliente_id: int) -> str:
    return f"No existe el cliente #{cliente_id}."


def no_encontrado(texto: str) -> str:
    return f"No encontré a «{texto}»."


def nombre_invalido(motivo: str) -> str:
    return f"No puedo usar ese nombre: {motivo}."


# --- /alta -------------------------------------------------------------------------------------

BOTON_CREAR_OTRO = "Crear otro"


def pie_alta(cliente: ResumenCliente) -> str:
    quien = f"{cliente.nombre} (#{cliente.id})"
    if cliente.citas_en_curso == 0:
        return f"✅ Cliente nuevo: {quien}, sin citas previas."
    return (
        f"✅ Cliente nuevo: {quien} con {cliente.citas_en_curso} citas previas. "
        "Revisa que la tarjeta coincida con la que tenía."
    )


def confirmar_homonimo(existentes: tuple[ResumenCliente, ...]) -> str:
    lista = ", ".join(f"{c.nombre} (#{c.id})" for c in existentes)
    verbo = "Ya existe" if len(existentes) == 1 else "Ya existen"
    return f"{verbo} {lista}. ¿Crear otro cliente con el mismo nombre?"


def previas_fuera_de_rango(maximo: int) -> str:
    return f"Las citas previas deben estar entre 0 y {maximo}."


# --- /deshacer ---------------------------------------------------------------------------------

BOTON_SI_DESHACER = "Sí, deshacer"


def confirmar_deshacer(cita: CitaVigente, cliente: ResumenCliente, zona: ZoneInfo) -> str:
    if cita.registrada_en is None:
        detalle = "cita previa al bot"
    else:
        detalle = fecha_hora(cita.registrada_en, zona)
    if cita.es_premio:
        detalle += " · cita de premio"
    return f"¿Anular la última cita de {cliente.nombre} (#{cliente.id})? {detalle}"


def pie_deshacer(cliente: ResumenCliente, era_premio: bool) -> str:
    flores = conteo.flores_a_dibujar(cliente.citas_en_curso, diseno.CASILLAS)
    pie = f"↩️ Cita anulada. {cliente.nombre} (#{cliente.id}): {flores} de {diseno.CASILLAS} flores."
    if era_premio:
        pie += f" La tarjeta n.º {cliente.tarjetas_completadas + 1} vuelve a estar en curso."
    return pie


def nada_que_deshacer(cliente: ResumenCliente) -> str:
    return f"{cliente.nombre} (#{cliente.id}) no tiene citas que deshacer."


def cita_cambio(cliente: ResumenCliente) -> str:
    return (
        f"La última cita de {cliente.nombre} (#{cliente.id}) cambió desde que pediste deshacer. "
        "No anulé nada; repite /deshacer."
    )


# --- /clientes y /tarjeta ----------------------------------------------------------------------

SIN_CLIENTES = "Todavía no hay clientes. Empieza con /cita o /alta."
LIMITE_MENSAJE = 4000  # Telegram admite 4096 caracteres por mensaje


def lista_clientes(clientes: tuple[ResumenCliente, ...]) -> str:
    lineas = [f"Clientes ({len(clientes)}):"]
    for cliente in clientes:
        flores = conteo.flores_a_dibujar(cliente.citas_en_curso, diseno.CASILLAS)
        linea = f"#{cliente.id} {cliente.nombre}: {flores}/{diseno.CASILLAS}"
        if cliente.proxima_es_premio:
            linea += " 🎁"
        completadas = cliente.tarjetas_completadas
        if completadas:
            linea += f" · {completadas} completada" + ("s" if completadas > 1 else "")
        lineas.append(linea)
    return "\n".join(lineas)


def dividir_mensajes(texto: str, limite: int = LIMITE_MENSAJE) -> list[str]:
    """Parte el texto entre líneas para no pasar el límite de un mensaje de Telegram."""
    partes: list[str] = []
    actual = ""
    for linea in texto.split("\n"):
        candidato = f"{actual}\n{linea}" if actual else linea
        if actual and len(candidato) > limite:
            partes.append(actual)
            actual = linea
        else:
            actual = candidato
    partes.append(actual)
    return partes


def pie_tarjeta(cliente: ResumenCliente) -> str:
    flores = conteo.flores_a_dibujar(cliente.citas_en_curso, diseno.CASILLAS)
    pie = f"🌸 {cliente.nombre} (#{cliente.id}): {flores} de {diseno.CASILLAS} flores"
    completadas = cliente.tarjetas_completadas
    if completadas == 1:
        return pie + " · 1 tarjeta completada."
    if completadas > 1:
        return pie + f" · {completadas} tarjetas completadas."
    return pie + "."
