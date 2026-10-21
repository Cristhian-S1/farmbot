"""Envío idempotente de la cola local mediante el contrato HTTP provisional."""

from __future__ import annotations

import hashlib
import json
import logging
import math
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable
from uuid import uuid4

from ..captura import Captura, ColaCapturas


__all__ = ["ResumenSincronizacion", "Sincronizador"]
_LOG = logging.getLogger(__name__)
_TIMEOUT_S = 10.0


@dataclass(frozen=True)
class ResumenSincronizacion:
    enviadas: int
    fallidas: int
    pendientes: int


def _transporte_urllib(url: str, cuerpo: bytes, cabeceras: dict, timeout: float) -> int:
    solicitud = urllib.request.Request(url, data=cuerpo, headers=cabeceras, method="POST")
    try:
        with urllib.request.urlopen(solicitud, timeout=timeout) as respuesta:
            return respuesta.getcode()
    except urllib.error.HTTPError as error:
        try:
            return error.code
        finally:
            error.close()


def _multipart(captura: Captura, jpeg: bytes) -> tuple[bytes, str]:
    frontera = "sabueso_" + uuid4().hex
    metadatos = json.dumps(asdict(captura), ensure_ascii=False).encode("utf-8")
    cuerpo = (
        ("--" + frontera + "\r\n"
         'Content-Disposition: form-data; name="metadatos"\r\n'
         "Content-Type: application/json; charset=utf-8\r\n\r\n").encode("ascii")
        + metadatos + b"\r\n"
        + ("--" + frontera + "\r\n"
           'Content-Disposition: form-data; name="imagen"; filename="' + captura.id
           + '.jpg"\r\nContent-Type: image/jpeg\r\n\r\n').encode("ascii")
        + jpeg + ("\r\n--" + frontera + "--\r\n").encode("ascii")
    )
    return cuerpo, "multipart/form-data; boundary=" + frontera


class Sincronizador:
    """Procesa una instantánea de pendientes, sin dormir ni repetirla en bucle.

    Los fallos transitorios aplazan la siguiente pasada. El reloj inyectado
    permite consultar la espera restante sin bloquear al operador. Los 4xx
    permanentes quedan registrados y pendientes para revisión; nunca se
    confunden con una confirmación del servidor.
    """

    def __init__(self, cola: ColaCapturas, url_base: str, token: str | None = None,
                 transporte: Callable | None = None, reloj=time.time,
                 espera_inicial_s: float = 2.0, espera_max_s: float = 300.0) -> None:
        if (not math.isfinite(espera_inicial_s) or not math.isfinite(espera_max_s)
                or espera_inicial_s < 0 or espera_max_s < espera_inicial_s):
            raise ValueError("Las esperas deben ser finitas y cumplir 0 <= inicial <= máxima")
        self._cola = cola
        self._url = url_base.rstrip("/") + "/capturas"
        self._token = token
        self._transporte = transporte if transporte is not None else _transporte_urllib
        self._reloj = reloj
        self._espera_inicial = espera_inicial_s
        self._espera_max = espera_max_s
        self._espera = 0.0
        self._proximo_intento = None

    def _registrar_fallo_transitorio(self) -> None:
        self._espera = min(
            self._espera_max,
            self._espera * 2 if self._proximo_intento is not None else self._espera_inicial,
        )
        self._proximo_intento = self._reloj() + self._espera

    def proxima_espera_s(self) -> float:
        """Segundos restantes antes de permitir la siguiente pasada (cero si está lista)."""
        if self._proximo_intento is None:
            return 0.0
        return max(0.0, self._proximo_intento - self._reloj())

    def _resumen(self, enviadas: int, fallidas: int) -> ResumenSincronizacion:
        # El contrato de la cola expone una lista limitada, no un contador.
        total = len(self._cola.pendientes(limite=9223372036854775807))
        return ResumenSincronizacion(enviadas, fallidas, total)

    def sincronizar_una_vez(self, limite: int = 20) -> ResumenSincronizacion:
        if limite < 0:
            raise ValueError("limite no puede ser negativo")
        if self.proxima_espera_s() > 0:
            return self._resumen(0, 0)
        enviadas = fallidas = 0
        for captura in self._cola.pendientes(limite=limite):
            try:
                jpeg = Path(self._cola.ruta_absoluta(captura)).read_bytes()
            except (OSError, ValueError) as error:
                _LOG.error("Captura %s: archivo no disponible: %s", captura.id, error)
                fallidas += 1
                continue
            if hashlib.sha256(jpeg).hexdigest() != captura.sha256:
                _LOG.error("Captura %s: sha256 no coincide; no se envía", captura.id)
                fallidas += 1
                continue
            cuerpo, tipo = _multipart(captura, jpeg)
            cabeceras = {"Content-Type": tipo, "Idempotency-Key": captura.id}
            if self._token:
                cabeceras["Authorization"] = "Bearer " + self._token
            try:
                codigo = self._transporte(self._url, cuerpo, cabeceras, _TIMEOUT_S)
            except OSError as error:
                _LOG.warning("Captura %s: fallo de red: %s", captura.id, error)
                fallidas += 1
                self._registrar_fallo_transitorio()
                continue
            if codigo in (200, 201, 409):
                self._cola.marcar_sincronizada(captura.id)
                enviadas += 1
                self._espera = 0.0
                self._proximo_intento = None
            else:
                fallidas += 1
                if 400 <= codigo < 500:
                    _LOG.error("Captura %s: falla permanente HTTP %s", captura.id, codigo)
                else:
                    _LOG.warning("Captura %s: respuesta HTTP %s no aceptada", captura.id, codigo)
                    self._registrar_fallo_transitorio()
        return self._resumen(enviadas, fallidas)
