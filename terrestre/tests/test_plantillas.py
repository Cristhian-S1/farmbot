"""Pruebas de las plantillas de configuración y de las unidades systemd."""

from __future__ import annotations

import configparser
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from sabueso_robot.config import cargar_config, cargar_limites

RAIZ = Path(__file__).resolve().parents[1]
DIRECTORIO_UNIDADES = RAIZ / "deploy" / "systemd"
SERVICIOS = sorted(DIRECTORIO_UNIDADES.glob("*.service"))
COMANDOS_ESPERADOS = {
    "sabueso-telemetria.service": "telemetria --registrar",
    "sabueso-sincronizacion.service": "sincronizar --continuo",
}


def _leer_unidad(ruta: Path) -> configparser.RawConfigParser:
    lector = configparser.RawConfigParser(interpolation=None, strict=False)
    lector.read_string(ruta.read_text(encoding="utf-8"))
    return lector


def test_configuracion_robot_carga():
    config = cargar_config(str(RAIZ / "config" / "robot.yaml"))
    assert config.interfaz_dds
    assert config.dominio_dds >= 0
    assert config.timeout_rpc_s > 0


def test_limites_seguridad_cargan():
    limites = cargar_limites(str(RAIZ / "config" / "limites_seguridad.yaml"))
    assert 0 < limites.vx_max < 1.0
    assert limites.distancia_paro_m > 0
    assert limites.bateria_min_operacion <= limites.bateria_min_inicio


def test_cyclonedds_es_xml_bien_formado_con_interfaz():
    raiz = ET.parse(RAIZ / "config" / "cyclonedds.xml").getroot()
    assert raiz.tag.rsplit("}", 1)[-1] == "CycloneDDS"
    interfaces = [
        elemento
        for elemento in raiz.iter()
        if elemento.tag.rsplit("}", 1)[-1] == "NetworkInterface"
    ]
    assert interfaces, "cyclonedds.xml debe declarar una NetworkInterface"
    assert all(elemento.get("name") for elemento in interfaces)


def test_existen_las_dos_unidades_esperadas():
    nombres = {servicio.name for servicio in SERVICIOS}
    assert set(COMANDOS_ESPERADOS) <= nombres


@pytest.mark.parametrize("servicio", SERVICIOS, ids=[ruta.name for ruta in SERVICIOS])
def test_unidad_tiene_secciones_y_no_mueve_el_robot(servicio):
    texto = servicio.read_text(encoding="utf-8")
    lector = _leer_unidad(servicio)
    assert {"Unit", "Service", "Install"} <= set(lector.sections())
    assert "Move" not in texto
    assert lector["Service"]["Restart"] == "on-failure"
    assert lector["Service"]["RestartSec"] == "5"


@pytest.mark.parametrize("servicio", SERVICIOS, ids=[ruta.name for ruta in SERVICIOS])
def test_unidad_usa_el_entorno_del_dock(servicio):
    # configparser no conserva varias líneas Environment=, así que se revisa el texto.
    texto = servicio.read_text(encoding="utf-8")
    servicio_systemd = _leer_unidad(servicio)["Service"]
    assert servicio_systemd["WorkingDirectory"] == "%h/sabueso"
    assert "Environment=CYCLONEDDS_HOME=%h/cyclonedds/install" in texto
    assert "Environment=SABUESO_CONFIG=%h/sabueso/config/robot.yaml" in texto
    assert servicio_systemd["ExecStart"].startswith("%h/sabueso/.venv/bin/python -m sabueso_robot ")
    assert COMANDOS_ESPERADOS[servicio.name] in servicio_systemd["ExecStart"]
