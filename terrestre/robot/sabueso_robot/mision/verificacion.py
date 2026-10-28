"""Comprobación de condiciones antes de iniciar el patrullaje (CU1, paso 2)."""

from __future__ import annotations

from ..seguridad import Limites


def problemas_para_iniciar(
    estado, edad_s: float | None, limites: Limites, max_edad_s: float = 1.0
) -> list[str]:
    """Devuelve la lista de motivos para no iniciar; vacía si se puede iniciar.

    `estado` tiene la forma de telemetria.EstadoRobot o es None.
    """
    if estado is None or edad_s is None:
        return ["sin telemetría del robot"]
    problemas = []
    if edad_s > max_edad_s:
        problemas.append(f"telemetría con {edad_s:.1f} s de antigüedad")
    if estado.bateria_pct is None:
        problemas.append("batería desconocida")
    elif estado.bateria_pct < limites.bateria_min_inicio:
        problemas.append(
            f"batería en {estado.bateria_pct:.0f} % (mínimo {limites.bateria_min_inicio} %)"
        )
    if estado.codigo_error:
        problemas.append(f"el robot informa el error {estado.codigo_error}")
    distancia = estado.distancia_minima_m()
    if distancia is not None and distancia < limites.distancia_paro_m:
        problemas.append(f"obstáculo a {distancia:.2f} m")
    return problemas
