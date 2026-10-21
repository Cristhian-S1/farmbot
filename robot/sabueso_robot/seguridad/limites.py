"""Límites de seguridad del movimiento (RFN5 y sección 4.4 del plan)."""

from __future__ import annotations

from dataclasses import dataclass, fields

# Tope absoluto del proyecto: RFN5 exige velocidad inferior a 1 m/s.
VX_MAXIMO_ABSOLUTO = 1.0


@dataclass(frozen=True)
class Limites:
    vx_max: float = 0.5  # m/s, avance
    vy_max: float = 0.2  # m/s, lateral
    vyaw_max: float = 0.5  # rad/s, giro
    timeout_comando_s: float = 0.3  # watchdog: sin comandos → StopMove
    distancia_paro_m: float = 0.5  # RFN5
    bateria_min_inicio: int = 30  # %, no iniciar misión por debajo
    bateria_min_operacion: int = 25  # %, detener la misión por debajo

    def __post_init__(self) -> None:
        for campo in fields(self):
            valor = getattr(self, campo.name)
            if valor < 0:
                raise ValueError(f"{campo.name} no puede ser negativo: {valor}")
        if self.vx_max >= VX_MAXIMO_ABSOLUTO:
            raise ValueError(
                f"vx_max={self.vx_max} m/s no cumple RFN5 (< {VX_MAXIMO_ABSOLUTO} m/s)"
            )
        if self.vy_max > self.vx_max:
            raise ValueError("vy_max no puede superar vx_max")
        if self.timeout_comando_s == 0:
            raise ValueError("timeout_comando_s debe ser mayor que cero")
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
        """Devuelve límites más estrictos; nunca permite aumentar una velocidad."""
        for nombre, valor in cambios.items():
            if nombre.endswith("_max") and valor > getattr(self, nombre):
                raise ValueError(f"{nombre} solo puede reducirse en tiempo de ejecución")
        datos = {campo.name: getattr(self, campo.name) for campo in fields(self)}
        datos.update(cambios)
        return Limites(**datos)
