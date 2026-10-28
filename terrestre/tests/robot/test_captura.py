"""Captura y persistencia local sin SDK ni hardware."""

from __future__ import annotations

import hashlib
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from sabueso_robot.captura import CamaraFrontal, ColaCapturas, ErrorCaptura


JPEG = b"\xff\xd8imagen de prueba\xff\xd9"


class ClienteVideo:
    def __init__(self, resultado=(0, JPEG)):
        self.resultado = resultado
        self.llamadas = []

    def SetTimeout(self, timeout):
        self.llamadas.append(("timeout", timeout))

    def Init(self):
        self.llamadas.append(("init",))

    def GetImageSample(self):
        if isinstance(self.resultado, Exception):
            raise self.resultado
        return self.resultado


def test_camara_inicializa_y_convierte_lista():
    cliente = ClienteVideo((0, list(JPEG)))
    camara = CamaraFrontal(timeout_s=1.5, cliente=cliente)
    assert cliente.llamadas == [("timeout", 1.5), ("init",)]
    assert camara.obtener_jpeg() == JPEG


@pytest.mark.parametrize("resultado", [(9, JPEG), (0, b""), (0, b"PNG"),
                                       (0, [999]), OSError("cámara desconectada")])
def test_camara_rechaza_fallos_y_datos_no_jpeg(resultado):
    with pytest.raises(ErrorCaptura):
        CamaraFrontal(cliente=ClienteVideo(resultado)).obtener_jpeg()


@pytest.mark.parametrize("hilera,zona", [(None, None), ("h1", None), (None, "z1")])
def test_registrar_sin_zona_no_inventa_ubicacion(tmp_path, hilera, zona):
    cola = ColaCapturas(str(tmp_path), reloj=lambda: 123.5)
    try:
        captura = cola.registrar(JPEG, "recorrido_1", hilera, zona)
        assert captura.estado_zona == "sin_zona"
        assert captura.hilera is None and captura.zona is None
        assert captura.marca_tiempo == 123.5
        assert not captura.sincronizada
    finally:
        cola.cerrar()


def test_archivo_integro_metadatos_y_persistencia(tmp_path):
    cola = ColaCapturas(str(tmp_path))
    captura = cola.registrar(JPEG, "r-1", "hilera 1", "zona 2")
    assert len(captura.id) == 32
    assert captura.estado_zona == "asignada"
    assert captura.hilera == "hilera 1" and captura.zona == "zona 2"
    assert captura.ruta_archivo == "capturas/r-1/{}.jpg".format(captura.id)
    assert Path(cola.ruta_absoluta(captura)).read_bytes() == JPEG
    assert captura.sha256 == hashlib.sha256(JPEG).hexdigest()
    assert not list(tmp_path.rglob("*.tmp"))
    cola.cerrar()
    reabierta = ColaCapturas(str(tmp_path))
    try:
        assert reabierta.pendientes() == [captura]
        assert reabierta.por_recorrido("r-1") == [captura]
        assert (tmp_path / "capturas.sqlite").is_file()
    finally:
        reabierta.cerrar()


@pytest.mark.parametrize("recorrido", ["../escape", "/tmp/fuera", "a/b", "a\\b", "", ".", "..", "r\n"])
def test_recorrido_rechaza_path_traversal(tmp_path, recorrido):
    cola = ColaCapturas(str(tmp_path))
    try:
        with pytest.raises(ValueError):
            cola.registrar(JPEG, recorrido, "h", "z")
        assert cola.pendientes() == []
    finally:
        cola.cerrar()


def test_pendientes_marcar_y_limite(tmp_path):
    cola = ColaCapturas(str(tmp_path))
    try:
        primera = cola.registrar(JPEG, "r1", "h", "z")
        segunda = cola.registrar(JPEG, "r2", "h", "z")
        assert cola.pendientes(limite=1) == [primera]
        assert cola.pendientes(limite=0) == []
        cola.marcar_sincronizada(primera.id)
        cola.marcar_sincronizada(primera.id)
        assert cola.pendientes() == [segunda]
        assert cola.por_recorrido("r1")[0].sincronizada is True
    finally:
        cola.cerrar()


def test_registros_concurrentes_y_lectura(tmp_path):
    cola = ColaCapturas(str(tmp_path))
    try:
        def registrar(indice):
            captura = cola.registrar(JPEG, "r", "h", str(indice))
            assert cola.pendientes()
            return captura

        with ThreadPoolExecutor(max_workers=6) as ejecutor:
            capturas = list(ejecutor.map(registrar, range(24)))
        assert len({c.id for c in capturas}) == 24
        assert len(cola.pendientes()) == 24
        assert all(Path(cola.ruta_absoluta(c)).read_bytes() == JPEG for c in capturas)
    finally:
        cola.cerrar()


def test_fallo_replace_no_deja_fila_ni_temporal(tmp_path, monkeypatch):
    cola = ColaCapturas(str(tmp_path))
    try:
        def fallar(*args):
            raise OSError("disco no disponible")

        monkeypatch.setattr("os.replace", fallar)
        with pytest.raises(OSError):
            cola.registrar(JPEG, "r", "h", "z")
        assert cola.pendientes() == []
        assert not list(tmp_path.rglob("*.jpg"))
        assert not list(tmp_path.rglob("*.tmp"))
    finally:
        cola.cerrar()


def test_fallo_sqlite_no_deja_archivo_huerfano(tmp_path):
    cola = ColaCapturas(str(tmp_path))
    with sqlite3.connect(str(tmp_path / "capturas.sqlite")) as conexion:
        conexion.execute("CREATE TRIGGER rechazar BEFORE INSERT ON capturas "
                         "BEGIN SELECT RAISE(ABORT, 'disco lleno'); END")
    try:
        with pytest.raises(sqlite3.DatabaseError):
            cola.registrar(JPEG, "r", "h", "z")
        assert cola.pendientes() == []
        assert not list(tmp_path.rglob("*.jpg"))
    finally:
        cola.cerrar()
