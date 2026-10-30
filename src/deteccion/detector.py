"""Análisis visual de maleza y frutos de tomate.

Por ahora no hay modelo: `detectar()` devuelve una lista vacía. Cuando exista
un modelo entrenado, se carga en `__init__` y se ejecuta en `detectar()`.
"""
from collections import namedtuple

import cv2

# caja = (x1, y1, x2, y2) en píxeles del cuadro.
Deteccion = namedtuple("Deteccion", ["clase", "confianza", "caja"])

COLORES = {
    "maleza": (0, 200, 255),
    "tomate_verde": (0, 200, 0),
    "tomate_maduro": (0, 0, 230),
}


class Detector:
    def detectar(self, cuadro):
        """Devuelve una lista de Deteccion para un cuadro BGR."""
        return []

    def dibujar(self, cuadro, detecciones):
        """Dibuja las detecciones sobre una copia del cuadro."""
        if not detecciones:
            return cuadro
        salida = cuadro.copy()
        for d in detecciones:
            x1, y1, x2, y2 = d.caja
            color = COLORES.get(d.clase, (255, 255, 255))
            cv2.rectangle(salida, (x1, y1), (x2, y2), color, 2)
            cv2.putText(salida, "%s %.0f%%" % (d.clase, d.confianza * 100), (x1, max(y1 - 6, 12)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
        return salida
