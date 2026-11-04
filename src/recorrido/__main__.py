"""Inicia un recorrido: lee la cámara, detecta y envía cada captura a la web.

Uso en el dock, desde src/:
    python3 -m recorrido [--id ID] [--hilera H] [--zona Z]
Ctrl+C termina el recorrido. La web lo inicia y lo detiene con el mismo comando.

Cada captura es una foto con todas sus detecciones. Además de las fotos con
hallazgos, cada CAPTURA_ZONA_S segundos se envía una captura aunque no haya
detecciones: así el mapa distingue una zona observada sin alertas de una zona
sin datos.

Pendiente:
- Movimiento del robot por las hileras, solo a través del módulo de seguridad.
- Hilera y zona reales según la posición; mientras tanto se usan las indicadas
  al iniciar o la captura queda "sin zona" (no se inventa una zona).
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


def crear_captura(recorrido_id, detector, detecciones, cuadro, hilera, zona):
    ok, jpg = cv2.imencode(".jpg", cuadro, [cv2.IMWRITE_JPEG_QUALITY, config.CALIDAD_JPEG])
    return {
        "id": uuid.uuid4().hex,
        "recorrido": recorrido_id,
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "hilera": hilera,
        "zona": zona,
        "modelo": {"nombre": detector.nombre, "version": detector.version},
        "detecciones": [
            {"clase": d.clase, "confianza": round(float(d.confianza), 3), "caja": [int(v) for v in d.caja]}
            for d in detecciones
        ],
        "foto_jpeg": base64.b64encode(jpg.tobytes()).decode() if ok else None,
    }


def main():
    parser = argparse.ArgumentParser(description="Recorrido de monitoreo con la cámara frontal")
    parser.add_argument("--id", default=None, help="id del recorrido; por defecto, la fecha y hora")
    parser.add_argument("--hilera", default=None)
    parser.add_argument("--zona", default=None)
    args = parser.parse_args()

    recorrido_id = args.id or datetime.now().strftime("%Y%m%d-%H%M%S")
    camara = CamaraFrontal(config.CAMARA_INTERFAZ, config.CAMARA_GRUPO, config.CAMARA_PUERTO).iniciar()
    detector = Detector()
    cliente = ClienteRegistro(config.UI_URL, config.PENDIENTES_DIR)
    print("recorrido %s iniciado, registrando en %s" % (recorrido_id, config.UI_URL), flush=True)

    estado = "incompleto"
    ultima_marca = 0.0
    ultima_captura = 0.0
    try:
        while True:
            cuadro, marca = camara.ultimo_cuadro()
            if cuadro is None or marca == ultima_marca:
                time.sleep(0.01)
                continue
            ultima_marca = marca
            detecciones = detector.detectar(cuadro)
            if not detecciones and time.monotonic() - ultima_captura < config.CAPTURA_ZONA_S:
                continue
            ultima_captura = time.monotonic()
            # La foto va sin cajas: la web las dibuja a partir de las detecciones.
            captura = crear_captura(recorrido_id, detector, detecciones, cuadro, args.hilera, args.zona)
            enviado = cliente.registrar(captura)
            hallazgos = ", ".join("%s %.0f%%" % (d.clase, d.confianza * 100) for d in detecciones) or "sin hallazgos"
            print("captura: %s · %s" % (hallazgos, "enviada" if enviado else "en cola"), flush=True)
    except KeyboardInterrupt:
        estado = "completado"
    finally:
        camara.detener()
        cliente.finalizar(recorrido_id, estado)
        print("recorrido %s terminado (%s)" % (recorrido_id, estado), flush=True)


if __name__ == "__main__":
    main()
