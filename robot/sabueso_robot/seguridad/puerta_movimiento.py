"""Única puerta de acceso al movimiento del robot.

Todo comando de desplazamiento pasa por PuertaMovimiento, que aplica los límites,
mantiene un watchdog y bloquea el movimiento tras un paro. El resto del código no debe
llamar a SportClient.Move directamente (lo comprueba tests/robot/test_puerta_unica.py).
"""

from __future__ import annotations

import threading
import time
from typing import Callable, Protocol

from .limites import Limites


class ClienteMovimiento(Protocol):
    """Subconjunto de unitree_sdk2py SportClient que usa Sabueso."""

    def Move(self, vx: float, vy: float, vyaw: float) -> int: ...

    def StopMove(self) -> int: ...


class MovimientoBloqueado(RuntimeError):
    """Se intentó mover el robot con un paro activo."""


def _recortar(valor: float, maximo: float) -> float:
    return max(-maximo, min(maximo, valor))


class PuertaMovimiento:
    def __init__(
        self,
        cliente: ClienteMovimiento,
        limites: Limites,
        reloj: Callable[[], float] = time.monotonic,
    ) -> None:
        self._cliente = cliente
        self._limites = limites
        self._reloj = reloj
        self._candado = threading.Lock()
        self._ultimo_comando: float | None = None
        self._motivo_paro: str | None = "inicio"  # se parte bloqueado hasta habilitar()

    @property
    def limites(self) -> Limites:
        return self._limites

    @property
    def bloqueada(self) -> bool:
        return self._motivo_paro is not None

    @property
    def motivo_paro(self) -> str | None:
        return self._motivo_paro

    def habilitar(self) -> None:
        """Lo invoca el operador tras comprobar condiciones seguras (CU1)."""
        with self._candado:
            self._motivo_paro = None
            self._ultimo_comando = self._reloj()

    def reducir_limites(self, **cambios: float) -> None:
        with self._candado:
            self._limites = self._limites.reducido(**cambios)

    def mover(self, vx: float, vy: float, vyaw: float) -> tuple[float, float, float]:
        """Envía un comando recortado a los límites y devuelve lo que realmente se envió."""
        with self._candado:
            if self._motivo_paro is not None:
                raise MovimientoBloqueado(self._motivo_paro)
            comando = (
                _recortar(vx, self._limites.vx_max),
                _recortar(vy, self._limites.vy_max),
                _recortar(vyaw, self._limites.vyaw_max),
            )
            self._cliente.Move(*comando)
            self._ultimo_comando = self._reloj()
            return comando

    def parar(self, motivo: str) -> None:
        """Paro inmediato; el movimiento queda bloqueado hasta un nuevo habilitar()."""
        with self._candado:
            self._motivo_paro = motivo
            self._cliente.StopMove()

    def informar_obstaculo(self, distancia_m: float) -> None:
        if distancia_m < self._limites.distancia_paro_m:
            self.parar(f"obstáculo a {distancia_m:.2f} m")

    def informar_bateria(self, porcentaje: float) -> None:
        if porcentaje < self._limites.bateria_min_operacion:
            self.parar(f"batería en {porcentaje:.0f} %")

    def revisar_watchdog(self) -> bool:
        """Debe llamarse periódicamente (p. ej. cada 50 ms). Devuelve True si detuvo el robot."""
        with self._candado:
            if self._motivo_paro is not None or self._ultimo_comando is None:
                return False
            vencido = self._reloj() - self._ultimo_comando > self._limites.timeout_comando_s
        if vencido:
            self.parar("watchdog: sin comandos")
        return vencido
