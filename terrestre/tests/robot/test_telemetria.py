"""Telemetría y almacenamiento con mensajes, reloj y transporte falsos."""

from __future__ import annotations

import logging
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from types import SimpleNamespace

import pytest

from sabueso_robot import telemetria
from sabueso_robot.config import ConfigRobot
from sabueso_robot.telemetria import (
    EstadoRobot,
    FuenteTelemetria,
    RegistroTelemetria,
    combinar_low,
    combinar_sport,
)


def test_estado_inmutable_y_combinacion_sport():
    base = EstadoRobot(1.0, bateria_pct=75)
    mensaje = SimpleNamespace(velocity=[0.1, 0.2, 0.3], yaw_speed=0.4,
                              position=[1.0, 2.0, 3.0], mode=2, error_code=7,
                              range_obstacle=[1.0, 0.0, 2.0, 3.0])
    nuevo = combinar_sport(base, mensaje, 2.0)
    assert nuevo == EstadoRobot(2.0, bateria_pct=75, velocidad=(0.1, 0.2, 0.3),
                                velocidad_giro=0.4, posicion=(1.0, 2.0, 3.0), modo=2,
                                codigo_error=7, distancias_obstaculo_m=(1.0, 0.0, 2.0, 3.0))
    mensaje.velocity[0] = 100
    assert nuevo.velocidad[0] == 0.1
    assert base.marca_tiempo == 1.0
    with pytest.raises(FrozenInstanceError):
        nuevo.bateria_pct = 0


@pytest.mark.parametrize("combinar", [combinar_sport, combinar_low])
def test_campos_ausentes_conservan_estado(combinar):
    base = EstadoRobot(1.0, bateria_pct=50, voltaje_v=28, temperatura_c=35,
                       velocidad=(0.1, 0.2, 0.3), velocidad_giro=0.4, posicion=(1, 2, 3),
                       modo=1, codigo_error=2, distancias_obstaculo_m=(1, 2, 3, 4))
    assert combinar(base, SimpleNamespace(), 2.0) == replace(base, marca_tiempo=2.0)


def test_combinar_low_y_bms_sin_soc():
    base = EstadoRobot(1.0)
    mensaje = SimpleNamespace(bms_state=SimpleNamespace(soc=81), power_v=29.5,
                              temperature_ntc1=37)
    nuevo = combinar_low(base, mensaje, 2.0)
    assert nuevo == EstadoRobot(2.0, bateria_pct=81, voltaje_v=29.5, temperatura_c=37)
    assert combinar_low(nuevo, SimpleNamespace(bms_state=SimpleNamespace()), 3.0) == replace(
        nuevo, marca_tiempo=3.0
    )


@pytest.mark.parametrize("distancias, esperado", [
    (None, None), ((), None), ((0, -1, float("nan"), float("inf"), -float("inf")), None),
    ((0, -2, float("nan"), 2.1, 0.3, float("inf")), 0.3),
])
def test_distancia_minima_ignora_valores_invalidos(distancias, esperado):
    assert EstadoRobot(0, distancias_obstaculo_m=distancias).distancia_minima_m() == esperado


@pytest.fixture
def fuente_falsa(monkeypatch):
    monkeypatch.setattr(telemetria, "tipo_sport_state", lambda: "SportFalso")
    monkeypatch.setattr(telemetria, "tipo_low_state", lambda: "LowFalso")
    suscriptores = []
    reloj = SimpleNamespace(t=10.0)

    class SuscriptorFalso:
        def __init__(self, topico, tipo, al_recibir):
            self.topico, self.tipo, self.al_recibir = topico, tipo, al_recibir
            self.inicios, self.cierres = 0, 0
            suscriptores.append(self)

        def iniciar(self):
            self.inicios += 1

        def cerrar(self):
            self.cierres += 1

    config = ConfigRobot(topico_sport="rt/sport_prueba", topico_low="rt/low_prueba")
    fuente = FuenteTelemetria(config, reloj=lambda: reloj.t, fabrica_suscriptor=SuscriptorFalso)
    yield fuente, suscriptores, reloj
    fuente.detener()


def test_fuente_une_topicos_y_calcula_edad(fuente_falsa):
    fuente, suscriptores, reloj = fuente_falsa
    assert fuente.ultimo() is None
    assert fuente.edad_s() is None
    fuente.iniciar()
    fuente.iniciar()
    assert [(s.topico, s.tipo, s.inicios) for s in suscriptores] == [
        ("rt/sport_prueba", "SportFalso", 1), ("rt/low_prueba", "LowFalso", 1),
    ]
    suscriptores[0].al_recibir(SimpleNamespace(velocity=[1, 2, 3]))
    reloj.t = 11.0
    suscriptores[1].al_recibir(SimpleNamespace(bms_state=SimpleNamespace(soc=70)))
    assert fuente.ultimo() == EstadoRobot(11.0, bateria_pct=70, velocidad=(1, 2, 3))
    reloj.t = 13.0
    assert fuente.edad_s() == 2.0
    fuente.detener()
    fuente.detener()
    assert [s.cierres for s in suscriptores] == [1, 1]
    suscriptores[1].al_recibir(SimpleNamespace(power_v=20))
    assert fuente.ultimo().voltaje_v is None


def test_fuente_callback_fallido_no_interrumpe_recepcion(fuente_falsa, caplog):
    fuente, suscriptores, _ = fuente_falsa
    recibidos = []

    def fallar(estado):
        raise RuntimeError("fallo intencional del consumidor")

    fuente.al_actualizar(fallar)
    # Consultar el último estado desde un callback también prueba ausencia de deadlock.
    fuente.al_actualizar(lambda estado: recibidos.append(fuente.ultimo()))
    fuente.iniciar()
    with caplog.at_level(logging.ERROR):
        suscriptores[0].al_recibir(SimpleNamespace(mode=1))
        suscriptores[0].al_recibir(SimpleNamespace(mode=2))
    assert [estado.modo for estado in recibidos] == [1, 2]
    assert "fallo intencional del consumidor" in caplog.text


def test_fuente_actualizaciones_concurrentes_preservan_ambos_topicos(fuente_falsa):
    fuente, suscriptores, _ = fuente_falsa
    fuente.iniciar()
    barrera = threading.Barrier(2)

    def enviar(indice, mensaje):
        barrera.wait(timeout=3)
        for _ in range(100):
            suscriptores[indice].al_recibir(mensaje)

    with ThreadPoolExecutor(max_workers=2) as ejecutor:
        sport = ejecutor.submit(enviar, 0, SimpleNamespace(mode=4))
        low = ejecutor.submit(enviar, 1, SimpleNamespace(power_v=28))
        sport.result(timeout=5)
        low.result(timeout=5)
    assert fuente.ultimo().modo == 4
    assert fuente.ultimo().voltaje_v == 28


def test_fuente_inicio_fallido_cierra_suscripciones(fuente_falsa, monkeypatch):
    fuente, suscriptores, _ = fuente_falsa
    fabrica = fuente._fabrica_suscriptor

    def fabricar(*args):
        suscriptor = fabrica(*args)
        if len(suscriptores) == 2:
            def fallar():
                raise RuntimeError("DDS no disponible")
            suscriptor.iniciar = fallar
        return suscriptor

    monkeypatch.setattr(fuente, "_fabrica_suscriptor", fabricar)
    with pytest.raises(RuntimeError, match="DDS"):
        fuente.iniciar()
    assert [s.cierres for s in suscriptores] == [1, 1]


def test_registro_throttle_consulta_y_persistencia(tmp_path):
    ruta = tmp_path / "datos" / "telemetria.sqlite"
    registro = RegistroTelemetria(str(ruta), periodo_min_s=1.0)
    estado = EstadoRobot(10.0, bateria_pct=70, voltaje_v=28, temperatura_c=35,
                         velocidad=(0.1, 0.2, 0.3), velocidad_giro=0.5,
                         posicion=(1, 2, 3), modo=4, codigo_error=7,
                         distancias_obstaculo_m=(0.5, 1, 2, 3))
    assert registro.guardar(estado)
    assert not registro.guardar(replace(estado, marca_tiempo=10.9))
    segundo = replace(estado, marca_tiempo=11.0)
    tercero = replace(estado, marca_tiempo=12.0)
    assert registro.guardar(segundo)
    assert registro.guardar(tercero)
    assert registro.consultar(10, 11) == [estado, segundo]
    assert registro.consultar(11, 12) == [segundo, tercero]
    assert registro.consultar(20, 30) == []
    registro.cerrar()
    registro.cerrar()
    reabierto = RegistroTelemetria(str(ruta))
    try:
        assert reabierto.consultar(0, 20) == [estado, segundo, tercero]
        assert not reabierto.guardar(replace(estado, marca_tiempo=12.1))
    finally:
        reabierto.cerrar()
    with sqlite3.connect(str(ruta)) as conexion:
        indices = conexion.execute("PRAGMA index_list(estados)").fetchall()
        assert any(conexion.execute("PRAGMA index_info('{}')".format(indice[1])).fetchone()[2]
                   == "marca_tiempo" for indice in indices)


def test_registro_nulos_y_consulta_ordenada(tmp_path):
    registro = RegistroTelemetria(str(tmp_path / "datos.sqlite"), periodo_min_s=0)
    try:
        for marca in (3, 1, 2):
            assert registro.guardar(EstadoRobot(marca))
        assert registro.consultar(1, 3) == [EstadoRobot(marca) for marca in (1, 2, 3)]
    finally:
        registro.cerrar()


def test_registro_concurrente_desde_callbacks(tmp_path):
    registro = RegistroTelemetria(str(tmp_path / "datos.sqlite"), periodo_min_s=0)
    try:
        with ThreadPoolExecutor(max_workers=4) as ejecutor:
            assert all(ejecutor.map(lambda i: registro.guardar(EstadoRobot(i)), range(40)))
        assert len(registro.consultar(0, 40)) == 40
    finally:
        registro.cerrar()


@pytest.mark.parametrize("periodo", [-1, float("nan"), float("inf")])
def test_registro_rechaza_periodos_invalidos(tmp_path, periodo):
    with pytest.raises(ValueError):
        RegistroTelemetria(str(tmp_path / "datos.sqlite"), periodo_min_s=periodo)
