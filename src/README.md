# src

Software del robot Unitree Go2 EDU que corre en el dock Jetson (192.168.123.18): durante un recorrido lee la cámara, detecta maleza y frutos, y registra cada detección en la web del cliente (`ui/`).

## Estructura

| Ruta | Contenido |
| --- | --- |
| `recorrido/` | Inicia un recorrido: cámara → detección → registro |
| `camara/` | Lectura de la cámara frontal del Go2 |
| `deteccion/` | Análisis visual de maleza y frutos (modelo pendiente) |
| `registro/` | Envío de los registros a `ui/`, con cola local si la web no responde |
| `transmision/` | Video en vivo de la cámara para la web del cliente |
| `config.py` | Cámara, dirección de la web y carpeta de datos |

Flujo: `camara` → `deteccion` → `registro` → HTTP `POST /api/registros` → `ui/`.

## Requisitos en el dock

Python 3.8 y OpenCV con GStreamer, ya instalados en la imagen del dock. No usa paquetes externos.

## Subir el código al robot

El repositorio se clona y actualiza en la PC; en el dock no se guardan credenciales de GitHub.

```bash
scripts/subir_al_robot.sh
```

Copia `src/` y la web del cliente (`ui/api` y `ui/web/dist`, que compila antes con `npm`) a `~/Workspace/farmbot` del dock. No toca `.venv` ni los datos del dock.

## Iniciar un recorrido

En el dock:

```bash
cd ~/Workspace/farmbot/src
SABUESO_UI_URL=http://<equipo-de-ui>:5000 python3 -m recorrido --hilera 1
```

`Ctrl+C` termina el recorrido. Los registros que no se pudieron enviar quedan en `~/Workspace/farmbot/datos/pendientes/` y se reenvían en el siguiente envío.

## Transmisión en vivo

En el dock, en otra terminal (puede correr junto a un recorrido):

```bash
cd ~/Workspace/farmbot/src
python3 -m transmision
```

La web del cliente la muestra en la sección "En vivo". También se puede abrir directamente:

| Ruta | Respuesta |
| --- | --- |
| `http://192.168.123.18:8080/video` | Video MJPEG |
| `http://192.168.123.18:8080/foto.jpg` | Último cuadro |
| `http://192.168.123.18:8080/estado` | FPS y si hay video, en JSON |

## Pendiente

- Modelo de detección en `deteccion/detector.py`: `detectar()` devuelve por ahora una lista vacía, así que no se registra nada.
- Movimiento del robot por las hileras, solo a través de un módulo de seguridad.
- Hilera y zona según la posición del robot.
- Evitar registrar varias veces el mismo hallazgo en cuadros seguidos.
