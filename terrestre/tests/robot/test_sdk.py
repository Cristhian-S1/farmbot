"""Adaptadores del SDK probados sin CycloneDDS ni hardware."""

from __future__ import annotations

import builtins
import subprocess
import sys
from types import SimpleNamespace

import pytest

from sabueso_robot import sdk


def test_importar_modulos_no_importa_sdk():
    codigo = """
import builtins
original = builtins.__import__
def importar(nombre, *args, **kwargs):
    if nombre.startswith('unitree_sdk2py'):
        raise AssertionError('Import del SDK al cargar módulos')
    return original(nombre, *args, **kwargs)
builtins.__import__ = importar
import sabueso_robot.sdk
import sabueso_robot.telemetria
"""
    resultado = subprocess.run(
        [sys.executable, "-c", codigo],
        env={**__import__("os").environ, "PYTHONPATH": "robot"},
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 0, resultado.stderr


@pytest.mark.parametrize("disponible", [False, True])
def test_sdk_disponible_sin_cargar_modulo(monkeypatch, disponible):
    monkeypatch.setattr(sdk.importlib.util, "find_spec", lambda nombre: object() if disponible else None)
    assert sdk.sdk_disponible() is disponible


def test_suscriptor_fabrica_inyectada_y_cierre_idempotente():
    eventos = []
    recibidos = []

    class CanalFalso:
        def __init__(self, topico, tipo):
            eventos.append((topico, tipo))

        def Init(self, handler, cola):
            eventos.append(("Init", cola))
            handler(SimpleNamespace(valor=42))

        def Close(self):
            eventos.append("Close")

    suscriptor = sdk.Suscriptor("rt/prueba", object, recibidos.append, CanalFalso, cola=7)
    assert eventos == []
    suscriptor.iniciar()
    suscriptor.iniciar()
    assert recibidos[0].valor == 42
    suscriptor.cerrar()
    suscriptor.cerrar()
    assert eventos == [("rt/prueba", object), ("Init", 7), "Close"]
    suscriptor.iniciar()
    suscriptor.cerrar()
    assert eventos.count("Close") == 2


def test_suscriptor_limpia_canal_si_init_falla():
    cerrados = []

    class CanalFalso:
        def __init__(self, *_):
            pass

        def Init(self, *_):
            raise RuntimeError("No se pudo iniciar DDS")

        def Close(self):
            cerrados.append(True)

    suscriptor = sdk.Suscriptor("rt/prueba", object, lambda msg: None, CanalFalso)
    with pytest.raises(RuntimeError, match="DDS"):
        suscriptor.iniciar()
    assert cerrados == [True]


def test_importaciones_sdk_diferidas(monkeypatch):
    solicitudes = []
    canal = SimpleNamespace(Init=lambda *args: None, Close=lambda: None)
    cliente = SimpleNamespace(SetTimeout=lambda valor: None, Init=lambda: None)
    original = builtins.__import__
    modulo_tipos = SimpleNamespace(SportModeState_=type("Sport", (), {}),
                                   LowState_=type("Low", (), {}))

    def importar(nombre, *args, **kwargs):
        if nombre.startswith("unitree_sdk2py"):
            solicitudes.append(nombre)
            if nombre.endswith("core.channel"):
                return SimpleNamespace(ChannelSubscriber=lambda *args: canal)
            if nombre.endswith("obstacles_avoid_client"):
                return SimpleNamespace(ObstaclesAvoidClient=lambda: cliente)
            return modulo_tipos
        return original(nombre, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", importar)
    assert sdk.tipo_sport_state() is modulo_tipos.SportModeState_
    assert sdk.tipo_low_state() is modulo_tipos.LowState_
    suscriptor = sdk.Suscriptor("rt/prueba", object, lambda msg: None)
    suscriptor.iniciar()
    suscriptor.cerrar()
    sdk.ClienteEvasion()
    assert "unitree_sdk2py.core.channel" in solicitudes
    assert "unitree_sdk2py.go2.obstacles_avoid.obstacles_avoid_client" in solicitudes


@pytest.mark.parametrize("respuesta, esperado", [( (0, True), True), ((0, False), False),
                                                   ((1, True), None), ((0, None), None)])
def test_cliente_evasion_solo_expone_interruptor(respuesta, esperado):
    eventos = []
    cliente = SimpleNamespace(
        SetTimeout=lambda valor: eventos.append(("timeout", valor)),
        Init=lambda: eventos.append("Init"),
        SwitchSet=lambda valor: eventos.append(("SwitchSet", valor)) or 0,
        SwitchGet=lambda: respuesta,
    )
    adaptador = sdk.ClienteEvasion(timeout_s=2.0, cliente=cliente)
    assert adaptador.activar(True) == 0
    assert adaptador.estado() is esperado
    assert eventos == [("timeout", 2.0), "Init", ("SwitchSet", True)]
    assert not hasattr(adaptador, "Move")


def test_cliente_evasion_propaga_codigo_switchset():
    cliente = SimpleNamespace(SetTimeout=lambda valor: None, Init=lambda: None,
                              SwitchSet=lambda valor: 42)
    assert sdk.ClienteEvasion(cliente=cliente).activar(False) == 42
