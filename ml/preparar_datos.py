"""Prepara AerialYield-T2M (CC BY 4.0, Zenodo 22071809) para entrenar.

Usa las anotaciones COCO y los splits oficiales (por bloques de fotogramas, sin solape).
NO usa la exportación YOLO del mismo registro: sus particiones repiten imágenes entre
train, val y test. Reescribe cada imagen con su proporción original (lado largo = --lado)
y guarda las cajas ya en las clases de Sabueso.

    python ml/preparar_datos.py --origen datos/aerialyield
"""
import argparse
import csv
import json
import os
import zipfile

import cv2
import numpy as np

from comun import MAPA_AERIALYIELD

LADO_MIN_CAJA = 4  # píxeles tras reescalar; cajas más pequeñas no son aprendibles


def fuentes_por_imagen(origen):
    """filename -> source/modality (mobile o drone) desde los CSV de splits."""
    datos = {}
    for split in ("train", "val", "test"):
        with open(os.path.join(origen, "splits", "splits", "images_%s.csv" % split)) as f:
            for fila in csv.DictReader(f):
                datos[fila["filename"]] = fila["source"]
    return datos


def preparar(origen, salida, lado, maximo):
    fuentes = fuentes_por_imagen(origen)
    with zipfile.ZipFile(os.path.join(origen, "dataset_images.zip")) as z:
        rutas = {os.path.basename(n): n for n in z.namelist() if n.lower().endswith(".jpg")}
        for split in ("train", "val", "test"):
            with open(os.path.join(origen, "coco", "dataset", "detection", "coco", "instances_%s.json" % split)) as f:
                coco = json.load(f)
            cajas_por_imagen = {}
            for a in coco["annotations"]:
                cajas_por_imagen.setdefault(a["image_id"], []).append(a)
            os.makedirs(os.path.join(salida, split), exist_ok=True)
            items, omitidas = [], 0
            for img in coco["images"][:maximo or None]:
                nombre = img["file_name"]
                cuadro = cv2.imdecode(np.frombuffer(z.read(rutas[nombre]), np.uint8), cv2.IMREAD_COLOR)
                alto, ancho = cuadro.shape[:2]
                if (ancho, alto) != (img["width"], img["height"]):
                    # La orientación EXIF no coincide con la anotada: sin cajas fiables, se omite.
                    omitidas += 1
                    continue
                k = lado / max(ancho, alto)
                if k < 1:
                    cuadro = cv2.resize(cuadro, (round(ancho * k), round(alto * k)), interpolation=cv2.INTER_AREA)
                else:
                    k = 1.0
                cajas, etiquetas = [], []
                for a in cajas_por_imagen.get(img["id"], []):
                    x, y, w, h = [v * k for v in a["bbox"]]
                    if w < LADO_MIN_CAJA or h < LADO_MIN_CAJA:
                        continue
                    cajas.append([round(x, 1), round(y, 1), round(x + w, 1), round(y + h, 1)])
                    etiquetas.append(MAPA_AERIALYIELD[a["category_id"]])
                cv2.imwrite(os.path.join(salida, split, nombre), cuadro, [cv2.IMWRITE_JPEG_QUALITY, 92])
                items.append({"archivo": nombre, "ancho": cuadro.shape[1], "alto": cuadro.shape[0],
                              "fuente": fuentes.get(nombre, "desconocida"), "cajas": cajas, "etiquetas": etiquetas})
            with open(os.path.join(salida, split + ".json"), "w") as f:
                json.dump(items, f)
            print("%s: %d imágenes, %d cajas, %d omitidas" % (split, len(items), sum(len(i["cajas"]) for i in items), omitidas))


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--origen", default="datos/aerialyield")
    p.add_argument("--salida", default=None, help="por defecto <origen>/prep")
    p.add_argument("--lado", type=int, default=960, help="lado largo en píxeles")
    p.add_argument("--maximo", type=int, default=0, help="máximo de imágenes por split (humo)")
    a = p.parse_args()
    preparar(a.origen, a.salida or os.path.join(a.origen, "prep"), a.lado, a.maximo)


if __name__ == "__main__":
    main()
