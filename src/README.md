# src

Software del robot Unitree Go2 EDU que corre en el dock Jetson (192.168.123.18): durante un recorrido lee la cámara, detecta maleza, frutos y signos en el follaje, y envía cada captura a la web del cliente (`ui/`).

## Estructura

| Ruta | Contenido |
| --- | --- |
| `recorrido/` | Recorrido: cámara → detección → envío de capturas |
| `camara/` | Lectura de la cámara frontal del Go2 |
| `deteccion/` | Detección de frutos de tomate con un modelo ONNX (entrenado con `ml/`) |
| `registro/` | Envío de las capturas a `ui/`, con cola local si la web no responde |
| `transmision/` | Video en vivo de la cámara para la web del cliente |
| `config.py` | Cámara, dirección de la web, carpeta de datos, cada cuánto se envía una captura sin hallazgos y modelo de detección (`SABUESO_MODELO`, `SABUESO_UMBRAL`) |

Flujo: `camara` → `deteccion` → `registro` → HTTP `POST /api/capturas` → `ui/`.

## Requisitos en el dock

Python 3.8 y OpenCV con GStreamer, ya instalados en la imagen del dock. Para detectar hace falta además `onnxruntime` (y NumPy) y el modelo exportado con `ml/exportar.py`: `sabueso.onnx` y `sabueso.onnx.json` en `~/Workspace/farmbot/datos/modelo/` (o la ruta de `SABUESO_MODELO`). Sin modelo, el recorrido arranca pero avisa por stderr y no registra nada; si `SABUESO_MODELO` apunta a un archivo que no existe, falla al iniciar. `SABUESO_UMBRAL` (por defecto 0.5) fija el puntaje mínimo. La compatibilidad de `onnxruntime` con Python 3.8 en la Jetson **no está verificada**; ver `ml/README.md`.

## Subir el código al robot

El repositorio se clona y actualiza en la PC; en el dock no se guardan credenciales de GitHub.

```bash
scripts/subir_al_robot.sh
```

Copia `src/` y la web del cliente (`ui/api` y `ui/web/dist`, que compila antes con `npm`) a `~/Workspace/farmbot` del dock. No toca `.venv` ni los datos del dock.

## Iniciar un recorrido

Desde la web: sección "Recorrido", elegir hilera y zona y "Iniciar recorrido". La API lanza el mismo comando que se puede usar a mano en el dock:

```bash
cd ~/Workspace/farmbot/src
SABUESO_UI_URL=http://<equipo-de-ui>:5000 python3 -m recorrido --hilera 1
```

Cada captura es una foto (sin cajas dibujadas) con todas sus detecciones. Si no hay detecciones, igual se envía una captura cada `CAPTURA_ZONA_S` segundos para marcar la zona como observada. `Ctrl+C` o "Detener recorrido" lo terminan y se avisa a la web. Las capturas que no se pudieron enviar quedan en `~/Workspace/farmbot/datos/pendientes/` y se reenvían en el siguiente envío.

## Transmisión en vivo

En el dock, en otra terminal (puede correr junto a un recorrido):

```bash
cd ~/Workspace/farmbot/src
python3 -m transmision
```

La web del cliente la muestra en la sección "Recorrido". También se puede abrir directamente:

| Ruta | Respuesta |
| --- | --- |
| `http://192.168.123.18:8080/video` | Video MJPEG |
| `http://192.168.123.18:8080/foto.jpg` | Último cuadro |
| `http://192.168.123.18:8080/estado` | FPS y si hay video, en JSON |

## Pendiente

- Modelo de detección: el pipeline existe (`ml/`), pero aún no hay un modelo entrenado en serio ni medido en el dock; sin `sabueso.onnx` solo llegan las capturas periódicas sin hallazgos. Solo detecta `tomate_verde` y `tomate_maduro`; maleza queda pendiente de datos.
- Movimiento del robot por las hileras, solo a través de un módulo de seguridad.
- Hilera y zona según la posición del robot.
- Evitar registrar varias veces el mismo hallazgo en cuadros seguidos.
