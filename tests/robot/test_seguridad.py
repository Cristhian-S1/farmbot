import pytest

from sabueso_robot.seguridad import Limites, MovimientoBloqueado, PuertaMovimiento


class ClienteFalso:
    def __init__(self) -> None:
        self.movimientos: list[tuple[float, float, float]] = []
        self.paradas = 0

    def Move(self, vx: float, vy: float, vyaw: float) -> int:
        self.movimientos.append((vx, vy, vyaw))
        return 0

    def StopMove(self) -> int:
        self.paradas += 1
        return 0


class RelojFalso:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


@pytest.fixture
def entorno():
    cliente, reloj = ClienteFalso(), RelojFalso()
    puerta = PuertaMovimiento(cliente, Limites(), reloj=reloj)
    puerta.habilitar()
    return puerta, cliente, reloj


def test_limites_rechazan_velocidad_que_incumple_rfn5():
    with pytest.raises(ValueError, match="RFN5"):
        Limites(vx_max=1.0)


@pytest.mark.parametrize(
    "cambios, mensaje",
    [
        ({"vx_max": float("nan")}, "finito"),
        ({"distancia_paro_m": 0.3}, "RFN5"),
        ({"timeout_comando_s": 1.0}, "timeout"),
        ({"vyaw_max": 5.0}, "vyaw_max"),
        ({"vx_max": 0.9, "vy_max": 0.9}, "combinada"),
        ({"vx_atras_max": 0.6}, "vx_atras_max"),
    ],
)
def test_limites_rechazan_valores_inseguros(cambios, mensaje):
    with pytest.raises(ValueError, match=mensaje):
        Limites(**cambios)


@pytest.mark.parametrize(
    "cambio",
    [{"distancia_paro_m": 0.5 - 1e-9}, {"bateria_min_operacion": 0}, {"timeout_comando_s": 0.31}],
)
def test_reducido_respeta_direccion_segura(cambio):
    with pytest.raises(ValueError):
        Limites().reducido(**cambio)
    assert Limites().reducido(distancia_paro_m=0.8).distancia_paro_m == 0.8


def test_limites_rechazan_claves_desconocidas():
    with pytest.raises(ValueError, match="desconocidas"):
        Limites.desde_dict({"vx_maximo": 0.3})


def test_limites_solo_se_reducen():
    with pytest.raises(ValueError, match="reducirse"):
        Limites(vx_max=0.3).reducido(vx_max=0.4)
    assert Limites(vx_max=0.3).reducido(vx_max=0.2).vx_max == 0.2


def test_puerta_parte_bloqueada():
    puerta = PuertaMovimiento(ClienteFalso(), Limites())
    with pytest.raises(MovimientoBloqueado):
        puerta.mover(0.1, 0, 0)


@pytest.mark.parametrize("vx", [5.0, 1.0, 0.51, -3.7])
def test_ningun_comando_supera_el_limite(entorno, vx):
    puerta, cliente, _ = entorno
    puerta.mover(vx, 9.0, -9.0)
    enviado = cliente.movimientos[-1]
    assert -puerta.limites.vx_atras_max <= enviado[0] <= puerta.limites.vx_max
    assert abs(enviado[1]) <= puerta.limites.vy_max
    assert abs(enviado[2]) <= puerta.limites.vyaw_max


def test_sin_retroceso_ni_lateral_por_defecto(entorno):
    puerta, cliente, _ = entorno
    assert puerta.mover(-0.5, -0.2, 0) == (0.0, 0.0, 0)


def test_parar_no_espera_a_un_move_bloqueado():
    import threading
    import time as tiempo

    liberar = threading.Event()

    class ClienteLento(ClienteFalso):
        def Move(self, vx, vy, vyaw):
            liberar.wait(2.0)
            return super().Move(vx, vy, vyaw)

    cliente = ClienteLento()
    puerta = PuertaMovimiento(cliente, Limites())
    puerta.habilitar()
    hilo = threading.Thread(target=lambda: pytest.raises(MovimientoBloqueado, puerta.mover, 0.2, 0, 0))
    hilo.start()
    tiempo.sleep(0.05)
    inicio = tiempo.monotonic()
    puerta.parar("operador")
    assert tiempo.monotonic() - inicio < 0.1
    assert cliente.paradas == 1
    liberar.set()
    hilo.join(1.0)


def test_stopmove_rechazado_se_reintenta_y_alarma(entorno):
    puerta, cliente, _ = entorno
    codigos = iter([3104, 3104, 3104])
    cliente.StopMove = lambda: next(codigos)
    puerta.parar("operador")
    assert puerta.bloqueada and not puerta.paro_confirmado


def test_stopmove_aceptado_al_segundo_intento(entorno):
    puerta, cliente, _ = entorno
    codigos = iter([3104, 0])
    cliente.StopMove = lambda: next(codigos)
    puerta.parar("operador")
    assert puerta.paro_confirmado


def test_sin_latido_del_supervisor_no_se_mueve():
    reloj = RelojFalso()
    puerta = PuertaMovimiento(ClienteFalso(), Limites(), reloj=reloj, latido_max_s=0.2)
    puerta.habilitar()
    with pytest.raises(MovimientoBloqueado, match="supervisor"):
        puerta.mover(0.1, 0, 0)
    puerta.registrar_latido()
    puerta.mover(0.1, 0, 0)
    reloj.t = 0.5
    with pytest.raises(MovimientoBloqueado, match="supervisor"):
        puerta.mover(0.1, 0, 0)


def test_watchdog_detiene_sin_comandos(entorno):
    puerta, cliente, reloj = entorno
    puerta.mover(0.2, 0, 0)
    reloj.t = 0.29
    assert puerta.revisar_watchdog() is False
    reloj.t = 0.31
    assert puerta.revisar_watchdog() is True
    assert cliente.paradas == 1
    assert puerta.bloqueada
    with pytest.raises(MovimientoBloqueado, match="watchdog"):
        puerta.mover(0.2, 0, 0)


def test_obstaculo_cercano_detiene(entorno):
    puerta, cliente, _ = entorno
    puerta.informar_obstaculo(0.6)
    assert not puerta.bloqueada
    puerta.informar_obstaculo(0.49)
    assert puerta.bloqueada and cliente.paradas == 1


def test_bateria_baja_detiene(entorno):
    puerta, cliente, _ = entorno
    puerta.informar_bateria(24)
    assert puerta.motivo_paro == "batería en 24 %"
    assert cliente.paradas == 1


def test_comando_no_finito_bloquea(entorno):
    puerta, cliente, _ = entorno
    with pytest.raises(MovimientoBloqueado, match="no finito"):
        puerta.mover(float("nan"), 0, 0)
    assert cliente.paradas == 1 and not cliente.movimientos


def test_detener_no_bloquea_ni_dispara_watchdog(entorno):
    puerta, cliente, reloj = entorno
    puerta.mover(0.2, 0, 0)
    puerta.detener()
    reloj.t = 10.0  # tras detener() el watchdog queda inactivo
    assert puerta.revisar_watchdog() is False
    assert not puerta.bloqueada and cliente.paradas == 1


def test_obstaculo_desconocido_lo_trata_el_supervisor(entorno):
    puerta, _, _ = entorno
    puerta.informar_obstaculo(None)  # la ausencia de lectura se vigila en SupervisorSeguridad
    assert not puerta.bloqueada
    puerta.informar_obstaculo(float("nan"))
    assert puerta.motivo_paro == "lectura de obstáculo no finita"


def test_cliente_sport_delega_y_equilibra():
    from types import SimpleNamespace

    llamadas = []
    falso = SimpleNamespace(
        StandUp=lambda: llamadas.append("StandUp") or 0,
        BalanceStand=lambda: llamadas.append("BalanceStand") or 0,
        StandDown=lambda: llamadas.append("StandDown") or 0,
        StopMove=lambda: llamadas.append("StopMove") or 0,
    )
    from sabueso_robot.seguridad import ClienteSportGo2

    cliente = ClienteSportGo2(cliente=falso)
    assert cliente.ponerse_de_pie() == 0 and cliente.echarse() == 0
    assert llamadas == ["StandUp", "BalanceStand", "StandDown"]


def test_habilitar_reanuda_tras_paro(entorno):
    puerta, cliente, _ = entorno
    puerta.parar("operador")
    puerta.habilitar()
    puerta.mover(0.1, 0, 0)
    assert cliente.movimientos[-1] == (0.1, 0, 0)
