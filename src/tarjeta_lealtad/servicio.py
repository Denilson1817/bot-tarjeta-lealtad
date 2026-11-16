"""Casos de uso del bot, sin Telegram (contracts/servicio-dominio.md).

Cada método de escritura es una transacción. Las fechas entran y salen en UTC con zona; la zona del
negocio solo se usa para la regla de "mismo día".
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, cast
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from tarjeta_lealtad import busqueda, conteo, diseno, render
from tarjeta_lealtad.db import Cita, Cliente

MAXIMO_PARECIDOS = 6
LARGO_MAXIMO_NOMBRE = 60
MOTIVO_NO_CABE = (
    "es demasiado largo para la tarjeta; prueba con una versión más corta "
    "(por ejemplo, solo el nombre de pila)"
)


@dataclass(frozen=True)
class ResumenCliente:
    id: int
    nombre: str
    citas_en_curso: int
    tarjetas_completadas: int
    ultima_cita: datetime | None
    proxima_es_premio: bool


@dataclass(frozen=True)
class Encontrado:
    cliente: ResumenCliente


@dataclass(frozen=True)
class Varios:
    opciones: tuple[ResumenCliente, ...]


@dataclass(frozen=True)
class Parecidos:
    opciones: tuple[ResumenCliente, ...]


@dataclass(frozen=True)
class SinCoincidencias:
    pass


@dataclass(frozen=True)
class IdInexistente:
    id: int


type Busqueda = Encontrado | Varios | Parecidos | SinCoincidencias | IdInexistente


@dataclass(frozen=True)
class ResultadoCita:
    cliente: ResumenCliente  # estado después de registrar
    es_premio: bool
    numero_tarjeta: int | None  # n.º de la tarjeta completada, si fue la cita de premio
    flores: int  # flores a dibujar en la foto de respuesta


@dataclass(frozen=True)
class CitaVigente:
    id: int
    origen: Literal["bot", "previa"]
    registrada_en: datetime | None
    es_premio: bool


class NombreInvalido(Exception):
    def __init__(self, motivo: str) -> None:
        super().__init__(motivo)
        self.motivo = motivo


class CitasPreviasFueraDeRango(Exception):
    pass


class ClienteInexistente(Exception):
    pass


class ServicioTarjetas:
    def __init__(
        self, sesiones: sessionmaker[Session], citas_por_tarjeta: int, zona: ZoneInfo
    ) -> None:
        self._sesiones = sesiones
        self._citas_por_tarjeta = citas_por_tarjeta
        self._zona = zona

    @property
    def zona(self) -> ZoneInfo:
        return self._zona

    @property
    def citas_por_tarjeta(self) -> int:
        return self._citas_por_tarjeta

    # --- consultas -----------------------------------------------------------------------------

    def resumen(self, cliente_id: int) -> ResumenCliente:
        with self._sesiones() as sesion:
            return self._resumen(sesion, self._cliente(sesion, cliente_id))

    def tarjeta_png(self, cliente_id: int, flores: int | None = None) -> bytes:
        """La tarjeta del cliente; por defecto, con las flores de su tarjeta en curso."""
        with self._sesiones() as sesion:
            cliente = self._cliente(sesion, cliente_id)
            resumen = self._resumen(sesion, cliente)
        if flores is None:
            flores = conteo.flores_a_dibujar(resumen.citas_en_curso, diseno.CASILLAS)
        return render.generar_tarjeta(cliente.nombre, flores)

    def listar(self) -> tuple[ResumenCliente, ...]:
        """Todos los clientes en orden alfabético (sin acentos ni mayúsculas) y luego por ID."""
        with self._sesiones() as sesion:
            clientes = sesion.scalars(
                select(Cliente).order_by(Cliente.nombre_normalizado, Cliente.id)
            )
            return tuple(self._resumen(sesion, cliente) for cliente in clientes)

    def buscar(self, texto: str) -> Busqueda:
        """Por ID ("#12"), por nombre exacto (sin mayúsculas, acentos ni espacios) o parecidos."""
        cliente_id = busqueda.interpretar_id(texto)
        consulta = busqueda.normalizar(texto)
        with self._sesiones() as sesion:
            if cliente_id is not None:
                por_id = sesion.get(Cliente, cliente_id)
                if por_id is None:
                    return IdInexistente(cliente_id)
                return Encontrado(self._resumen(sesion, por_id))
            clientes = list(sesion.scalars(select(Cliente).order_by(Cliente.id)))
            exactos = [c for c in clientes if c.nombre_normalizado == consulta]
            if len(exactos) == 1:
                return Encontrado(self._resumen(sesion, exactos[0]))
            if exactos:  # mismo nombre: el dueño elige, nunca se adivina (FR-006)
                return Varios(tuple(self._resumen(sesion, c) for c in exactos))
            puntuados = [
                (puntuacion, cliente)
                for cliente in clientes
                if (puntuacion := busqueda.parecido(consulta, cliente.nombre_normalizado))
                is not None
            ]
            if not puntuados:
                return SinCoincidencias()
            puntuados.sort(key=lambda pc: (pc[0], pc[1].nombre_normalizado, pc[1].id))
            return Parecidos(
                tuple(self._resumen(sesion, c) for _, c in puntuados[:MAXIMO_PARECIDOS])
            )

    def homonimos(self, nombre: str) -> tuple[ResumenCliente, ...]:
        """Clientes con el mismo nombre normalizado, por ID (FR-020)."""
        consulta = busqueda.normalizar(busqueda.limpiar_nombre(nombre))
        with self._sesiones() as sesion:
            iguales = sesion.scalars(
                select(Cliente).where(Cliente.nombre_normalizado == consulta).order_by(Cliente.id)
            )
            return tuple(self._resumen(sesion, cliente) for cliente in iguales)

    def cita_del_dia(self, cliente_id: int, cuando: datetime) -> datetime | None:
        """Hora de la última cita del bot del mismo día (en la zona del negocio), si la hay."""
        dia = cuando.astimezone(self._zona).date()
        with self._sesiones() as sesion:
            self._cliente(sesion, cliente_id)
            del_dia = [
                cita.registrada_en
                for cita in self._vigentes(sesion, cliente_id)
                if cita.registrada_en is not None
                and cita.registrada_en.astimezone(self._zona).date() == dia
            ]
        return max(del_dia, default=None)

    # --- escritura -----------------------------------------------------------------------------

    def validar_nombre(self, nombre: str) -> str:
        """Devuelve el nombre limpio o lanza NombreInvalido con el motivo (FR-028)."""
        limpio = busqueda.limpiar_nombre(nombre)
        malos = busqueda.caracteres_no_admitidos(limpio)
        if malos:
            raise NombreInvalido("contiene caracteres no admitidos: " + " ".join(malos))
        if not any(c.isalpha() for c in limpio):
            raise NombreInvalido("debe contener al menos una letra")
        if len(limpio) > LARGO_MAXIMO_NOMBRE:
            raise NombreInvalido(MOTIVO_NO_CABE)
        try:
            render.ajustar_nombre(limpio)
        except render.NombreNoCabe:
            raise NombreInvalido(MOTIVO_NO_CABE) from None
        return limpio

    def crear_cliente(self, nombre: str, citas_previas: int, ahora: datetime) -> ResumenCliente:
        """Alta con las citas que ya lleva en su tarjeta actual (FR-018), sin cita del día."""
        maximo = self._citas_por_tarjeta - 1
        if not 0 <= citas_previas <= maximo:
            raise CitasPreviasFueraDeRango(f"las citas previas deben estar entre 0 y {maximo}")
        limpio = self.validar_nombre(nombre)
        with self._sesiones.begin() as sesion:
            cliente = Cliente(
                nombre=limpio, nombre_normalizado=busqueda.normalizar(limpio), creado_en=ahora
            )
            sesion.add(cliente)
            sesion.flush()
            sesion.add_all(
                Cita(cliente_id=cliente.id, origen="previa", registrada_en=None, creada_en=ahora)
                for _ in range(citas_previas)
            )
            sesion.flush()
            return self._resumen(sesion, cliente)

    def registrar_cita(self, cliente_id: int, cuando: datetime) -> ResultadoCita:
        """Suma una cita con la fecha del comando (FR-008). El "mismo día" lo revisa el bot."""
        with self._sesiones.begin() as sesion:
            cliente = self._cliente(sesion, cliente_id)
            antes = conteo.estado(self._eventos(sesion, cliente.id))
            # Con N citas por tarjeta, la N.ª es la de premio y cierra la tarjeta (FR-012, FR-016).
            es_premio = conteo.siguiente_es_premio(antes.citas_en_curso, self._citas_por_tarjeta)
            sesion.add(
                Cita(
                    cliente_id=cliente.id,
                    origen="bot",
                    registrada_en=cuando,
                    es_premio=es_premio,
                    creada_en=datetime.now(UTC),
                )
            )
            sesion.flush()
            resumen = self._resumen(sesion, cliente)
        if es_premio:  # la foto muestra la tarjeta recién completada, con todas las casillas
            return ResultadoCita(
                resumen,
                es_premio=True,
                numero_tarjeta=resumen.tarjetas_completadas,
                flores=diseno.CASILLAS,
            )
        flores = conteo.flores_a_dibujar(resumen.citas_en_curso, diseno.CASILLAS)
        return ResultadoCita(resumen, es_premio=False, numero_tarjeta=None, flores=flores)

    def ultima_cita_vigente(self, cliente_id: int) -> CitaVigente | None:
        with self._sesiones() as sesion:
            self._cliente(sesion, cliente_id)
            vigentes = self._vigentes(sesion, cliente_id)
        if not vigentes:
            return None
        ultima = vigentes[-1]
        return CitaVigente(
            id=ultima.id,
            origen=cast(conteo.Origen, ultima.origen),
            registrada_en=ultima.registrada_en,
            es_premio=ultima.es_premio,
        )

    def deshacer_ultima(self, cliente_id: int, ahora: datetime) -> ResumenCliente | None:
        """Anula la cita vigente más reciente (FR-022); nunca borra. None si no había ninguna.

        Si era la de premio, la tarjeta se reabre sola: el conteo se deriva de las vigentes.
        """
        with self._sesiones.begin() as sesion:
            cliente = self._cliente(sesion, cliente_id)
            vigentes = self._vigentes(sesion, cliente_id)
            if not vigentes:
                return None
            vigentes[-1].anulada_en = ahora
            sesion.flush()
            return self._resumen(sesion, cliente)

    # --- auxiliares ----------------------------------------------------------------------------

    @staticmethod
    def _cliente(sesion: Session, cliente_id: int) -> Cliente:
        cliente = sesion.get(Cliente, cliente_id)
        if cliente is None:
            raise ClienteInexistente(cliente_id)
        return cliente

    @staticmethod
    def _vigentes(sesion: Session, cliente_id: int) -> list[Cita]:
        consulta = (
            select(Cita)
            .where(Cita.cliente_id == cliente_id, Cita.anulada_en.is_(None))
            .order_by(Cita.id)
        )
        return list(sesion.scalars(consulta))

    def _eventos(self, sesion: Session, cliente_id: int) -> list[conteo.CitaEvento]:
        return [
            conteo.CitaEvento(
                id=cita.id,
                origen=cast(conteo.Origen, cita.origen),
                registrada_en=cita.registrada_en,
                es_premio=cita.es_premio,
            )
            for cita in self._vigentes(sesion, cliente_id)
        ]

    def _resumen(self, sesion: Session, cliente: Cliente) -> ResumenCliente:
        estado = conteo.estado(self._eventos(sesion, cliente.id))
        return ResumenCliente(
            id=cliente.id,
            nombre=cliente.nombre,
            citas_en_curso=estado.citas_en_curso,
            tarjetas_completadas=len(estado.completadas),
            ultima_cita=estado.ultima_cita,
            proxima_es_premio=conteo.siguiente_es_premio(
                estado.citas_en_curso, self._citas_por_tarjeta
            ),
        )
