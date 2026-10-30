"""Configuración del software que corre en el dock del Go2. Sin secretos."""
import os

# Cámara frontal: H264 por RTP multicast en la red interna del robot.
CAMARA_INTERFAZ = "eth0"
CAMARA_GRUPO = "230.1.1.1"
CAMARA_PUERTO = 1720

# Web del cliente (ui/) que recibe los registros. Cambiar cuando se defina dónde corre.
UI_URL = os.environ.get("SABUESO_UI_URL", "http://127.0.0.1:5000")

# Datos locales del robot, fuera de src/ porque scripts/subir_al_robot.sh reemplaza src/.
DATOS_DIR = os.path.expanduser(os.environ.get("SABUESO_DATOS", "~/Workspace/farmbot/datos"))
PENDIENTES_DIR = os.path.join(DATOS_DIR, "pendientes")

CALIDAD_JPEG = 80
