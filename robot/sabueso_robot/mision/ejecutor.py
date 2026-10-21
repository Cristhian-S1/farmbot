"""Recorrido guiado por tramos (opción D8-b del plan) con captura por zona."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

from ..movimiento import Primitivas
from ..seguridad import PuertaMovimiento
from .maquina import EstadoMision, Evento, MaquinaMision

registro = logging.getLogger(__name__)


class CondicionesInseguras(RuntimeError):
    """No se puede reanudar: la verificación encontró problemas."""

    def __init__(self, problemas: list[str]) -> None:
        super().__init__("; ".join(problemas))
        self.problemas = problemas


@dataclass(frozen=True)
class Tramo:
    """Avance hasta la zona y captura al llegar. Los tiempos se calibran en F4.4."""

    hilera: str
    zona: str
    velocidad_m_s: float
    duracion_s: float
    capturas: int = 1


class EjecutorRecorrido:
    """Recorre los tramos en orden. Ante un paro deja la misión en PAUSADA y no continúa:
    reanudar exige confirmación explícita del operador (reanudar(seguro=True))."""

    def __init__(
        self,
        maquina: MaquinaMision,
        tramos: list[Tramo],
        puerta: PuertaMovimiento,
        primitivas: Primitivas,
        capturar: Callable[[str, str, str], object],
        verificar: Callable[[], list[str]] = lambda: [],
    ) -> None:
        """verificar: devuelve los motivos para no reanudar (p. ej. problemas_para_iniciar
        con la telemetría vigente); se exige lista vacía antes de reanudar (S9)."""
        zonas = [(t.hilera, t.zona) for t in tramos]
        if zonas != maquina.zonas:
            raise ValueError("los tramos deben coincidir con las zonas de la misión")
        self._maquina = maquina
        self._tramos = tramos
        self._puerta = puerta
        self._primitivas = primitivas
        self._capturar = capturar  # (recorrido_id, hilera, zona) -> Captura
        self._verificar = verificar

    def ejecutar(self) -> EstadoMision:
        """Avanza por los tramos pendientes. Requiere la misión EN_PATRULLAJE."""
        if self._maquina.estado is not EstadoMision.EN_PATRULLAJE:
            raise RuntimeError("la misión debe estar EN_PATRULLAJE")
        for tramo in self._tramos:
            if (tramo.hilera, tramo.zona) in self._maquina.completadas:
                continue
            if not self._primitivas.avanzar(tramo.velocidad_m_s, tramo.duracion_s):
                return self._pausar()
            try:
                for _ in range(tramo.capturas):
                    self._capturar(self._maquina.recorrido_id, tramo.hilera, tramo.zona)
            except Exception as error:
                registro.exception("falla de captura en %s/%s", tramo.hilera, tramo.zona)
                self._puerta.parar(f"falla de captura: {error}")
                return self._pausar()
            self._maquina.marcar_zona(tramo.hilera, tramo.zona)
        return self._maquina.disparar(Evento.FIN_DE_RUTA)

    def reanudar(self, seguro: bool) -> EstadoMision:
        problemas = self._verificar()
        if problemas:
            raise CondicionesInseguras(problemas)
        self._maquina.disparar(Evento.REANUDAR, "operador confirmó condiciones", seguro=seguro)
        self._puerta.habilitar()
        return self.ejecutar()

    def cancelar(self, motivo: str) -> EstadoMision:
        self._puerta.parar(f"cancelación: {motivo}")
        return self._maquina.disparar(Evento.CANCELAR, motivo)

    def _pausar(self) -> EstadoMision:
        motivo = self._puerta.motivo_paro or "interrupción"
        registro.warning("misión pausada: %s", motivo)
        return self._maquina.disparar(Evento.PAUSAR, motivo)
