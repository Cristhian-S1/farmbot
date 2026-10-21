"""Adaptadores mínimos del SDK de Unitree con importaciones diferidas."""

from __future__ import annotations

import importlib.util
from typing import Callable

__all__ = ["sdk_disponible", "Suscriptor", "tipo_sport_state", "tipo_low_state", "ClienteEvasion"]


def sdk_disponible() -> bool:
    """Indica si el paquete está instalado, sin cargarlo ni iniciar DDS."""
    try:
        return importlib.util.find_spec("unitree_sdk2py") is not None
    except (ImportError, ValueError):
        return False


class Suscriptor:
    """Gestiona un ChannelSubscriber; la fábrica inyectada evita necesitar el SDK."""

    def __init__(
        self,
        topico: str,
        tipo_mensaje,
        al_recibir: Callable[[object], None],
        fabrica: Callable | None = None,
        cola: int = 10,
    ) -> None:
        self._topico = topico
        self._tipo_mensaje = tipo_mensaje
        self._al_recibir = al_recibir
        self._fabrica = fabrica
        self._cola = cola
        self._canal = None

    def iniciar(self) -> None:
        if self._canal is not None:
            return
        fabrica = self._fabrica
        if fabrica is None:
            from unitree_sdk2py.core.channel import ChannelSubscriber

            fabrica = ChannelSubscriber
        canal = fabrica(self._topico, self._tipo_mensaje)
        try:
            canal.Init(self._al_recibir, self._cola)
        except Exception:
            canal.Close()
            raise
        self._canal = canal

    def cerrar(self) -> None:
        canal, self._canal = self._canal, None
        if canal is not None:
            canal.Close()


def tipo_sport_state():
    """Carga el tipo DDS únicamente cuando se solicita."""
    from unitree_sdk2py.idl.unitree_go.msg.dds_ import SportModeState_

    return SportModeState_


def tipo_low_state():
    """Carga el tipo DDS únicamente cuando se solicita."""
    from unitree_sdk2py.idl.unitree_go.msg.dds_ import LowState_

    return LowState_


class ClienteEvasion:
    """Permite consultar y activar la evasión, sin interfaz de movimiento."""

    def __init__(self, timeout_s: float = 3.0, cliente=None) -> None:
        if cliente is None:
            # Ruta y respuesta de SwitchGet verificadas con Context7:
            # /unitreerobotics/unitree_sdk2_python, go2-aux-clients.md.
            from unitree_sdk2py.go2.obstacles_avoid.obstacles_avoid_client import (
                ObstaclesAvoidClient,
            )

            cliente = ObstaclesAvoidClient()
        self._cliente = cliente
        self._cliente.SetTimeout(timeout_s)
        self._cliente.Init()

    def activar(self, encendido: bool) -> int:
        return self._cliente.SwitchSet(encendido)

    def estado(self) -> bool | None:
        codigo, encendido = self._cliente.SwitchGet()
        if codigo != 0 or encendido is None:
            return None
        return bool(encendido)
