"""Contrato HTTP y reintentos con transporte y reloj inyectados."""

from __future__ import annotations

import json
from email import policy
from email.parser import BytesParser
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

from sabueso_robot.captura import ColaCapturas
from sabueso_robot.sincronizacion import ResumenSincronizacion, Sincronizador


JPEG = b"\xff\xd8imagen\r\ncon datos\xff\xd9"


@pytest.fixture
def cola(tmp_path):
    instancia = ColaCapturas(str(tmp_path), reloj=lambda: 12.5)
    yield instancia
    instancia.cerrar()


class Transporte:
    def __init__(self, *resultados):
        self.resultados = iter(resultados)
        self.llamadas = []

    def __call__(self, url, cuerpo, cabeceras, timeout):
        self.llamadas.append((url, cuerpo, cabeceras, timeout))
        resultado = next(self.resultados)
        if isinstance(resultado, Exception):
            raise resultado
        return resultado


def test_multipart_parseable_con_metadatos_imagen_y_token(cola):
    captura = cola.registrar(JPEG, "r1", "hilera á", "zona 1")
    transporte = Transporte(201)
    sinc = Sincronizador(cola, "https://servidor.invalid/api/", token="secreto",
                         transporte=transporte)
    assert sinc.sincronizar_una_vez() == ResumenSincronizacion(1, 0, 0)
    url, cuerpo, cabeceras, timeout = transporte.llamadas[0]
    assert url == "https://servidor.invalid/api/capturas"
    assert timeout > 0
    assert cabeceras["Idempotency-Key"] == captura.id
    assert cabeceras["Authorization"] == "Bearer secreto"
    mensaje = BytesParser(policy=policy.default).parsebytes(
        ("Content-Type: " + cabeceras["Content-Type"] + "\r\nMIME-Version: 1.0\r\n\r\n")
        .encode("ascii") + cuerpo)
    assert mensaje.is_multipart()
    assert not mensaje.defects
    partes = {parte.get_param("name", header="content-disposition"): parte
              for parte in mensaje.iter_parts()}
    assert set(partes) == {"metadatos", "imagen"}
    metadatos = json.loads(partes["metadatos"].get_payload(decode=True))
    assert metadatos["id"] == captura.id
    assert metadatos["sha256"] == captura.sha256
    assert metadatos["hilera"] == "hilera á"
    assert metadatos["marca_tiempo"] == 12.5
    assert partes["imagen"].get_content_type() == "image/jpeg"
    assert partes["imagen"].get_payload(decode=True) == JPEG


@pytest.mark.parametrize("codigo", [200, 201, 409])
def test_codigos_aceptados_marcan_sincronizada_sin_token(cola, codigo):
    captura = cola.registrar(JPEG, "r", None, None)
    transporte = Transporte(codigo)
    assert Sincronizador(cola, "https://servidor.invalid", transporte=transporte) \
        .sincronizar_una_vez() == ResumenSincronizacion(1, 0, 0)
    assert "Authorization" not in transporte.llamadas[0][2]
    assert cola.por_recorrido(captura.recorrido_id)[0].sincronizada


def test_retroceso_exponencial_tope_y_reinicio(cola):
    cola.registrar(JPEG, "r", "h", "z")
    ahora = [100.0]
    transporte = Transporte(500, OSError("sin red"), 503, 200, 500)
    sinc = Sincronizador(cola, "https://servidor.invalid", transporte=transporte,
                         reloj=lambda: ahora[0], espera_inicial_s=2, espera_max_s=5)
    assert sinc.proxima_espera_s() == 0
    for espera in [2, 4, 5]:
        assert sinc.sincronizar_una_vez() == ResumenSincronizacion(0, 1, 1)
        assert sinc.proxima_espera_s() == espera
        llamadas = len(transporte.llamadas)
        assert sinc.sincronizar_una_vez() == ResumenSincronizacion(0, 0, 1)
        assert len(transporte.llamadas) == llamadas
        ahora[0] += espera
    assert sinc.sincronizar_una_vez() == ResumenSincronizacion(1, 0, 0)
    assert sinc.proxima_espera_s() == 0
    cola.registrar(JPEG, "r", "h", "z")
    assert sinc.sincronizar_una_vez().fallidas == 1
    assert sinc.proxima_espera_s() == 2
    ahora[0] += 0.5
    assert sinc.proxima_espera_s() == 1.5


def test_4xx_falla_permanente_una_sola_vez_por_pasada(cola, caplog):
    captura = cola.registrar(JPEG, "r", "h", "z")
    cola.registrar(JPEG, "r", "h", "z")
    transporte = Transporte(400, 201)
    sinc = Sincronizador(cola, "https://servidor.invalid", transporte=transporte)
    assert sinc.sincronizar_una_vez() == ResumenSincronizacion(1, 1, 1)
    assert len(transporte.llamadas) == 2
    assert captura.id in caplog.text and "400" in caplog.text
    assert "permanente" in caplog.text
    assert sinc.proxima_espera_s() == 0


@pytest.mark.parametrize("falta", [False, True])
def test_archivo_corrupto_o_ausente_no_se_envia(cola, falta, caplog):
    captura = cola.registrar(JPEG, "r", "h", "z")
    ruta = Path(cola.ruta_absoluta(captura))
    if falta:
        ruta.unlink()
    else:
        ruta.write_bytes(b"\xff\xd8alterado")
    transporte = Transporte()
    sinc = Sincronizador(cola, "https://servidor.invalid", transporte=transporte)
    assert sinc.sincronizar_una_vez() == ResumenSincronizacion(0, 1, 1)
    assert transporte.llamadas == []
    assert captura.id in caplog.text


def test_limite_y_total_pendientes(cola):
    for _ in range(3):
        cola.registrar(JPEG, "r", "h", "z")
    transporte = Transporte(200)
    sinc = Sincronizador(cola, "https://servidor.invalid", transporte=transporte)
    assert sinc.sincronizar_una_vez(limite=0) == ResumenSincronizacion(0, 0, 3)
    assert sinc.sincronizar_una_vez(limite=1) == ResumenSincronizacion(1, 0, 2)
    assert len(transporte.llamadas) == 1


@pytest.mark.parametrize("codigo", [201, 409, 503])
def test_transporte_urllib_post_y_http_error(cola, monkeypatch, codigo):
    cola.registrar(JPEG, "r", "h", "z")
    solicitudes = []

    class Respuesta:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def getcode(self):
            return codigo

    def abrir(solicitud, timeout):
        solicitudes.append(solicitud)
        if codigo != 201:
            raise HTTPError(solicitud.full_url, codigo, "respuesta", {}, None)
        return Respuesta()

    monkeypatch.setattr("urllib.request.urlopen", abrir)
    resumen = Sincronizador(cola, "https://servidor.invalid").sincronizar_una_vez()
    assert solicitudes[0].get_method() == "POST"
    assert resumen.enviadas == (0 if codigo == 503 else 1)
    assert resumen.fallidas == (1 if codigo == 503 else 0)


def test_transporte_urllib_error_red(cola, monkeypatch):
    cola.registrar(JPEG, "r", "h", "z")

    def abrir(*args, **kwargs):
        raise URLError("sin conexión")

    monkeypatch.setattr("urllib.request.urlopen", abrir)
    sinc = Sincronizador(cola, "https://servidor.invalid")
    assert sinc.sincronizar_una_vez() == ResumenSincronizacion(0, 1, 1)
    assert sinc.proxima_espera_s() > 0
