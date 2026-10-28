"""Única puerta de acceso al movimiento del robot.

Todo comando de desplazamiento pasa por PuertaMovimiento, que aplica los límites,
mantiene un watchdog y bloquea el movimiento tras un paro. El resto del código no debe
llamar a SportClient.Move directamente (lo comprueba tests/robot/test_puerta_unica.py).

El paro nunca espera a un Move en curso: el motivo se fija de inmediato (sin candado) y
StopMove se envía fuera del candado de comandos (hallazgo S1 de docs/revision_seguridad.md).
"""

from __future__ import annotations

import logging
import math
import threading
import time
from typing import Callable, Protocol

from .limites import Limites

registro = logging.getLogger(__name__)

REINTENTOS_STOP = 3


class ClienteMovimiento(Protocol):
    """Subconjunto de unitree_sdk2py SportClient que usa Sabueso."""

    def Move(self, vx: float, vy: float, vyaw: float) -> int: ...

    def StopMove(self) -> int: ...


class MovimientoBloqueado(RuntimeError):
    """Se intentó mover el robot con un paro activo o sin supervisión."""


def _finito(valor) -> bool:
    return isinstance(valor, (int, float)) and math.isfinite(valor)


class PuertaMovimiento:
    def __init__(
        self,
        cliente: ClienteMovimiento,
        limites: Limites,
        reloj: Callable[[], float] = time.monotonic,
        latido_max_s: float | None = None,
    ) -> None:
        """latido_max_s: si se indica, mover() exige un latido del supervisor reciente (S3)."""
        self._cliente = cliente
        self._limites = limites
        self._reloj = reloj
        self._latido_max_s = latido_max_s
        self._candado = threading.Lock()  # serializa comandos; parar() no lo espera
        self._ultimo_comando: float | None = None
        self._ultimo_latido: float | None = None
        self._ultimo_enviado: tuple[float, float, float] | None = None
        self._motivo_paro: str | None = "inicio"  # se parte bloqueado hasta habilitar()
        self._paro_confirmado = True

    @property
    def limites(self) -> Limites:
        return self._limites

    @property
    def bloqueada(self) -> bool:
        return self._motivo_paro is not None

    @property
    def motivo_paro(self) -> str | None:
        return self._motivo_paro

    @property
    def paro_confirmado(self) -> bool:
        """False si el robot no aceptó StopMove: el operador debe usar el control remoto."""
        return self._paro_confirmado

    @property
    def en_movimiento(self) -> bool:
        return self._ultimo_comando is not None and not self.bloqueada

    def registrar_latido(self) -> None:
        self._ultimo_latido = self._reloj()

    def habilitar(self) -> None:
        """Lo invoca el operador tras comprobar condiciones seguras (CU1)."""
        with self._candado:
            registro.info("movimiento habilitado (paro previo: %s)", self._motivo_paro)
            self._motivo_paro = None
            self._ultimo_comando = None

    def reducir_limites(self, **cambios: float) -> None:
        with self._candado:
            self._limites = self._limites.reducido(**cambios)

    def mover(self, vx: float, vy: float, vyaw: float) -> tuple[float, float, float]:
        """Envía un comando recortado a los límites y devuelve lo que realmente se envió."""
        if not all(_finito(v) for v in (vx, vy, vyaw)):
            self.parar("comando no finito")
            raise MovimientoBloqueado("comando no finito")
        with self._candado:
            if self._motivo_paro is not None:
                raise MovimientoBloqueado(self._motivo_paro)
            if self._latido_max_s is not None and (
                self._ultimo_latido is None
                or self._reloj() - self._ultimo_latido > self._latido_max_s
            ):
                raise MovimientoBloqueado("supervisor de seguridad inactivo")
            comando = self._limites.recortar(vx, vy, vyaw)
            self._cliente.Move(*comando)
            # Un paro pudo llegar durante Move: no se registra el comando como vigente.
            if self._motivo_paro is not None:
                raise MovimientoBloqueado(self._motivo_paro)
            self._ultimo_comando = self._reloj()
            self._ultimo_enviado = comando
            return comando

    def detener(self) -> None:
        """Detención normal al terminar una primitiva; no bloquea ni activa el watchdog."""
        with self._candado:
            self._ultimo_comando = None
        if not self._enviar_stop():
            self.parar("StopMove rechazado al detener")

    def parar(self, motivo: str) -> None:
        """Paro inmediato; el movimiento queda bloqueado hasta un nuevo habilitar()."""
        if self._motivo_paro is None:
            self._motivo_paro = motivo  # asignación atómica: mover() deja de enviar ya
        registro.warning(
            "PARO: %s (último comando %s, t=%.3f)", motivo, self._ultimo_enviado, self._reloj()
        )
        self._ultimo_comando = None
        self._paro_confirmado = self._enviar_stop()

    def _enviar_stop(self) -> bool:
        for intento in range(1, REINTENTOS_STOP + 1):
            try:
                codigo = self._cliente.StopMove()
            except Exception:
                registro.exception("StopMove lanzó una excepción (intento %d)", intento)
                continue
            if codigo in (0, None):
                return True
            registro.error("StopMove devolvió %s (intento %d)", codigo, intento)
        registro.critical("El robot no confirmó StopMove: use el control remoto físico")
        return False

    def informar_obstaculo(self, distancia_m: float | None, margen_m: float = 0.0) -> None:
        """None significa «sin lectura» y se trata en el supervisor; nan detiene (S2)."""
        if distancia_m is None:
            return
        if not _finito(distancia_m):
            self.parar("lectura de obstáculo no finita")
        elif distancia_m < self._limites.distancia_paro_m + margen_m:
            self.parar(f"obstáculo a {distancia_m:.2f} m")

    def informar_bateria(self, porcentaje: float | None) -> None:
        if porcentaje is None:
            return
        if not _finito(porcentaje):
            self.parar("lectura de batería no finita")
        elif porcentaje < self._limites.bateria_min_operacion:
            self.parar(f"batería en {porcentaje:.0f} %")

    def revisar_watchdog(self) -> bool:
        """Debe llamarse periódicamente (lo hace SupervisorSeguridad). True si detuvo el robot."""
        ultimo = self._ultimo_comando
        if self._motivo_paro is not None or ultimo is None:
            return False
        if self._reloj() - ultimo > self._limites.timeout_comando_s:
            self.parar("watchdog: sin comandos")
            return True
        return False
