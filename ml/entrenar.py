"""Ajusta el detector sobre los datos preparados y guarda el mejor modelo según mAP@.5 en val.

    python ml/entrenar.py --datos datos/aerialyield/prep --salida datos/ml --epocas 20
"""
import argparse
import json
import os
import random

import numpy as np
import torch

from comun import CLASES, Conjunto, agrupar, crear_modelo, dispositivo_auto
from evaluar import evaluar


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--datos", default="datos/aerialyield/prep")
    p.add_argument("--salida", default="datos/ml")
    p.add_argument("--epocas", type=int, default=20)
    p.add_argument("--batch", type=int, default=4)
    p.add_argument("--lr", type=float, default=0.01)
    p.add_argument("--semilla", type=int, default=42)
    p.add_argument("--dispositivo", default="auto")
    p.add_argument("--maximo", type=int, default=0, help="imágenes por split (prueba de humo)")
    p.add_argument("--sin-preentrenar", action="store_true")
    a = p.parse_args()

    random.seed(a.semilla); np.random.seed(a.semilla); torch.manual_seed(a.semilla)
    d = dispositivo_auto(a.dispositivo)
    os.makedirs(a.salida, exist_ok=True)

    train = Conjunto(a.datos, "train", entrenamiento=True, maximo=a.maximo)
    val = Conjunto(a.datos, "val", maximo=a.maximo)
    cargador = torch.utils.data.DataLoader(train, batch_size=a.batch, shuffle=True, collate_fn=agrupar, num_workers=0)

    modelo = crear_modelo(preentrenado=not a.sin_preentrenar).to(d)
    params = [q for q in modelo.parameters() if q.requires_grad]
    opt = torch.optim.SGD(params, lr=a.lr, momentum=0.9, weight_decay=1e-4)
    plan = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=max(a.epocas, 1))
    amp = torch.amp.GradScaler(enabled=d.type == "cuda")

    mejor, historial = -1.0, []
    for ep in range(1, a.epocas + 1):
        modelo.train()
        perdidas = []
        for imgs, objetivos, _ in cargador:
            imgs = [i.to(d) for i in imgs]
            objetivos = [{k: v.to(d) for k, v in o.items()} for o in objetivos]
            with torch.autocast(d.type, enabled=d.type == "cuda"):
                perdida = sum(modelo(imgs, objetivos).values())
            opt.zero_grad()
            amp.scale(perdida).backward()
            amp.step(opt)
            amp.update()
            perdidas.append(float(perdida.detach()))
        plan.step()
        r = evaluar(modelo, val, d)
        historial.append({"epoca": ep, "perdida": round(float(np.mean(perdidas)), 4), "mAP50_val": r["mAP50"], "mAP_val": r["mAP"]})
        print(historial[-1], flush=True)
        if r["mAP50"] > mejor:
            mejor = r["mAP50"]
            torch.save(modelo.state_dict(), os.path.join(a.salida, "mejor.pt"))
            with open(os.path.join(a.salida, "metricas_val.json"), "w") as f:
                json.dump(r, f, indent=2, ensure_ascii=False)
    with open(os.path.join(a.salida, "historial.json"), "w") as f:
        json.dump({"argumentos": vars(a), "clases": CLASES, "historial": historial}, f, indent=2)
    print("mejor mAP50 val: %.3f -> %s" % (mejor, os.path.join(a.salida, "mejor.pt")))


if __name__ == "__main__":
    main()
