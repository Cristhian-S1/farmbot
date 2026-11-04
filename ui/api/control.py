"""Inicio y término del recorrido desde la web.

La API corre en el dock del Go2, así que lanza `python3 -m recorrido` de src/
como un proceso hijo. El recorrido solo activa cámara, detección y registro:
no mueve el robot. El movimiento queda para el módulo de seguridad.
"""
import os
import signal
import subprocess
import sys
import threading
from datetime import datetime

ESPERA_DETENCION_S = 10
LINEAS_SALIDA = 20


class RecorridoEnCurso(Exception):
    pass


class ControlRecorrido:
    def __init__(self, almacenamiento, src_dir, python, ui_url, datos_dir):
        self.almacenamiento = almacenamiento
        self.src_dir = src_dir
        self.python = python
        self.ui_url = ui_url
        self.ruta_salida = os.path.join(datos_dir, "recorrido.log")
        self._lock = threading.Lock()
        self._proceso = None
        self._recorrido_id = None
        self._detenido = False

    def iniciar(self, hilera=None, zona=None, iniciado_por="web"):
        with self._lock:
            self._revisar()
            if self._proceso is not None:
                raise RecorridoEnCurso(self._recorrido_id)
            recorrido_id = datetime.now().strftime("%Y%m%d-%H%M%S")
            comando = [self.python, "-u", "-m", "recorrido", "--id", recorrido_id]
            if hilera:
                comando += ["--hilera", str(hilera)]
            if zona:
                comando += ["--zona", str(zona)]
            entorno = dict(os.environ, SABUESO_UI_URL=self.ui_url)
            salida = open(self.ruta_salida, "w")
            try:
                self._proceso = subprocess.Popen(comando, cwd=self.src_dir, env=entorno,
                                                 stdout=salida, stderr=subprocess.STDOUT)
            except OSError:
                self._proceso = None
                raise
            finally:
                salida.close()
            self._recorrido_id = recorrido_id
            self._detenido = False
            self.almacenamiento.iniciar_recorrido(recorrido_id, iniciado_por)
            return recorrido_id

    def detener(self):
        with self._lock:
            self._revisar()
            if self._proceso is None:
                return None
            self._detenido = True
            self._proceso.send_signal(signal.SIGINT)
            try:
                self._proceso.wait(ESPERA_DETENCION_S)
            except subprocess.TimeoutExpired:
                self._proceso.kill()
                self._proceso.wait()
            recorrido_id = self._recorrido_id
            self._revisar()
            return recorrido_id

    def estado(self):
        with self._lock:
            self._revisar()
            return {
                "corriendo": self._proceso is not None,
                "recorrido": self._recorrido_id,
                "salida": self._ultimas_lineas(),
            }

    def _revisar(self):
        """Si el proceso terminó, cierra el recorrido: completado si lo detuvo la web, incompleto si se cayó."""
        if self._proceso is None or self._proceso.poll() is None:
            return
        estado = "completado" if self._detenido else "incompleto"
        self.almacenamiento.cerrar_recorrido(self._recorrido_id, estado)
        if not self._detenido:
            self.almacenamiento.registrar_incidencia(
                self._recorrido_id, "proceso",
                "el recorrido terminó solo (código %s)" % self._proceso.returncode,
            )
        self._proceso = None

    def _ultimas_lineas(self):
        try:
            with open(self.ruta_salida) as f:
                return f.read().splitlines()[-LINEAS_SALIDA:]
        except OSError:
            return []


def python_robot():
    """Python con OpenCV y GStreamer. En el dock es el del sistema, no el del entorno de Flask."""
    return os.environ.get("SABUESO_PYTHON_ROBOT", "python3" if sys.platform != "win32" else sys.executable)
