# Contrato: dominio ↔ bot

Frontera del principio II. Nada de lo que aparece aquí importa `aiogram`, y todo se prueba con
pytest sin red. Solo se fijan firmas, tipos y semántica; los cuerpos se escriben con TDD en la
implementación.

## `conteo.py` (puro, sin E/S)

```python
@dataclass(frozen=True)
class CitaEvento:                 # solo citas vigentes, en orden de id
    id: int
    origen: Literal["bot", "previa"]
    registrada_en: datetime | None
    es_premio: bool

@dataclass(frozen=True)
class EstadoTarjetas:
    citas_en_curso: int
    completadas: tuple[datetime | None, ...]   # fecha de cada cita de premio, en orden
    ultima_cita: datetime | None               # máxima registrada_en con origen "bot"

def estado(citas: Sequence[CitaEvento]) -> EstadoTarjetas
def siguiente_es_premio(citas_en_curso: int, citas_por_tarjeta: int) -> bool   # k >= N - 1
def flores_a_dibujar(citas_en_curso: int, casillas: int) -> int                # min(k, casillas)
def faltan_para_premio(citas_en_curso: int, citas_por_tarjeta: int) -> int     # citas, incluida la de premio
```

## `busqueda.py` (puro)

```python
def normalizar(texto: str) -> str                    # NFKD, sin diacríticos, casefold, espacios colapsados
def interpretar_id(texto: str) -> int | None         # "#12" o "12" -> 12
def distancia(a: str, b: str) -> int                 # Damerau-Levenshtein (OSA)
def parecido(consulta: str, nombre: str) -> int | None
    # ambos normalizados; devuelve la puntuación (menor = más parecido) o None.
    # Parecido si distancia <= 2 contra el nombre o alguna palabra, o si es prefijo de alguno.
def caracteres_no_admitidos(nombre: str) -> list[str]   # vacío = válido (research §8)
def limpiar_nombre(nombre: str) -> str               # recorta y colapsa espacios, conserva mayúsculas/acentos
```

## `diseno.py` (constantes versionadas)

Rutas de `assets/`, centros de las 9 casillas en orden de llenado, lado y desplazamiento de la
flor, centro y borde inferior del nombre, ancho máximo, tamaños de fuente máximo (117) y mínimo
(36), zona prohibida del ✨ y color. Valores en
[research §9](../research.md#9-render-de-la-tarjeta-pillow). `CASILLAS = len(CENTROS)`.

## `render.py` (Pillow, sin estado mutable compartido)

```python
class NombreNoCabe(Exception): ...

@dataclass(frozen=True)
class AjusteNombre:
    tamano: int                    # tamaño de fuente elegido (36..117)
    origen: tuple[int, int]        # dónde se dibuja

def ajustar_nombre(nombre: str) -> AjusteNombre          # lanza NombreNoCabe
def generar_tarjeta(nombre: str, flores: int) -> bytes   # PNG; 0 <= flores <= CASILLAS
```

Garantías verificables:
- casillas 1..`flores` con flor y el resto blancas;
- tinta del nombre dentro del área y fuera de la zona del ✨;
- píxeles fuera de las casillas y del área del nombre idénticos a la plantilla;
- mismos argumentos producen los mismos bytes.

## `servicio.py` (casos de uso; usa SQLAlchemy, conteo, búsqueda y render)

```python
@dataclass(frozen=True)
class ResumenCliente:
    id: int
    nombre: str
    citas_en_curso: int
    tarjetas_completadas: int
    ultima_cita: datetime | None
    proxima_es_premio: bool

# Resultado de buscar()
@dataclass(frozen=True) class Encontrado:      cliente: ResumenCliente
@dataclass(frozen=True) class Varios:          opciones: tuple[ResumenCliente, ...]
@dataclass(frozen=True) class Parecidos:       opciones: tuple[ResumenCliente, ...]   # máx. 6
@dataclass(frozen=True) class SinCoincidencias: ...
@dataclass(frozen=True) class IdInexistente:   id: int
Busqueda = Encontrado | Varios | Parecidos | SinCoincidencias | IdInexistente

@dataclass(frozen=True)
class ResultadoCita:
    cliente: ResumenCliente         # estado después de registrar
    es_premio: bool
    numero_tarjeta: int | None      # n.º de la tarjeta completada, si fue premio
    flores: int                     # flores a dibujar en la foto de respuesta

@dataclass(frozen=True)
class CitaVigente:
    id: int
    origen: Literal["bot", "previa"]
    registrada_en: datetime | None
    es_premio: bool

class NombreInvalido(Exception):  motivo: str   # caracteres o NombreNoCabe
class CitasPreviasFueraDeRango(Exception): ...
class ClienteInexistente(Exception): ...

class ServicioTarjetas:
    def __init__(self, sesiones: sessionmaker[Session], citas_por_tarjeta: int, zona: ZoneInfo) -> None
    def buscar(self, texto: str) -> Busqueda
    def validar_nombre(self, nombre: str) -> str                    # nombre limpio; lanza NombreInvalido
    def homonimos(self, nombre: str) -> tuple[ResumenCliente, ...]  # misma forma normalizada
    def crear_cliente(self, nombre: str, citas_previas: int, ahora: datetime) -> ResumenCliente
    def cita_del_dia(self, cliente_id: int, cuando: datetime) -> datetime | None   # hora de la cita de ese día, si hay
    def registrar_cita(self, cliente_id: int, cuando: datetime) -> ResultadoCita
    def ultima_cita_vigente(self, cliente_id: int) -> CitaVigente | None
    def deshacer_ultima(self, cliente_id: int, ahora: datetime) -> ResumenCliente | None   # None: no había citas
    def resumen(self, cliente_id: int) -> ResumenCliente
    def listar(self) -> tuple[ResumenCliente, ...]                  # orden alfabético normalizado, luego id
    def tarjeta_png(self, cliente_id: int, flores: int | None = None) -> bytes   # por defecto, la tarjeta en curso
```

Semántica:
- Cada método de escritura es una transacción: se aplica completo o nada.
- `registrar_cita` no comprueba "mismo día": esa confirmación es del flujo del bot, que pregunta
  `cita_del_dia` antes.
- Los `datetime` que entran y salen están en UTC con zona; la conversión a `ZONA_HORARIA` solo se
  usa para la regla de "mismo día" y para los textos.

## `config.py`

```python
class Ajustes(BaseSettings):        # lee .env
    bot_token: SecretStr
    owner_id: int
    zona_horaria: str               # nombre IANA, validado con zoneinfo
    citas_por_tarjeta: int = 10     # >= 2
    db_path: Path = Path("data/lealtad.db")
    log_level: str = "INFO"

def verificar_diseno(citas_por_tarjeta: int) -> None   # lanza si CASILLAS != N - 1 (FR-017)
```
