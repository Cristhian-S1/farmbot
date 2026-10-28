"""Primitivas de desplazamiento. Todo comando pasa por seguridad.PuertaMovimiento."""

from __future__ import annotations

import time
from typing import Callable

from ..seguridad import MovimientoBloqueado, PuertaMovimiento


class Primitivas:
    """Sostiene un comando a frecuencia fija durante un tiempo y se detiene al terminar.

    Las distancias se aproximan por tiempo mientras no exista navegación validada (D8).
    Cada primitiva devuelve True si terminó y False si un paro la interrumpió.
    """

    def __init__(
        self,
        puerta: PuertaMovimiento,
        frecuencia_hz: float = 20.0,
        reloj: Callable[[], float] = time.monotonic,
        dormir: Callable[[float], None] = time.sleep,
    ) -> None:
        if frecuencia_hz <= 0:
            raise ValueError("frecuencia_hz debe ser mayor que cero")
        periodo = 1.0 / frecuencia_hz
        if periodo >= puerta.limites.timeout_comando_s:
            raise ValueError("el periodo de comando debe ser menor que el timeout del watchdog")
        self._puerta = puerta
        self._periodo = periodo
        self._reloj = reloj
        self._dormir = dormir

    def avanzar(self, vx: float, duracion_s: float) -> bool:
        return self._sostener(vx, 0.0, 0.0, duracion_s)

    def desplazar_lateral(self, vy: float, duracion_s: float) -> bool:
        return self._sostener(0.0, vy, 0.0, duracion_s)

    def girar(self, vyaw: float, duracion_s: float) -> bool:
        return self._sostener(0.0, 0.0, vyaw, duracion_s)

    def _sostener(self, vx: float, vy: float, vyaw: float, duracion_s: float) -> bool:
        if duracion_s < 0:
            raise ValueError("duracion_s no puede ser negativa")
        inicio = self._reloj()
        try:
            while self._reloj() - inicio < duracion_s:
                if self._puerta.bloqueada:
                    return False
                self._puerta.mover(vx, vy, vyaw)
                self._dormir(self._periodo)
        except MovimientoBloqueado:
            return False
        self._puerta.detener()
        return True
