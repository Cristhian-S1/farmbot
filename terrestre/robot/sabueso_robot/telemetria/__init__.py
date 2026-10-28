"""Recepción de estados del robot y registro local sin comandos de movimiento."""

from __future__ import annotations

import json
import logging
import math
import sqlite3
import threading
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable

from ..config import ConfigRobot
from ..sdk import Suscriptor, tipo_low_state, tipo_sport_state

__all__ = [
    "EstadoRobot", "combinar_sport", "combinar_low", "FuenteTelemetria", "RegistroTelemetria",
]

_LOG = logging.getLogger(__name__)


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
    distancias_obstaculo_m: tuple[float, ...] | None = None

    def distancia_minima_m(self) -> float | None:
        """Descarta distancias nulas, negativas y no finitas del sensor."""
        validas = (
            distancia for distancia in (self.distancias_obstaculo_m or ())
            if math.isfinite(distancia) and distancia > 0
        )
        return min(validas, default=None)


def combinar_sport(base: EstadoRobot, msg, marca_tiempo: float) -> EstadoRobot:
    """Conserva los campos previos que no publica esta versión del mensaje."""
    cambios = {"marca_tiempo": marca_tiempo}
    for origen, destino in (
        ("velocity", "velocidad"),
        ("yaw_speed", "velocidad_giro"),
        ("position", "posicion"),
        ("mode", "modo"),
        ("error_code", "codigo_error"),
        ("range_obstacle", "distancias_obstaculo_m"),
    ):
        valor = getattr(msg, origen, None)
        if valor is not None:
            if origen in ("velocity", "position", "range_obstacle"):
                valor = tuple(valor)
            cambios[destino] = valor
    return replace(base, **cambios)


def combinar_low(base: EstadoRobot, msg, marca_tiempo: float) -> EstadoRobot:
    """Combina batería, tensión y temperatura disponibles sin exigir esos campos."""
    cambios = {"marca_tiempo": marca_tiempo}
    bateria = getattr(getattr(msg, "bms_state", None), "soc", None)
    if bateria is not None:
        cambios["bateria_pct"] = bateria
    for origen, destino in (("power_v", "voltaje_v"), ("temperature_ntc1", "temperatura_c")):
        valor = getattr(msg, origen, None)
        if valor is not None:
            cambios[destino] = valor
    return replace(base, **cambios)


class FuenteTelemetria:
    """Combina dos tópicos DDS con acceso concurrente protegido por un Lock."""

    def __init__(
        self,
        config: ConfigRobot,
        reloj=time.time,
        fabrica_suscriptor=Suscriptor,
    ) -> None:
        self._config = config
        self._reloj = reloj
        self._fabrica_suscriptor = fabrica_suscriptor
        self._candado = threading.Lock()
        self._ciclo = threading.Lock()
        self._estado: EstadoRobot | None = None
        self._callbacks: list[Callable[[EstadoRobot], None]] = []
        self._suscriptores: list[Suscriptor] = []
        self._activa = False

    def iniciar(self) -> None:
        # Init y Close pueden esperar hilos DDS; nunca se ejecutan bajo _candado.
        with self._ciclo:
            with self._candado:
                if self._activa:
                    return
            especificaciones = (
                (self._config.topico_sport, tipo_sport_state(), combinar_sport),
                (self._config.topico_low, tipo_low_state(), combinar_low),
            )
            suscriptores = []
            with self._candado:
                self._activa = True
            try:
                for topico, tipo, combinar in especificaciones:
                    suscriptor = self._fabrica_suscriptor(
                        topico, tipo,
                        lambda msg, combinar=combinar: self._recibir(msg, combinar),
                    )
                    suscriptores.append(suscriptor)
                    suscriptor.iniciar()
            except Exception:
                with self._candado:
                    self._activa = False
                for suscriptor in suscriptores:
                    try:
                        suscriptor.cerrar()
                    except Exception:
                        _LOG.exception("Error al cerrar una suscripción tras fallar el inicio")
                raise
            with self._candado:
                self._suscriptores = suscriptores

    def detener(self) -> None:
        with self._ciclo:
            with self._candado:
                self._activa = False
                suscriptores, self._suscriptores = self._suscriptores, []
            error = None
            for suscriptor in suscriptores:
                try:
                    suscriptor.cerrar()
                except Exception as exc:
                    _LOG.exception("Error al cerrar una suscripción de telemetría")
                    if error is None:
                        error = exc
            if error is not None:
                raise error

    def _recibir(self, msg, combinar: Callable) -> None:
        with self._candado:
            if not self._activa:
                return
            marca = self._reloj()
            base = self._estado if self._estado is not None else EstadoRobot(marca)
            estado = combinar(base, msg, marca)
            self._estado = estado
            callbacks = tuple(self._callbacks)
        for funcion in callbacks:
            try:
                funcion(estado)
            except Exception:
                _LOG.exception("Error en un callback de telemetría")

    def ultimo(self) -> EstadoRobot | None:
        with self._candado:
            return self._estado

    def edad_s(self) -> float | None:
        with self._candado:
            if self._estado is None:
                return None
            return max(0.0, self._reloj() - self._estado.marca_tiempo)

    def al_actualizar(self, funcion: Callable[[EstadoRobot], None]) -> None:
        with self._candado:
            self._callbacks.append(funcion)


class RegistroTelemetria:
    """Guarda muestras completas; el periodo mínimo se aplica a marca_tiempo."""

    def __init__(self, ruta_sqlite: str, periodo_min_s: float = 1.0) -> None:
        if not math.isfinite(periodo_min_s) or periodo_min_s < 0:
            raise ValueError("periodo_min_s debe ser finito y no negativo")
        self._periodo_min_s = periodo_min_s
        self._candado = threading.Lock()
        Path(ruta_sqlite).parent.mkdir(parents=True, exist_ok=True)
        self._conexion = sqlite3.connect(ruta_sqlite, check_same_thread=False)
        self._conexion.row_factory = sqlite3.Row
        with self._conexion:
            self._conexion.execute(
                """CREATE TABLE IF NOT EXISTS estados (
                    marca_tiempo REAL NOT NULL,
                    bateria_pct REAL, voltaje_v REAL, temperatura_c REAL,
                    velocidad TEXT, velocidad_giro REAL, posicion TEXT,
                    modo INTEGER, codigo_error INTEGER, distancias_obstaculo_m TEXT
                )"""
            )
            self._conexion.execute(
                "CREATE INDEX IF NOT EXISTS idx_estados_marca_tiempo ON estados (marca_tiempo)"
            )
        self._ultima_marca = self._conexion.execute(
            "SELECT MAX(marca_tiempo) FROM estados"
        ).fetchone()[0]

    def guardar(self, estado: EstadoRobot) -> bool:
        if not math.isfinite(estado.marca_tiempo):
            raise ValueError("marca_tiempo debe ser finita")
        with self._candado:
            if (
                self._periodo_min_s > 0
                and self._ultima_marca is not None
                and estado.marca_tiempo - self._ultima_marca < self._periodo_min_s
            ):
                return False
            with self._conexion:
                self._conexion.execute(
                    """INSERT INTO estados (
                        marca_tiempo, bateria_pct, voltaje_v, temperatura_c,
                        velocidad, velocidad_giro, posicion, modo, codigo_error,
                        distancias_obstaculo_m
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        estado.marca_tiempo, estado.bateria_pct, estado.voltaje_v,
                        estado.temperatura_c, self._serializar(estado.velocidad),
                        estado.velocidad_giro, self._serializar(estado.posicion),
                        estado.modo, estado.codigo_error,
                        self._serializar(estado.distancias_obstaculo_m),
                    ),
                )
            self._ultima_marca = estado.marca_tiempo
            return True

    @staticmethod
    def _serializar(valores) -> str | None:
        return json.dumps(valores) if valores is not None else None

    def consultar(self, desde: float, hasta: float) -> list[EstadoRobot]:
        """Consulta el intervalo inclusivo [desde, hasta] en orden temporal."""
        with self._candado:
            filas = self._conexion.execute(
                "SELECT * FROM estados WHERE marca_tiempo >= ? AND marca_tiempo <= ? "
                "ORDER BY marca_tiempo, rowid",
                (desde, hasta),
            ).fetchall()
        estados = []
        for fila in filas:
            datos = dict(fila)
            for campo in ("velocidad", "posicion", "distancias_obstaculo_m"):
                if datos[campo] is not None:
                    datos[campo] = tuple(json.loads(datos[campo]))
            estados.append(EstadoRobot(**datos))
        return estados

    def cerrar(self) -> None:
        with self._candado:
            self._conexion.close()
