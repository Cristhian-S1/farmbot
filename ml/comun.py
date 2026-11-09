"""Piezas compartidas por preparar_datos, entrenar, evaluar y exportar."""
import json
import os

import cv2
import torch
from torchvision.models.detection import FasterRCNN_MobileNet_V3_Large_FPN_Weights, fasterrcnn_mobilenet_v3_large_fpn
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor

# Clases del producto. La etiqueta de torchvision es la posición + 1 (0 es el fondo).
# Para añadir "maleza" u otras hace falta reentrenar con datos que las incluyan.
CLASES = ["tomate_verde", "tomate_maduro"]

# AerialYield-T2M tiene 6 etapas de madurez (Silal): 1 Green, 2 Breakers, 3 Turning,
# 4 Pink, 5 Light Red, 6 Red. Se agrupan en las 2 clases del producto: verde = menos
# de 40 % de color, maduro = 40 % o más. Decisión de producto, ajustable aquí.
MAPA_AERIALYIELD = {1: 1, 2: 1, 3: 1, 4: 2, 5: 2, 6: 2}

TAM_MIN, TAM_MAX = 640, 960


def crear_modelo(preentrenado=True):
    """Faster R-CNN con MobileNetV3-Large FPN: ligero y con cabeza reemplazable."""
    pesos = FasterRCNN_MobileNet_V3_Large_FPN_Weights.DEFAULT if preentrenado else None
    modelo = fasterrcnn_mobilenet_v3_large_fpn(weights=pesos, weights_backbone=None,
                                               min_size=TAM_MIN, max_size=TAM_MAX, box_score_thresh=0.05)
    entradas = modelo.roi_heads.box_predictor.cls_score.in_features
    modelo.roi_heads.box_predictor = FastRCNNPredictor(entradas, len(CLASES) + 1)
    return modelo


def dispositivo_auto(nombre="auto"):
    if nombre != "auto":
        return torch.device(nombre)
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


class Conjunto(torch.utils.data.Dataset):
    """Lee `<carpeta>/<split>.json` generado por preparar_datos.py."""

    def __init__(self, carpeta, split, entrenamiento=False, maximo=0):
        self.carpeta, self.split, self.entrenamiento = carpeta, split, entrenamiento
        with open(os.path.join(carpeta, split + ".json")) as f:
            self.items = json.load(f)
        if maximo:
            self.items = self.items[:maximo]

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        it = self.items[i]
        img = cv2.cvtColor(cv2.imread(os.path.join(self.carpeta, self.split, it["archivo"])), cv2.COLOR_BGR2RGB)
        cajas = torch.tensor(it["cajas"], dtype=torch.float32).reshape(-1, 4)
        etiquetas = torch.tensor(it["etiquetas"], dtype=torch.int64)
        if self.entrenamiento:
            if torch.rand(1) < 0.5:  # volteo horizontal
                img = img[:, ::-1]
                ancho = img.shape[1]
                cajas = torch.stack([ancho - cajas[:, 2], cajas[:, 1], ancho - cajas[:, 0], cajas[:, 3]], 1)
            # luz variable en el invernadero: brillo y contraste leves
            img = cv2.convertScaleAbs(img, alpha=float(0.8 + 0.4 * torch.rand(1)), beta=float(40 * torch.rand(1) - 20))
        tensor = torch.from_numpy(img.copy()).permute(2, 0, 1).float() / 255.0
        return tensor, {"boxes": cajas, "labels": etiquetas}, it


def agrupar(lote):
    return tuple(zip(*lote))
