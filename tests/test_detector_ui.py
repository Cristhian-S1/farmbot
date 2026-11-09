"""Detector -> registro -> API de ui/, sin cámara ni modelo real."""
import numpy as np
import pytest

from almacenamiento import Almacenamiento
from app import crear_app
from deteccion import Deteccion, Detector
from recorrido.__main__ import crear_registro

CLASES = ["tomate_verde", "tomate_maduro"]


class SesionFalsa:
    """Imita onnxruntime: devuelve cajas (en píxeles), etiquetas base 1 y puntajes."""

    def __init__(self, cajas, etiquetas, puntajes):
        self.salida = [np.array(cajas, dtype=np.float32).reshape(-1, 4), np.array(etiquetas), np.array(puntajes, dtype=np.float32)]
        self.entrada = None

    def run(self, _, alimentacion):
        self.entrada = alimentacion["imagen"]
        return self.salida


def cuadro():
    return np.full((60, 100, 3), (10, 20, 200), np.uint8)  # BGR: rojo


def test_filtra_por_umbral_recorta_y_traduce_clases():
    sesion = SesionFalsa([[10, 10, 50, 40], [-5, -5, 130, 90], [0, 0, 5, 5]], [2, 1, 1], [0.9, 0.7, 0.2])
    dets = Detector(sesion=sesion, clases=CLASES, umbral=0.5).detectar(cuadro())
    assert dets == [Deteccion("tomate_maduro", pytest.approx(0.9), (10, 10, 50, 40)),
                    Deteccion("tomate_verde", pytest.approx(0.7), (0, 0, 100, 60))]
    assert sesion.entrada.shape == (3, 60, 100) and sesion.entrada.dtype == np.float32
    assert sesion.entrada[0, 0, 0] == pytest.approx(200 / 255)  # el canal 0 es R: se convirtió de BGR a RGB


def test_sin_modelo_devuelve_vacio(monkeypatch, tmp_path):
    monkeypatch.delenv("SABUESO_MODELO", raising=False)
    monkeypatch.setattr("config.MODELO_RUTA", str(tmp_path / "no_existe.onnx"))
    assert Detector().detectar(cuadro()) == []


def test_modelo_pedido_que_no_existe_falla(tmp_path):
    with pytest.raises(FileNotFoundError):
        Detector(modelo=str(tmp_path / "no_existe.onnx"))


def test_registro_llega_a_la_api_con_el_contrato(tmp_path):
    det = Detector(sesion=SesionFalsa([[10, 10, 50, 40]], [2], [0.93]), clases=CLASES).detectar(cuadro())[0]
    registro = crear_registro("rec1", det, cuadro(), "H1", None)
    cliente = crear_app(Almacenamiento(str(tmp_path)), web_dir=str(tmp_path)).test_client()
    assert cliente.post("/api/registros", json=registro).status_code == 201
    [fila] = cliente.get("/api/registros").get_json()
    assert (fila["clase"], fila["confianza"], fila["caja"], fila["hilera"], fila["zona"]) == ("tomate_maduro", 0.93, "10,10,50,40", "H1", None)
    assert fila["foto"].endswith(".jpg")
