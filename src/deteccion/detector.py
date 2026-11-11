"""Análisis visual de frutos de tomate (y, cuando haya datos, maleza).

Carga un modelo ONNX exportado con `ml/exportar.py` (junto a un `.json` con las clases)
y lo ejecuta con onnxruntime. Sin modelo, `detectar()` devuelve una lista vacía y avisa
una vez por stderr: el recorrido sigue funcionando, pero solo envía capturas sin hallazgos.
"""
import hashlib
import json
import os
import sys
from collections import namedtuple

import cv2
import numpy as np

import config

# caja = (x1, y1, x2, y2) en píxeles del cuadro.
Deteccion = namedtuple("Deteccion", ["clase", "confianza", "caja"])

COLORES = {
    "maleza": (0, 200, 255),
    "tomate_verde": (0, 200, 0),
    "tomate_maduro": (0, 0, 230),
}


def identificar_modelo(ruta):
    """Nombre del archivo sin extensión y los primeros 8 caracteres de su SHA-256 como versión:
    dos exportaciones distintas quedan registradas como modelos distintos."""
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return os.path.splitext(os.path.basename(ruta))[0], h.hexdigest()[:8]


class Detector:
    # Se registra con cada captura para saber con qué modelo se analizó.
    nombre = "sin_modelo"
    version = "0"

    def __init__(self, modelo=None, umbral=None, sesion=None, clases=None):
        """`modelo`: ruta al .onnx (por defecto config.MODELO_RUTA). `sesion` y `clases` solo
        se pasan en pruebas, para no necesitar un modelo real."""
        self.umbral = config.UMBRAL_DETECCION if umbral is None else umbral
        self._sesion, self.clases = sesion, clases or []
        if sesion is not None:
            return
        ruta = modelo or config.MODELO_RUTA
        if not os.path.exists(ruta):
            if modelo or "SABUESO_MODELO" in os.environ:  # ruta pedida de forma explícita: error claro
                raise FileNotFoundError("no existe el modelo: %s" % ruta)
            print("detector: sin modelo en %s, no se detectará nada" % ruta, file=sys.stderr, flush=True)
            return
        import onnxruntime  # solo se exige cuando hay modelo

        with open(ruta + ".json") as f:
            self.clases = json.load(f)["clases"]
        self._sesion = onnxruntime.InferenceSession(ruta, providers=onnxruntime.get_available_providers())
        self.nombre, self.version = identificar_modelo(ruta)

    def detectar(self, cuadro):
        """Devuelve una lista de Deteccion para un cuadro BGR."""
        if self._sesion is None:
            return []
        rgb = cv2.cvtColor(cuadro, cv2.COLOR_BGR2RGB)
        entrada = np.ascontiguousarray(rgb.transpose(2, 0, 1), dtype=np.float32) / 255.0
        cajas, etiquetas, puntajes = self._sesion.run(None, {"imagen": entrada})
        alto, ancho = cuadro.shape[:2]
        salida = []
        for c, e, p in zip(cajas, etiquetas, puntajes):
            if p < self.umbral:
                continue
            x1, y1 = max(int(round(c[0])), 0), max(int(round(c[1])), 0)
            x2, y2 = min(int(round(c[2])), ancho), min(int(round(c[3])), alto)
            if x2 > x1 and y2 > y1:
                salida.append(Deteccion(self.clases[int(e) - 1], float(p), (x1, y1, x2, y2)))
        return salida

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
