"""Evalúa un detector en un split: mAP (COCO), precisión/recall/F1, matriz de confusión y latencia.

    python ml/evaluar.py --datos datos/aerialyield/prep --pesos datos/ml/mejor.pt --split test
"""
import argparse
import contextlib
import io
import json
import os
import time

import numpy as np
import torch
from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval
from torchvision.ops import box_iou

from comun import CLASES, Conjunto, crear_modelo, dispositivo_auto


@torch.no_grad()
def predecir(modelo, conjunto, dispositivo):
    """Devuelve (predicciones, ms_por_imagen). La latencia excluye leer y decodificar la imagen."""
    modelo.eval()
    salidas, tiempos = [], []
    for i in range(len(conjunto)):
        img = conjunto[i][0].to(dispositivo)
        if dispositivo.type == "cuda":
            torch.cuda.synchronize()
        t0 = time.perf_counter()
        r = modelo([img])[0]
        if dispositivo.type == "cuda":
            torch.cuda.synchronize()
        tiempos.append((time.perf_counter() - t0) * 1000)
        salidas.append({k: v.cpu() for k, v in r.items()})
    return salidas, tiempos


def _coco_gt(conjunto):
    imgs, anns = [], []
    for i, it in enumerate(conjunto.items):
        imgs.append({"id": i, "width": it["ancho"], "height": it["alto"]})
        for c, e in zip(it["cajas"], it["etiquetas"]):
            anns.append({"id": len(anns) + 1, "image_id": i, "category_id": e, "iscrowd": 0,
                         "bbox": [c[0], c[1], c[2] - c[0], c[3] - c[1]], "area": (c[2] - c[0]) * (c[3] - c[1])})
    gt = COCO()
    gt.dataset = {"images": imgs, "annotations": anns, "categories": [{"id": k + 1, "name": n} for k, n in enumerate(CLASES)]}
    with contextlib.redirect_stdout(io.StringIO()):
        gt.createIndex()
    return gt


def mapa(conjunto, preds):
    """mAP@[.5:.95], mAP@.5 y AP@.5 por clase con pycocotools."""
    gt = _coco_gt(conjunto)
    dets = [{"image_id": i, "category_id": int(l), "score": float(s), "bbox": [float(b[0]), float(b[1]), float(b[2] - b[0]), float(b[3] - b[1])]}
            for i, p in enumerate(preds) for b, l, s in zip(p["boxes"], p["labels"], p["scores"])]
    if not dets:
        return {"mAP": 0.0, "mAP50": 0.0, "AP50_por_clase": {n: 0.0 for n in CLASES}}
    with contextlib.redirect_stdout(io.StringIO()):
        ev = COCOeval(gt, gt.loadRes(dets), "bbox")
        ev.evaluate(); ev.accumulate(); ev.summarize()
    ap50 = {}
    for k, n in enumerate(CLASES):
        p = ev.eval["precision"][0, :, k, 0, 2]
        ap50[n] = float(np.mean(p[p > -1])) if (p > -1).any() else 0.0
    return {"mAP": float(ev.stats[0]), "mAP50": float(ev.stats[1]), "AP50_por_clase": ap50}


def confusion(conjunto, preds, umbral=0.5, iou=0.5):
    """Matriz [real][predicho] con la última fila/columna = fondo (omitido / falso positivo)."""
    n = len(CLASES)
    m = np.zeros((n + 1, n + 1), dtype=int)
    for it, p in zip(conjunto.items, preds):
        gt = torch.tensor(it["cajas"], dtype=torch.float32).reshape(-1, 4)
        gl = [e - 1 for e in it["etiquetas"]]
        sel = p["scores"] >= umbral
        pb, pl = p["boxes"][sel], (p["labels"][sel] - 1).tolist()
        usados = set()
        if len(gt) and len(pb):
            ious = box_iou(gt, pb)
            for g in range(len(gt)):  # cada real toma la predicción libre con más IoU
                j = int(ious[g].argmax())
                if ious[g, j] >= iou and j not in usados:
                    usados.add(j)
                    m[gl[g], pl[j]] += 1
                else:
                    m[gl[g], n] += 1
        else:
            for g in gl:
                m[g, n] += 1
        for j in range(len(pb)):
            if j not in usados:
                m[n, pl[j]] += 1
    return m


def prf(m):
    """Precisión, recall y F1 por clase desde la matriz de confusión."""
    r = {}
    for k, nombre in enumerate(CLASES):
        tp, fp, fn = m[k, k], m[:, k].sum() - m[k, k], m[k, :].sum() - m[k, k]
        p = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        r[nombre] = {"precision": round(float(p), 3), "recall": round(float(rec), 3),
                     "f1": round(float(2 * p * rec / (p + rec)) if p + rec else 0.0, 3)}
    return r


def evaluar(modelo, conjunto, dispositivo, umbral=0.5):
    preds, tiempos = predecir(modelo, conjunto, dispositivo)
    m = confusion(conjunto, preds, umbral)
    return {"imagenes": len(conjunto), "umbral": umbral, **mapa(conjunto, preds), "por_clase": prf(m),
            "confusion": {"filas_real_columnas_predicho": CLASES + ["fondo"], "matriz": m.tolist()},
            "latencia_ms": {"media": round(float(np.mean(tiempos)), 1), "p95": round(float(np.percentile(tiempos, 95)), 1),
                            "dispositivo": str(dispositivo)}}


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--datos", default="datos/aerialyield/prep")
    p.add_argument("--pesos", required=True)
    p.add_argument("--split", default="test")
    p.add_argument("--umbral", type=float, default=0.5)
    p.add_argument("--dispositivo", default="auto")
    p.add_argument("--maximo", type=int, default=0)
    p.add_argument("--salida", default=None)
    a = p.parse_args()
    d = dispositivo_auto(a.dispositivo)
    modelo = crear_modelo(preentrenado=False)
    modelo.load_state_dict(torch.load(a.pesos, map_location="cpu"))
    r = evaluar(modelo.to(d), Conjunto(a.datos, a.split, maximo=a.maximo), d, a.umbral)
    texto = json.dumps(r, indent=2, ensure_ascii=False)
    print(texto)
    if a.salida:
        os.makedirs(os.path.dirname(a.salida) or ".", exist_ok=True)
        with open(a.salida, "w") as f:
            f.write(texto)


if __name__ == "__main__":
    main()
