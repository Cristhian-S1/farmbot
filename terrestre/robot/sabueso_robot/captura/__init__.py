"""JPEG de la cámara frontal y cola persistente de capturas del recorrido."""

from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


__all__ = ["Captura", "ErrorCaptura", "CamaraFrontal", "ColaCapturas"]


@dataclass(frozen=True)
class Captura:
    id: str
    recorrido_id: str
    hilera: str | None
    zona: str | None
    marca_tiempo: float
    ruta_archivo: str
    sha256: str
    estado_zona: str
    sincronizada: bool = False


class ErrorCaptura(RuntimeError):
    """La cámara no entregó una captura JPEG válida."""


def _validar_jpeg(jpeg: bytes) -> None:
    if not isinstance(jpeg, bytes) or not jpeg.startswith(b"\xff\xd8"):
        raise ErrorCaptura("La captura no contiene la firma JPEG")


class CamaraFrontal:
    """Adapta VideoClient; el SDK solo se carga al crear el cliente real."""

    def __init__(self, timeout_s: float = 3.0, cliente=None) -> None:
        if timeout_s <= 0:
            raise ValueError("timeout_s debe ser mayor que cero")
        try:
            if cliente is None:
                from unitree_sdk2py.go2.video.video_client import VideoClient

                cliente = VideoClient()
            self._cliente = cliente
            cliente.SetTimeout(timeout_s)
            cliente.Init()
        except Exception as error:
            raise ErrorCaptura("No se pudo inicializar la cámara frontal") from error

    def obtener_jpeg(self) -> bytes:
        try:
            codigo, datos = self._cliente.GetImageSample()
            if codigo != 0:
                raise ErrorCaptura(f"La cámara devolvió el código {codigo}")
            if not isinstance(datos, (bytes, bytearray, memoryview, list)):
                raise ErrorCaptura("La cámara devolvió datos de imagen inválidos")
            jpeg = bytes(datos)
            _validar_jpeg(jpeg)
            return jpeg
        except ErrorCaptura:
            raise
        except Exception as error:
            raise ErrorCaptura("No se pudo obtener el JPEG de la cámara frontal") from error


def _validar_recorrido(recorrido_id: str) -> None:
    if not isinstance(recorrido_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", recorrido_id):
        raise ValueError("recorrido_id solo puede contener letras ASCII, dígitos, _ y -")


def _sincronizar_directorio(directorio: Path) -> None:
    descriptor = os.open(str(directorio), os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class ColaCapturas:
    """Almacena imágenes antes de publicar sus metadatos en SQLite.

    El candado cubre tanto el archivo como la transacción y permite compartir
    una instancia entre el capturador y el hilo de sincronización. SQLite
    serializa las transacciones de otras instancias que usen el mismo archivo.
    """

    def __init__(self, directorio: str, reloj=time.time) -> None:
        self._directorio = Path(directorio).resolve()
        self._directorio.mkdir(parents=True, exist_ok=True)
        self._reloj = reloj
        self._candado = threading.RLock()
        self._conexion = sqlite3.connect(
            str(self._directorio / "capturas.sqlite"), check_same_thread=False
        )
        self._conexion.row_factory = sqlite3.Row
        with self._conexion:
            self._conexion.execute("PRAGMA synchronous = FULL")
            self._conexion.execute(
                "CREATE TABLE IF NOT EXISTS capturas ("
                "id TEXT PRIMARY KEY, recorrido_id TEXT NOT NULL, hilera TEXT, zona TEXT, "
                "marca_tiempo REAL NOT NULL, ruta_archivo TEXT NOT NULL, sha256 TEXT NOT NULL, "
                "estado_zona TEXT NOT NULL, sincronizada INTEGER NOT NULL DEFAULT 0)"
            )

    def registrar(self, jpeg: bytes, recorrido_id: str,
                  hilera: str | None, zona: str | None) -> Captura:
        _validar_recorrido(recorrido_id)
        _validar_jpeg(jpeg)
        if hilera is None or zona is None:
            hilera = zona = None
        captura_id = uuid4().hex
        relativa = Path("capturas") / recorrido_id / (captura_id + ".jpg")
        captura = Captura(
            id=captura_id, recorrido_id=recorrido_id, hilera=hilera, zona=zona,
            marca_tiempo=self._reloj(), ruta_archivo=relativa.as_posix(),
            sha256=hashlib.sha256(jpeg).hexdigest(),
            estado_zona="sin_zona" if zona is None else "asignada",
        )
        with self._candado:
            destino = Path(self.ruta_absoluta(captura))
            destino.parent.mkdir(parents=True, exist_ok=True)
            # Persistir también la creación de capturas/ y del recorrido.
            _sincronizar_directorio(self._directorio)
            _sincronizar_directorio(destino.parent.parent)
            temporal = None
            publicado = False
            try:
                with tempfile.NamedTemporaryFile(
                    dir=str(destino.parent), suffix=".tmp", delete=False
                ) as archivo:
                    temporal = Path(archivo.name)
                    archivo.write(jpeg)
                    archivo.flush()
                    os.fsync(archivo.fileno())
                os.replace(str(temporal), str(destino))
                publicado = True
                _sincronizar_directorio(destino.parent)
                with self._conexion:
                    self._conexion.execute(
                        "INSERT INTO capturas VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (captura.id, captura.recorrido_id, captura.hilera, captura.zona,
                         captura.marca_tiempo, captura.ruta_archivo, captura.sha256,
                         captura.estado_zona, int(captura.sincronizada)),
                    )
            except Exception:
                if publicado:
                    destino.unlink()
                    _sincronizar_directorio(destino.parent)
                raise
            finally:
                if temporal is not None and temporal.exists():
                    temporal.unlink()
        return captura

    @staticmethod
    def _desde_fila(fila: sqlite3.Row) -> Captura:
        datos = dict(fila)
        datos["sincronizada"] = bool(datos["sincronizada"])
        return Captura(**datos)

    def pendientes(self, limite: int = 50) -> list[Captura]:
        if limite < 0:
            raise ValueError("limite no puede ser negativo")
        with self._candado:
            filas = self._conexion.execute(
                "SELECT * FROM capturas WHERE sincronizada = 0 "
                "ORDER BY marca_tiempo, rowid LIMIT ?", (limite,)
            ).fetchall()
            return [self._desde_fila(fila) for fila in filas]

    def marcar_sincronizada(self, captura_id: str) -> None:
        with self._candado, self._conexion:
            self._conexion.execute(
                "UPDATE capturas SET sincronizada = 1 WHERE id = ?", (captura_id,)
            )

    def por_recorrido(self, recorrido_id: str) -> list[Captura]:
        _validar_recorrido(recorrido_id)
        with self._candado:
            filas = self._conexion.execute(
                "SELECT * FROM capturas WHERE recorrido_id = ? ORDER BY marca_tiempo, rowid",
                (recorrido_id,),
            ).fetchall()
            return [self._desde_fila(fila) for fila in filas]

    def ruta_absoluta(self, captura: Captura) -> str:
        ruta = (self._directorio / captura.ruta_archivo).resolve()
        try:
            ruta.relative_to(self._directorio)
        except ValueError as error:
            raise ValueError("La ruta de captura sale del directorio de datos") from error
        return str(ruta)

    def cerrar(self) -> None:
        with self._candado:
            self._conexion.close()
