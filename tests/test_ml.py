"""Métricas y conversión de datos del pipeline de ml/, con datos sintéticos."""
import json
import os

import cv2
import numpy as np
import pytest
import torch

from comun import CLASES, MAPA_AERIALYIELD, Conjunto
from evaluar import confusion, mapa, prf


def conjunto(tmp_path, items):
    os.makedirs(tmp_path / "val")
    for it in items:
        cv2.imwrite(str(tmp_path / "val" / it["archivo"]), np.zeros((it["alto"], it["ancho"], 3), np.uint8))
    (tmp_path / "val.json").write_text(json.dumps(items))
    return Conjunto(str(tmp_path), "val")


def pred(cajas, etiquetas, puntajes):
    return {"boxes": torch.tensor(cajas, dtype=torch.float32).reshape(-1, 4), "labels": torch.tensor(etiquetas), "scores": torch.tensor(puntajes)}


def test_mapa_semantico_cubre_las_6_etapas():
    assert sorted(MAPA_AERIALYIELD) == [1, 2, 3, 4, 5, 6]
    assert {MAPA_AERIALYIELD[k] for k in MAPA_AERIALYIELD} == {1, 2} and len(CLASES) == 2


def test_confusion_y_prf_con_aciertos_confusiones_omisiones_y_falsos_positivos(tmp_path):
    items = [{"archivo": "a.jpg", "ancho": 100, "alto": 100, "fuente": "mobile",
              "cajas": [[0, 0, 20, 20], [30, 30, 50, 50], [60, 60, 80, 80]], "etiquetas": [1, 1, 2]}]
    c = conjunto(tmp_path, items)
    # acierta la 1.ª, confunde la 2.ª (verde -> maduro), omite la 3.ª y añade un falso positivo verde
    p = [pred([[0, 0, 20, 20], [30, 30, 50, 50], [85, 0, 99, 14]], [1, 2, 1], [0.9, 0.8, 0.7])]
    m = confusion(c, p)
    assert m.tolist() == [[1, 1, 0], [0, 0, 1], [1, 0, 0]]
    assert prf(m)["tomate_verde"] == {"precision": 0.5, "recall": 0.5, "f1": 0.5}


def test_mapa_es_perfecto_con_predicciones_exactas(tmp_path):
    items = [{"archivo": "a.jpg", "ancho": 100, "alto": 100, "fuente": "mobile",
              "cajas": [[0, 0, 20, 20], [60, 60, 80, 80]], "etiquetas": [1, 2]}]
    c = conjunto(tmp_path, items)
    r = mapa(c, [pred([[0, 0, 20, 20], [60, 60, 80, 80]], [1, 2], [0.99, 0.99])])
    assert r["mAP50"] == pytest.approx(1.0) and r["AP50_por_clase"] == pytest.approx({"tomate_verde": 1.0, "tomate_maduro": 1.0})
    assert mapa(c, [pred([], [], [])])["mAP50"] == 0.0


def test_conjunto_voltea_y_entrega_cajas_validas(tmp_path):
    items = [{"archivo": "a.jpg", "ancho": 100, "alto": 60, "fuente": "mobile", "cajas": [[10, 10, 30, 40]], "etiquetas": [1]}]
    c = conjunto(tmp_path, items)
    c.entrenamiento = True
    for _ in range(10):
        img, obj, _ = c[0]
        x1, y1, x2, y2 = obj["boxes"][0].tolist()
        assert img.shape == (3, 60, 100) and 0 <= x1 < x2 <= 100 and (y1, y2) == (10, 40)
