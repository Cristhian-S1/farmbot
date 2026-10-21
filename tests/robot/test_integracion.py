"""Integración sin hardware: telemetría DDS → supervisor → puerta de movimiento."""

from types import SimpleNamespace

import pytest

import sabueso_robot.telemetria as telemetria
from sabueso_robot.__main__ import construir_parser
from sabueso_robot.config import ConfigRobot
from sabueso_robot.seguridad import Limites, PuertaMovimiento, SupervisorSeguridad


class SuscriptorFalso:
    creados = {}

    def __init__(self, topico, tipo, al_recibir, *args, **kwargs):
        SuscriptorFalso.creados[topico] = al_recibir

    def iniciar(self):
        pass

    def cerrar(self):
        pass


class ClienteFalso:
    def __init__(self):
        self.paradas = 0

    def Move(self, vx, vy, vyaw):
        return 0

    def StopMove(self):
        self.paradas += 1
        return 0


@pytest.fixture
def sistema(monkeypatch):
    monkeypatch.setattr(telemetria, "tipo_sport_state", lambda: object())
    monkeypatch.setattr(telemetria, "tipo_low_state", lambda: object())
    SuscriptorFalso.creados = {}
    config = ConfigRobot()
    fuente = telemetria.FuenteTelemetria(config, fabrica_suscriptor=SuscriptorFalso)
    cliente = ClienteFalso()
    puerta = PuertaMovimiento(cliente, Limites())
    supervisor = SupervisorSeguridad(puerta)
    fuente.al_actualizar(supervisor.al_recibir_estado)
    fuente.iniciar()
    puerta.habilitar()
    yield SimpleNamespace(config=config, fuente=fuente, puerta=puerta, cliente=cliente)
    fuente.detener()


def low(soc):
    return SimpleNamespace(bms_state=SimpleNamespace(soc=soc), power_v=29.0)


def sport(distancias):
    return SimpleNamespace(
        velocity=[0.0, 0.0, 0.0], yaw_speed=0.0, position=[0.0, 0.0, 0.0],
        mode=0, error_code=0, range_obstacle=list(distancias),
    )


def test_bateria_baja_por_dds_detiene(sistema):
    SuscriptorFalso.creados[sistema.config.topico_low](low(80))
    assert not sistema.puerta.bloqueada
    SuscriptorFalso.creados[sistema.config.topico_low](low(20))
    assert sistema.puerta.motivo_paro == "batería en 20 %"
    assert sistema.cliente.paradas == 1


def test_obstaculo_por_dds_detiene(sistema):
    SuscriptorFalso.creados[sistema.config.topico_sport](sport([1.5, 2.0, 0.4, 3.0]))
    assert sistema.puerta.motivo_paro.startswith("obstáculo a 0.40")
    assert sistema.cliente.paradas == 1


def test_cli_postura_sin_confirmacion_se_rechaza(capsys):
    args = construir_parser().parse_args(["postura", "de-pie"])
    assert args.funcion(args, ConfigRobot()) == 2
    assert "Rechazado" in capsys.readouterr().out


def test_cli_sincronizar_sin_url(capsys):
    args = construir_parser().parse_args(["sincronizar"])
    assert args.funcion(args, ConfigRobot()) == 1
