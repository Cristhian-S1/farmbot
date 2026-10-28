"""Carga de la configuración del robot y de los límites de seguridad."""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass, fields
from pathlib import Path

from .seguridad import Limites

RAIZ_REPO = Path(__file__).resolve().parents[2]
RUTA_CONFIG = RAIZ_REPO / "config" / "robot.yaml"
RUTA_LIMITES = RAIZ_REPO / "config" / "limites_seguridad.yaml"
VARIABLE_CONFIG = "SABUESO_CONFIG"
VARIABLE_LIMITES = "SABUESO_LIMITES"

registro = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConfigRobot:
    interfaz_dds: str = "eth0"
    dominio_dds: int = 0
    directorio_datos: str = "/home/unitree/sabueso_datos"
    topico_sport: str = "rt/sportmodestate"
    topico_low: str = "rt/lowstate"
    url_servidor: str | None = None
    timeout_rpc_s: float = 3.0

    def __post_init__(self) -> None:
        if not self.interfaz_dds:
            raise ValueError("interfaz_dds no puede estar vacía")
        if self.timeout_rpc_s <= 0:
            raise ValueError("timeout_rpc_s debe ser mayor que cero")


def _leer_yaml(ruta: Path) -> dict:
    import yaml  # PyYAML: python3-yaml en Ubuntu

    with ruta.open(encoding="utf-8") as archivo:
        datos = yaml.safe_load(archivo) or {}
    if not isinstance(datos, dict):
        raise ValueError(f"{ruta} debe contener un mapa de claves")
    return datos


def _resolver(ruta: str | None, variable: str, por_defecto: Path) -> Path:
    return Path(ruta or os.environ.get(variable) or por_defecto)


def cargar_config(ruta: str | None = None) -> ConfigRobot:
    datos = _leer_yaml(_resolver(ruta, VARIABLE_CONFIG, RUTA_CONFIG))
    conocidos = {campo.name for campo in fields(ConfigRobot)}
    desconocidos = set(datos) - conocidos
    if desconocidos:
        raise ValueError(f"Claves desconocidas en la configuración: {sorted(desconocidos)}")
    return ConfigRobot(**datos)


def cargar_limites(ruta: str | None = None) -> Limites:
    """Carga y valida los límites; deja constancia de la ruta, el hash y los valores (S13)."""
    archivo = _resolver(ruta, VARIABLE_LIMITES, RUTA_LIMITES)
    limites = Limites.desde_dict(_leer_yaml(archivo))
    huella = hashlib.sha256(archivo.read_bytes()).hexdigest()[:16]
    if archivo.resolve() != RUTA_LIMITES.resolve():
        registro.warning("límites cargados desde una ruta no estándar: %s", archivo)
    registro.info("límites %s (sha256 %s): %s", archivo, huella, limites)
    return limites
