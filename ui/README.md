# ui

Web del cliente: recibe los registros que envía el robot durante un recorrido (maleza, frutos) y permite consultarlos.

## Estructura

| Ruta | Contenido |
| --- | --- |
| `api/` | API en Flask: recibe los registros del robot, los guarda y los entrega a la web |
| `api/almacenamiento.py` | Registros en SQLite y fotos en una carpeta |
| `web/` | Web en React + TypeScript (Vite) |
| `datos/` | Base de datos y fotos; se crea al iniciar la API y no se sube al repositorio |

Flujo: robot → `POST /api/registros` → `api/` → SQLite y fotos → `GET /api/registros` → `web/`.

## Desarrollo

API (Python 3.8 o superior):

```bash
cd ui/api
pip install -r requirements.txt
python3 app.py
```

Web, en otra terminal (Node 20 o superior):

```bash
cd ui/web
npm install
npm run dev
```

Abrir `http://localhost:5173`. Vite redirige `/api` y `/fotos` a la API en el puerto 5000.

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

El robot envía los registros a la dirección definida en `UI_URL` de `src/config.py` o en la variable `SABUESO_UI_URL`.

| Variable | Valor por defecto |
| --- | --- |
| `SABUESO_UI_DATOS` | `ui/datos` |
| `SABUESO_UI_HOST` | `0.0.0.0` |
| `SABUESO_UI_PUERTO` | `5000` |

## API

| Método y ruta | Uso |
| --- | --- |
| `POST /api/registros` | El robot envía un registro en JSON |
| `GET /api/registros` | Lista de registros en JSON, del más reciente al más antiguo |
| `GET /fotos/<nombre>` | Foto de un registro |

Registro que envía el robot:

```json
{
  "id": "3f2a…",
  "recorrido": "20261030-153000",
  "fecha": "2026-10-30T15:31:02",
  "clase": "maleza",
  "confianza": 0.91,
  "caja": [120, 340, 260, 470],
  "hilera": "3",
  "zona": null,
  "foto_jpeg": "<JPEG en base64>"
}
```

`hilera` y `zona` pueden venir vacías; la web las muestra como "sin hilera" o "sin zona". Si el robot reenvía un registro desde su cola local, el `id` evita duplicarlo.

Pendiente: mapa de zonas, ficha de zona e historial, según `documentacion/fases/`.
