"""Envío de registros del robot a la web del cliente (ui/).

Cada registro es un JSON con la detección y su foto en base64, enviado por
POST a `<UI_URL>/api/registros`. Si la web no responde, el registro se guarda
en una cola local y se reintenta en el siguiente envío, para no perder evidencia
cuando se cae la red.
"""
import json
import os
import urllib.error
import urllib.request


class ClienteRegistro:
    def __init__(self, url_ui, pendientes_dir, timeout=5):
        self.url = url_ui.rstrip("/") + "/api/registros"
        self.pendientes_dir = pendientes_dir
        self.timeout = timeout
        os.makedirs(pendientes_dir, exist_ok=True)

    def registrar(self, registro):
        """Envía un registro; si falla, queda en la cola local. Devuelve True si se envió."""
        self.reintentar_pendientes()
        if self._enviar(registro):
            return True
        self._guardar_pendiente(registro)
        return False

    def reintentar_pendientes(self):
        for nombre in sorted(os.listdir(self.pendientes_dir)):
            ruta = os.path.join(self.pendientes_dir, nombre)
            with open(ruta) as f:
                registro = json.load(f)
            if not self._enviar(registro):
                return
            os.remove(ruta)

    def _enviar(self, registro):
        datos = json.dumps(registro).encode()
        req = urllib.request.Request(self.url, data=datos, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return 200 <= r.status < 300
        except (urllib.error.URLError, OSError) as e:
            print("registro: no se pudo enviar (%s)" % e, flush=True)
            return False

    def _guardar_pendiente(self, registro):
        ruta = os.path.join(self.pendientes_dir, "%s.json" % registro["id"])
        with open(ruta, "w") as f:
            json.dump(registro, f)
