"""Máquina de estados de la misión (Figura 4 del informe de la Parte 1)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class EstadoMision(Enum):
    DISPONIBLE = "Disponible"
    VERIFICANDO = "Verificando"
    EN_PATRULLAJE = "En patrullaje"
    PAUSADA = "Pausada"
    ADQUISICION_CERRADA = "Adquisición cerrada"
    PROCESANDO = "Procesando"
    COMPLETADA = "Completada"
    INCOMPLETA = "Incompleta / cancelada"


class Evento(Enum):
    INICIAR = "INICIAR"
    CONDICIONES_OK = "CONDICIONES OK"
    RECHAZAR = "RECHAZAR"
    PAUSAR = "OBSTÁCULO, INCIDENCIA U ORDEN DE DETENCIÓN"
    REANUDAR = "REANUDAR [SEGURO]"
    FIN_DE_RUTA = "FIN DE RUTA"
    ANALIZAR = "ANALIZAR"
    REGISTRO_OK = "REGISTRO OK"
    ERROR_REGISTRO = "ERROR DE REGISTRO"
    CANCELAR = "CANCELAR / NO RECUPERABLE"


E, V = EstadoMision, Evento
TRANSICIONES: dict[tuple[EstadoMision, Evento], EstadoMision] = {
    (E.DISPONIBLE, V.INICIAR): E.VERIFICANDO,
    (E.VERIFICANDO, V.CONDICIONES_OK): E.EN_PATRULLAJE,
    (E.VERIFICANDO, V.RECHAZAR): E.DISPONIBLE,
    (E.EN_PATRULLAJE, V.PAUSAR): E.PAUSADA,
    (E.EN_PATRULLAJE, V.FIN_DE_RUTA): E.ADQUISICION_CERRADA,
    (E.EN_PATRULLAJE, V.CANCELAR): E.INCOMPLETA,
    (E.PAUSADA, V.REANUDAR): E.EN_PATRULLAJE,
    (E.PAUSADA, V.CANCELAR): E.INCOMPLETA,
    (E.ADQUISICION_CERRADA, V.ANALIZAR): E.PROCESANDO,
    (E.PROCESANDO, V.REGISTRO_OK): E.COMPLETADA,
    (E.PROCESANDO, V.ERROR_REGISTRO): E.INCOMPLETA,
}
FINALES = frozenset({E.COMPLETADA, E.INCOMPLETA})


class TransicionInvalida(RuntimeError):
    pass


@dataclass(frozen=True)
class Transicion:
    origen: EstadoMision
    evento: Evento
    destino: EstadoMision
    marca_tiempo: float
    motivo: str = ""


@dataclass
class MaquinaMision:
    recorrido_id: str
    zonas: list[tuple[str, str]]  # (hilera, zona) en orden de recorrido
    reloj: Callable[[], float] = time.time
    estado: EstadoMision = EstadoMision.DISPONIBLE
    historial: list[Transicion] = field(default_factory=list)
    completadas: list[tuple[str, str]] = field(default_factory=list)

    def disparar(self, evento: Evento, motivo: str = "", seguro: bool = False) -> EstadoMision:
        if evento is Evento.REANUDAR and not seguro:
            raise TransicionInvalida("REANUDAR exige que el operador confirme condiciones seguras")
        destino = TRANSICIONES.get((self.estado, evento))
        if destino is None:
            raise TransicionInvalida(f"{evento.name} no es válido en {self.estado.name}")
        self.historial.append(Transicion(self.estado, evento, destino, self.reloj(), motivo))
        self.estado = destino
        return destino

    def marcar_zona(self, hilera: str, zona: str) -> None:
        if self.estado is not EstadoMision.EN_PATRULLAJE:
            raise TransicionInvalida("solo se registran zonas durante el patrullaje")
        if (hilera, zona) not in self.zonas:
            raise ValueError(f"zona desconocida {hilera}/{zona}: no se inventan ubicaciones")
        if (hilera, zona) not in self.completadas:
            self.completadas.append((hilera, zona))

    def pendientes(self) -> list[tuple[str, str]]:
        return [z for z in self.zonas if z not in self.completadas]

    @property
    def terminada(self) -> bool:
        return self.estado in FINALES
