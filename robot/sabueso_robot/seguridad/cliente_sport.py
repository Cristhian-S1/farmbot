"""Adaptador de SportClient del Go2. Solo PuertaMovimiento debe usar Move/StopMove.

Expone únicamente los métodos de la lista blanca de tests/robot/test_puerta_unica.py.
Damp y las acciones acrobáticas no se exponen (S10; sección 4.4 del plan).
"""

from __future__ import annotations


class ClienteSportGo2:
    """Envuelve unitree_sdk2py SportClient; cumple el protocolo ClienteMovimiento."""

    def __init__(self, timeout_s: float = 3.0, cliente=None) -> None:
        if cliente is None:
            from unitree_sdk2py.go2.sport.sport_client import SportClient

            cliente = SportClient()
            cliente.SetTimeout(timeout_s)
            cliente.Init()
        self._cliente = cliente

    def Move(self, vx: float, vy: float, vyaw: float) -> int:
        return self._cliente.Move(vx, vy, vyaw)

    def StopMove(self) -> int:
        return self._cliente.StopMove()

    # Posturas: no desplazan el robot, pero requieren operador presente (F4.1).
    def ponerse_de_pie(self) -> int:
        codigo = self._cliente.StandUp()
        if codigo == 0:
            # Por verificar en el robot: Move solo responde tras BalanceStand.
            codigo = self._cliente.BalanceStand()
        return codigo

    def echarse(self) -> int:
        return self._cliente.StandDown()
