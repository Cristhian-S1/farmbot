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
    assert abs(enviado[0]) <= puerta.limites.vx_max
    assert abs(enviado[1]) <= puerta.limites.vy_max
    assert abs(enviado[2]) <= puerta.limites.vyaw_max


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


def test_habilitar_reanuda_tras_paro(entorno):
    puerta, cliente, _ = entorno
    puerta.parar("operador")
    puerta.habilitar()
    puerta.mover(0.1, 0, 0)
    assert cliente.movimientos[-1] == (0.1, 0, 0)
