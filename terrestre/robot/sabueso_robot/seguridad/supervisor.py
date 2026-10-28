"""Conecta la telemetría con la puerta de movimiento (RFN5, CU1 y sección 4.4 del plan)."""

from __future__ import annotations

import logging
import math
import threading
import time
from typing import Callable

from .puerta_movimiento import PuertaMovimiento

registro = logging.getLogger(__name__)


class SupervisorSeguridad:
    """Detiene el robot ante obstáculo, batería baja, error del robot o pérdida de datos.

    Recibe estados con la forma de telemetria.EstadoRobot (duck typing). Política «sin dato,
    sin garantía» (S2): mientras se envían comandos, si la lectura de obstáculo o de batería
    lleva más de max_edad_s sin un valor válido, el robot se detiene. Así se vigila cada
    tópico por separado (obstáculo en rt/sportmodestate, batería en rt/lowstate).
    """

    def __init__(
        self,
        puerta: PuertaMovimiento,
        reloj: Callable[[], float] = time.monotonic,
        max_edad_s: float = 0.2,
        periodo_s: float = 0.05,
        dormir: Callable[[float], None] = time.sleep,
    ) -> None:
        self._puerta = puerta
        self._reloj = reloj
        self._max_edad_s = max_edad_s
        self._periodo_s = periodo_s
        self._dormir = dormir
        self._ultimo_obstaculo: float | None = None
        self._ultima_bateria: float | None = None
        self._detener = threading.Event()
        self._hilo: threading.Thread | None = None

    @property
    def margen_frenado_m(self) -> float:
        """S11: margen por la antigüedad máxima del dato a la velocidad máxima."""
        return self._puerta.limites.vx_max * self._max_edad_s

    def al_recibir_estado(self, estado) -> None:
        """Callback para FuenteTelemetria.al_actualizar."""
        ahora = self._reloj()
        distancia = estado.distancia_minima_m()
        if distancia is not None:
            if math.isfinite(distancia):
                self._ultimo_obstaculo = ahora
            self._puerta.informar_obstaculo(distancia, self.margen_frenado_m)
        if estado.bateria_pct is not None:
            if math.isfinite(estado.bateria_pct):
                self._ultima_bateria = ahora
            self._puerta.informar_bateria(estado.bateria_pct)
        if estado.codigo_error:
            self._puerta.parar(f"error del robot {estado.codigo_error}")

    def datos_vigentes(self) -> list[str]:
        """Motivos por los que los datos no están vigentes; vacía si lo están."""
        ahora, motivos = self._reloj(), []
        for nombre, marca in (("obstáculo", self._ultimo_obstaculo), ("batería", self._ultima_bateria)):
            if marca is None or ahora - marca > self._max_edad_s:
                motivos.append(f"sin lectura vigente de {nombre}")
        return motivos

    def revisar(self) -> None:
        """Un ciclo: latido, watchdog de comandos y vigencia de los datos."""
        self._puerta.registrar_latido()
        self._puerta.revisar_watchdog()
        if self._puerta.en_movimiento:
            motivos = self.datos_vigentes()
            if motivos:
                self._puerta.parar("sin comunicación: " + ", ".join(motivos))

    def iniciar(self) -> None:
        if self._hilo is not None:
            return
        self._detener.clear()
        self._hilo = threading.Thread(target=self._bucle, name="supervisor", daemon=True)
        self._hilo.start()

    def detener(self) -> None:
        self._detener.set()
        if self._hilo is not None:
            self._hilo.join(timeout=1.0)
            self._hilo = None

    def _bucle(self) -> None:
        while not self._detener.is_set():
            try:
                self.revisar()
            except Exception as error:  # el supervisor nunca debe morir (S3)
                registro.exception("falla del supervisor")
                try:
                    self._puerta.parar(f"falla del supervisor: {error}")
                except Exception:
                    registro.exception("no se pudo ordenar el paro tras la falla")
            self._dormir(self._periodo_s)
