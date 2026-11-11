# ui

Web del cliente: inicia y detiene el recorrido del robot, recibe sus capturas (foto con detecciones de frutos, maleza y follaje) y permite consultarlas en un mapa de hileras y zonas, una ficha por zona y un historial.

La interfaz sigue el estilo de Centinela (la plataforma del dron), para que las dos se vean como una misma familia.

## Estructura

| Ruta | Contenido |
| --- | --- |
| `api/app.py` | API en Flask: rutas para el robot y para la web; sirve la web compilada |
| `api/almacenamiento.py` | Modelo de datos en SQLite (sector, hileras, zonas, recorridos, capturas, detecciones, clases, modelos, incidencias) y fotos en una carpeta |
| `api/control.py` | Inicia y detiene `python3 -m recorrido` (src/) desde la web |
| `api/estructura.json` | Sector, cantidad de hileras y zonas por hilera del invernadero |
| `api/test_api.py` | Pruebas de la API |
| `web/` | Web en React + TypeScript (Vite) |
| `datos/` | Base de datos, fotos y salida del recorrido; se crea al iniciar la API y no se sube al repositorio |

La web está dividida en módulos:

| Ruta en `web/src/` | Contenido |
| --- | --- |
| `api/` | Cliente HTTP y tipos de las respuestas |
| `hooks/` | `useConsulta` (consultas con actualización periódica) y `useRuta` (navegación por `#/seccion/id`) |
| `componentes/` | Piezas reutilizables: barra lateral, tarjeta, insignia de estado, indicador, foto con detecciones, selector de recorrido |
| `paginas/` | Una carpeta por sección: `Inicio`, `Zonas` (mapa, ficha e historial de zona), `Recorrido` (en vivo e iniciar/detener) y `Historial` (gráfico y tabla de recorridos) |
| `utilidades/` | Estados de zona y recorrido con su texto y color; formato de fechas |
| `estilos/` | Tokens (colores, tipografía, espacios) y estilos compartidos |

Flujo: web → `POST /api/recorridos` → `api/` lanza el recorrido en `src/` → el robot envía `POST /api/capturas` → SQLite y fotos → `GET /api/mapa`, `/api/zonas/<id>` → web.

## Estado de una zona

Para el recorrido elegido gana la primera regla que se cumple:

1. Sin capturas en la zona: **Sin datos**.
2. Alguna captura con análisis pendiente: **Análisis pendiente**.
3. Detecciones del grupo maleza: **Revisar maleza**.
4. Detecciones del grupo follaje: **Revisar follaje**.
5. Lo demás (solo frutos o nada): **Sin alertas registradas**.

El robot envía una captura cada `CAPTURA_ZONA_S` segundos aunque no detecte nada, para que una zona observada no aparezca como "Sin datos".

## Desarrollo

API (Python 3.8 o superior):

```bash
cd ui/api
pip install -r requirements.txt
python3 app.py
python3 -m unittest      # pruebas
```

Web, en otra terminal (Node 20 o superior):

```bash
cd ui/web
npm install
npm run dev
```

Abrir `http://localhost:5173`. Vite redirige `/api` y `/fotos` a la API en el puerto 5000.

La sección "Recorrido" muestra la transmisión del robot (`python3 -m transmision` en el dock). Por defecto la busca en el puerto 8080 del mismo equipo que sirve la web; si el robot está en otro equipo, definir su dirección al compilar o en desarrollo:

```bash
VITE_CAMARA_URL=http://192.168.123.18:8080 npm run dev
```

"Iniciar recorrido" lanza `python3 -m recorrido` en `src/` del mismo equipo que corre la API. Fuera del robot el proceso termina enseguida porque no hay cámara, y el recorrido queda como incompleto.

## Producción local

```bash
cd ui/web && npm run build
cd ../api && python3 app.py
```

La API sirve la web compilada (`web/dist`) en `http://<equipo>:5000`.

En el robot, `scripts/subir_al_robot.sh` compila la web y copia `api/` y `web/dist/` a `~/Workspace/farmbot/ui`, sin tocar `ui/datos`. Ahí se ejecuta con el entorno que tiene Flask:

```bash
cd ~/Workspace/farmbot/ui/api
../../.venv/bin/python app.py
```

El recorrido se lanza con el `python3` del sistema, que tiene OpenCV con GStreamer.

| Variable | Valor por defecto |
| --- | --- |
| `SABUESO_UI_DATOS` | `ui/datos` |
| `SABUESO_UI_HOST` | `0.0.0.0` |
| `SABUESO_UI_PUERTO` | `5000` |
| `SABUESO_SRC` | `src/` del repositorio |
| `SABUESO_PYTHON_ROBOT` | `python3` |
| `SABUESO_ESTRUCTURA` | `api/estructura.json` |

## API

| Método y ruta | Uso |
| --- | --- |
| `POST /api/capturas` | El robot envía una captura con sus detecciones (también acepta `/api/registros`, formato anterior) |
| `POST /api/recorridos/<id>/fin` | El robot avisa que terminó: `{"estado": "completado"}` o `"incompleto"` |
| `POST /api/recorridos/<id>/incidencias` | Registra una incidencia: `{"tipo": "comunicacion", "detalle": "…"}` |
| `POST /api/recorridos` | La web inicia un recorrido: `{"hilera": 2, "zona": 3}` (ambos opcionales) |
| `GET /api/recorridos/actual` | Si hay un recorrido corriendo y las últimas líneas de su salida |
| `POST /api/recorridos/actual/detener` | Detiene el recorrido |
| `GET /api/recorridos` | Recorridos con sus totales y zonas por revisar (`zonas_maleza`, `zonas_follaje`), del más reciente al más antiguo |
| `GET /api/estructura` | Sector, hileras, zonas y catálogo de clases |
| `GET /api/mapa?recorrido=<id>` | Estado y conteos de cada zona; sin `recorrido`, el último |
| `GET /api/zonas/<id>?recorrido=<id>` | Ficha de la zona con sus capturas y detecciones |
| `GET /api/zonas/<id>/historial` | La zona en cada recorrido |
| `GET /api/capturas?recorrido=<id>&hallazgos=1&limite=50` | Capturas recientes |
| `GET /fotos/<nombre>` | Foto de una captura |

Captura que envía el robot:

```json
{
  "id": "3f2a…",
  "recorrido": "20261104-153000",
  "fecha": "2026-11-04T15:31:02",
  "hilera": "2",
  "zona": "3",
  "modelo": {"nombre": "sin_modelo", "version": "0"},
  "detecciones": [
    {"clase": "maleza", "confianza": 0.91, "caja": [120, 340, 260, 470]}
  ],
  "foto_jpeg": "<JPEG en base64, sin cajas dibujadas>"
}
```

`detecciones` puede venir vacía (zona observada sin hallazgos). Si `hilera` o `zona` no corresponden a una zona de `estructura.json`, la captura queda "sin zona" para revisión. Si el robot reenvía una captura desde su cola local, el `id` evita duplicarla.

Clases: `tomate_verde`, `tomate_maduro` (grupo fruto), `maleza`, `follaje_mancha`, `follaje_decoloracion`, `follaje_marchitez` (grupo follaje). Una clase desconocida se guarda en el grupo "otro".
