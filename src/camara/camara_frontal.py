"""Lectura de la cámara frontal del Go2.

El control de movimiento (192.168.123.161) emite la cámara frontal como H264
sobre RTP multicast en la red interna del robot. Se decodifica con GStreamer
desde OpenCV, que en el dock está compilado con soporte GStreamer.
"""
import threading
import time

import cv2

PIPELINE = (
    "udpsrc address={grupo} port={puerto} multicast-iface={interfaz} ! "
    "application/x-rtp,media=video,encoding-name=H264 ! "
    "rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! "
    "video/x-raw,format=BGR ! appsink drop=true max-buffers=1 sync=false"
)


class CamaraFrontal:
    """Mantiene el último cuadro de la cámara en un hilo propio y reconecta si se corta."""

    def __init__(self, interfaz="eth0", grupo="230.1.1.1", puerto=1720):
        self.pipeline = PIPELINE.format(grupo=grupo, puerto=puerto, interfaz=interfaz)
        self._lock = threading.Lock()
        self._cuadro = None
        self._marca = 0.0
        self._detener = threading.Event()
        self._hilo = None
        self.fps = 0.0

    def iniciar(self):
        self._hilo = threading.Thread(target=self._bucle, daemon=True)
        self._hilo.start()
        return self

    def detener(self):
        self._detener.set()
        if self._hilo:
            self._hilo.join(timeout=3)

    def ultimo_cuadro(self):
        """Devuelve (cuadro BGR, marca de tiempo) o (None, 0.0) si aún no hay video."""
        with self._lock:
            return self._cuadro, self._marca

    def _bucle(self):
        while not self._detener.is_set():
            cap = cv2.VideoCapture(self.pipeline, cv2.CAP_GSTREAMER)
            if not cap.isOpened():
                print("camara: no se pudo abrir, reintentando", flush=True)
                time.sleep(2)
                continue
            print("camara: abierta", flush=True)
            cuenta, t0 = 0, time.time()
            while not self._detener.is_set():
                ok, cuadro = cap.read()
                if not ok:
                    print("camara: se perdió el video, reconectando", flush=True)
                    break
                with self._lock:
                    self._cuadro, self._marca = cuadro, time.time()
                cuenta += 1
                if time.time() - t0 >= 1.0:
                    self.fps = cuenta / (time.time() - t0)
                    cuenta, t0 = 0, time.time()
            cap.release()
            time.sleep(1)
