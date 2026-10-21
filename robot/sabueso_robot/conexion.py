"""Inicialización de DDS (CycloneDDS) con la interfaz conectada al robot."""

from __future__ import annotations

import threading
from typing import Callable

_candado = threading.Lock()
_iniciado: tuple[int, str] | None = None


def iniciar_dds(interfaz: str, dominio: int = 0, fabrica: Callable | None = None) -> None:
    """Llama una sola vez a ChannelFactoryInitialize; repetirla con otra interfaz es un error.

    No debe ejecutarse en una terminal con ROS 2 cargado: el SDK usa su propio CycloneDDS
    (ver docs/entorno.md).
    """
    global _iniciado
    with _candado:
        if _iniciado is not None:
            if _iniciado != (dominio, interfaz):
                raise RuntimeError(
                    f"DDS ya iniciado con dominio {_iniciado[0]} e interfaz {_iniciado[1]}"
                )
            return
        if fabrica is None:
            from unitree_sdk2py.core.channel import ChannelFactoryInitialize

            fabrica = ChannelFactoryInitialize
        fabrica(dominio, interfaz)
        _iniciado = (dominio, interfaz)


def _reiniciar_para_pruebas() -> None:
    global _iniciado
    with _candado:
        _iniciado = None
