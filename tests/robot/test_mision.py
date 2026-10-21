from types import SimpleNamespace

import pytest

from sabueso_robot.mision import (
    EjecutorRecorrido,
    EstadoMision,
    Evento,
    MaquinaMision,
    Tramo,
    TransicionInvalida,
    problemas_para_iniciar,
)
from sabueso_robot.movimiento import Primitivas
from sabueso_robot.seguridad import Limites, PuertaMovimiento, SupervisorSeguridad

ZONAS = [("H1", "Z1"), ("H1", "Z2")]


class ClienteFalso:
    def __init__(self):
        self.movimientos, self.paradas = [], 0

    def Move(self, vx, vy, vyaw):
        self.movimientos.append((vx, vy, vyaw))
        return 0

    def StopMove(self):
        self.paradas += 1
        return 0


class Reloj:
    """Reloj simulado: dormir() hace avanzar el tiempo."""

    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def dormir(self, segundos):
        self.t += segundos


def estado(bateria=80.0, error=0, distancias=(2.0, 2.0, 2.0, 2.0)):
    minima = min((d for d in distancias if d > 0), default=None)
    return SimpleNamespace(
        bateria_pct=bateria, codigo_error=error, distancia_minima_m=lambda: minima
    )


@pytest.fixture
def entorno():
    reloj, cliente = Reloj(), ClienteFalso()
    puerta = PuertaMovimiento(cliente, Limites(), reloj=reloj)
    puerta.habilitar()
    primitivas = Primitivas(puerta, reloj=reloj, dormir=reloj.dormir)
    return SimpleNamespace(reloj=reloj, cliente=cliente, puerta=puerta, primitivas=primitivas)


def mision_en_patrullaje():
    maquina = MaquinaMision("r1", list(ZONAS))
    maquina.disparar(Evento.INICIAR)
    maquina.disparar(Evento.CONDICIONES_OK)
    return maquina


def test_flujo_completo_de_estados():
    maquina = mision_en_patrullaje()
    maquina.marcar_zona("H1", "Z1")
    maquina.marcar_zona("H1", "Z2")
    for evento in (Evento.FIN_DE_RUTA, Evento.ANALIZAR, Evento.REGISTRO_OK):
        maquina.disparar(evento)
    assert maquina.estado is EstadoMision.COMPLETADA and maquina.terminada
    assert [t.destino for t in maquina.historial][-1] is EstadoMision.COMPLETADA


def test_reanudar_exige_confirmacion_segura():
    maquina = mision_en_patrullaje()
    maquina.disparar(Evento.PAUSAR, "obstáculo")
    with pytest.raises(TransicionInvalida, match="seguras"):
        maquina.disparar(Evento.REANUDAR)
    assert maquina.disparar(Evento.REANUDAR, seguro=True) is EstadoMision.EN_PATRULLAJE


def test_transicion_invalida_y_zona_inventada():
    maquina = MaquinaMision("r1", list(ZONAS))
    with pytest.raises(TransicionInvalida):
        maquina.disparar(Evento.FIN_DE_RUTA)
    maquina = mision_en_patrullaje()
    with pytest.raises(ValueError, match="no se inventan"):
        maquina.marcar_zona("H9", "Z9")


def test_problemas_para_iniciar():
    limites = Limites()
    assert problemas_para_iniciar(None, None, limites) == ["sin telemetría del robot"]
    assert problemas_para_iniciar(estado(), 0.1, limites) == []
    motivos = problemas_para_iniciar(estado(bateria=20, error=7, distancias=(0.3,)), 3.0, limites)
    assert len(motivos) == 4


def test_primitiva_sostiene_y_detiene(entorno):
    assert entorno.primitivas.avanzar(0.3, 1.0) is True
    assert len(entorno.cliente.movimientos) == 20  # 20 Hz durante 1 s
    assert entorno.cliente.paradas == 1
    assert not entorno.puerta.bloqueada


def test_primitiva_se_interrumpe_con_paro(entorno):
    original = entorno.reloj.dormir

    def dormir_y_parar(segundos):
        original(segundos)
        if entorno.reloj.t >= 0.5:
            entorno.puerta.parar("operador")

    entorno.primitivas._dormir = dormir_y_parar
    assert entorno.primitivas.avanzar(0.3, 2.0) is False
    assert entorno.puerta.motivo_paro == "operador"


def test_periodo_debe_ser_menor_que_watchdog(entorno):
    with pytest.raises(ValueError, match="watchdog"):
        Primitivas(entorno.puerta, frecuencia_hz=2.0)


def test_ejecutor_completa_y_captura_cada_zona(entorno):
    maquina = mision_en_patrullaje()
    capturas = []
    tramos = [Tramo(h, z, 0.3, 1.0) for h, z in ZONAS]
    ejecutor = EjecutorRecorrido(
        maquina, tramos, entorno.puerta, entorno.primitivas, lambda *a: capturas.append(a)
    )
    assert ejecutor.ejecutar() is EstadoMision.ADQUISICION_CERRADA
    assert capturas == [("r1", "H1", "Z1"), ("r1", "H1", "Z2")]
    assert maquina.pendientes() == []


def test_ejecutor_pausa_ante_falla_de_captura_y_reanuda(entorno):
    maquina = mision_en_patrullaje()
    fallas = {"quedan": 1}

    def capturar(recorrido, hilera, zona):
        if zona == "Z2" and fallas["quedan"]:
            fallas["quedan"] -= 1
            raise OSError("cámara sin respuesta")

    tramos = [Tramo(h, z, 0.3, 0.5) for h, z in ZONAS]
    ejecutor = EjecutorRecorrido(maquina, tramos, entorno.puerta, entorno.primitivas, capturar)
    assert ejecutor.ejecutar() is EstadoMision.PAUSADA
    assert maquina.pendientes() == [("H1", "Z2")]
    assert entorno.puerta.bloqueada
    assert ejecutor.reanudar(seguro=True) is EstadoMision.ADQUISICION_CERRADA


def estado_completo(bateria=80.0, distancia=2.0, error=0):
    return SimpleNamespace(bateria_pct=bateria, codigo_error=error, distancia_minima_m=lambda: distancia)


def test_supervisor_detiene_si_falta_dato_durante_movimiento(entorno):
    supervisor = SupervisorSeguridad(entorno.puerta, reloj=entorno.reloj)
    supervisor.al_recibir_estado(estado_completo())
    entorno.puerta.mover(0.3, 0, 0)
    entorno.reloj.t += 0.1
    supervisor.revisar()
    assert not entorno.puerta.bloqueada
    entorno.reloj.t += 0.2  # 0,3 s sin lecturas
    entorno.puerta.mover(0.3, 0, 0)  # el comando sigue llegando: no salta el watchdog
    supervisor.revisar()
    assert entorno.puerta.motivo_paro.startswith("sin comunicación")


def test_supervisor_sin_movimiento_no_exige_datos(entorno):
    supervisor = SupervisorSeguridad(entorno.puerta, reloj=entorno.reloj)
    entorno.reloj.t = 100.0
    supervisor.revisar()
    assert not entorno.puerta.bloqueada


def test_supervisor_bateria_obstaculo_error_y_nan(entorno):
    supervisor = SupervisorSeguridad(entorno.puerta, reloj=entorno.reloj)
    casos = [
        (estado_completo(bateria=10), "batería en 10 %"),
        (estado_completo(distancia=0.55), "obstáculo a 0.55 m"),  # 0,5 m + margen 0,1 m
        (estado_completo(error=12), "error del robot 12"),
        (estado_completo(distancia=float("nan")), "lectura de obstáculo no finita"),
        (estado_completo(bateria=float("nan")), "lectura de batería no finita"),
    ]
    for estado_robot, motivo in casos:
        entorno.puerta.habilitar()
        supervisor.al_recibir_estado(estado_robot)
        assert entorno.puerta.motivo_paro == motivo
    assert supervisor.margen_frenado_m == pytest.approx(0.1)


def test_supervisor_sobrevive_a_stopmove_que_falla(entorno):
    pasos = {"n": 0}
    supervisor = SupervisorSeguridad(entorno.puerta, reloj=entorno.reloj)

    def revisar_que_falla():
        pasos["n"] += 1
        if pasos["n"] >= 3:
            supervisor._detener.set()
        raise OSError("rpc")

    supervisor.revisar = revisar_que_falla
    entorno.cliente.StopMove = lambda: (_ for _ in ()).throw(OSError("rpc"))
    supervisor._dormir = lambda s: None
    supervisor._bucle()  # no debe propagar la excepción
    assert pasos["n"] == 3
    assert entorno.puerta.bloqueada and not entorno.puerta.paro_confirmado


def test_reanudar_reverifica_condiciones(entorno):
    from sabueso_robot.mision import CondicionesInseguras

    maquina = mision_en_patrullaje()
    problemas = ["batería en 10 %"]
    tramos = [Tramo(h, z, 0.3, 0.5) for h, z in ZONAS]
    ejecutor = EjecutorRecorrido(
        maquina, tramos, entorno.puerta, entorno.primitivas, lambda *a: None, lambda: problemas
    )
    entorno.puerta.parar("batería")
    maquina.disparar(Evento.PAUSAR, "batería")
    with pytest.raises(CondicionesInseguras, match="batería"):
        ejecutor.reanudar(seguro=True)
    assert maquina.estado is EstadoMision.PAUSADA and entorno.puerta.bloqueada
    problemas.clear()
    assert ejecutor.reanudar(seguro=True) is EstadoMision.ADQUISICION_CERRADA
