"""Transmisión en vivo de la cámara frontal (MJPEG por HTTP) para la web del cliente.

Uso en el dock, desde src/:
    python3 -m transmision [--puerto 8080]

Puede correr junto a un recorrido: la cámara es multicast y admite varios lectores.

| Ruta        | Respuesta                                 |
| /video      | Video MJPEG                               |
| /foto.jpg   | Último cuadro                             |
| /estado     | {"fps": ..., "video": true/false} en JSON |
"""
import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2

import config
from camara import CamaraFrontal

# Si no llega un cuadro nuevo en este tiempo, se informa que no hay video.
SIN_VIDEO_S = 3.0


class Codificador:
    """Convierte cada cuadro nuevo a JPEG una sola vez para todos los clientes."""

    def __init__(self, camara):
        self.camara = camara
        self._lock = threading.Lock()
        self._jpeg = None
        self._marca = 0.0

    def jpeg(self):
        cuadro, marca = self.camara.ultimo_cuadro()
        if cuadro is None:
            return None
        with self._lock:
            if marca != self._marca:
                ok, buf = cv2.imencode(".jpg", cuadro, [cv2.IMWRITE_JPEG_QUALITY, config.CALIDAD_JPEG])
                if ok:
                    self._jpeg, self._marca = buf.tobytes(), marca
            return self._jpeg


def crear_manejador(camara, codificador):
    class Manejador(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            ruta = self.path.split("?")[0]
            if ruta == "/video":
                self._transmitir()
            elif ruta == "/foto.jpg":
                jpg = codificador.jpeg()
                if jpg is None:
                    self._responder(503, "text/plain; charset=utf-8", b"sin video")
                else:
                    self._responder(200, "image/jpeg", jpg)
            elif ruta == "/estado":
                _, marca = camara.ultimo_cuadro()
                hay_video = marca > 0 and time.time() - marca < SIN_VIDEO_S
                cuerpo = json.dumps({"fps": round(camara.fps, 1) if hay_video else 0, "video": hay_video})
                self._responder(200, "application/json", cuerpo.encode())
            else:
                self._responder(404, "text/plain; charset=utf-8", b"no encontrado")

        def _transmitir(self):
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=cuadro")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            anterior = None
            try:
                while True:
                    jpg = codificador.jpeg()
                    if jpg is None or jpg is anterior:
                        time.sleep(0.01)
                        continue
                    anterior = jpg
                    self.wfile.write(b"--cuadro\r\nContent-Type: image/jpeg\r\nContent-Length: "
                                     + str(len(jpg)).encode() + b"\r\n\r\n" + jpg + b"\r\n")
            except (BrokenPipeError, ConnectionResetError):
                pass

        def _responder(self, codigo, tipo, cuerpo):
            self.send_response(codigo)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(cuerpo)))
            # La web del cliente corre en otro puerto u otro equipo y consulta /estado.
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(cuerpo)

    return Manejador


def main():
    parser = argparse.ArgumentParser(description="Transmisión en vivo de la cámara frontal")
    parser.add_argument("--puerto", type=int, default=config.TRANSMISION_PUERTO)
    args = parser.parse_args()

    camara = CamaraFrontal(config.CAMARA_INTERFAZ, config.CAMARA_GRUPO, config.CAMARA_PUERTO).iniciar()
    servidor = ThreadingHTTPServer(("0.0.0.0", args.puerto), crear_manejador(camara, Codificador(camara)))
    print("transmision en http://0.0.0.0:%d/video" % args.puerto, flush=True)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        camara.detener()


if __name__ == "__main__":
    main()
