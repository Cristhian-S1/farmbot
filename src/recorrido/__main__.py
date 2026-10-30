"""Inicia un recorrido: lee la cámara, detecta y registra cada detección en la web.

Uso en el dock, desde src/:
    python3 -m recorrido [--hilera H] [--zona Z]
Ctrl+C termina el recorrido.

Pendiente:
- Movimiento del robot por las hileras, solo a través del módulo de seguridad.
- Hilera y zona reales según la posición; mientras tanto se usan las indicadas
  al iniciar o el registro queda "sin zona" (no se inventa una zona).
- Evitar registrar varias veces el mismo hallazgo en cuadros seguidos.
"""
import argparse
import base64
import time
import uuid
from datetime import datetime

import cv2

import config
from camara import CamaraFrontal
from deteccion import Detector
from registro import ClienteRegistro


def crear_registro(recorrido_id, deteccion, cuadro, hilera, zona):
    ok, jpg = cv2.imencode(".jpg", cuadro, [cv2.IMWRITE_JPEG_QUALITY, config.CALIDAD_JPEG])
    return {
        "id": uuid.uuid4().hex,
        "recorrido": recorrido_id,
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "clase": deteccion.clase,
        "confianza": round(float(deteccion.confianza), 3),
        "caja": list(deteccion.caja),
        "hilera": hilera,
        "zona": zona,
        "foto_jpeg": base64.b64encode(jpg.tobytes()).decode() if ok else None,
    }


def main():
    parser = argparse.ArgumentParser(description="Recorrido de monitoreo con la cámara frontal")
    parser.add_argument("--hilera", default=None)
    parser.add_argument("--zona", default=None)
    args = parser.parse_args()

    recorrido_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    camara = CamaraFrontal(config.CAMARA_INTERFAZ, config.CAMARA_GRUPO, config.CAMARA_PUERTO).iniciar()
    detector = Detector()
    cliente = ClienteRegistro(config.UI_URL, config.PENDIENTES_DIR)
    print("recorrido %s iniciado, registrando en %s" % (recorrido_id, config.UI_URL), flush=True)

    ultima_marca = 0.0
    try:
        while True:
            cuadro, marca = camara.ultimo_cuadro()
            if cuadro is None or marca == ultima_marca:
                time.sleep(0.01)
                continue
            ultima_marca = marca
            detecciones = detector.detectar(cuadro)
            if not detecciones:
                continue
            foto = detector.dibujar(cuadro, detecciones)
            for d in detecciones:
                registro = crear_registro(recorrido_id, d, foto, args.hilera, args.zona)
                enviado = cliente.registrar(registro)
                print("%s %.0f%% %s" % (d.clase, d.confianza * 100, "enviado" if enviado else "en cola"), flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        camara.detener()
        print("recorrido %s terminado" % recorrido_id, flush=True)


if __name__ == "__main__":
    main()
