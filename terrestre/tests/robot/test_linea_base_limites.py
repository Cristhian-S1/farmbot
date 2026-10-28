"""S12: el YAML de límites del repositorio no puede superar la línea base aprobada."""

from sabueso_robot.config import cargar_limites

# Línea base aprobada por ambos integrantes. Endurecer es libre; relajar exige cambiar
# este archivo, protegido por CODEOWNERS.
LINEA_BASE_MAXIMOS = {"vx_max": 0.5, "vx_atras_max": 0.0, "vy_max": 0.0, "vyaw_max": 0.5,
                      "timeout_comando_s": 0.3}
LINEA_BASE_MINIMOS = {"distancia_paro_m": 0.5, "bateria_min_inicio": 30,
                      "bateria_min_operacion": 25}


def test_yaml_respeta_la_linea_base():
    limites = cargar_limites()
    for campo, maximo in LINEA_BASE_MAXIMOS.items():
        assert getattr(limites, campo) <= maximo, campo
    for campo, minimo in LINEA_BASE_MINIMOS.items():
        assert getattr(limites, campo) >= minimo, campo
