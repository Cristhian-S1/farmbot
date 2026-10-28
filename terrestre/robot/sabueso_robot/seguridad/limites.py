"""Límites de seguridad del movimiento (RFN5 y sección 4.4 del plan)."""

from __future__ import annotations

import math
from dataclasses import dataclass, fields

# Topes del proyecto. RFN5: velocidad < 1 m/s y detención ante obstáculos a 0,5 m.
VX_MAXIMO_ABSOLUTO = 1.0
DISTANCIA_PARO_MINIMA_M = 0.5
TIMEOUT_COMANDO_MAXIMO_S = 0.3  # sección 4.4: watchdog de 300 ms
VYAW_MAXIMO_ABSOLUTO = 1.0  # rad/s; decisión del coordinador, por verificar en F4.2

# Dirección segura de cada campo al cambiarlo en tiempo de ejecución.
SOLO_BAJA = frozenset({"vx_max", "vx_atras_max", "vy_max", "vyaw_max", "timeout_comando_s"})
SOLO_SUBE = frozenset({"distancia_paro_m", "bateria_min_inicio", "bateria_min_operacion"})


@dataclass(frozen=True)
class Limites:
    vx_max: float = 0.5  # m/s, avance
    vx_atras_max: float = 0.0  # m/s, retroceso: prohibido salvo prueba supervisada (S8)
    vy_max: float = 0.0  # m/s, lateral: prohibido salvo prueba supervisada (S8)
    vyaw_max: float = 0.5  # rad/s, giro
    timeout_comando_s: float = 0.3  # watchdog: sin comandos → StopMove
    distancia_paro_m: float = 0.5  # RFN5
    bateria_min_inicio: float = 30  # %, no iniciar misión por debajo
    bateria_min_operacion: float = 25  # %, detener la misión por debajo

    def __post_init__(self) -> None:
        for campo in fields(self):
            valor = getattr(self, campo.name)
            if not isinstance(valor, (int, float)) or not math.isfinite(valor):
                raise ValueError(f"{campo.name} debe ser un número finito: {valor!r}")
            if valor < 0:
                raise ValueError(f"{campo.name} no puede ser negativo: {valor}")
        if self.vx_max >= VX_MAXIMO_ABSOLUTO:
            raise ValueError(
                f"vx_max={self.vx_max} m/s no cumple RFN5 (< {VX_MAXIMO_ABSOLUTO} m/s)"
            )
        if math.hypot(max(self.vx_max, self.vx_atras_max), self.vy_max) >= VX_MAXIMO_ABSOLUTO:
            raise ValueError("la velocidad combinada (vx, vy) no cumple RFN5")
        if self.vx_atras_max > self.vx_max or self.vy_max > self.vx_max:
            raise ValueError("vx_atras_max y vy_max no pueden superar vx_max")
        if self.vyaw_max > VYAW_MAXIMO_ABSOLUTO:
            raise ValueError(f"vyaw_max no puede superar {VYAW_MAXIMO_ABSOLUTO} rad/s")
        if not 0 < self.timeout_comando_s <= TIMEOUT_COMANDO_MAXIMO_S:
            raise ValueError(f"timeout_comando_s debe estar en (0, {TIMEOUT_COMANDO_MAXIMO_S}] s")
        if self.distancia_paro_m < DISTANCIA_PARO_MINIMA_M:
            raise ValueError(f"distancia_paro_m no cumple RFN5 (>= {DISTANCIA_PARO_MINIMA_M} m)")
        if self.bateria_min_inicio > 100:
            raise ValueError("bateria_min_inicio no puede superar 100 %")
        if self.bateria_min_operacion > self.bateria_min_inicio:
            raise ValueError("bateria_min_operacion no puede superar bateria_min_inicio")

    @classmethod
    def desde_dict(cls, datos: dict) -> "Limites":
        conocidos = {campo.name for campo in fields(cls)}
        desconocidos = set(datos) - conocidos
        if desconocidos:
            raise ValueError(f"Claves desconocidas en límites: {sorted(desconocidos)}")
        return cls(**datos)

    def reducido(self, **cambios: float) -> "Limites":
        """Devuelve límites más estrictos; rechaza cualquier cambio en la dirección insegura."""
        for nombre, valor in cambios.items():
            actual = getattr(self, nombre)
            if nombre in SOLO_BAJA and valor > actual:
                raise ValueError(f"{nombre} solo puede reducirse en tiempo de ejecución")
            if nombre in SOLO_SUBE and valor < actual:
                raise ValueError(f"{nombre} solo puede aumentarse en tiempo de ejecución")
        datos = {campo.name: getattr(self, campo.name) for campo in fields(self)}
        datos.update(cambios)
        return Limites(**datos)

    def recortar(self, vx: float, vy: float, vyaw: float) -> tuple[float, float, float]:
        return (
            max(-self.vx_atras_max, min(self.vx_max, vx)),
            max(-self.vy_max, min(self.vy_max, vy)),
            max(-self.vyaw_max, min(self.vyaw_max, vyaw)),
        )
