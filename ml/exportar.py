"""Exporta el modelo a ONNX (para onnxruntime en el dock) y comprueba que coincide con PyTorch.

    python ml/exportar.py --pesos datos/ml/mejor.pt --salida datos/ml/sabueso.onnx --imagen foto.jpg

Entrada: RGB float32 0-1, forma (3, alto, ancho), tamaño libre. Salidas: cajas (N,4) en píxeles
de la imagen de entrada, etiquetas (N,) base 1 y puntajes (N,). Escribe también <salida>.json
con las clases.
"""
import argparse
import json
import time

import cv2
import numpy as np
import onnxruntime as ort
import torch

from comun import CLASES, crear_modelo


class Envoltura(torch.nn.Module):
    def __init__(self, modelo):
        super().__init__()
        self.modelo = modelo

    def forward(self, x):
        r = self.modelo([x])[0]
        return r["boxes"], r["labels"], r["scores"]


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--pesos", required=True)
    p.add_argument("--salida", required=True)
    p.add_argument("--imagen", required=True, help="imagen de ejemplo para trazar y comparar")
    p.add_argument("--opset", type=int, default=17)
    a = p.parse_args()

    modelo = crear_modelo(preentrenado=False)
    modelo.load_state_dict(torch.load(a.pesos, map_location="cpu"))
    modelo.eval()
    img = cv2.cvtColor(cv2.imread(a.imagen), cv2.COLOR_BGR2RGB)
    x = torch.from_numpy(img).permute(2, 0, 1).float() / 255.0

    envoltura = Envoltura(modelo).eval()
    torch.onnx.export(envoltura, (x,), a.salida, opset_version=a.opset, input_names=["imagen"],
                      output_names=["cajas", "etiquetas", "puntajes"], dynamic_axes={
                          "imagen": {1: "alto", 2: "ancho"}, "cajas": {0: "n"}, "etiquetas": {0: "n"}, "puntajes": {0: "n"}},
                      dynamo=False)
    with open(a.salida + ".json", "w") as f:
        json.dump({"clases": CLASES, "entrada": "RGB float32 0-1 CHW", "etiquetas_base": 1}, f, ensure_ascii=False)

    with torch.no_grad():
        ref = envoltura(x)
    sesion = ort.InferenceSession(a.salida, providers=["CPUExecutionProvider"])
    sesion.run(None, {"imagen": x.numpy()})  # calentamiento
    t0 = time.perf_counter()
    for _ in range(5):
        out = sesion.run(None, {"imagen": x.numpy()})
    ms = (time.perf_counter() - t0) / 5 * 1000
    # Se comparan solo las detecciones sobre 0.5 para no depender del orden de las de bajo puntaje.
    n_ref, n_onnx = int((ref[2] >= 0.5).sum()), int((out[2] >= 0.5).sum())
    print("detecciones >=0.5: torch=%d onnx=%d" % (n_ref, n_onnx))
    if n_ref and n_onnx:
        dif = float(np.abs(ref[0][:min(n_ref, n_onnx)].numpy() - out[0][:min(n_ref, n_onnx)]).max())
        print("diferencia máxima de cajas (px): %.3f" % dif)
    print("latencia ONNX CPU: %.0f ms por imagen (%dx%d)" % (ms, img.shape[1], img.shape[0]))


if __name__ == "__main__":
    main()
