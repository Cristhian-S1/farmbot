# Contratos entre módulos del software del robot

Este documento lo mantiene el orquestador. Fija las interfaces públicas para que los subagentes trabajen en paralelo sin modificar archivos ajenos. Un cambio de interfaz se pide al orquestador; no se hace por cuenta propia.

## Reglas comunes

- Python ≥ 3.8 (el dock usa Ubuntu 20.04). Use `from __future__ import annotations`. No use `match`, `X | Y` fuera de anotaciones, ni `dict[...]` fuera de anotaciones.
- **`unitree_sdk2py` se importa de forma diferida**, dentro de funciones o constructores, nunca al cargar el módulo. Así las pruebas corren sin SDK y sin robot. Todo cliente del SDK recibe un parámetro opcional para inyectar un doble de prueba.
- Solo biblioteca estándar más `PyYAML`. Nada de `requests`: use `urllib.request`.
- Nombres, docstrings y mensajes en español, siguiendo el estilo de `robot/sabueso_robot/seguridad/`.
- **Ninguna llamada a `.Move(`, `.MoveToAbsolutePosition(` ni `.MoveToIncrementPosition(` fuera de `seguridad/`.** La prueba `tests/robot/test_puerta_unica.py` lo verifica.
- Pruebas con `pytest` en `tests/robot/`, sin red ni hardware, con relojes y transportes falsos.
- No hacer `git commit`, `git push` ni conectarse al robot.

## Propiedad de archivos

| Responsable | Archivos |
| --- | --- |
| Orquestador (Opus 5.5) | `robot/sabueso_robot/config.py`, `conexion.py`, `seguridad/`, `movimiento/`, `mision/`, `__main__.py`, este documento |
| Codex 1 (GPT 6.1 Sol) | `robot/sabueso_robot/sdk/`, `robot/sabueso_robot/telemetria/`, `tests/robot/test_sdk.py`, `tests/robot/test_telemetria.py` |
| Codex 2 (GPT 6.1 Sol) | `robot/sabueso_robot/captura/`, `robot/sabueso_robot/sincronizacion/`, `tests/robot/test_captura.py`, `tests/robot/test_sincronizacion.py` |
| OpenCode (DeepSeek v4.1 flash) | `deploy/`, `scripts/robot/instalar_dock.sh`, `scripts/robot/desplegar.sh`, `tests/test_plantillas.py` |
| Sonnet 5.5 | `docs/entorno.md`, `docs/manual_instalacion.md`, `docs/revision_seguridad.md` |

## Interfaces ya disponibles (orquestador)

```python
# sabueso_robot.config
@dataclass(frozen=True)
class ConfigRobot:
    interfaz_dds: str = "eth0"              # interfaz del dock en 192.168.123.0/24
    dominio_dds: int = 0
    directorio_datos: str = "/home/unitree/sabueso_datos"
    topico_sport: str = "rt/sportmodestate"  # por verificar en el robot (algunos demos usan rt/sportstate)
    topico_low: str = "rt/lowstate"
    url_servidor: str | None = None
    timeout_rpc_s: float = 3.0
def cargar_config(ruta: str | None = None) -> ConfigRobot      # YAML; ver config/robot.yaml
def cargar_limites(ruta: str | None = None) -> Limites          # config/limites_seguridad.yaml

# sabueso_robot.conexion
def iniciar_dds(interfaz: str, dominio: int = 0, fabrica=None) -> None  # idempotente
```

## Interfaces que debe entregar Codex 1

```python
# sabueso_robot.sdk
def sdk_disponible() -> bool
class Suscriptor:                       # envuelve ChannelSubscriber
    def __init__(self, topico: str, tipo_mensaje, al_recibir: Callable[[object], None],
                 fabrica: Callable | None = None, cola: int = 10) -> None
    def iniciar(self) -> None
    def cerrar(self) -> None
def tipo_sport_state()  # -> unitree_sdk2py.idl.unitree_go.msg.dds_.SportModeState_ (import diferido)
def tipo_low_state()    # -> LowState_
class ClienteEvasion:                   # ObstaclesAvoidClient, SIN Move
    def __init__(self, timeout_s: float = 3.0, cliente=None) -> None
    def activar(self, encendido: bool) -> int   # SwitchSet
    def estado(self) -> bool | None             # SwitchGet

# sabueso_robot.telemetria
@dataclass(frozen=True)
class EstadoRobot:
    marca_tiempo: float
    bateria_pct: float | None = None
    voltaje_v: float | None = None
    temperatura_c: float | None = None
    velocidad: tuple[float, float, float] | None = None
    velocidad_giro: float | None = None
    posicion: tuple[float, float, float] | None = None
    modo: int | None = None
    codigo_error: int | None = None
    distancias_obstaculo_m: tuple[float, ...] | None = None   # SportModeState_.range_obstacle
    def distancia_minima_m(self) -> float | None
def combinar_sport(base: EstadoRobot, msg, marca_tiempo: float) -> EstadoRobot
def combinar_low(base: EstadoRobot, msg, marca_tiempo: float) -> EstadoRobot   # bms_state.soc, power_v, ...
class FuenteTelemetria:
    def __init__(self, config: ConfigRobot, reloj=time.time, fabrica_suscriptor=Suscriptor) -> None
    def iniciar(self) -> None
    def detener(self) -> None
    def ultimo(self) -> EstadoRobot | None
    def edad_s(self) -> float | None            # segundos desde el último mensaje
    def al_actualizar(self, funcion: Callable[[EstadoRobot], None]) -> None
class RegistroTelemetria:                       # SQLite
    def __init__(self, ruta_sqlite: str, periodo_min_s: float = 1.0) -> None
    def guardar(self, estado: EstadoRobot) -> bool   # False si se descartó por periodo_min_s
    def consultar(self, desde: float, hasta: float) -> list[EstadoRobot]
    def cerrar(self) -> None
```

## Interfaces que debe entregar Codex 2

```python
# sabueso_robot.captura
@dataclass(frozen=True)
class Captura:
    id: str                  # uuid4().hex
    recorrido_id: str
    hilera: str | None
    zona: str | None
    marca_tiempo: float
    ruta_archivo: str        # relativa a directorio_datos
    sha256: str
    estado_zona: str         # "asignada" | "sin_zona"  (CU1: nunca inventar una zona)
    sincronizada: bool = False
class ErrorCaptura(RuntimeError): ...
class CamaraFrontal:                             # VideoClient.GetImageSample
    def __init__(self, timeout_s: float = 3.0, cliente=None) -> None
    def obtener_jpeg(self) -> bytes              # valida firma JPEG; ErrorCaptura si falla
class ColaCapturas:                              # SQLite + archivos; escritura atómica
    def __init__(self, directorio: str, reloj=time.time) -> None
    def registrar(self, jpeg: bytes, recorrido_id: str, hilera: str | None, zona: str | None) -> Captura
    def pendientes(self, limite: int = 50) -> list[Captura]
    def marcar_sincronizada(self, captura_id: str) -> None
    def por_recorrido(self, recorrido_id: str) -> list[Captura]
    def ruta_absoluta(self, captura: Captura) -> str
    def cerrar(self) -> None

# sabueso_robot.sincronizacion
@dataclass(frozen=True)
class ResumenSincronizacion:
    enviadas: int
    fallidas: int
    pendientes: int
class Sincronizador:
    def __init__(self, cola: ColaCapturas, url_base: str, token: str | None = None,
                 transporte: Callable | None = None, reloj=time.time,
                 espera_inicial_s: float = 2.0, espera_max_s: float = 300.0) -> None
    def sincronizar_una_vez(self, limite: int = 20) -> ResumenSincronizacion
    def proxima_espera_s(self) -> float          # retroceso exponencial tras fallas
```

El envío es `POST {url_base}/capturas` (multipart: `metadatos` en JSON + `imagen` en JPEG), con la cabecera `Idempotency-Key: <id>`. Las respuestas 200, 201 y 409 (ya existía) marcan la captura como sincronizada; las 5xx y los errores de red cuentan como falla con reintento. El servidor aún no existe (decisión D1), por lo que el contrato HTTP es provisional.

## Interfaces del orquestador que consumen los demás

```python
# sabueso_robot.mision  (Figura 4 del informe de la Parte 1)
class EstadoMision(Enum): DISPONIBLE, VERIFICANDO, EN_PATRULLAJE, PAUSADA,
                          ADQUISICION_CERRADA, PROCESANDO, COMPLETADA, INCOMPLETA
```
